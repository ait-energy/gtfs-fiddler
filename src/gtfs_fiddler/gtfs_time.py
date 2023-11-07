import math
from typing import Self


class GtfsTime:
    def __init__(self, time: str | int | float):
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
                self.seconds_of_day += int(tokens[2])
            except:
                raise ValueError(f"expected HH:MM:SS format but got {time}")

    def __eq__(self, other: Self) -> bool:
        return self.seconds_of_day == other.seconds_of_day

    def __sub__(self, other: Self) -> Self:
        return GtfsTime(self.seconds_of_day - other.seconds_of_day)

    def __add__(self, other: Self) -> Self:
        return GtfsTime(self.seconds_of_day + other.seconds_of_day)
