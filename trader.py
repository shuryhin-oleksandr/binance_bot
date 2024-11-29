from enum import Enum
from utils import logger, convert_unix_full_date_str


class TradeStatus(Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class Order:
    def __init__(self, trade_type, entry_price, stop_price, take_profit_price):
        self.trade_type = trade_type  # 'short' or 'long'
        self.entry_price = entry_price
        self.stop_price = stop_price
        self.take_profit_price = take_profit_price
        self.status = TradeStatus.CREATED
        self.close_time = None
        self.entry_time = None
        self.close_price = None

    @property
    def profit(self):
        order_investment = 1000  # USDT
        if self.status != TradeStatus.CLOSED:
            return 0
        if self.trade_type == "long":
            return (self.close_price - self.entry_price) / self.entry_price * order_investment
        # if the order type is short, then the the selling price is entry_price and the buying price is close_price
        return (self.entry_price - self.close_price) / self.close_price * order_investment

    def close(self, time, price):
        self.status = TradeStatus.CLOSED
        self.close_time = time
        self.close_price = price

    def fullfill(self, time):
        self.status = TradeStatus.IN_PROGRESS
        self.entry_time = time

    def evaluate(self, kline):
        low_price = kline["low"]
        high_price = kline["high"]
        time = kline["closeTime"]

        if self.status == TradeStatus.CREATED:
            is_long_fulfilled = self.trade_type == "long" and high_price >= self.entry_price
            is_short_fulfilled = self.trade_type == "short" and low_price <= self.entry_price

            if is_long_fulfilled or is_short_fulfilled:
                self.fullfill(time)
                self.log_in_progress_trade()

        elif self.status == TradeStatus.IN_PROGRESS:
            if self.trade_type == "short":
                if low_price <= self.take_profit_price:
                    self.close(time, self.take_profit_price)
                    self.log_completed_trade()
                elif high_price >= self.stop_price:
                    self.close(time, self.stop_price)
                    self.log_completed_trade()

            elif self.trade_type == "long":
                if high_price >= self.take_profit_price:
                    self.close(time, self.take_profit_price)
                    self.log_completed_trade()
                elif low_price <= self.stop_price:
                    self.close(time, self.stop_price)
                    self.log_completed_trade()

    def get_info(self):
        return f"Type: {self.trade_type}, Entry Price: {self.entry_price}, Stop Price: {self.stop_price}, Take Profit: {self.take_profit_price}"

    def log_in_progress_trade(self):
        trade_field = self.get_info()
        logger.info(
            f"Order in progress: {trade_field}, Entry Time: {convert_unix_full_date_str(self.entry_time)}"
        )

    def log_completed_trade(self):
        trade_field = self.get_info()
        logger.info(
            f"Order completed: Profit: {self.profit}, {trade_field}, Entry Time: {convert_unix_full_date_str(self.entry_time)}, "
            f"Close Time: {convert_unix_full_date_str(self.close_time)}"
        )


class Trader:
    def __init__(self):
        self.orders = []

    @property
    def failed_trades_count(self):
        return len([order for order in self.orders if order.profit < 0])

    @property
    def successful_trades_count(self):
        return len([order for order in self.orders if order.profit > 0])

    @property
    def total_trades(self):
        return len(self.orders)

    @property
    def total_profit(self):
        profit = 0
        for order in self.orders:
            profit += order.profit
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
        entry_price, stop_price, take_profit_price = (
            self.get_short_order_params(high, low, mid)
        )
        order = Order("short", entry_price, stop_price, take_profit_price)
        self.orders.append(order)
        return order

    def place_long_trade(self, high, low, mid):
        entry_price, stop_price, take_profit_price = (
            self.get_long_order_params(high, low, mid)
        )
        order = Order("long", entry_price, stop_price, take_profit_price)
        self.orders.append(order)
        return order

    def evaluate_trades(self, kline):
        for order in self.orders:
            order.evaluate(kline)

    def log_trade_summary(self):
        logger.info(
            f"Order summary: Total={self.total_trades}, Successful={self.successful_trades_count}, "
            f"Failed={self.failed_trades_count}, Net profit/loss={self.total_profit:.2f}"
        )

    def has_uncompleted_trade(self):
        return any(
            order.status in {TradeStatus.CREATED, TradeStatus.IN_PROGRESS} for order in self.orders
        )
