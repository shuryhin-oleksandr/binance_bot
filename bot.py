import os
import argparse
import json
from datetime import datetime
from draw_graph import create_graph
from src.analyzer import PriceAnalyzer
from src.dispatcher import Dispatcher
from src.trader import Trader
from utils import (
    get_unix_timestamp,
    determine_analysis_start_time,
    convert_unix_to_date_only_str,
    get_next_file_number,
    parse_date,
    serialize_object, )


TIME_STEP = 1 * 60 * 1000  # one minute in unix
MONGO_URL = "mongodb://localhost:27017/"
DB_NAME = "crypto_data"
DEVIATION = 0.04
OUTPUT_DIRECTORY = "analyzed_data"


def process_coin(config):
    from src.kline_manager import KlineManager

    kline_manager = KlineManager(MONGO_URL, DB_NAME, config.get('coin_symbol'))
    analyzer = PriceAnalyzer(
        config.get('time_window'),
        config.get('growth_percent'),
        config.get('drop_percent'),
    )
    trader = Trader()
    dispatcher = Dispatcher(
        analyzer,
        trader,
        kline_manager,
    )

    if config.get('real_time'):
        dispatcher.real_time_monitoring()
    else:
        analysis_end_time = config.get('analysis_end_time')
        if not config.get('analysis_start_time'):
            # find start time for analysis
            analysis_start_time = determine_analysis_start_time(analysis_end_time,  config.get('time_window'), config.get('coin_symbol'))
        else:
            analysis_start_time = config.get('analysis_start_time')

        dispatcher.set_time_interval(analysis_start_time, analysis_end_time)

        analyzed_klines, orders = dispatcher.run_for_historical_data()

        visualization_manager = VisualizationManager(OUTPUT_DIRECTORY)
        visualization_manager.save_and_visualize(
            analyzed_klines=analyzed_klines,
            orders=orders,
            file_prefix="analyzed_data",
            symbol=config.get('coin_symbol'),
            start_time=analysis_start_time,
            end_time=analysis_end_time,
            draw_graph=config.get('draw_graph')
        )

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

    args.analysis_end_time = get_unix_timestamp(args.analysis_end_time)
    args.analysis_start_time = get_unix_timestamp(args.analysis_start_time)
    process_coin(vars(args))


if __name__ == "__main__":
    main()
