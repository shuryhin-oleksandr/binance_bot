
import math
import time
import argparse
from graphic import initialize_plot, update_plot
from db import find_klines_near_close_time, get_min_price_in_range, save_klines
from utils import get_unix_timestamp, convert_unix_to_str, show_high_point, show_low_point
from binance_api import get_all_klines

TIME_STEP = 1 * 60 * 1000 # one minute in unix

high_point = None
mid_point = None
low_point = None

def is_high_point(point):
    global high_point
    if high_point["price"] < point["price"]:
        return True

def is_low_point(point):
    global low_point
    if low_point["price"] > point["price"]:
        return True


def check_price(time_window, end_time, percent_rised, percent_drop):
    global high_point, low_point, mid_point
    klines_start_time = time.time()
    kline = find_klines_near_close_time(end_time, 59000)
    klines_end_time = time.time()
    print(f"Time for find klines: {klines_end_time - klines_start_time} s")

    if not kline:
        raise Exception(f"No klines for time: {convert_unix_to_str(end_time)}")

    kline = kline[0]
    start_time = end_time - time_window * 60 * 60 * 1000
    klines_start_time = time.time()
    min_price = get_min_price_in_range(start_time, end_time) 
    klines_end_time = time.time()
    print(f"Time for find min value: {klines_end_time - klines_start_time} s")

    closing_price = kline["close"]
    closing_time = kline["closeTime"]
    open_time = kline["startTime"]

    res_percent_rised = ((closing_price - min_price) / min_price) * 100

    # Check if price change exceeds the threshold
    point = {
            "start_time": convert_unix_to_str(start_time),
            "end_time": convert_unix_to_str(end_time),
            "closing_time": convert_unix_to_str(closing_time),
            "open_time": convert_unix_to_str(open_time),
            "min_price": min_price,
            "price": closing_price,
            "percent_rised": res_percent_rised
        }

    # find high point
    if res_percent_rised >= percent_rised:
        if high_point is None or is_high_point(point):
            high_point = point
            mid_point = None
            # show_high_point(point)

    # find low point
    if high_point:
        res_percent_drop = ((high_point["price"] - closing_price) / high_point["price"]) * 100
        point["percent_drop"] = res_percent_drop
        if res_percent_drop >= percent_drop:
            if low_point is None or is_low_point(point):
                low_point = point
                mid_point = None
                # show_low_point(point)
    
    # find mid point 
    if low_point:
        if closing_price >= math.sqrt(high_point["price"] * low_point["price"]): 
            mid_point = point

    return point

def process_time_frames(args, line):
    t1 = get_unix_timestamp(args.t1)
    t2 = get_unix_timestamp(args.t2)
    current_time = t1
    time_window = args.time_window * 60 * 60 * 1000
    start_time = current_time - time_window
    klines_start_time = time.time()
    klines = get_all_klines(start_time, t2)
    klines_end_time = time.time()
    print(f"Time for getting klines: {klines_end_time - klines_start_time} s")
    save_klines(klines)

    while current_time < t2:
        point = check_price(args.time_window, current_time, args.percent_rised, args.percent_drop)
        update_plot(line, point, high_point, low_point, mid_point)
        current_time += TIME_STEP


def real_time_monitoring(args, line):
    time_window = args.time_window * 60 * 60 * 1000
    current_time = int(time.time() * 1000)
    start_time = current_time - time_window
    klines = get_all_klines(start_time, current_time)
    save_klines(klines)

    while True:
        point = check_price(args.time_window, current_time, args.percent_rised, args.percent_drop)
        update_plot(line, point, high_point, low_point, mid_point)
        time.sleep(60)
        current_time = int(time.time() * 1000)
        klines = get_all_klines(current_time - TIME_STEP, current_time)
        save_klines(klines)


def main():
    parser = argparse.ArgumentParser(
        description="Check if a coin price has increased by a certain percentage within a time period.")

    parser.add_argument('percent_rised', type=float, help='Percentage rised threshold (X%)')
    parser.add_argument('percent_drop', type=float, help='Percentage drop threshold (Y%)')
    parser.add_argument('time_window', type=int, help='Time window in hours to check the price increase (Yhr)')
    parser.add_argument('--t1', type=str, help='Start time in format YYYY-MM-DD HH:MM:SS')
    parser.add_argument('--t2', type=str, help='End time in format YYYY-MM-DD HH:MM:SS')
    parser.add_argument('--real_time', action='store_true', help='Real times')
    args = parser.parse_args()
    fig, ax, line = initialize_plot()

    if args.real_time:
        real_time_monitoring(args, line)
    else:
        if not args.t1 or not args.t2:
            raise ValueError("Set t1 t2 interval.")
        process_time_frames(args, line)


if __name__ == '__main__':
    main()
