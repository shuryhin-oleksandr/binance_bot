import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from datetime import datetime


def remove_dashes_line(ax, color):
    for child in ax.get_children():
        if isinstance(child, plt.Line2D) and child.get_linestyle() == '--':
            if child.get_color() == color:
                child.remove()


def plot_point(ax, point, color, label):
    if point:
        point_time = datetime.strptime(point['closing_time'], '%Y-%m-%d %H:%M:%S')
        point_price = point['price']

        ax.plot(point_time, point_price, color[0] + 'o', label=label, markersize=8)
        label_point = label.split(' ', 1)[0]
        ax.text(point_time, point_price, f'{label_point}: {point_price}', fontsize=8, verticalalignment='bottom')

        # Remove any existing dashed line of the specified color
        remove_dashes_line(ax, color)

        # Draw the horizontal line
        ax.axhline(y=point_price, color=color, linestyle='--', linewidth=0.8)

def is_mid_point_label_present(ax):
    for child in ax.get_children():
        if isinstance(child, plt.Text) and child.get_text().startswith("Mid:"):
            return True
    return False

def clear_old_labels(ax):
    for child in ax.get_children():
        if isinstance(child, plt.Text):
            if child.get_text().startswith("High:") or child.get_text().startswith("Low:"):
                child.remove()

def initialize_plot():
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
    ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=5))
    plt.xticks(rotation=90)

    plt.xlabel('Closing Time')
    plt.ylabel('Price')
    plt.title('Real-Time Price Visualization with High, Low, and Mid Points')
    plt.grid(True)

    line, = ax.plot([], [], 'bo-', label='All Prices', markersize=5)
    plt.legend()
    plt.tight_layout()

    return fig, ax, line


def update_plot(line, new_point, high_point=None, low_point=None, mid_point=None):
    # Get data
    x_data = line.get_xdata()
    y_data = line.get_ydata()

    # Add new data
    new_time = datetime.strptime(new_point['closing_time'], '%Y-%m-%d %H:%M:%S')
    new_price = new_point['price']
    
    if mid_point and len(x_data) > 0:
        last_time = x_data[-1]
        last_price = y_data[-1]
        ax = line.axes
        ax.plot([last_time, new_time], [last_price, new_price], 'yo-', markersize=5)  # Yellow line for new segment

    # Otherwise, extend the blue line
    x_data = list(x_data) + [new_time]
    y_data = list(y_data) + [new_price]
    line.set_data(x_data, y_data)

    # Keep axis constraints for automatic scaling
    ax = line.axes
    ax.relim()
    ax.autoscale_view()

    clear_old_labels(ax)

    # Show high low and mid points
    plot_point(ax, high_point, 'green', 'High Point (Rise X%)')
    plot_point(ax, low_point, 'red', 'Low Point (Drop by Y%)')

    if mid_point and not is_mid_point_label_present(ax):
        plot_point(ax, mid_point, 'yellow', 'Mid Point')

    plt.draw()
    plt.pause(0.0001)
