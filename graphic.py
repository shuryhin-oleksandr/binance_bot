import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from datetime import datetime, timedelta
from utils import convert_unix_to_str

matplotlib.use("TkAgg")

def set_point_price(point):
    if point["status"] == "high" or  point["status"] == "mid":
        point["price"] = point["high"]
    elif point["status"] == "low":
        point["price"] = point["low"]
    else:
        point["price"] = point["close"]

class Graphic:
    def __init__(self):
        self.fig, self.ax = plt.subplots(
            figsize=(12, 6)
        )  # axes encapsulates all the elements of an individual (sub-)plot in a figure
        self._initialize_plot()
        (self.line,) = self.ax.plot([], [], "bo-", label="All Prices", markersize=1)
        self.current_page = 0
        self.points_per_page = 1440 * 100  # ~ 100days
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
            point["closeTime"] = datetime.strptime(
                convert_unix_to_str(point["closeTime"]), "%Y-%m-%d %H:%M:%S"
            )
            set_point_price(point)
            # Add the time and price to respective x and y data lists for plotting
            self.x_data.append(point["closeTime"])
            self.y_data.append(point["price"])

        max_page = (len(self.x_data) - 1) // self.points_per_page
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
        new_point["closeTime"] = datetime.strptime(
            convert_unix_to_str(new_point["closeTime"]), "%Y-%m-%d %H:%M:%S"
        )
        set_point_price(new_point)

        x_data = list(x_data) + [new_point["closeTime"]]
        y_data = list(y_data) + [new_point["price"]]
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
        start_idx = self.current_page * self.points_per_page
        end_idx = min((self.current_page + 1) * self.points_per_page, len(self.x_data))

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
                # Last high point before low must be with label and line
                self._plot_last_point(high_points[-1], color="k", label="High:")
            elif kline["status"] == "mid":
                mid_points.append(kline)
                 # Last low point before mid point must be with label and line
                self._plot_last_point(low_points[-1], color="r", label="Low:")

        self.plot_all_points(high_points, color="k")
        self.plot_all_points(low_points, color="r")

        for point in mid_points:
            self._plot_last_point(point, color="m", label="Mid:")

        self.ax.relim()
        self.ax.autoscale_view()
        self.ax.legend()

        self.fig.canvas.draw_idle()
        plt.show()

    def plot_all_points(self, points, color):
        for point in points:
            self._plot_point(point, color=color)

    def _update_plot_with_slider(self, val):
        self.current_page = int(val)
        self.paginate_plot()

    def _plot_point(self, point, color):

        self.ax.plot(point["closeTime"], point["price"], color[0] + "o", markersize=2)
        return point["closeTime"], point["price"]

    def _plot_last_point(self, point, color, label):
        x_offset = 30
        y_offset = 100
        if point:
            point_time, point_price = self._plot_point(point, color)
            self.ax.text(
                point_time + timedelta(minutes=x_offset),
                point_price + y_offset,
                f"{label} {point_price} {point_time}",
                fontsize=8,
                verticalalignment="bottom",
            )

            self.ax.axhline(y=point_price, color=color, linestyle="--", linewidth=0.8)
