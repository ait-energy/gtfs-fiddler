# %%
import importlib
import math
from datetime import date
from pathlib import Path

import gtfs_kit as gk
import pandas as pd
from gtfs_kit.validators import check_stop_times
from pandas import DataFrame

from gtfs_fiddler import gtfs_time
from gtfs_fiddler.fiddle import (
    GtfsFiddler,
    compute_stop_time_stats,
    cumcount,
    make_unique,
    trips_for_route,
)
from gtfs_fiddler.gtfs_time import GtfsTime

importlib.reload(gtfs_time)

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
# st.set_index("trip_id").loc["CNS2014-CNS_MUL-Sunday-00-4165971"]

# %%
import numpy as np

st.speed.replace([np.inf, -np.inf], np.nan).dropna().describe()

# %%
te = f.trips_enriched()
te = te.join(f.routes.set_index("route_id").agency_id, on="route_id")
# %% general speed statistics
te.groupby(by="route_type").apply(lambda v: v.speed.describe())

# %% speed statistics Wiener Linien only
wiener_linien = "04"
wl = te[te.agency_id == wiener_linien]
wl.groupby(by="route_type").apply(lambda v: v.speed.describe())
# %%
from collections.abc import Sequence

from pandas import DataFrame


def adjust_times(stop_times: DataFrame, trip_ids: Sequence[str], speed: float):
    st = stop_times.sort_values(["trip_id", "stop_sequence"]).set_index("trip_id")

    def adjust_trip(df):
        """adjust stop times (of a single trip)"""
        # first =

    st_mod = st.loc[list(trip_ids)]
    st_mod = st_mod.groupby("trip_id").apply(time_adjust)


# %%
st = compute_stop_time_stats(f.feed)
st = st.sort_values(["trip_id", "stop_sequence"]).set_index("trip_id")
st = st.loc[["999.T0.23-70A-j22-1.3.R"]]

# %%


# %%
st = compute_stop_time_stats(f.feed)
st = st[st.trip_id == "CNS2014-CNS_MUL-Sunday-00-4165971"]
