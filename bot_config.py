import yaml

import os
import logging
from datetime import datetime
from src.analyzer import PriceAnalyzer
from src.dispatcher import Dispatcher
from src.trader import Trader
from utils import (
    get_unix_timestamp,
    determine_analysis_start_time,
    parse_date
)

from bot import (
    MONGO_URL,
    DB_NAME,
    OUTPUT_DIRECTORY,
    VisualizationManager
)


def load_config(file_path="config.yaml"):
    if os.path.exists(file_path):
        with open(file_path, "r") as config_file:
            return yaml.safe_load(config_file)
    else:
        return {}

def process_coin(config, visualization_manager):
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
        analysis_end_time = get_unix_timestamp(parse_date(config.get('analysis_end_time'))) if config.get('analysis_end_time') else get_unix_timestamp(datetime.now())
        if not config.get('analysis_start_time'):
            # find start time for analysis
            analysis_start_time = determine_analysis_start_time(analysis_end_time,  config.get('time_window'), config.get('coin_symbol'))
        else:
            analysis_start_time = get_unix_timestamp(datetime.strptime(config.get('analysis_start_time'), '%Y-%m-%d'))

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
