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


def get_min_price(klines, start_index, last_index):
    return min(klines[j]["low"] for j in range(start_index, last_index))


class PriceMonitoring:
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
        # TODO: Compare by high value
        return self.high_kline is None or (self.high_kline["close"] < kline["close"])

    def _is_lowest_kline(self, kline):
        # TODO: Compare by low value
        return self.low_kline is None or self.low_kline["close"] > kline["close"]

    def _analyze_kline(self, kline, min_price):
        # TODO: we should take high price
        closing_price = kline["close"]
        kline["status"] = ""  # all klines with status low, high, mid or none

        calculated_target_price_growth_percent = (
            (closing_price - min_price) / min_price
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
        if self.high_kline:
            calculated_target_price_drop_percent = (
                # TODO: calculate based on low price
                (self.high_kline["close"] - closing_price) / self.high_kline["close"]
            ) * 100
            kline["target_price_drop_percent"] = calculated_target_price_drop_percent
            if (
                calculated_target_price_drop_percent >= self.target_price_drop_percent
                and self._is_lowest_kline(kline)
            ):
                self.low_kline = kline
                kline["status"] = "low"
                self.mid_price = math.sqrt(
                    self.high_kline["close"] * self.low_kline["close"]
                )
                self.mid_kline = None
                log_low_kline(kline)
                return kline

        if self.low_kline and not self.mid_kline and closing_price >= self.mid_price:
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
        # TODO: Add docstring
        processed_klines = []
        # What is analysis start_index used for?
        analysis_start_index = self._analyzed_time_interval(klines, current_time)

        for index in range(analysis_start_index, len(klines)):
            current_kline = klines[index]
            min_search_start = index - analysis_start_index
            min_price = get_min_price(klines, min_search_start, index)
            processed_klines.append(self._analyze_kline(current_kline, min_price))

        return processed_klines

    def monitoring(self):
        raise NotImplementedError("Subclasses should implement this method")


class RealTimePriceMonitoring(PriceMonitoring):

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


# TODO: Fix naming
class HistoricalPriceMonitoring(PriceMonitoring):
    def __init__(
        self,
        kline_manager,
        time_window,
        target_price_growth_percent,
        target_price_drop_percent,
        plot_graphic,
        t1,
        t2,
    ):
        super().__init__(
            kline_manager,
            time_window,
            target_price_growth_percent,
            target_price_drop_percent,
            plot_graphic,
        )
        self.analysis_start_time = get_unix_timestamp(t1)
        self.analysis_end_time = get_unix_timestamp(t2)

    def monitoring(self):
        chunk_analysis_start_time = self.analysis_start_time
        # TODO: Fix typo
        chank_time_size = int(
            60 * 60 * 24 * 43 * 365 * TIME_STEP / 1000
        )  # klines size ~ 0.5 Gb

        # TODO: Refine chunk_analysis_start_time naming
        while chunk_analysis_start_time < self.analysis_end_time:
            chunk_start_time = (
                chunk_analysis_start_time - self.time_window
            )  # get data starting from t1 - Yhr
            chunk_end_time = min(
                chunk_analysis_start_time + chank_time_size, self.analysis_end_time
            )

            # TODO: rename to chunk_klines
            klines = self.kline_manager.find_or_fetch_klines_in_range(
                chunk_start_time, chunk_end_time
            )
            processed_klines = self._analyze_klines(klines, chunk_analysis_start_time)
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
        "--t1", type=str, help="Start time in format YYYY-MM-DD HH:MM:SS"
    )
    parser.add_argument("--t2", type=str, help="End time in format YYYY-MM-DD HH:MM:SS")
    parser.add_argument("--real_time", action="store_true", help="Real time monitoring")
    parser.add_argument("--plot_graphic", action="store_true", help="Plot graphic")

    args = parser.parse_args()

    from manager import KlineManager

    kline_manager = KlineManager(
        # TODO: Extract mongo url, db name to constants on the top of the file
        # TODO: Extract collection name to a top of the file, make it dependant on SYMBOL value
        "mongodb://localhost:27017/", "crypto_data", "btc_klines"
    )

    if args.real_time:
        monitoring = RealTimePriceMonitoring(
            kline_manager,
            args.time_window,
            args.target_price_growth_percent,
            args.target_price_drop_percent,
            args.plot_graphic,
        )
    else:
        if not args.t1 or not args.t2:
            raise ValueError("Set t1 t2 interval.")
        monitoring = HistoricalPriceMonitoring(
            kline_manager,
            args.time_window,
            args.target_price_growth_percent,
            args.target_price_drop_percent,
            args.plot_graphic,
            # TODO: rename t1, t2
            args.t1,
            args.t2,
        )

    monitoring.monitoring()


if __name__ == "__main__":
    main()
