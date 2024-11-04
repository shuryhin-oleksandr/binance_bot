import math
import time
import argparse
from graphic import Graphic
import logging

# Configure the logging level and format
logging.basicConfig(
    filename="kline_log.log",  # Specify the log file name
    level=logging.INFO,  # Set the log level
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="w",  # Use 'w' to overwrite the log file each run, or 'a' to append
)

from utils import get_unix_timestamp, log_high_kline, log_low_kline, log_middle_kline

TIME_STEP = 1 * 60 * 1000  # one minute in unix
MONGO_URL = "mongodb://localhost:27017/"
DB_NAME = "crypto_data"
SYMBOL = "BTCUSDT"
COLLECTION_NAME = f"{SYMBOL.lower()}_klines"


def get_min_price(klines, start_index, last_index):
    return min(klines[j]["low"] for j in range(start_index, last_index))


class PriceAnalyzer:
    def __init__(
        self,
        kline_manager,
        time_window,
        target_price_growth_percent,
        target_price_drop_percent,
        plot_graphic=False,
    ):
        self.kline_manager = kline_manager
        self.time_window = time_window * 60 * 60 * 1000  # Convert hours to milliseconds
        self.target_price_growth_percent = target_price_growth_percent
        self.target_price_drop_percent = target_price_drop_percent
        self.high_kline = None
        self.mid_kline = None
        self.low_kline = None
        self.mid_price = None
        self.graphic = Graphic() if plot_graphic else None

    def _is_highest_kline(self, kline):
        return self.high_kline is None or (self.high_kline["high"] < kline["high"])

    def _is_lowest_kline(self, kline):
        return self.low_kline is None or self.low_kline["low"] > kline["low"]

    def _analyze_kline(self, kline, min_price):
        high_price = kline["high"]
        kline["status"] = ""  # all klines with status low, high, mid or none

        calculated_target_price_growth_percent = (
            (high_price - min_price) / min_price
        ) * 100

        if (
            calculated_target_price_growth_percent >= self.target_price_growth_percent
            and self._is_highest_kline(kline)
        ):
            kline["target_price_growth_percent"] = (
                calculated_target_price_growth_percent
            )
            kline["status"] = "high"
            self.high_kline = kline
            log_high_kline(kline)
            return kline

        # TODO: Add phase property, which can be one of: idle, high_found, low_found, mid_found
        low_price = kline["low"]
        if self.high_kline:
            calculated_target_price_drop_percent = (
                (self.high_kline["high"] - low_price) / self.high_kline["high"]
            ) * 100
            kline["target_price_drop_percent"] = calculated_target_price_drop_percent
            if (
                calculated_target_price_drop_percent >= self.target_price_drop_percent
                and self._is_lowest_kline(kline)
            ):
                self.low_kline = kline
                kline["status"] = "low"
                self.mid_price = math.sqrt(
                    self.high_kline["high"] * self.low_kline["low"]
                )
                self.mid_kline = None
                log_low_kline(kline)
                return kline

        if self.low_kline and not self.mid_kline and high_price >= self.mid_price:
            kline["status"] = "mid"
            self.mid_kline = kline
            self.high_kline = None
            self.low_kline = None
            log_middle_kline(kline)

        return kline

    def _analyzed_time_interval(self, klines, current_time):

        for i, kline in enumerate(klines):
            if kline["closeTime"] >= current_time:  # first kline index >= current time
                return i

        return len(klines) - 1  # end list of klines

    def _analyze_klines(self, klines, current_time):
        """
        Analyze a list of kline data within a specified time interval.
        - This function uses the `current_time` and calculates the starting index for analysis based
          on the time interval determined by `_analyzed_time_interval`.
        - For each kline, it calculates the minimum price within the time window and
          applies `_analyze_kline` to perform specific processing.
        """
        processed_klines = []
        analysis_start_index = self._analyzed_time_interval(
            klines, current_time
        )  # the time index of the start of the analysis (the lower limit of the interval)

        for index in range(analysis_start_index, len(klines)):
            current_kline = klines[index]
            min_search_start = self._analyzed_time_interval(
                klines, current_time - self.time_window
            )  # find the start index for searching for minimum values within the time window Y hours
            min_price = get_min_price(klines, min_search_start, index)
            processed_klines.append(self._analyze_kline(current_kline, min_price))

        return processed_klines

    def monitoring(self):
        raise NotImplementedError("Subclasses should implement this method")


class RealTimePriceAnalyzer(PriceAnalyzer):

    def monitoring(self):
        while True:
            current_time = int(time.time() * 1000)
            start_time = (
                current_time - self.time_window
            )  # get data starting from now - Yhr
            klines = self.kline_manager.find_or_fetch_klines_in_range(
                start_time, current_time
            )
            processed_klines = self._analyze_klines(klines, current_time)
            if self.graphic:
                self.graphic.update_plot_real_time(processed_klines[-1])

            time.sleep(60)


class HistoricalPriceAnalyzer(PriceAnalyzer):
    def __init__(
        self,
        kline_manager,
        time_window,
        target_price_growth_percent,
        target_price_drop_percent,
        plot_graphic,
        analysis_start_time,
        analysis_end_time,
    ):
        super().__init__(
            kline_manager,
            time_window,
            target_price_growth_percent,
            target_price_drop_percent,
            plot_graphic,
        )
        self.analysis_start_time = get_unix_timestamp(analysis_start_time)
        self.analysis_end_time = get_unix_timestamp(analysis_end_time)

    def monitoring(self):
        chunk_analysis_start_time = self.analysis_start_time
        chunk_time_size = int(
            60 * 60 * 24 * 43 * 365 * TIME_STEP / 1000
        )  # klines size ~ 0.5 Gb

        # TODO: Refine chunk_analysis_start_time naming
        while chunk_analysis_start_time < self.analysis_end_time:
            chunk_start_time = (
                chunk_analysis_start_time - self.time_window
            )  # get data starting from analysis_start_time- Yhr
            chunk_end_time = min(
                chunk_analysis_start_time + chunk_time_size, self.analysis_end_time
            )

            chunk_klines = self.kline_manager.find_or_fetch_klines_in_range(
                chunk_start_time, chunk_end_time
            )
            processed_klines = self._analyze_klines(
                chunk_klines, chunk_analysis_start_time
            )
            chunk_analysis_start_time = chunk_end_time

            if self.graphic:
                self.graphic.create_plot_for_historical_data(processed_klines)


def main():
    parser = argparse.ArgumentParser(
        description="Check if a coin price has increased by a certain percentage within a time period."
    )
    parser.add_argument(
        "target_price_growth_percent",
        type=float,
        help="Percentage rised threshold (X%)",
    )
    parser.add_argument(
        "target_price_drop_percent", type=float, help="Percentage drop threshold (Y%)"
    )
    parser.add_argument(
        "time_window",
        type=int,
        help="Time window in hours to check the price increase (Yhr)",
    )
    parser.add_argument(
        "--analysis_start_time",
        type=str,
        help="Start time in format YYYY-MM-DD HH:MM:SS",
    )
    parser.add_argument(
        "--analysis_end_time", type=str, help="End time in format YYYY-MM-DD HH:MM:SS"
    )
    parser.add_argument("--real_time", action="store_true", help="Real time monitoring")
    parser.add_argument("--plot_graphic", action="store_true", help="Plot graphic")

    args = parser.parse_args()

    from manager import KlineManager

    kline_manager = KlineManager(MONGO_URL, DB_NAME, COLLECTION_NAME)

    if args.real_time:
        monitoring = RealTimePriceAnalyzer(
            kline_manager,
            args.time_window,
            args.target_price_growth_percent,
            args.target_price_drop_percent,
            args.plot_graphic,
        )
    else:
        if not args.analysis_start_time or not args.analysis_end_time:
            raise ValueError("Set start time and end time interval for analysis.")
        monitoring = HistoricalPriceAnalyzer(
            kline_manager,
            args.time_window,
            args.target_price_growth_percent,
            args.target_price_drop_percent,
            args.plot_graphic,
            args.analysis_start_time,
            args.analysis_end_time,
        )

    monitoring.monitoring()


if __name__ == "__main__":
    main()
