import time
import logging
from pymongo import MongoClient
from bot import TIME_STEP
from binance_api import get_klines
from utils import convert_unix_to_str

def get_missing_intervals(missing_times):
        """Convert missing times into start and end intervals."""
        if not missing_times:
            return []

        # Sort the missing times
        missing_times = sorted(missing_times)

        intervals = []
        start = missing_times[0]
        end = missing_times[0]

        for current_time in missing_times[1:]:
            if current_time <= end + TIME_STEP:
                end = current_time
            else:
                # If there's a gap, close the previous interval
                intervals.append((start, end))
                start = current_time
                end = current_time

        # Add the last interval
        intervals.append((start, end))

        return intervals

class KlineManager:
    def __init__(self, mongo_uri, db_name, collection_name):
        self.mongo_client = MongoClient(mongo_uri)
        self.db = self.mongo_client[db_name]
        self.collection = self.db[collection_name]
        self.collection.create_index("startTime")

    def get_and_save_all_klines(self, start_time, end_time):
        """Get all candlestick data for a year by requesting in chunks of 1000."""
        current_time = start_time

        while current_time < end_time:

            klines = get_klines(current_time, end_time)
            
            if not klines:
                break

            self.save_klines(klines)
            current_time = klines[-1][6] + 1 # closing time last kline

    def find_missing_klines_time(self, start_time, end_time):
        expected_times = set(range(start_time, end_time, TIME_STEP))

        # Get all available timestamps from the database
        available_klines = list(self.collection.find({"startTime": {"$gte": start_time, "$lt": end_time}}, {"startTime": 1}))
        available_times = set([kline["startTime"] for kline in available_klines])

        # Determine missing timestamps
        missing_times = expected_times - available_times

        return sorted(list(missing_times))

    def save_klines(self, klines):
        documents = []

        for kline in klines:
            document = {
                "startTime": kline[0],
                "open": float(kline[1]),
                "high": float(kline[2]),
                "low": float(kline[3]),
                "close": float(kline[4]),
                "volume": float(kline[5]),
                "closeTime": kline[6],
                "quoteAssetVolume": float(kline[7]),
                "numberOfTrades": kline[8],
                "takerBuyBaseAssetVolume": float(kline[9]),
                "takerBuyQuoteAssetVolume": float(kline[10]),
                "ignore": float(kline[11])
            }

            documents.append(document)

        insert_klines_start_time = time.time()
        self.collection.insert_many(documents)
        insert_klines_end_time = time.time()
        logging.info(f"Time for insert klines: {insert_klines_end_time - insert_klines_start_time} s")
    
    def find_klines_in_range(self, start_time, end_time):
        return list(self.collection.find({"startTime": {"$gte": start_time, "$lt": end_time}}))

    def find_or_fetch_klines_in_range(self, start_time, end_time):
        klines = self.find_klines_in_range(start_time, end_time)

        # Load missing data from API and save it to the database
        missing_times = self.find_missing_klines_time(start_time, end_time)
        if missing_times:
            logging.warning(f"Data for the range {convert_unix_to_str(start_time)} - {convert_unix_to_str(end_time)} is incomplete. Fetching missing data...")
            missing_intervals = get_missing_intervals(missing_times)

            # Fetch and save missing data for each interval
            missing_klines = []
            for interval_start, interval_end in missing_intervals:
                logging.warning(f"Missing intervals: {convert_unix_to_str(interval_start)} - {convert_unix_to_str(interval_end)}")
                self.get_and_save_all_klines(interval_start, interval_end)
                missing_klines += self.find_klines_in_range(interval_start, interval_end)

            # Add new data to existing ones
            klines += missing_klines
        
        return klines
