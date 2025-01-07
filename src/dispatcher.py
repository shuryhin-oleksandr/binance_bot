import time
from datetime import datetime


class Dispatcher:
    def __init__(self, analyzer, trader, kline_manager):
        self.analyzer = analyzer
        self.trader = trader
        self.kline_manager = kline_manager

    def set_time_interval(self, analysis_start_time, analysis_end_time):
        self.analysis_start_time = analysis_start_time
        self.analysis_end_time = analysis_end_time

    def run_for_historical_data(self):
        from bot import prepare_kline_plot_data

        # Fetch all klines for the analysis period
        klines = self.kline_manager.find_or_fetch_klines_in_range(
            self.analysis_start_time - self.analyzer.time_window,  # Start time with buffer for analysis
            self.analysis_end_time,
        )
        analyzed_klines = []
        orders = []

        # Process klines using a generator
        for index in range(self.analyzer.snapshot_klines_count, len(klines)):
            current_kline = klines[index]

            # the analyzer does not work while the trader is working
            if self.trader.has_active_sideway():
                self.trader.update_orders(current_kline)
                self.trader.calculate_and_place_averaging_order(current_kline)
                kline = prepare_kline_plot_data(current_kline)
                analyzed_klines.append(kline)
                continue

            analyzed_kline = self.analyzer._analyze_snapshot(klines, index)
            if analyzed_kline["status"] == "mid":
                sideway_orders = self.trader.add_sideway(
                    self.analyzer.high_kline["high"],
                    self.analyzer.low_kline["low"]
                )
                orders.extend(sideway_orders)
                self.analyzer.reset_klines()

            analyzed_klines.append(analyzed_kline)
        self.summarize_trader_results()
        return analyzed_klines, orders

    def summarize_trader_results(self):
        self.trader.log_order_summary()

    def real_time_monitoring(self):
        while True:
            current_time = int(datetime.now().timestamp() * 1000)
            start_time = (
                current_time - self.analyzer.time_window
            )  # get data starting from now - Yhr
            klines = self.kline_manager.find_or_fetch_klines_in_range(
                start_time, current_time
            )

            # the analyzer does not work while the trader is working
            if self.trader.has_active_sideway():
                self.trader.update_orders(klines[-1])
                continue

            analyzed_kline = self.analyzer._analyze_snapshot(klines, len(klines) - 1)
            if analyzed_kline["status"] == "mid":
                self.trader.new_orders_in_sideway = True
                self.trader.place_short_order(
                    self.analyzer.high_kline["high"],
                    self.analyzer.low_kline["low"],
                    self.analyzer.mid_kline["high"],
                )
                self.trader.place_long_order(
                    self.analyzer.high_kline["high"],
                    self.analyzer.low_kline["low"],
                    self.analyzer.mid_kline["high"],
                )
                # reset high and low points after finding the middle
                self.analyzer.reset_klines()

            time.sleep(60)
