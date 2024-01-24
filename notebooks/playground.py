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
        first = 


    st_mod = st.loc[list(trip_ids)]
    st_mod = st_mod.groupby("trip_id").apply(time_adjust)
    
#%%
st = compute_stop_time_stats(f.feed)
st = st.sort_values(["trip_id", "stop_sequence"]).set_index("trip_id")
st = st.loc[["999.T0.23-70A-j22-1.3.R"]]

#%%
import importlib
from gtfs_fiddler import gtfs_time
importlib.reload(gtfs_time)
from gtfs_fiddler.gtfs_time import GtfsTime
from pandas import DataFrame

def adjust_trip(df, speed):
    """adjust stop times (of a single trip)"""
    seconds_to_next_stop_new = ((df.dist_to_next_stop / speed) * 3600)
    seconds_to_next_stop_min = DataFrame([df.seconds_to_next_stop.values, seconds_to_next_stop_new.values]).min()
    traveltime_cumsum = seconds_to_next_stop_min.shift(periods=1).cumsum()
    traveltime_cumsum.iloc[0] = 0
    
    stay_seconds = (st.departure_time - st.arrival_time).apply(lambda v: v.seconds_of_day)
    first_arrival_time = df.iloc[0].arrival_time
    df["arrival_time_new"] = (traveltime_cumsum.apply(lambda v : GtfsTime(v)) + first_arrival_time).values
    df["departure_time_new"] = df.arrival_time_new + stay_seconds
    return df

s = adjust_trip(st, 30)#.arrival_time_new
type(s)
s

# %%
st = compute_stop_time_stats(f.feed)
st = st[st.trip_id == "CNS2014-CNS_MUL-Sunday-00-4165971"]

# %%
def adjust_trip(df, speed):
    """adjust stop times (of a single trip)"""
    seconds_to_next_stop_new = ((df.dist_to_next_stop / speed) * 3600)
    seconds_to_next_stop_min = pd.DataFrame([df.seconds_to_next_stop.values, seconds_to_next_stop_new.values]).min()
    traveltime_cumsum = seconds_to_next_stop_min.shift(periods=1).cumsum()
    traveltime_cumsum.iloc[0] = 0
    
    stay_seconds = (st.departure_time - st.arrival_time).apply(lambda v: v.seconds_of_day)
    first_arrival_time = df.iloc[0].arrival_time
    df = df.copy()
    df["arrival_time_new"] = (traveltime_cumsum.apply(lambda v : GtfsTime(v)) + first_arrival_time).values
    #return df["arrival_time_new"] 
    df["departure_time_new"] = df.arrival_time_new + stay_seconds

    df["seconds_to_next_stop_min"] = seconds_to_next_stop_min
    df["traveltime_cumsum"] = traveltime_cumsum

    return df[["arrival_time", "departure_time", 
               'shape_dist_traveled',  'dist_to_next_stop', 
               'seconds_to_next_stop', 'speed',"seconds_to_next_stop_min","traveltime_cumsum","arrival_time_new", "departure_time_new"]]

adjust_trip(st, 10)






# %%
from gtfs_kit.stop_times import append_dist_to_stop_times
import gtfs_kit.helpers as hp
def compute_stop_time_stats(feed):
    """
    returns a copy of the stop_times df with the additional columns
    `seconds_to_next_stop`, `dist_to_next_stop`, `speed` (in either mph or kph depending on the feed's distance unit).
    Also `arrival_time` and `departure_time` are converted to GtfsTime.
    """
    st = feed.stop_times
    if "shape_dist_traveled" in st.columns:
        st = st.copy()
    else:
        st = append_dist_to_stop_times(feed).stop_times
                
    # convert to km or mi
    if hp.is_metric(feed.dist_units):
        convert_dist = hp.get_convert_dist(feed.dist_units, "km")
    else:
        convert_dist = hp.get_convert_dist(feed.dist_units, "mi")
    st.shape_dist_traveled = st.shape_dist_traveled.apply(convert_dist).ffill()

    st.arrival_time = st.arrival_time.apply(GtfsTime)
    st.departure_time = st.departure_time.apply(GtfsTime)

    #st = st[st.arrival_time]

    def seconds_to_next_stop(df):
        departure = df.departure_time.reset_index(drop=True).apply(
            lambda v: v.seconds_of_day
        )
        arrival = (
            df.arrival_time[1:].reset_index(drop=True).apply(lambda v: v.seconds_of_day)
        )
        return arrival - departure

    st = st.sort_values(by=["trip_id", "stop_sequence"])
    st["seconds_to_next_stop"] = (
        st.groupby(["trip_id"]).apply(seconds_to_next_stop).values
    )
    st["dist_to_next_stop"] = (
        st.groupby("trip_id")["shape_dist_traveled"].diff(periods=-1) * -1
    )
    # speed in distance unit per hour
    st["speed"] = st.dist_to_next_stop / (st.seconds_to_next_stop / 3600)
    return st

x = compute_stop_time_stats(f.feed)
y = x[x.trip_id == "CNS2014-CNS_MUL-Sunday-00-4165971"]
y

# %%
