import math
from typing import Self


class GtfsTime:
    """
    Encapsulates HH:MM:SS time strings as used in GTFS to seconds
    to enable comparisons and simple arithmetics.
    Allows for hour values larger than 24.
    """

    def __init__(self, time: str | int | float):
        """
        param time: either a HH:MM[:SS] string or seconds of day
        """
        self.seconds_of_day = -1
        if isinstance(time, int):
            self.seconds_of_day = time
        elif isinstance(time, float):
            if not math.isnan(time):
                raise ValueError("only NaN floats are allowed")
        else:
            tokens = time.split(":")
            try:
                self.seconds_of_day = int(tokens[0]) * 60 * 60
                self.seconds_of_day += int(tokens[1]) * 60
                if len(tokens) > 2:
                    self.seconds_of_day += int(tokens[2])
            except:
                raise ValueError(f"expected HH:MM:SS format but got {time}")

    def __repr__(self):
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

    def __sub__(self, other: Self) -> Self:
        return GtfsTime(self.seconds_of_day - other.seconds_of_day)

    def __add__(self, other: Self) -> Self:
        return GtfsTime(self.seconds_of_day + other.seconds_of_day)
