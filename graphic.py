import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime


def initialize_plot():

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
    ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=5))
    plt.xticks(rotation=45)

    plt.xlabel('Closing Time')
    plt.ylabel('Price')
    plt.title('Real-Time Price Visualization')
    plt.grid(True)

    line, = ax.plot([], [], 'bo-', label='All Prices', markersize=5)
    plt.legend()
    plt.tight_layout()

    return fig, ax, line


def update_plot(ax, line, all_points, condition_met_points):
    
    all_prices_times = [datetime.strptime(point['closing_time'], '%Y-%m-%d %H:%M:%S') for point in all_points]
    all_prices_prices = [point['price'] for point in all_points]
    # Plot all points in blue
    line.set_data(all_prices_times, all_prices_prices)


    # Highlight condition_met_points in red
    if  condition_met_points:
        condition_met_times = [datetime.strptime(point['closing_time'], '%Y-%m-%d %H:%M:%S') for point in condition_met_points]
        condition_met_prices = [point['price'] for point in condition_met_points]
        ax.plot(condition_met_times, condition_met_prices, 'ro', label='Condition Met Points', markersize=8)

    ax.relim()
    ax.autoscale_view()
    plt.draw()
    plt.pause(0.001)
