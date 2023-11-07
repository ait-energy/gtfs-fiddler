# %%
import gtfs_kit as gk
from gtfs_kit.validators import check_stop_times
from pathlib import Path
import pandas as pd

DATA_PATH = Path("../data")
print(f"working with data in {DATA_PATH.resolve().absolute()}")
CAIRNS = DATA_PATH / "cairns_gtfs.zip"
CAIRNS_MODIFIED = DATA_PATH / "cairns_gtfs_modified.zip"

# %% basic usage of gtfs_kit
feed = gk.read_feed(CAIRNS, dist_units="km")
feed.describe()


# %% reduce feed to busiest day
from gtfs_kit.miscellany import restrict_to_dates

CAIRNS_BUSIEST_DAY = DATA_PATH / "cairns_busiest_day_only.zip"
busiest_date = feed.compute_busiest_date(feed.get_dates())
print(f"busiest date: {busiest_date}")
restricted_feed = restrict_to_dates(feed, [busiest_date])
restricted_feed.write(CAIRNS_BUSIEST_DAY)

# %% init fiddler
from gtfs_fiddler.fiddle import GtfsFiddler

fiddle = GtfsFiddler(CAIRNS)

# %%
