import time
from pymongo import MongoClient

mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["crypto_data"]
collection = db["btc_klines"]
collection.create_index("startTime")
collection.create_index("closeTime")

def save_klines(klines):
    documents = []
    klines_start_time = time.time()

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

        # Check before adding
        if not collection.find_one({"startTime": kline[0]}):
            documents.append(document)

    klines_end_time = time.time()
    print(f"Time for checking all klines: {klines_end_time - klines_start_time} s")

    insert_klines_start_time = time.time()
    if documents:
        collection.insert_many(documents)
    insert_klines_end_time = time.time()
    print(f"Time for insert klines: {insert_klines_end_time - insert_klines_start_time} s")

def find_klines_near_close_time(current_time, buffer_ms=5000):
    return list(collection.find({
        "closeTime": {
            "$gte": current_time - buffer_ms,
            "$lte": current_time + buffer_ms
        }
    }))

def get_min_price_in_range(start_time, end_time):
    min_price_doc = collection.find({"startTime": {"$gte": start_time, "$lt": end_time}}).sort("low", 1).limit(1)
    return min_price_doc[0]["low"] if min_price_doc else None
