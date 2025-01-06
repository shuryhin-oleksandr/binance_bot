from utils import log_high_kline, log_low_kline, log_middle_kline, log_sideway


class PriceAnalyzer:
    def __init__(
        self,
        time_window,
        target_price_growth_percent,
        target_price_drop_percent,
    ):
        from bot import TIME_STEP
        
        self.time_window = time_window * 60 * 60 * 1000  # Convert hours to milliseconds
        self.target_price_growth_percent = target_price_growth_percent
        self.target_price_drop_percent = target_price_drop_percent
        self.high_kline = None
        self.mid_kline = None
        self.low_kline = None
        self.mid_price = None
        self.snapshot_klines_count = int(self.time_window / TIME_STEP)

    def _is_highest_kline(self, kline):
        return self.high_kline is None or (self.high_kline["high"] < kline["high"])

    def _is_lowest_kline(self, kline):
        return self.low_kline is None or self.low_kline["low"] > kline["low"]

    def calculate_middle_price(self):
        from bot import DEVIATION
        
        sideway_height = self.high_kline["high"] / self.low_kline["low"] - 1
        return self.low_kline["low"] * (1 + sideway_height * (0.5 - DEVIATION))

    def reset_klines(self):
        self.high_kline = None
        self.low_kline = None
        self.mid_kline = None

    def is_new_high_kline(self, kline, min_price):
        kline_is_higher_than_existing = self.high_kline and not self.low_kline and self._is_highest_kline(kline)
        if kline_is_higher_than_existing:
            return True

        current_kline_growth_percent = ((kline["high"] - min_price) / min_price) * 100
        new_impulse_is_higher_than_previous = (
                current_kline_growth_percent >= self.target_price_growth_percent and self._is_highest_kline(kline)
        )
        if new_impulse_is_higher_than_previous:
            kline["target_price_growth_percent"] = current_kline_growth_percent
            return True

        return False

    def is_new_low_kline(self, kline):
        if self.high_kline:
            calculated_target_price_drop_percent = (
                (self.high_kline["high"] - kline["low"]) / self.high_kline["high"]
            ) * 100
            kline["target_price_drop_percent"] = calculated_target_price_drop_percent

            return calculated_target_price_drop_percent >= self.target_price_drop_percent and self._is_lowest_kline(kline)

    def is_new_middle_kline(self, kline):
        return (self.high_kline and self.low_kline) and kline["high"] >= self.mid_price

    def _analyze_kline(self, kline, min_price):
        analyzed_kline = {  # save only data needed for plotting
            "status": "",  # one of: low, high, mid or none
            "time": kline[
                "closeTime"
            ],  # save the closeTime as x coordinate to show the kline
        }

        if self.is_new_high_kline(kline, min_price):
            analyzed_kline["status"] = "high"
            analyzed_kline["price"] = kline["high"] # save the high price as y coordinate to show the kline
            self.high_kline = kline
            log_high_kline(kline)
            return analyzed_kline

        if self.is_new_low_kline(kline):
            self.low_kline = kline
            analyzed_kline["status"] = "low"
            analyzed_kline["price"] = kline["low"]
            self.mid_price = self.calculate_middle_price()
            log_low_kline(kline)
            return analyzed_kline

        if self.is_new_middle_kline(kline):
            analyzed_kline["status"] = "mid"
            analyzed_kline["price"] = kline["high"]
            self.mid_kline = kline
            log_middle_kline(kline)
            log_sideway(self.high_kline, self.low_kline, self.mid_kline, self.mid_price)
            return analyzed_kline

        analyzed_kline["price"] = kline["close"]
        return analyzed_kline

    def _analyze_snapshot(self, klines, snapshot_end):
        from bot import get_min_price

        snapshot_start = snapshot_end - self.snapshot_klines_count
        min_price = get_min_price(klines, snapshot_start, snapshot_end)
        return self._analyze_kline(klines[snapshot_end], min_price)
