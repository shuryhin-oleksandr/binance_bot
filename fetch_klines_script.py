import argparse
import time
from manager import KlineManager
from utils import get_unix_timestamp

def main():
    parser = argparse.ArgumentParser(description="Fetch and save klines data from Binance.")
    parser.add_argument('start_time', type=str, help='Start time in format YYYY-MM-DD HH:MM:SS')
    parser.add_argument('end_time', type=str, help='End time in format YYYY-MM-DD HH:MM:SS')
    args = parser.parse_args()

    start_timestamp = get_unix_timestamp(args.start_time)
    end_timestamp = get_unix_timestamp(args.end_time)
    kline_manager = KlineManager("mongodb://localhost:27017/", "crypto_data", "btc_klines")
    
    print(f"Fetching klines from {args.start_time} to {args.end_time}...")
    klines_start_time = time.time()
    kline_manager.get_and_save_all_klines(start_timestamp, end_timestamp)
    klines_end_time = time.time()
    print(f"Time for getting klines: {klines_end_time - klines_start_time} s")
    print("Klines fetched and saved successfully.")

if __name__ == '__main__':
    main()
