# %%
import gtfs_kit as gk
from gtfs_kit.validators import check_stop_times
from pathlib import Path
import pandas as pd

DATA_PATH = Path("../data")
print(f"working with data in {DATA_PATH.resolve().absolute()}")
CAIRNS = DATA_PATH / "cairns_gtfs.zip"
CAIRNS_MODIFIED = DATA_PATH / "cairns_gtfs_modified.zip"

# %%
feed = gk.read_feed(CAIRNS, dist_units="km")
# feed.describe()


trip_stats = feed.compute_trip_stats()
trip2service = feed.trips[["trip_id", "service_id"]]
joined = trip_stats.join(trip2service.set_index("trip_id"), on="trip_id")


# %%
# reduce feed to busiest day
from gtfs_kit.miscellany import restrict_to_dates

CAIRNS_BUSIEST_DAY = DATA_PATH / "cairns_busiest_day_only.zip"
busiest_date = feed.compute_busiest_date(feed.get_dates())
print(f"busiest date: {busiest_date}")
restricted_feed = restrict_to_dates(feed, [busiest_date])
restricted_feed.write(CAIRNS_BUSIEST_DAY)

# %%
gk.read_feed(CAIRNS, dist_units="km")


st = feed.stop_times
print(f"found {len(st)} stop times")


# feed.stop_times[["stop_sequence"]] = 1
err = check_stop_times(feed)
if len(err) > 0:
    print(err)
else:
    print("all good!")

# feed.validate()

# %%
x = st.groupby(["trip_id"])
import pandas as pd

y = pd.read_csv("yolo")
blu = y.groupby("x")


# %%
from gtfs_fiddler.fiddle import Fiddle

fiddle = Fiddle(CAIRNS)
# st = fiddle.get_stop_times()
# st.groupby("trip_id").first().index
# %%
