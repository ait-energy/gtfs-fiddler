from pathlib import Path
from typing import Hashable

import gtfs_kit as gk
import pandas as pd
from gtfs_kit.feed import Feed
from pandas import DataFrame, Series


class Fiddle:
    """Wrapper of Feed providing getter methods with proper type annotations for better autocompletion"""

    def __init__(self, p: Path):
        self.feed = gk.read_feed(p, dist_units="km")
        self.feed.validate()

    def get_feed(self) -> Feed:
        return self.feed

    def get_routes(self) -> DataFrame:
        return self.feed.routes

    def get_trips(self) -> DataFrame:
        return self.feed.trips

    def get_stop_times(self) -> DataFrame:
        return self.feed.stop_times

    def tripcount_per_route_and_service(self) -> Series:
        return self.get_trips().groupby(["route_id", "service_id"]).size()

    def densify(self, multiplier):
        """
        insert <factor> trips between each previously existing pair of trips (per route and service)
        with departure times evenly distributed
        """
        groups = self._trips_to_be_densified()
        df_to_merge = [self.get_trips()]
        for name, labels in groups.items():
            for i in range(2, multiplier + 1):
                trips_for_group = self.get_trips().loc[labels].copy()
                trips_for_group["trip_id"] = trips_for_group["trip_id"] + f"#{i}"
                df_to_merge.append(trips_for_group)

        self.feed.trips = pd.concat(df_to_merge)

    def _trips_to_be_densified(self) -> dict[Hashable, list[Hashable]]:
        groups = self.get_trips().groupby(["route_id", "service_id"]).groups
        return {k: v for k, v in groups.items() if len(v) > 1}
