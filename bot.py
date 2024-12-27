import os
import argparse
import time
import json
from datetime import datetime
from draw_graph import create_graph
from trader import Trader
from utils import (
    get_unix_timestamp,
    determine_analysis_start_time,
    convert_unix_to_date_only_str,
    get_next_file_number,
    log_high_kline,
    log_low_kline,
    log_middle_kline,
    parse_date,
    serialize_object, log_sideway,
)


TIME_STEP = 1 * 60 * 1000  # one minute in unix
MONGO_URL = "mongodb://localhost:27017/"
DB_NAME = "crypto_data"
DEVIATION = 0.05
OUTPUT_DIRECTORY = "analyzed_data"


def prepare_kline_plot_data(kline):
    kline = {  # save only data needed for plotting
            "status": "",
            "time": kline["closeTime"],  # save the closeTime as x coordinate to show the kline
            "price": kline["close"] # save close price as y coordinate
        }
    return kline


def get_min_price(
    klines, start_index, last_index
):  # optimization of the search for the minimum value
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

    def reset_klines(self):
        self.high_kline = None
        self.low_kline = None
        self.mid_kline = None

    def is_new_high_kline(self, kline, min_price):
        kline_is_higher_than_existing = self.high_kline and not self.low_kline and self._is_highest_kline(kline)
        if kline_is_higher_than_existing:
            return True

        current_kline_growth_percent = ((kline["high"] - min_price) / min_price) * 100
        new_impulse_is_higher_than_previous = (
                current_kline_growth_percent >= self.target_price_growth_percent and self._is_highest_kline(kline)
        )
        if new_impulse_is_higher_than_previous:
            kline["target_price_growth_percent"] = current_kline_growth_percent
            return True

        return False

    def is_new_low_kline(self, kline):
        if self.high_kline:
            calculated_target_price_drop_percent = (
                (self.high_kline["high"] - kline["low"]) / self.high_kline["high"]
            ) * 100
            kline["target_price_drop_percent"] = calculated_target_price_drop_percent

            return calculated_target_price_drop_percent >= self.target_price_drop_percent and self._is_lowest_kline(kline)

    def is_new_middle_kline(self, kline):
        return (self.high_kline and self.low_kline) and kline["high"] >= self.mid_price

    def _analyze_kline(self, kline, min_price):
        analyzed_kline = {  # save only data needed for plotting
            "status": "",  # one of: low, high, mid or none
            "time": kline[
                "closeTime"
            ],  # save the closeTime as x coordinate to show the kline
        }

        if self.is_new_high_kline(kline, min_price):
            analyzed_kline["status"] = "high"
            analyzed_kline["price"] = kline["high"] # save the high price as y coordinate to show the kline
            self.high_kline = kline
            log_high_kline(kline)
            return analyzed_kline

        if self.is_new_low_kline(kline):
            self.low_kline = kline
            analyzed_kline["status"] = "low"
            analyzed_kline["price"] = kline["low"]
            self.mid_price = self.calculate_middle_price()
            log_low_kline(kline)
            return analyzed_kline

        if self.is_new_middle_kline(kline):
            analyzed_kline["status"] = "mid"
            analyzed_kline["price"] = kline["high"]
            self.mid_kline = kline
            log_middle_kline(kline)
            log_sideway(self.high_kline, self.low_kline, self.mid_kline, self.mid_price)
            return analyzed_kline

        analyzed_kline["price"] = kline["close"]
        return analyzed_kline

    def _analyze_snapshot(self, klines, snapshot_end):
        snapshot_start = snapshot_end - self.snapshot_klines_count
        min_price = get_min_price(klines, snapshot_start, snapshot_end)
        return self._analyze_kline(klines[snapshot_end], min_price)


class Dispatcher:
    def __init__(self, analyzer, trader, kline_manager):
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
            self.analysis_end_time,
        )
        analyzed_klines = []
        orders = []

        # Process klines using a generator
        for index in range(self.analyzer.snapshot_klines_count, len(klines)):
            current_kline = klines[index]

            # the analyzer does not work while the trader is working
            if self.trader.has_active_sideway():
                self.trader.update_orders(current_kline)
                kline = prepare_kline_plot_data(current_kline)
                analyzed_klines.append(kline)
                continue

            analyzed_kline = self.analyzer._analyze_snapshot(klines, index)
            if analyzed_kline["status"] == "mid":
                # Start a new sideway period
                subway_orders = self.trader.add_subway(
                    self.analyzer.high_kline["high"],
                    self.analyzer.low_kline["low"]
                )
                orders.extend(subway_orders)
                self.analyzer.reset_klines()

            analyzed_klines.append(analyzed_kline)
        self.summarize_trader_results()
        return analyzed_klines, orders

    def summarize_trader_results(self):
        self.trader.log_order_summary()

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
            if self.trader.has_active_sideway():
                self.trader.update_orders(klines[-1])
                continue

            analyzed_kline = self.analyzer._analyze_snapshot(klines, len(klines) - 1)
            if analyzed_kline["status"] == "mid":
                self.trader.new_orders_in_sideway = True
                self.trader.place_short_order(
                    self.analyzer.high_kline["high"],
                    self.analyzer.low_kline["low"],
                    self.analyzer.mid_kline["high"],
                )
                self.trader.place_long_order(
                    self.analyzer.high_kline["high"],
                    self.analyzer.low_kline["low"],
                    self.analyzer.mid_kline["high"],
                )
                # reset high and low points after finding the middle
                self.analyzer.reset_klines()

            time.sleep(60)


class VisualizationManager:
    def __init__(self, output_directory):
        self.output_directory = output_directory
        if not os.path.exists(self.output_directory):
            os.makedirs(self.output_directory)

    def generate_output_file_path(self, file_prefix, symbol, start_time, end_time, file_format=".json"):
        str_start_time = convert_unix_to_date_only_str(start_time)
        str_end_time = convert_unix_to_date_only_str(end_time)
        file_number = get_next_file_number(directory=self.output_directory, format=file_format)
        return f"{self.output_directory}/{file_number}_{file_prefix}_{symbol}_{str_start_time}_{str_end_time}{file_format}"

    def save_to_json_file(self, data, file_path):
        with open(file_path, "w") as file:
            json.dump(data, file, default=serialize_object, indent=4)

    def visualize_data(self, file_path):
        create_graph(file_path)

    def save_and_visualize(self, analyzed_klines, orders, file_prefix, symbol, start_time, end_time, draw_graph=False):
        """
        Save the results to a file, and optionally visualize the data.
        """
        output_file = self.generate_output_file_path(
            file_prefix=file_prefix,
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
        )

        self.save_to_json_file({"klines": analyzed_klines, "orders": orders}, output_file)

        if draw_graph:
            self.visualize_data(output_file)


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
            # find start time for analysis
            analysis_start_time = determine_analysis_start_time(analysis_end_time,  args.time_window, args.coin_symbol)
        else:
            analysis_start_time = get_unix_timestamp(args.analysis_start_time)

        dispatcher.set_time_interval(analysis_start_time, analysis_end_time)

        analyzed_klines, orders = dispatcher.run_for_historical_data()

        visualization_manager = VisualizationManager(OUTPUT_DIRECTORY)
        visualization_manager.save_and_visualize(
            analyzed_klines=analyzed_klines,
            orders=orders,
            file_prefix="analyzed_data",
            symbol=args.coin_symbol,
            start_time=analysis_start_time,
            end_time=analysis_end_time,
            draw_graph=args.draw_graph
        )


if __name__ == "__main__":
    main()
