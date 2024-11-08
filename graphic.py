import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, TextBox
from datetime import datetime
from utils import convert_unix_full_date_str

matplotlib.use("TkAgg")


class Graphic:
    def __init__(self):
        self.fig, self.ax = plt.subplots(
            figsize=(12, 6)
        )  # axes encapsulates all the elements of an individual (sub-)plot in a figure
        self._initialize_plot()
        (self.line,) = self.ax.plot(
            [], [], "darkgrey", label="All Prices", markersize=1
        )
        self.current_page = 0
        self.points_per_page = 1440 * 100  # ~ 100days
        self._create_pagination_controls()

    def _initialize_plot(self):
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
        self.ax.xaxis.set_minor_locator(mdates.DayLocator(interval=1))
        self.ax.grid(True)

        self.ax.set_xlabel("Date")
        self.ax.set_ylabel("Price")

    def _create_pagination_controls(self):
        # Text box for setting points per page
        ax_textbox = plt.axes([0.1, 0.01, 0.1, 0.05])
        self.textbox = TextBox(
            ax_textbox, "Points per page:", initial=str(self.points_per_page)
        )
        self.textbox.on_submit(self._set_points_per_page)

        # Previous button
        ax_prev = plt.axes([0.3, 0.01, 0.1, 0.05])
        self.prev_button = Button(ax_prev, "Previous")
        self.prev_button.on_clicked(self._prev_page)

        # Next button
        ax_next = plt.axes([0.45, 0.01, 0.1, 0.05])
        self.next_button = Button(ax_next, "Next")
        self.next_button.on_clicked(self._next_page)

    def _set_points_per_page(self, text):
        try:
            self.points_per_page = max(
                1, int(text)
            )  # Ensures at least 1 point per page
            self.current_page = 0
            self.paginate_plot()
        except ValueError:
            pass

    def _prev_page(self, event):
        if self.current_page > 0:
            self.current_page -= 1
            self.paginate_plot()

    def _next_page(self, event):
        if (self.current_page + 1) * self.points_per_page < len(self.x_data):
            self.current_page += 1
            self.paginate_plot()

    def create_plot_for_historical_data(self, all_points):
        self.all_points = all_points
        self.x_data = []
        self.y_data = []

        for point in all_points:
            point["time"] = datetime.strptime(
                convert_unix_full_date_str(point["time"]), "%Y-%m-%d %H:%M:%S"
            )
            # Add the time and price to respective x and y data lists for plotting
            self.x_data.append(point["time"])
            self.y_data.append(point["price"])

        self.paginate_plot()

    def _clear_old_labels(self):
        for child in self.ax.get_children():
            if isinstance(child, plt.Text):
                if child.get_text().startswith("High:") or child.get_text().startswith(
                    "Low:"
                ):
                    child.remove()

    def update_plot_real_time(self, new_point):
        # Get data
        x_data = self.line.get_xdata()
        y_data = self.line.get_ydata()

        # Add new data
        new_point["time"] = datetime.strptime(
            convert_unix_full_date_str(new_point["time"]), "%Y-%m-%d %H:%M:%S"
        )
        x_data = list(x_data) + [new_point["time"]]
        y_data = list(y_data) + [new_point["price"]]
        self.line.set_data(x_data, y_data)
        # Keep axis constraints for automatic scaling
        self.ax.relim()
        self.ax.autoscale_view()

        self._clear_old_labels()

        # Show high, low, and mid points
        if new_point["status"] == "high":
            self._plot_last_point(new_point, "green", "High:")
        elif new_point["status"] == "low":
            self._plot_last_point(new_point, "red", "Low:")
        elif new_point["status"] == "mid":
            self._plot_last_point(new_point, "orange", "Mid:")

        self.fig.canvas.draw_idle()
        plt.show()

    def paginate_plot(self):
        # clear graphic
        self.ax.clear()
        self._initialize_plot()

        # Calculation of indices for the current page
        start_idx = self.current_page * self.points_per_page
        end_idx = min((self.current_page + 1) * self.points_per_page, len(self.x_data))

        # Draw line
        self.ax.plot(
            self.x_data[start_idx:end_idx],
            self.y_data[start_idx:end_idx],
            "darkgrey",
            label="All Prices",
            markersize=1,
        )

        all_klines = self.all_points[start_idx:end_idx]
        high_points = []
        low_points = []
        mid_points = []

        for kline in all_klines:
            if kline["status"] == "high":
                high_points.append(kline)
            elif kline["status"] == "low":
                low_points.append(kline)
                # Last high point before low must be with label
                if high_points:
                    self._plot_last_point(
                        high_points[-1], color="green", label="High:", markersize=4
                    )
            elif kline["status"] == "mid":
                mid_points.append(kline)
                # Last low point before mid point must be with label
                if low_points:
                    self._plot_last_point(
                        low_points[-1], color="red", label="Low:", markersize=4
                    )

        self.plot_all_points(high_points, color="green")
        self.plot_all_points(low_points, color="red")

        for point in mid_points:
            self._plot_last_point(point, color="orange", label="Mid:", markersize=4)

        self.ax.relim()
        self.ax.autoscale_view()
        self.ax.legend()

        self.fig.canvas.draw_idle()
        plt.show()

    def plot_all_points(self, points, color):
        for point in points:
            self._plot_point(point, color=color)

    def _plot_point(self, point, color, markersize=2):
        self.ax.plot(
            point["time"],
            point["price"],
            marker="o",
            color=color,
            markersize=markersize,
        )
        return point["time"], point["price"]

    def _plot_last_point(self, point, color, label, markersize=2):
        if point:
            point_time, point_price = self._plot_point(point, color, markersize)
            self.ax.text(
                point_time,
                point_price,
                f"{label} {point_price} {point_time}",
                fontsize=8,
                verticalalignment="bottom",
            )
