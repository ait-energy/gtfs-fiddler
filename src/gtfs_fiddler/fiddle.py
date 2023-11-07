from pathlib import Path
from typing import Hashable

import gtfs_kit as gk
import pandas as pd
from gtfs_kit.feed import Feed
from pandas import DataFrame, Series


class GtfsFiddler:
    """
    Built on top of gtfs_kit.Feed to:
    - Provide typed access to the feed's members (autocompletion!)
    - Densify a feed by copying trips (and adjusting the copies' times)
    """

    def __init__(self, p: Path):
        self._feed = gk.read_feed(p, dist_units="km")
        self._feed.validate()
        self._sorted_trips = GtfsFiddler._prepare_trips(self._feed)

    @staticmethod
    def _prepare_trips(feed: Feed) -> DataFrame:
        trip_stats = feed.compute_trip_stats()
        trip2service = feed.trips[["trip_id", "service_id"]]
        joined = trip_stats.join(trip2service.set_index("trip_id"), on="trip_id")
        return joined.sort_values(
            by=["route_id", "direction_id", "service_id", "start_time"]
        )

    @property
    def feed(self) -> Feed:
        return self._feed

    @property
    def routes(self) -> DataFrame:
        return self._feed.routes

    @property
    def trips(self) -> DataFrame:
        return self._feed.trips

    @property
    def sorted_trips(self) -> DataFrame:
        return self._sorted_trips

    @property
    def stop_times(self) -> DataFrame:
        return self._feed.stop_times

    def tripcount_per_route_and_service(self) -> Series:
        return self.trips.groupby(["route_id", "service_id"]).size()

    def densify(self, multiplier):
        """
        insert <factor> trips between each previously existing pair of trips (per route and service)
        with departure times evenly distributed
        """
        groups = self._trips_to_be_densified()
        df_to_merge = [self.trips]
        for name, labels in groups.items():
            for i in range(2, multiplier + 1):
                trips_for_group = self.trips.loc[labels].copy()
                trips_for_group["trip_id"] = trips_for_group["trip_id"] + f"#{i}"
                df_to_merge.append(trips_for_group)

        self._feed.trips = pd.concat(df_to_merge)

    def _trips_to_be_densified(self) -> dict[Hashable, list[Hashable]]:
        groups = self.trips.groupby(["route_id", "service_id"]).groups
        return {k: v for k, v in groups.items() if len(v) > 1}
