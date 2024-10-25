from datetime import datetime


def get_unix_timestamp(date_str):
    return int(datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').timestamp() * 1000)


def convert_unix_to_str(unix_timestamp):
    return datetime.fromtimestamp(unix_timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')


def show_kline(kline):
    print(
        f"Start time: {convert_unix_to_str(kline['startTime'])}, Closing Time: {convert_unix_to_str(kline['closeTime'])}, "
        f"Price: {kline['close']}"
    )


def show_high_kline(kline):
    print(f"High kline: (the the price increased by {kline['percent_rised']}% from its peak.)")
    show_kline(kline)


def show_low_kline(kline):
    print(f"Low kline: (the price has dropped by {kline['percent_drop']}%)")
    show_kline(kline)
