# %%
import importlib
from datetime import date
from pathlib import Path

import gtfs_kit as gk
import pandas as pd
from gtfs_kit.validators import check_stop_times

from gtfs_fiddler.fiddle import GtfsFiddler

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
trips = f.sorted_trips
df = trips[trips.route_id == "23-92A-j22-2"]
# %%
