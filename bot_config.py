import yaml

from datetime import datetime
import os
import logging

from binance_bot.utils import get_unix_timestamp
from bot import process_coin


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

    for coin_config in config_data.get("coins", []):
        
        logger.info(f"Processing {coin_config['coin_symbol']}...")

        coin_config['analysis_start_time'] = get_unix_timestamp(datetime.strptime(coin_config['analysis_start_time'], '%Y-%m-%d'))
        if coin_config['analysis_end_time']:
            coin_config['analysis_end_time'] = get_unix_timestamp(datetime.strptime(coin_config['analysis_end_time'], '%Y-%m-%d'))
        else:
            coin_config['analysis_end_time'] = get_unix_timestamp(datetime.now())
                    
        process_coin(coin_config)


if __name__ == "__main__":
    main()
