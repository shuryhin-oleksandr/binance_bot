from itertools import chain
from enum import Enum
from utils import logger, convert_unix_full_date_str


class OrderStatus(Enum):
    OPEN = "open"
    FULFILLED = "fulfilled"
    CLOSED = "closed"
    CANCELED = "canceled"


class Order:
    def __init__(self, type, entry_price, stop_price, take_profit_price, high, low, mid):
        self.type = type  # 'short' or 'long'
        self.entry_price = entry_price
        self.stop_price = stop_price
        self.take_profit_price = take_profit_price
        self.status = OrderStatus.OPEN
        self.close_time = None
        self.entry_time = None
        self.close_price = None

        self.high = high
        self.low = low
        self.mid = mid

    @property
    def profit(self):
        order_investment = 1000  # USDT
        if self.status == OrderStatus.CANCELED:
            return 0
        if self.type == "long":
            return (self.close_price - self.entry_price) / self.entry_price * order_investment
        # if the order type is short, then the the selling price is entry_price and the buying price is close_price
        return (self.entry_price - self.close_price) / self.close_price * order_investment

    def close(self, time, price):
        self.status = OrderStatus.CLOSED
        self.close_time = time
        self.close_price = price

    @property        
    def is_closed(self):
        return self.closed_by_stop or self.closed_by_take_profit

    @property        
    def closed_by_stop(self):
        return self.status == OrderStatus.CLOSED and self.close_price == self.stop_price 

    @property        
    def closed_by_take_profit(self):
        return self.status == OrderStatus.CLOSED and self.close_price == self.take_profit_price

    def cancel(self):
        self.status = OrderStatus.CANCELED
        self.close_time = None
        self.close_price = None

    def fullfill(self, time):
        self.status = OrderStatus.FULFILLED
        self.entry_time = time

    def evaluate(self, kline):
        low_price = kline["low"]
        high_price = kline["high"]
        time = kline["closeTime"]

        if self.status == OrderStatus.OPEN:
            is_long_fulfilled = self.type == "long" and low_price <= self.entry_price
            is_short_fulfilled = self.type == "short" and high_price >= self.entry_price

            if is_long_fulfilled or is_short_fulfilled:
                self.fullfill(time)
                self.log_order_fulfilled()

        elif self.status == OrderStatus.FULFILLED:
            if self.type == "short":
                if low_price <= self.take_profit_price:
                    self.close(time, self.take_profit_price)
                    self.log_order_closed()
                elif high_price >= self.stop_price:
                    self.close(time, self.stop_price)
                    self.log_order_closed()

            elif self.type == "long":
                if high_price >= self.take_profit_price:
                    self.close(time, self.take_profit_price)
                    self.log_order_closed()
                elif low_price <= self.stop_price:
                    self.close(time, self.stop_price)
                    self.log_order_closed()

    def get_info(self):
        return f"(entry: {self.entry_price}, stop: {self.stop_price}, take: {self.take_profit_price})"

    def log_order_fulfilled(self):
        order_info = self.get_info()
        logger.info(
            f"Order fulfilled: {order_info}, Entry Time: {convert_unix_full_date_str(self.entry_time)}"
        )

    @property
    def entry_time_str(self):
        return convert_unix_full_date_str(self.entry_time) if self.entry_time else "N/A"

    @property
    def close_time_str(self):
        return convert_unix_full_date_str(self.entry_time) if self.entry_time else "N/A"

    def log_order_closed(self):
        order_info = self.get_info()
        status = "closed" if self.close_time and self.entry_time else "canceled"
        logger.info(
            f"{self.type.capitalize()} order {status}: Profit: {self.profit}, {order_info}, Entry Time: {self.entry_time_str}, "
            f"Close Time: {self.close_time_str}"
        )


class Trader:
    def __init__(self):
        self.sideways_orders = []

    @property
    def flat_orders(self):
        return list(chain.from_iterable(self.sideways_orders))

    @property
    def failed_orders_count(self):
        return len([order for order in self.flat_orders if order.profit < 0])

    @property
    def successful_orders_count(self):
        return len([order for order in self.flat_orders if order.profit > 0])

    @property
    def total_orders(self):
        return sum(len(sideway_orders) for sideway_orders in self.sideways_orders)

    @property
    def total_profit(self):
        profit = 0
        for sideway_orders in self.sideways_orders:
            for order in sideway_orders:
                profit += order.profit
        return profit

    @property
    def current_sideway_orders(self):
        return self.sideways_orders[-1] if self.sideways_orders else []
    
    def add_subway(self, high, low, mid):
        self.start_new_sideway_period()

        short_order = self.place_short_order(high, low, mid)
        long_order = self.place_long_order(high, low, mid)
        return short_order, long_order

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

    def start_new_sideway_period(self):
        self.sideways_orders.append([])

    def place_short_order(self, high, low, mid):
        entry_price, stop_price, take_profit_price = (
            self.get_short_order_params(high, low, mid)
        )
        order = Order("short", entry_price, stop_price, take_profit_price, high, low, mid)
        self.current_sideway_orders.append(order)
        return order

    def place_long_order(self, high, low, mid):
        entry_price, stop_price, take_profit_price = (
            self.get_long_order_params(high, low, mid)
        )
        order = Order("long", entry_price, stop_price, take_profit_price, high, low, mid)
        self.current_sideway_orders.append(order)
        return order

    @property
    def get_current_closed_orders(self):
        return [order for order in self.current_sideway_orders if order.is_closed]

    def get_current_pending_orders(self):
        return [order for order in self.current_sideway_orders if order.status == OrderStatus.OPEN or order.status == OrderStatus.FULFILLED]

    def is_current_orders_were_closed_by_sl(self):
        return any([order for order in self.current_sideway_orders if order.status == OrderStatus.CLOSED and order.close_price == order.stop_price])

    def update_orders(self, kline):
        for order in self.current_sideway_orders:
            order.evaluate(kline)

        for order in self.current_sideway_orders:
            if order.status == OrderStatus.OPEN and self.is_current_orders_were_closed_by_sl():
                order.cancel()
                order.log_order_closed()
            
            if len(self.get_current_closed_orders) >= 2 and order.status == OrderStatus.OPEN:
                order.cancel()
                order.log_order_closed()

            if order.status == OrderStatus.CLOSED and order.close_price == order.take_profit_price and len(self.get_current_closed_orders) < 2 and len(self.get_current_pending_orders()) < 2:
                if order.type == 'long':
                    self.place_long_order(order.high, order.low, order.mid)
                else:
                    self.place_short_order(order.high, order.low, order.mid)

    def log_order_summary(self):
        logger.info(
            f"Order summary: Total={self.total_orders}, Positive={self.successful_orders_count}, "
            f"Negative={self.failed_orders_count}, Net profit/loss={self.total_profit:.2f}"
        )

    def has_traded_sideway(self):
        if not self.current_sideway_orders:
            return False
        return any(
            order.status in {OrderStatus.OPEN, OrderStatus.FULFILLED} for order in self.current_sideway_orders
        )
