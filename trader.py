from enum import Enum
from utils import logger, convert_unix_full_date_str


class TradeStatus(Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILURE = "failure"


class Trade:
    def __init__(self, trade_type, entry_price, stop_price, take_profit):
        self.trade_type = trade_type  # 'short' or 'long'
        self.entry_price = entry_price
        self.stop_price = stop_price
        self.take_profit = take_profit
        self.status = TradeStatus.CREATED
        self.close_time = None
        self.entry_time = None

    def close_trade(self, outcome: TradeStatus, time):
        self.status = outcome
        self.close_time = time

    def set_in_progress_status(self, time):
        self.status = TradeStatus.IN_PROGRESS
        self.entry_time = time

    def get_info(self):
        return f"Type: {self.trade_type}, Entry Price: {self.entry_price}, Stop Price: {self.stop_price}, Take Profit: {self.take_profit}"

    def log_in_progress_trade(self):
        trade_field = self.get_info()
        logger.info(
            f"Trade in progress: {trade_field}, Entry Time: {convert_unix_full_date_str(self.entry_time)}"
        )

    def log_completed_trade(self):
        trade_field = self.get_info()
        logger.info(
            f"Trade completed: Status: {self.status.value}, {trade_field}, Entry Time: {convert_unix_full_date_str(self.entry_time)}, "
            f"Close Time: {convert_unix_full_date_str(self.close_time)}"
        )


class Trader:
    def __init__(self):
        self.trades = []

    @property
    def failed_trades(self):
        return len([trade for trade in self.trades if trade.status == TradeStatus.FAILURE])

    @property
    def successful_trades(self):
        return len([trade for trade in self.trades if trade.status == TradeStatus.SUCCESS])

    @property
    def total_trades(self):
        return len(self.trades)

    @property
    def total_profit(self):
        profit = 0
        for trade in self.trades:
            if trade.status == TradeStatus.SUCCESS:
                if trade.trade_type == "long":
                    profit += trade.take_profit - trade.entry_price
                elif trade.trade_type == "short":
                    profit += trade.entry_price - trade.take_profit
            elif trade.status == TradeStatus.FAILURE:
                if trade.trade_type == "long":
                    profit -= trade.entry_price - trade.stop_price
                elif trade.trade_type == "short":
                    profit -= trade.stop_price - trade.entry_price
        return profit

    def get_sideway_height_deviation(self, high, low):
        sideway_height = (high / low) - 1
        deviation = 0.05 * sideway_height
        return deviation, sideway_height

    def get_short_order_params(self, high, low, mid):
        deviation, sideway_height = self.get_sideway_height_deviation(high, low)
        short_entry = high * (1 + deviation)
        short_stop = high * (1 + sideway_height / 2)
        short_take_profit = mid
        return short_entry, short_stop, short_take_profit

    def get_long_order_params(self, high, low, mid):
        deviation, sideway_height = self.get_sideway_height_deviation(high, low)
        long_entry = low * (1 - deviation)
        long_stop = low * (1 - sideway_height / 2)
        long_take_profit = mid
        return long_entry, long_stop, long_take_profit

    def place_short_trade(self, high, low, mid):
        entry_price, stop_price, take_profit = (
            self.get_short_order_params(high, low, mid)
        )
        trade = Trade("short", entry_price, stop_price, take_profit)
        self.trades.append(trade)
        return trade

    def place_long_trade(self, high, low, mid):
        entry_price, stop_price, take_profit = (
            self.get_long_order_params(high, low, mid)
        )
        trade = Trade("long", entry_price, stop_price, take_profit)
        self.trades.append(trade)
        return trade

    def evaluate_trades(self, kline):
        for trade in self.trades:
            self.evaluate_trade(trade, kline)

    def evaluate_trade(self, trade, kline):
        low_price = kline["low"]
        high_price = kline["high"]
        time = kline["closeTime"]

        if trade.status == TradeStatus.CREATED:
            is_long_order_in_progress = trade.trade_type == "long" and high_price >= trade.entry_price
            is_short_order_in_progress = trade.trade_type == "short" and low_price <= trade.entry_price
            if is_long_order_in_progress or is_short_order_in_progress:
                trade.set_in_progress_status(time)
                trade.log_in_progress_trade()

        elif trade.status == TradeStatus.IN_PROGRESS:
            if trade.trade_type == "short":
                if low_price <= trade.take_profit:
                    trade.close_trade(TradeStatus.SUCCESS, time)
                    trade.log_completed_trade()
                elif high_price >= trade.stop_price:
                    trade.close_trade(TradeStatus.FAILURE, time)
                    trade.log_completed_trade()

            elif trade.trade_type == "long":
                if high_price >= trade.take_profit:
                    trade.close_trade(TradeStatus.SUCCESS, time)
                    trade.log_completed_trade()
                elif low_price <= trade.stop_price:
                    trade.close_trade(TradeStatus.FAILURE, time)
                    trade.log_completed_trade()

    def log_trade_summary(self):
        logger.info(
            f"Trade summary: Total={self.total_trades}, Successful={self.successful_trades}, "
            f"Failed={self.failed_trades}, Net profit/loss={self.total_profit:.2f}"
        )

    def has_uncompleted_trade(self):
        return any(
            trade.status in {TradeStatus.CREATED, TradeStatus.IN_PROGRESS} for trade in self.trades
        )
