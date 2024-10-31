import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from datetime import datetime
from utils import convert_unix_to_str

matplotlib.use("TkAgg")


class Graphic:
    def __init__(self):
        self.fig, self.ax = plt.subplots(figsize=(12, 6))
        self._initialize_plot()
        (self.line,) = self.ax.plot([], [], "bo-", label="All Prices", markersize=1)
        self.current_page = 0
        self.points_per_page = 1440
        self.slider = self._create_slider()

    def _initialize_plot(self):
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
        self.ax.xaxis.set_minor_locator(mdates.DayLocator(interval=1))
        self.ax.grid(True)

        self.ax.set_xlabel("Date")
        self.ax.set_ylabel("Price")

    def _create_slider(self):
        slider_ax = self.fig.add_axes(
            [0.2, 0.02, 0.6, 0.03], facecolor="lightgoldenrodyellow"
        )
        slider = Slider(slider_ax, "Page", 0, 1, valinit=0, valstep=1)
        slider.on_changed(self._update_plot_with_slider)
        return slider

    def create_plot_for_historical_data(self, all_points):
        self.all_points = all_points
        self.x_data = []
        self.y_data = []

        for point in all_points:
            new_time = datetime.strptime(
                convert_unix_to_str(point["closeTime"]), "%Y-%m-%d %H:%M:%S"
            )
            new_price = point["close"]
            self.x_data.append(new_time)
            self.y_data.append(new_price)

        max_page = (len(self.x_data) - 1) // self.points_per_page // 100
        self.slider.valmax = max_page  #  Max slider value
        self.slider.ax.set_xlim(
            0, max_page
        )  # Display the slider scale according to the number of pages
        self.slider.set_val(0)  # Set first page
        self.slider.ax.figure.canvas.draw_idle()

        self.paginate_plot()

    def _clear_old_labels(self):
        for child in self.ax.get_children():
            if isinstance(child, plt.Text):
                if child.get_text().startswith("High:") or child.get_text().startswith(
                    "Low:"
                ):
                    child.remove()

    def _remove_dashed_line(self, color):
        for child in self.ax.get_children():
            if isinstance(child, plt.Line2D) and child.get_linestyle() == "--":
                if child.get_color() == color:
                    child.remove()

    def update_plot_real_time(self, new_point):
        # Get data
        x_data = self.line.get_xdata()
        y_data = self.line.get_ydata()

        # Add new data
        new_time = datetime.strptime(
            convert_unix_to_str(new_point["closeTime"]), "%Y-%m-%d %H:%M:%S"
        )
        new_price = new_point["close"]

        x_data = list(x_data) + [new_time]
        y_data = list(y_data) + [new_price]
        self.line.set_data(x_data, y_data)

        # Keep axis constraints for automatic scaling
        self.ax.relim()
        self.ax.autoscale_view()

        self._clear_old_labels()

        # Show high, low, and mid points
        if new_point["status"] == "high":
            self._plot_last_point(new_point, "k", "High:")
        elif new_point["status"] == "low":
            self._plot_last_point(new_point, "r", "Low:")
        elif new_point["status"] == "mid":
            self._plot_last_point(new_point, "m", "Mid:")

        self.fig.canvas.draw_idle()
        plt.show()

    def paginate_plot(self):
        # clear graphic
        self.ax.clear()
        self._initialize_plot()

        # Calculation of indices for the current page
        start_idx = self.current_page * self.points_per_page * 100
        end_idx = min(
            (self.current_page + 1) * self.points_per_page * 100, len(self.x_data)
        )

        # Draw line
        self.ax.plot(
            self.x_data[start_idx:end_idx],
            self.y_data[start_idx:end_idx],
            "bo-",
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
            elif kline["status"] == "mid":
                mid_points.append(kline)

        self.plot_all_points(high_points, color="k", label="High:")
        self.plot_all_points(low_points, color="r", label="Low:")

        for point in mid_points:
            self._plot_last_point(point, color="m", label="Mid:")

        self.ax.relim()
        self.ax.autoscale_view()
        self.ax.legend()

        self.fig.canvas.draw_idle()
        plt.show()

    def plot_all_points(self, points, color, label=None):
        for point in points:
            self._plot_point(point, color=color)
        if points:
            self._plot_last_point(points[-1], color=color, label=label)

    def _update_plot_with_slider(self, val):
        self.current_page = int(val)
        self.paginate_plot()

    def _plot_point(self, point, color):

        point_time = datetime.strptime(
            convert_unix_to_str(point["closeTime"]), "%Y-%m-%d %H:%M:%S"
        )
        point_price = point["close"]

        self.ax.plot(point_time, point_price, color[0] + "o", markersize=4)
        return point_time, point_price

    def _plot_last_point(self, point, color, label):
        if point:
            point_time, point_price = self._plot_point(point, color)
            self.ax.text(
                point_time,
                point_price,
                f"{label} {point_price} {point_time}",
                fontsize=8,
                verticalalignment="bottom",
            )

            self._remove_dashed_line(color)
            self.ax.axhline(y=point_price, color=color, linestyle="--", linewidth=0.8)
