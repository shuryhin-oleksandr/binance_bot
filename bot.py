import requests
import argparse
import time
from graphic import initialize_plot, update_plot
from utils import get_unix_timestamp, convert_unix_to_str, show_point

BINANCE_API_URL = 'https://api.binance.com/api/v3/klines'
SYMBOL = 'BTCUSDT'
TIME_STEP = 1 * 60 * 1000 # one minute in unix

all_points = []
condition_met_points = []

def process_time_frames(args, ax, line):
    t1 = get_unix_timestamp(args.t1)
    t2 = get_unix_timestamp(args.t2)
    percent = args.percent_change
    time_window = args.time_window
    current_time = t1

    while current_time <= t2:
        check_price_increase(time_window, current_time, percent, ax, line)
        current_time += TIME_STEP


def real_time_monitoring(args, ax, line):
    percent = args.percent_change
    time_window = args.time_window

    while True:
        current_time = int(time.time() * 1000)
        check_price_increase(time_window, current_time, percent, ax,line)
        time.sleep(60)


def get_klines(start_time, end_time):
    """Get candlestick data from Binance API."""
    params = {
        'symbol': SYMBOL,
        'interval': "1m",
        'startTime': start_time,
        'endTime': end_time
    }
    response = requests.get(BINANCE_API_URL, params=params)
    return response.json()


def check_price_increase(time_window, end_time, percent_change, ax, line):
    start_time = end_time - time_window * 60 * 60 * 1000
    # interval = str(time_window) + 'h'
    
    klines = get_klines(start_time, end_time)
    
    if not klines:
        raise Exception("Klines data is empty.")
    
    if "msg" in klines:
        raise Exception(klines)
    min_price = min(float(kline[3]) for kline in klines)
    closing_price = float(klines[-1][4])
    closing_time = (klines[-1][6])
    open_time = klines[-1][0]

    res_change_percent = ((closing_price - min_price) / min_price) * 100
    
    
    # Check if price change exceeds the threshold
    point = {
            "start_time": convert_unix_to_str(start_time),
            "end_time": convert_unix_to_str(end_time),
            "closing_time": convert_unix_to_str(closing_time),
            "open_time": convert_unix_to_str(open_time),
            "min_price": min_price,
            "price": closing_price,
            "percent": res_change_percent
        }
    all_points.append(point) 
    if res_change_percent >= percent_change:
        condition_met_points.append(point)
        show_point(point)
    update_plot(ax, line, all_points, condition_met_points)


def main():
    parser = argparse.ArgumentParser(description="Check if a coin price has increased by a certain percentage within a time period.")
    
    parser.add_argument('percent_change', type=float, help='Percentage change threshold (X%)')
    parser.add_argument('time_window', type=int, help='Time window in hours to check the price increase (Yhr)')
    parser.add_argument('--t1', type=str, help='Start time in format YYYY-MM-DD HH:MM:SS')
    parser.add_argument('--t2', type=str, help='End time in format YYYY-MM-DD HH:MM:SS')
    parser.add_argument('--real_time', action='store_true', help='Real times')
    args = parser.parse_args()
    fig, ax, line = initialize_plot()
    
    if args.real_time:
        real_time_monitoring(args, ax, line)
    else:
        if not args.t1 or not args.t2:
            raise ValueError("Set t1 t2 interval.")
        process_time_frames(args, ax, line)


if __name__ == '__main__':
    main()
