import math
from typing import Self


class GtfsTime:
    """
    Encapsulates HH:MM:SS time strings as used in GTFS to seconds
    to enable comparisons and simple arithmetics.
    Allows for hour values larger than 24.
    """

    def __init__(self, time: Self | str | int | float):
        """
        Args:
          time:
             either a HH:MM[:SS] string or seconds of day. float values are rounded.
        """
        if isinstance(time, GtfsTime):
            self.seconds_of_day = time.seconds_of_day
        elif isinstance(time, int):
            self.seconds_of_day = time
        elif isinstance(time, float):
            self.seconds_of_day = time
            if not math.isnan(time):
                self.seconds_of_day = round(time)
        elif time == "":
            self.seconds_of_day = math.nan
        else:
            tokens = time.split(":")
            try:
                self.seconds_of_day = int(tokens[0]) * 60 * 60
                self.seconds_of_day += int(tokens[1]) * 60
                if len(tokens) > 2:
                    self.seconds_of_day += int(tokens[2])
            except:
                raise ValueError(f"expected HH:MM:SS format but got {time}")

    def isnan(self):
        return math.isnan(self.seconds_of_day)

    def __repr__(self):
        if math.isnan(self.seconds_of_day):
            return ""
        hours = int(self.seconds_of_day / (60 * 60))
        minutes = int(self.seconds_of_day / 60) % 60
        seconds = self.seconds_of_day % 60
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    def __hash__(self):
        return self.seconds_of_day

    def __eq__(self, other: Self) -> bool:
        return self.seconds_of_day == other.seconds_of_day

    def __lt__(self, other: Self) -> bool:
        return self.seconds_of_day < other.seconds_of_day

    def __gt__(self, other: Self) -> bool:
        return self.seconds_of_day > other.seconds_of_day

    def __sub__(self, other: int | float | Self) -> Self:
        secs = other
        if isinstance(other, GtfsTime):
            secs = other.seconds_of_day
        return GtfsTime(self.seconds_of_day - secs)

    def __add__(self, other: int | float | Self) -> Self:
        secs = other
        if isinstance(other, GtfsTime):
            secs = other.seconds_of_day
        return GtfsTime(self.seconds_of_day + secs)
