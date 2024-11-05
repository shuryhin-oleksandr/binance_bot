from datetime import datetime
import logging


# Configure the logging level and format
logger = logging.getLogger("root")
logger.setLevel(logging.INFO)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', 
                                  datefmt='%Y-%m-%d %H:%M:%S')

# File Handler
file_handler = logging.FileHandler("kline_log.log", "w")
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

def get_unix_timestamp(date):
    return int(date.timestamp() * 1000)


def convert_unix_to_str(unix_timestamp):
    return datetime.fromtimestamp(unix_timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")


def get_kline_time(kline):
    return (
        f"Start time: {convert_unix_to_str(kline['startTime'])}, Closing Time: {convert_unix_to_str(kline['closeTime'])}"
    )


def log_middle_kline(kline):
    logger.info(f"Middle kline: {get_kline_time(kline)}, High price: {kline['high']}")


def log_high_kline(kline):
    logger.info(
        f"High kline: (the price increased by {kline['target_price_growth_percent']}%) {get_kline_time(kline)}, High price: {kline['high']}"
    )


def log_low_kline(kline):
    logger.info(
        f"Low kline: (the price has dropped by {kline['target_price_drop_percent']}%) {get_kline_time(kline)}, High price: {kline['high']}"
    )
