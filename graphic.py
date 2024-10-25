import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from datetime import datetime
from utils import convert_unix_to_str

class Graphic:
    def __init__(self):
        self.fig, self.ax, self.line = self._initialize_plot()

    def _initialize_plot(self):
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=5))
        plt.xticks(rotation=90)

        plt.xlabel('Closing Time')
        plt.ylabel('Price')
        plt.title('Real-Time Price Visualization with High, Low, and Mid Points')
        plt.grid(True)

        line, = ax.plot([], [], 'bo-', label='All Prices', markersize=2)
        plt.legend()
        plt.tight_layout()

        # Enable zoom and pan
        fig.canvas.mpl_connect('scroll_event', lambda event: ax.set_xlim(auto=True))  # Zoom
        fig.canvas.mpl_connect('button_press_event', lambda event: ax.set_xlim(auto=True))  # Pan

        return fig, ax, line

    def _remove_dashed_line(self, color):
        for child in self.ax.get_children():
            if isinstance(child, plt.Line2D) and child.get_linestyle() == '--':
                if child.get_color() == color:
                    child.remove()

    def _plot_point(self, point, color, label):
        if point:
            point_time = datetime.strptime(convert_unix_to_str(point['closeTime']), '%Y-%m-%d %H:%M:%S')
            point_price = point['close']

            self.ax.plot(point_time, point_price, color[0] + 'o', label=label, markersize=5)
            label_point = label.split(' ', 1)[0]
            self.ax.text(point_time, point_price, f'{label_point}: {point_price}', fontsize=5, verticalalignment='bottom')

            # Remove any existing dashed line of the specified color
            self._remove_dashed_line(color)

            # Draw the horizontal line
            self.ax.axhline(y=point_price, color=color, linestyle='--', linewidth=0.8)

    def _is_mid_point_label_present(self):
        for child in self.ax.get_children():
            if isinstance(child, plt.Text) and child.get_text().startswith("Mid:"):
                return True
        return False

    def _clear_old_labels(self):
        for child in self.ax.get_children():
            if isinstance(child, plt.Text):
                if child.get_text().startswith("High:") or child.get_text().startswith("Low:"):
                    child.remove()

    def update_plot(self, new_point, high_point=None, low_point=None, mid_point=None):
        # Get data
        x_data = self.line.get_xdata()
        y_data = self.line.get_ydata()

        # Add new data
        new_time = datetime.strptime(convert_unix_to_str(new_point['closeTime']), '%Y-%m-%d %H:%M:%S')
        new_price = new_point['close']

        # Update plot lines for mid points
        if mid_point and len(x_data) > 0:
            last_time = x_data[-1]
            last_price = y_data[-1]
            self.ax.plot([last_time, new_time], [last_price, new_price], 'yo-', markersize=2)  # Yellow line for new segment

        # Otherwise, extend the blue line
        x_data = list(x_data) + [new_time]
        y_data = list(y_data) + [new_price]
        self.line.set_data(x_data, y_data)

        # Keep axis constraints for automatic scaling
        self.ax.relim()
        self.ax.autoscale_view()

        self._clear_old_labels()

        # Show high, low, and mid points
        self._plot_point(high_point, 'green', 'High Point (Rise X%)')
        self._plot_point(low_point, 'red', 'Low Point (Drop by Y%)')

        if mid_point and not self._is_mid_point_label_present():
            self._plot_point(mid_point, 'yellow', 'Mid Point')

        plt.draw()
        plt.pause(0.0001)
