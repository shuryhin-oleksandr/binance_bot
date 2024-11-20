import os
import argparse
import json
import time
from datetime import datetime
from binance_api import get_klines
from draw_graph import create_graph
from trader import Trader, Trade
from utils import (
    get_unix_timestamp,
    convert_unix_to_date_only_str,
    get_next_file_number,
    log_high_kline,
    log_low_kline,
    log_middle_kline,
    parse_date,
)
import json

def serialize_trade(trade):
    if isinstance(trade, Trade):
        return trade.__dict__  # Повертає атрибути об'єкта у вигляді словника
    raise TypeError(f"Object of type {type(trade).__name__} is not JSON serializable")


TIME_STEP = 1 * 60 * 1000  # one minute in unix
MONGO_URL = "mongodb://localhost:27017/"
DB_NAME = "crypto_data"
DEVIATION = 0.05
JSON_DIRECTORY = "analyzed_data"


def get_min_price(klines, start_index, last_index): # optimization of the search for the minimum value
    min_price = klines[start_index]["low"]
    for j in range(start_index + 1, last_index):
        if klines[j]["low"] < min_price:
            min_price = klines[j]["low"]
    return min_price


class PriceAnalyzer:
    def __init__(
        self,
        time_window,
        target_price_growth_percent,
        target_price_drop_percent,
    ):
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
    
    def reset_points(self):
        self.high_kline = None
        self.low_kline = None

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
            log_middle_kline(kline)
            return processed_kline

        processed_kline["price"] = kline["close"]
        return processed_kline

    def _analyze_snapshot(self, klines, snapshot_end):
        snapshot_start = snapshot_end - self.snapshot_klines_count
        min_price = get_min_price(klines, snapshot_start, snapshot_end)
        return self._analyze_kline(klines[snapshot_end], min_price)


class Dispatcher():
    def __init__(
        self,
        analyzer,
        trader,
        kline_manager,
    ):
        self.analyzer = analyzer
        self.trader = trader
        self.kline_manager = kline_manager
    
    def set_time_interval(self, analysis_start_time, analysis_end_time):
        self.analysis_start_time = analysis_start_time
        self.analysis_end_time = analysis_end_time

    def run_for_historical_data(self):
        # Fetch all klines for the analysis period
        klines = self.kline_manager.find_or_fetch_klines_in_range(
            self.analysis_start_time - self.analyzer.time_window,  # Start time with buffer for analysis
            self.analysis_end_time                        # End time of analysis
        )
        analyzed_klines = []
        trades = []

        # Process klines using a generator
        for index in range(self.analyzer.snapshot_klines_count, len(klines)):
            current_kline = klines[index]

            # the analyzer does not work while the trader is working
            if self.trader.has_uncompleted_trade():
                self.trader.evaluate_trades(current_kline)
                continue
    
            analyzed_kline = self.analyzer._analyze_snapshot(klines, index)
            if analyzed_kline["status"] == "mid":
                trades.append(self.trader.place_short_trade(self.analyzer.high_kline["high"], self.analyzer.low_kline["low"], self.analyzer.mid_kline["high"]))
                trades.append(self.trader.place_long_trade(self.analyzer.high_kline["high"], self.analyzer.low_kline["low"], self.analyzer.mid_kline["high"]))
                
                self.analyzer.reset_points()

            analyzed_klines.append(analyzed_kline)
        return analyzed_klines, trades


    def real_time_monitoring(self):
        while True:
            current_time = int(datetime.now().timestamp() * 1000)
            start_time = (
                current_time - self.analyzer.time_window
            )  # get data starting from now - Yhr
            klines = self.kline_manager.find_or_fetch_klines_in_range(
                start_time, current_time
            )

            # the analyzer does not work while the trader is working
            if self.trader.has_uncompleted_trade():
                self.trader.evaluate_trades(klines[-1])
                continue

            analyzed_kline = self.analyzer._analyze_snapshot(klines, len(klines) - 1)
            if analyzed_kline["status"] == "mid":
                self.trader.place_short_trade(self.analyzer.high_kline["high"], self.analyzer.low_kline["low"], self.analyzer.mid_kline["high"])
                self.trader.place_long_trade(self.analyzer.high_kline["high"], self.analyzer.low_kline["low"], self.analyzer.mid_kline["high"])
                # reset high and low points after finding the middle 
                self.analyzer.reset_points()

            time.sleep(60)


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
    analyzer = PriceAnalyzer(
            args.time_window,
            args.growth_percent,
            args.drop_percent,
        )
    trader = Trader()
    dispatcher = Dispatcher(
            analyzer,
            trader,
            kline_manager,
        )

    if args.real_time:
        dispatcher.real_time_monitoring()
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

        dispatcher.set_time_interval(analysis_start_time, analysis_end_time)

        # create file
        str_start_time = convert_unix_to_date_only_str(analysis_start_time)
        str_end_time = convert_unix_to_date_only_str(analysis_end_time)

        if not os.path.exists(JSON_DIRECTORY):
            os.makedirs(JSON_DIRECTORY)

        file_number = get_next_file_number(directory=JSON_DIRECTORY, format=".json")
        output_file = f"{JSON_DIRECTORY}/{file_number}_analyzed_data_{kline_manager.symbol}_{str_start_time}_{str_end_time}.json"

        analyzed_klines, trades = dispatcher.run_for_historical_data()

        with open(output_file, "w") as file:
            json.dump({"klines": analyzed_klines, "trades": trades}, file, default=serialize_trade, indent=4)
    
        if args.draw_graph:
            create_graph(output_file)
        trader.log_trade_summary()


if __name__ == "__main__":
    main()
