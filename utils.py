import logging
from datetime import datetime


def get_unix_timestamp(date_str):
    return int(datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").timestamp() * 1000)


def convert_unix_to_str(unix_timestamp):
    return datetime.fromtimestamp(unix_timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")


def log_kline(kline):
    logging.info(
        f"Start time: {convert_unix_to_str(kline['startTime'])}, Closing Time: {convert_unix_to_str(kline['closeTime'])}, "
        f"Price: {kline['close']}"
    )


def log_middle_kline(kline):
    logging.info("Middle kline:")
    log_kline(kline)


def log_high_kline(kline):
    logging.info(
        f"High kline: (the price increased by {kline['target_price_growth_percent']}% from its peak.)"
    )
    log_kline(kline)


def log_low_kline(kline):
    logging.info(
        f"Low kline: (the price has dropped by {kline['target_price_drop_percent']}%)"
    )
    log_kline(kline)
