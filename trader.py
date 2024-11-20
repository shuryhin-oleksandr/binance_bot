from utils import logger, convert_unix_full_date_str


class Trade:
    def __init__(self, trade_type, entry_price, stop_price, take_profit):
        self.trade_type = trade_type  # 'short' або 'long'
        self.entry_price = entry_price
        self.stop_price = stop_price
        self.take_profit = take_profit
        self.status = None  # 'success', 'failure' або 'open'\
        self.close_time = None
        self.open_time = None

    def close_trade(self, outcome, time):
        self.status = outcome
        self.close_time = time

    def open_trade(self, time):
        self.status = "open"
        self.open_time = time

    def get_general_trade_field(self):
        return f"Type: {self.trade_type}, Entry Price: {self.entry_price}, Stop Price: {self.stop_price}, Take Profit: {self.take_profit}"

    def log_opened_trade(self):
        trade_field = self.get_general_trade_field()
        logger.info(
            f"Trade opened: {trade_field}, Open Time: {convert_unix_full_date_str(self.open_time)}"
        )

    def log_completed_trade(self):
        trade_field = self.get_general_trade_field()
        logger.info(
            f"Trade completed: Status: {self.status}, {trade_field}, Open Time: {convert_unix_full_date_str(self.open_time)}, "
            f"Close Time: {convert_unix_full_date_str(self.close_time)}"
        )


class Trader:
    def __init__(self):
        self.trades = []

    @property
    def failed_trades(self):
        return len([trade for trade in self.trades if trade.status == "failure"])

    @property
    def successful_trades(self):
        return len([trade for trade in self.trades if trade.status == "success"])

    @property
    def total_trades(self):
        return len(self.trades)

    @property
    def total_profit(self):
        profit = 0
        for trade in self.trades:
            if trade.status == "success":
                if trade.trade_type == "long":
                    profit += trade.take_profit - trade.entry_price
                elif trade.trade_type == "short":
                    profit += trade.entry_price - trade.take_profit
            elif trade.status == "failure":
                if trade.trade_type == "long":
                    profit -= trade.entry_price - trade.stop_price
                elif trade.trade_type == "short":
                    profit -= trade.stop_price - trade.entry_price
        return profit

    def calculate_trade_parameters(self, high, low):
        sideway_height = (high / low) - 1
        deviation = 0.05 * sideway_height
        return deviation, sideway_height

    def calculate_trade_parameters_short_order(self, high, low, mid):
        deviation, sideway_height = self.calculate_trade_parameters(high, low)
        short_entry = high * (1 + deviation)
        short_stop = high * (1 + sideway_height / 2)
        short_take_profit = mid
        return short_entry, short_stop, short_take_profit

    def calculate_trade_parameters_long_order(self, high, low, mid):
        deviation, sideway_height = self.calculate_trade_parameters(high, low)
        long_entry = low * (1 - deviation)
        long_stop = low * (1 - sideway_height / 2)
        long_take_profit = mid
        return long_entry, long_stop, long_take_profit

    def place_short_trade(self, high, low, mid):
        entry_price, stop_price, take_profit = (
            self.calculate_trade_parameters_short_order(high, low, mid)
        )
        trade = Trade("short", entry_price, stop_price, take_profit)
        self.trades.append(trade)
        return trade

    def place_long_trade(self, high, low, mid):
        entry_price, stop_price, take_profit = (
            self.calculate_trade_parameters_long_order(high, low, mid)
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

        # if trade is not opened
        if trade.status is None:
            is_long_order_open = trade.trade_type == "long" and low_price >= trade.entry_price
            is_short_order_open = trade.trade_type == "short" and high_price <= trade.entry_price
            if is_long_order_open or is_short_order_open:
                trade.open_trade(time)
                trade.log_opened_trade()

        elif trade.status == "open":

            if trade.trade_type == "short":
                if low_price <= trade.take_profit:
                    trade.close_trade("success", time)
                    trade.log_completed_trade()
                elif high_price >= trade.stop_price:
                    trade.close_trade("failure", time)
                    trade.log_completed_trade()

            elif trade.trade_type == "long":
                if high_price >= trade.take_profit:
                    trade.close_trade("success", time)
                    trade.log_completed_trade()
                elif low_price <= trade.stop_price:
                    trade.close_trade("failure", time)
                    trade.log_completed_trade()

    def log_trade_summary(self):
        logger.info(
            f"Trade summary: Total={self.total_trades}, Successful={self.successful_trades}, "
            f"Failed={self.failed_trades}, Net profit/loss={self.total_profit:.2f}"
        )

    def has_uncompleted_trade(self):
        return any(
            trade.status is None or trade.status == "open" for trade in self.trades
        )
