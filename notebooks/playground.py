# %%
import importlib
import math
from datetime import date
from pathlib import Path

import gtfs_kit as gk
import pandas as pd
from gtfs_kit.validators import check_stop_times

from gtfs_fiddler.fiddle import GtfsFiddler, trips_for_route, make_unique, cumcount
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
f.feed.describe()

# %%
trips = f.trips_enriched
df = trips[trips.route_id == "23-92A-j22-2"]
# %%


def add_time_to_next_trip(df):
    start = df.start_time.reset_index(drop=True)
    next_start = df.start_time[1:].reset_index(drop=True)
    df["time_to_next_trip"] = (next_start - start).values
    return df


t = f.trips_enriched()
t.groupby(["route_id", "direction_id"]).apply(lambda df: add_time_to_next_trip(df))[
    ["start_time", "time_to_next_trip"]
]


snip = t.loc[t.groupby(["route_id", "direction_id"]).groups[("110-423", 0)]]

# %%
route_id = "110-423"
direction_id = 0
f.ensure_max_trip_interval(19)
df = f.trips_for_route(route_id, direction_id)
# %%


t = f.trips_enriched()
minutes = 19
t = t[t.time_to_next_trip > GtfsTime(minutes * 60)]
# %%
