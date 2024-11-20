import json
import argparse
from graphic import Graphic

def create_graph(json_file):
    graphic = Graphic()
    # Load data from the JSON file
    with open(json_file, "r") as file:
        # TODO: read a certain amount of data 
        data = json.load(file)
        klines = data.get("klines", [])
        trades = data.get("trades", [])

        graphic.create_plot_for_historical_data(klines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot kline data from JSON file.")
    parser.add_argument("json_file", type=str, help="Path to JSON file with kline data")
    args = parser.parse_args()
    
    create_graph(args.json_file)
