import os
import logging
from datetime import datetime

LOG_DIRECTORY = "logs"

def get_next_file_number(directory=".", format=".json"):
    files = [file for file in os.listdir(directory) if file.endswith(format)]

    # Extract the number at the beginning of each file, if it exists
    numbers = []
    for file in files:
        try:
            number = int(file.split('_')[0])
            numbers.append(number)
        except ValueError:
            pass

    next_number = max(numbers, default=0) + 1
    return f"{next_number:04d}"  # Format as four-digit number


# Configure the logging level and format
logger = logging.getLogger("root")
logger.setLevel(logging.INFO)
log_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

# File Handler
if not os.path.exists(LOG_DIRECTORY):
    os.makedirs(LOG_DIRECTORY)

file_number = get_next_file_number(directory=LOG_DIRECTORY, format=".log")
file_handler = logging.FileHandler(f"{LOG_DIRECTORY}/{file_number}_processed_klines.log", "w")
file_handler.setFormatter(log_formatter)

# Stream Handler
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(log_formatter)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(stream_handler)


def parse_date(date_str):
    try:
        # Try parsing date and time
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        # If time is missing, set it to "00:00:00" by default
        return datetime.strptime(date_str, "%Y-%m-%d")


def determine_analysis_start_time(analysis_end_time, time_window, coin):
    from binance_api import get_klines

    binance_foundation_date = get_unix_timestamp(datetime.strptime("2017-07-01", "%Y-%m-%d"))
    klines = get_klines(binance_foundation_date, analysis_end_time, coin)
    return int(klines[0][0]) + time_window * 60 * 60 * 1000


def serialize_object(obj):
    return obj.__dict__  if hasattr(obj, "__dict__") else str(obj)


def get_unix_timestamp(date):
    return int(date.timestamp() * 1000)


def convert_unix_full_date_str(unix_timestamp):
    return datetime.fromtimestamp(unix_timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")

def convert_unix_to_date_only_str(unix_timestamp):
    return datetime.fromtimestamp(unix_timestamp / 1000).strftime("%Y-%m-%d")


def get_kline_time(kline):
    return f"Start time: {convert_unix_full_date_str(kline['startTime'])}, Closing Time: {convert_unix_full_date_str(kline['closeTime'])}"


def log_middle_kline(kline):
    logger.debug(f"Middle kline: {get_kline_time(kline)}, High price: {kline['high']}")


def log_high_kline(kline):
    if 'target_price_growth_percent' in kline is not None:
        logger.debug(
            f"New impulse. High kline: (the price increased by {kline['target_price_growth_percent']}%) {get_kline_time(kline)}, High price: {kline['high']}"
        )
    else:
        logger.debug(
            f"High kline: {get_kline_time(kline)}, High price: {kline['high']}"
        )


def log_low_kline(kline):
    logger.debug(
        f"Low kline: (the price has dropped by {kline['target_price_drop_percent']}%) {get_kline_time(kline)}, Low price: {kline['low']}"
    )


def log_sideway(high_kline, low_kline, mid_price):
    logger.info(f"Sideway, High price: {high_kline['high']}, Low price: {low_kline['low']}, Mid price: {mid_price}")
