import os
import argparse
import json
import time
from datetime import datetime
from binance_api import get_klines
from draw_graph import create_graph
from utils import (
    get_unix_timestamp,
    convert_unix_to_date_only_str,
    get_next_file_number,
    log_high_kline,
    log_low_kline,
    log_middle_kline,
    parse_date,
)

TIME_STEP = 1 * 60 * 1000  # one minute in unix
MONGO_URL = "mongodb://localhost:27017/"
DB_NAME = "crypto_data"
DEVIATION = 0.05
JSON_DIRECTORY = "processed_klines"


def get_min_price(klines, start_index, last_index):  # optimization of the search for the minimum value
    min_price = klines[start_index]["low"]
    for i in range(start_index + 1, last_index):
        if klines[i]["low"] < min_price:
            min_price = klines[i]["low"]
    return min_price


class PriceAnalyzer:
    def __init__(
        self,
        kline_manager,
        time_window,
        target_price_growth_percent,
        target_price_drop_percent,
    ):
        self.kline_manager = kline_manager
        self.time_window = time_window * 60 * 60 * 1000  # Convert hours to milliseconds
        self.target_price_growth_percent = target_price_growth_percent
        self.target_price_drop_percent = target_price_drop_percent
        self.high_kline = None
        self.mid_kline = None
        self.low_kline = None
        self.mid_price = None
        self.snapshot_klines_count = int(self.time_window / TIME_STEP)

    def _is_highest_kline(self, kline):
        return self.high_kline is None or (self.high_kline["high"] < kline["high"])

    def _is_lowest_kline(self, kline):
        return self.low_kline is None or self.low_kline["low"] > kline["low"]

    def calculate_middle_price(self):
        sideway_height = self.high_kline["high"] / self.low_kline["low"] - 1
        return self.low_kline["low"] * (1 + sideway_height * (0.5 - DEVIATION))

    def _analyze_kline(self, kline, min_price):
        high_price = kline["high"]
        processed_kline = {  # save only data needed for plotting
            "status": "",  # one of: low, high, mid or none
            "time": kline["closeTime"],  # save the closeTime as x coordinate to show the kline
        }
        high_found = False

        # if kline higher than the existing high kline
        if self.high_kline and not self.low_kline and self._is_highest_kline(kline):
            high_found = True
        else:
            calculated_target_price_growth_percent = ((high_price - min_price) / min_price) * 100
            # if the new impulse is higher than the previous one
            if calculated_target_price_growth_percent >= self.target_price_growth_percent and self._is_highest_kline(kline):
                kline["target_price_growth_percent"] = calculated_target_price_growth_percent
                high_found = True

        if high_found:
            processed_kline["status"] = "high"
            processed_kline["price"] = kline["high"] # save the high price as y coordinate to show the kline
            self.high_kline = kline
            log_high_kline(kline)
            return processed_kline

        # TODO: Add phase property, which can be one of: idle, high_found, low_found, mid_found
        low_price = kline["low"]
        if self.high_kline:
            calculated_target_price_drop_percent = (
                (self.high_kline["high"] - low_price) / self.high_kline["high"]
            ) * 100
            kline["target_price_drop_percent"] = calculated_target_price_drop_percent
            if (
                calculated_target_price_drop_percent >= self.target_price_drop_percent
                and self._is_lowest_kline(kline)
            ):
                self.low_kline = kline
                processed_kline["status"] = "low"
                processed_kline["price"] = kline["low"]
                self.mid_price = self.calculate_middle_price()
                self.mid_kline = None
                log_low_kline(kline)
                return processed_kline

        if (self.high_kline and self.low_kline) and not self.mid_kline and high_price >= self.mid_price:
            processed_kline["status"] = "mid"
            processed_kline["price"] = kline["high"]
            self.mid_kline = kline
            self.high_kline = None
            self.low_kline = None
            log_middle_kline(kline)
            return processed_kline

        processed_kline["price"] = kline["close"]
        return processed_kline

    def _analyze_snapshot(self, klines, snapshot_end):
        snapshot_start = snapshot_end - self.snapshot_klines_count
        min_price = get_min_price(klines, snapshot_start, snapshot_end)
        return self._analyze_kline(klines[snapshot_end], min_price)


class RealTimePriceAnalyzer(PriceAnalyzer):

    def monitoring(self):
        while True:
            current_time = int(datetime.now().timestamp() * 1000)
            start_time = (
                current_time - self.time_window
            )  # get data starting from now - Yhr
            klines = self.kline_manager.find_or_fetch_klines_in_range(
                start_time, current_time
            )
            processed_klines = self._analyze_snapshot(klines)
            if self.graphic:
                self.graphic.update_plot_real_time(processed_klines[-1])

            time.sleep(60)


class HistoricalPriceAnalyzer(PriceAnalyzer):
    def __init__(
        self,
        kline_manager,
        time_window,
        target_price_growth_percent,
        target_price_drop_percent,
        analysis_start_time,
        analysis_end_time,
    ):
        super().__init__(
            kline_manager,
            time_window,
            target_price_growth_percent,
            target_price_drop_percent,
        )
        self.analysis_start_time = analysis_start_time
        self.analysis_end_time = analysis_end_time
        str_start_time = convert_unix_to_date_only_str(self.analysis_start_time)
        str_end_time = convert_unix_to_date_only_str(self.analysis_end_time)

        if not os.path.exists(JSON_DIRECTORY):
            os.makedirs(JSON_DIRECTORY)

        file_number = get_next_file_number(directory=JSON_DIRECTORY, format=".json")
        self.output_file = f"{JSON_DIRECTORY}/{file_number}_processed_klines_{kline_manager.symbol}_{str_start_time}_{str_end_time}.json"

    def analyze(self, klines):
        """
        - A generator to yield processed klines one at a time.
        - The start of the analysis = to the size of the snapshot
        """
        for current_kline_index in range(self.snapshot_klines_count, len(klines)):
            analyzed_kline = self._analyze_snapshot(klines, current_kline_index)
            yield analyzed_kline

    def run(self):
        """
        Fetch and analyze all klines within the specified analysis time range in one step.
        """
        all_klines = self.kline_manager.find_or_fetch_klines_in_range(
            self.analysis_start_time - self.time_window,
            self.analysis_end_time
        )

        analyzed_klines = list(self.analyze(all_klines))

        with open(self.output_file, "w") as file:
            json.dump(analyzed_klines, file)


def main():
    parser = argparse.ArgumentParser(
        description="Check if a coin price has increased by a certain percentage within a time period."
    )
    parser.add_argument(
        "--coin-symbol", type=str, default="BTCUSDT", help="Coin symbol"
    )
    parser.add_argument(
        "--growth-percent",
        type=float,
        default=30,
        help="Percentage rised threshold (X%%)",
    )
    parser.add_argument(
        "--drop-percent", type=float, default=10, help="Percentage drop threshold (Y%%)"
    )
    parser.add_argument(
        "--time-window",
        type=int,
        default=24,
        help="Time window in hours to check the price increase (Yhr)",
    )
    parser.add_argument(
        "--analysis-start-time",
        type=parse_date,
        help="Start time in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD",
    )
    parser.add_argument(
        "--analysis-end-time",
        type=parse_date,
        default=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        help="End time in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD",
    )
    parser.add_argument("--real-time", action="store_true", help="Real time monitoring")
    parser.add_argument("--draw-graph", action="store_true", help="Draw graph")

    args = parser.parse_args()

    from manager import KlineManager

    kline_manager = KlineManager(MONGO_URL, DB_NAME, args.coin_symbol)

    if args.real_time:
        monitoring = RealTimePriceAnalyzer(
            kline_manager,
            args.time_window,
            args.growth_percent,
            args.drop_percent,
            args.draw_graph,
        )
        monitoring.monitoring()
    else:
        analysis_end_time = get_unix_timestamp(args.analysis_end_time)
        if not args.analysis_start_time:
            binance_foundation_date = get_unix_timestamp(datetime.strptime("2017-07-01", "%Y-%m-%d"))
            # get kline to to check the date of the first kline in binance
            klines = get_klines(binance_foundation_date, analysis_end_time, args.coin_symbol)
            # find start time for analysis
            analysis_start_time = int(klines[0][0]) + args.time_window * 60 * 60 * 1000
        else:
            analysis_start_time = get_unix_timestamp(args.analysis_start_time)

        analyzer = HistoricalPriceAnalyzer(
            kline_manager,
            args.time_window,
            args.growth_percent,
            args.drop_percent,
            analysis_start_time,
            analysis_end_time,
        )

        analyzer.run()
        if args.draw_graph:
            create_graph(analyzer.output_file)


if __name__ == "__main__":
    main()
