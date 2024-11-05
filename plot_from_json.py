import json
import argparse
from graphic import Graphic


def plot_klines_from_json(json_file):
    graphic = Graphic()
    # Load data from the JSON file
    with open(json_file, "r") as file:
        all_points = json.load(file)
        graphic.create_plot_for_historical_data(all_points)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot kline data from JSON file.")
    parser.add_argument("json_file", type=str, help="Path to JSON file with kline data")
    args = parser.parse_args()

    plot_klines_from_json(args.json_file)
