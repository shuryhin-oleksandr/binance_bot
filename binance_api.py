import requests
from utils import convert_unix_to_str, logger

BINANCE_API_URL = "https://api.binance.com/api/v3/klines"
INTERVAL = "1m"
LIMIT = 1000


def get_klines(start_time, end_time, symbol):
    """Get candlestick data from Binance API."""
    params = {
        "symbol": symbol,
        "interval": INTERVAL,
        "startTime": start_time,
        "endTime": end_time,
        "limit": LIMIT,
    }
    response = requests.get(BINANCE_API_URL, params=params)
    klines = response.json()

    if not klines:
        logger.error(
            f"No data found in binance on the interval: {convert_unix_to_str(start_time)} - {convert_unix_to_str(end_time)}"
        )

    if "msg" in klines:
        raise Exception(klines)

    return klines
