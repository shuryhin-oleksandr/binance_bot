from datetime import datetime

def get_unix_timestamp(date_str):
    return int(datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').timestamp() * 1000)


def convert_unix_to_str(unix_timestamp):
    return datetime.fromtimestamp(unix_timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')


def show_point(point):
    print(
        f"Start time: {point['start_time']}, End Time: {point['end_time']}, Closing Time: {point['closing_time']}, "
        f"Price: {point['price']}, Min Price: {point['min_price']}"
    )

def show_high_point(point):
    print(f"High point: (the the price increased by {point['percent_rised']}% from its peak.)")
    show_point(point)

def show_low_point(point):
    print(f"Low point: (the price has dropped by {point['percent_drop']})")
    show_point(point)
