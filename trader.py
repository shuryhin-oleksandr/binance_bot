from enum import Enum
from utils import logger, convert_unix_full_date_str


class TradeStatus(Enum):
    OPEN = "open"
    FULFILLED = "fulfilled"
    CLOSED = "closed"


class Order:
    def __init__(self, trade_type, entry_price, stop_price, take_profit_price):
        self.trade_type = trade_type  # 'short' or 'long'
        self.entry_price = entry_price
        self.stop_price = stop_price
        self.take_profit_price = take_profit_price
        self.status = TradeStatus.OPEN
        self.close_time = None
        self.entry_time = None
        self.close_price = None
        self.is_canceled = False

    @property
    def profit(self):
        order_investment = 1000  # USDT
        if not self.close_price:
            return 0
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

    def cancel(self):
        self.status = TradeStatus.CLOSED
        self.close_time = None
        self.close_price = None
        self.is_canceled = True

    def fullfill(self, time):
        self.status = TradeStatus.FULFILLED
        self.entry_time = time

    def evaluate(self, kline):
        low_price = kline["low"]
        high_price = kline["high"]
        time = kline["closeTime"]

        if self.status == TradeStatus.OPEN:
            is_long_fulfilled = self.trade_type == "long" and low_price <= self.entry_price
            is_short_fulfilled = self.trade_type == "short" and high_price >= self.entry_price

            if is_long_fulfilled or is_short_fulfilled:
                self.fullfill(time)
                self.log_order_fulfilled()

        elif self.status == TradeStatus.FULFILLED:
            if self.trade_type == "short":
                if low_price <= self.take_profit_price:
                    self.close(time, self.take_profit_price)
                    self.log_order_closed()
                elif high_price >= self.stop_price:
                    self.close(time, self.stop_price)
                    self.log_order_closed()

            elif self.trade_type == "long":
                if high_price >= self.take_profit_price:
                    self.close(time, self.take_profit_price)
                    self.log_order_closed()
                elif low_price <= self.stop_price:
                    self.close(time, self.stop_price)
                    self.log_order_closed()

    def get_info(self):
        return f"Type: {self.trade_type}, Entry Price: {self.entry_price}, Stop Price: {self.stop_price}, Take Profit: {self.take_profit_price}"

    def log_order_fulfilled(self):
        order_info = self.get_info()
        logger.info(
            f"Order fulfilled: {order_info}, Entry Time: {convert_unix_full_date_str(self.entry_time)}"
        )

    def log_order_closed(self):
        order_info = self.get_info()
        entry_time_str = convert_unix_full_date_str(self.entry_time) if self.entry_time else "N/A"
        close_time_str = convert_unix_full_date_str(self.close_time) if self.close_time else "N/A"
        logger.info(
            f"Order closed: Profit: {self.profit}, {order_info}, Entry Time: {entry_time_str}, "
            f"Close Time: {close_time_str}"
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
            if order.status == TradeStatus.CLOSED and order.close_price == order.stop_price:
                self.cancel_opposite_order(order)

    def cancel_opposite_order(self, closed_order):
        last_short_order = self.orders[-2]
        last_long_order = self.orders[-1]
        if last_long_order == closed_order and not last_short_order.is_canceled:
            last_short_order.cancel()
            last_short_order.log_order_closed()
        elif last_short_order == closed_order and not last_long_order.is_canceled:
            last_long_order.cancel()
            last_long_order.log_order_closed()

    def log_trade_summary(self):
        logger.info(
            f"Order summary: Total={self.total_trades}, Positive={self.successful_trades_count}, "
            f"Negative={self.failed_trades_count}, Net profit/loss={self.total_profit:.2f}"
        )

    def has_uncompleted_trade(self):
        return any(
            order.status in {TradeStatus.OPEN, TradeStatus.FULFILLED} for order in self.orders
        )
