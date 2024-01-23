# %%
import importlib
import math
from datetime import date
from pathlib import Path

import gtfs_kit as gk
import pandas as pd
from gtfs_kit.validators import check_stop_times

from gtfs_fiddler.fiddle import (
    GtfsFiddler,
    trips_for_route,
    make_unique,
    cumcount,
    compute_stop_time_stats,
)
from gtfs_fiddler.gtfs_time import GtfsTime

DATA_PATH = Path("../data")
print(f"working with data in {DATA_PATH.resolve().absolute()}")

# %% load cairns
GTFS_PATH = DATA_PATH / "cairns_gtfs.zip"
f = GtfsFiddler(GTFS_PATH, "km", date(2014, 6, 1))

# %% load VOR
GTFS_PATH = DATA_PATH / "20221105-0340_gtfs_vor_2022_busiestDayOnly.zip"
f = GtfsFiddler(GTFS_PATH, "m")

# %%
from gtfs_kit.stop_times import append_dist_to_stop_times

st = f.stop_times
if "shape_dist_traveled" in st.columns:
    st = st.copy()
else:
    st = append_dist_to_stop_times(f.feed).stop_times

st.arrival_time = st.arrival_time.apply(GtfsTime)
st.departure_time = st.departure_time.apply(GtfsTime)


def compute_stop_time_stats(feed: Feed):
    """
    returns a copy of the stop_times df with the additional columns
    `seconds_to_next_stop`, `dist_to_next_stop`, `speed`.
    """
    pass


# %%
def seconds_to_next_stop(df):
    departure = df.departure_time.reset_index(drop=True).apply(
        lambda v: v.seconds_of_day
    )
    arrival = (
        df.arrival_time[1:].reset_index(drop=True).apply(lambda v: v.seconds_of_day)
    )
    return arrival - departure


def seconds_to_next_stop(df):
    departure = df.departure_time.reset_index(drop=True).apply(
        lambda v: v.seconds_of_day
    )
    arrival = (
        df.arrival_time[1:].reset_index(drop=True).apply(lambda v: v.seconds_of_day)
    )
    return arrival - departure


st["seconds_to_next_stop"] = st.groupby(["trip_id"]).apply(seconds_to_next_stop).values
st["dist_to_next_stop"] = (
    st.groupby("trip_id")["shape_dist_traveled"].diff(periods=-1) * -1
)
st["speed"] = st.dist_to_next_stop / (st.seconds_to_next_stop / 3600)

# TODO shape dist traveled auch anpassen!
# %%

st = compute_stop_time_stats(f.feed)
st.set_index("trip_id").loc["CNS2014-CNS_MUL-Sunday-00-4165971"]

# %%
