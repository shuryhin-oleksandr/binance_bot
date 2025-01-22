import yaml

import os
import logging

from bot import (
    OUTPUT_DIRECTORY,
    VisualizationManager,
    process_coin
)


def load_config(file_path="config.yaml"):
    if os.path.exists(file_path):
        with open(file_path, "r") as config_file:
            return yaml.safe_load(config_file)
    else:
        return {}

def main():
    logger = logging.getLogger("root")
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    config_data = load_config(config_path)
    visualization_manager = VisualizationManager(OUTPUT_DIRECTORY)

    for coin_config in config_data.get("coins", []):
        
        logger.info(f"Processing {coin_config['coin_symbol']}...")
        process_coin(coin_config, visualization_manager)


if __name__ == "__main__":
    main()
