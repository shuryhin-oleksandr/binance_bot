import math
import time
import sys
import argparse
from graphic import Graphic
from utils import get_unix_timestamp, show_high_point, show_low_point

TIME_STEP = 1 * 60 * 1000  # one minute in unix

def get_min_price(klines, start_index, last_index):
        return min(klines[j]["close"] for j in range(start_index, last_index))

class PriceMonitoring:
    def __init__(self, kline_manager, time_window, percent_rised, percent_drop, plot_graphic=False):
        self.kline_manager = kline_manager
        self.time_window = time_window * 60 * 60 * 1000  # Convert hours to milliseconds
        self.percent_rised = percent_rised
        self.percent_drop = percent_drop
        self.high_point = None
        self.mid_point = None
        self.low_point = None
        self.graphic = Graphic() if plot_graphic else None

    def _is_high_point(self, point):
        return self.high_point is None or self.high_point["close"] < point["close"]

    def _is_low_point(self, point):
        return self.low_point is None or self.low_point["close"] > point["close"]

    def _analyze_kline(self, kline, min_price):
        closing_price = kline["close"]

        res_percent_rised = ((closing_price - min_price) / min_price) * 100

        if res_percent_rised >= self.percent_rised and self._is_high_point(kline):
            kline["percent_rised"] = res_percent_rised
            self.high_point = kline
            self.mid_point = None
            show_high_point(kline)

        if self.high_point:
            res_percent_drop = ((self.high_point["close"] - closing_price) / self.high_point["close"]) * 100
            kline["percent_drop"] = res_percent_drop
            if res_percent_drop >= self.percent_drop and self._is_low_point(kline):
                self.low_point = kline
                self.mid_point = None
                show_low_point(kline)

        if self.low_point and closing_price >= math.sqrt(self.high_point["close"] * self.low_point["close"]):
            self.mid_point = kline

        return kline
    
    def _start_index_for_analyze(self):
        return int(self.time_window / TIME_STEP)

    def _analyze_klines(self, klines):
        start_index = self._start_index_for_analyze()
        for index in range(start_index, len(klines)):
            current_kline = klines[index]
            min_search_start = index - start_index
            min_price = get_min_price(klines, min_search_start, index)

            self._analyze_kline(current_kline, min_price)
    
    def _analyze_klines_and_plot_point(self, klines):
        start_index = self._start_index_for_analyze()

        for index in range(start_index, len(klines)):
            current_kline = klines[index]
            min_search_start = index - start_index
            min_price = self._get_min_price(klines,min_search_start, index)

            self._analyze_kline(current_kline, min_price)
            self.graphic.update_plot(current_kline, self.high_point, self.low_point, self.mid_point)

    def monitoring(self):
        raise NotImplementedError("Subclasses should implement this method")

class RealTimePriceMonitoring(PriceMonitoring):
    
    def monitoring(self):
        current_time = int(time.time() * 1000)
        
        while True:
            start_time = current_time - self.time_window # get data starting from now - Yhr
            klines = self.kline_manager.find_or_fetch_klines_in_range(start_time, current_time)

            if self.graphic:
                self._analyze_klines_and_plot_point(klines)
            else:
                self._analyze_klines(klines)
            
            time.sleep(60)

class HistoricalPriceMonitoring(PriceMonitoring):
    def __init__(self, kline_manager, time_window, percent_rised, percent_drop, plot_graphic, t1, t2):
        super().__init__(kline_manager, time_window, percent_rised, percent_drop, plot_graphic)
        self.t1 = get_unix_timestamp(t1)
        self.t2 = get_unix_timestamp(t2)

    def monitoring(self):
        current_time = self.t1
        interval = int(60 * 60 * 24 * 43 * 150 * TIME_STEP / 1000) # klines size == 0.5 Gb

        while current_time < self.t2:
            next_time = min(current_time + interval, self.t2)
            start_time = current_time - self.time_window # get data starting from t1 - Yhr

            klines = self.kline_manager.find_or_fetch_klines_in_range(start_time, next_time)
            size_in_mb = sys.getsizeof(klines) / 1024 / 1024
            print(f"Data size: {size_in_mb:.6f} MB")

            if self.graphic:
                self._analyze_klines_and_plot_point(klines)
            else:
                self._analyze_klines(klines)
            current_time = next_time

def main():
    parser = argparse.ArgumentParser(description="Check if a coin price has increased by a certain percentage within a time period.")
    parser.add_argument('percent_rised', type=float, help='Percentage rised threshold (X%)')
    parser.add_argument('percent_drop', type=float, help='Percentage drop threshold (Y%)')
    parser.add_argument('time_window', type=int, help='Time window in hours to check the price increase (Yhr)')
    parser.add_argument('--t1', type=str, help='Start time in format YYYY-MM-DD HH:MM:SS')
    parser.add_argument('--t2', type=str, help='End time in format YYYY-MM-DD HH:MM:SS')
    parser.add_argument('--real_time', action='store_true', help='Real time monitoring')
    parser.add_argument('--plot_graphic', action='store_true', help='Plot graphic')

    args = parser.parse_args()

    from manager import KlineManager
    kline_manager = KlineManager("mongodb://localhost:27017/", "crypto_data", "btc_klines")

    if args.real_time:
        monitoring = RealTimePriceMonitoring(kline_manager, args.time_window, args.percent_rised, args.percent_drop, args.plot_graphic)
    else:
        if not args.t1 or not args.t2:
            raise ValueError("Set t1 t2 interval.")
        monitoring = HistoricalPriceMonitoring(kline_manager, args.time_window, args.percent_rised, args.percent_drop, args.plot_graphic, args.t1, args.t2)

    monitoring.monitoring()

if __name__ == '__main__':
    main()
