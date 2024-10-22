import requests

BINANCE_API_URL = 'https://api.binance.com/api/v3/klines'
SYMBOL = 'BTCUSDT'
INTERVAL = "1m"
LIMIT = 1000

def get_all_klines(start_time, end_time):
    """Get all candlestick data for a year by requesting in chunks of 1000."""
    all_klines = []
    current_time = start_time

    while current_time < end_time:

        klines = get_klines(current_time, end_time)
        
        if not klines:
            break
        
        all_klines.extend(klines)
        current_time = klines[-1][6] + 1

    return all_klines


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
            raise Exception("Klines data is empty.")
        
    if "msg" in klines:
        raise Exception(klines)
    
    return klines
