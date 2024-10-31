import requests
import logging
from utils import convert_unix_to_str

BINANCE_API_URL = 'https://api.binance.com/api/v3/klines'
SYMBOL = 'BTCUSDT'
INTERVAL = "1m"
LIMIT = 1000

def get_klines(start_time, end_time):
    """Get candlestick data from Binance API."""
    params = {
        'symbol': SYMBOL,
        'interval': INTERVAL,
        'startTime': start_time,
        'endTime': end_time,
        'limit': LIMIT
    }
    response = requests.get(BINANCE_API_URL, params=params)
    klines = response.json()

    if not klines:
        logging.error(f"Data not found for the interval: {convert_unix_to_str(start_time)} - {convert_unix_to_str(end_time)}")
        
    if "msg" in klines:
        raise Exception(klines)
    
    return klines
