from datetime import date
from pathlib import Path
from typing import Hashable

import gtfs_kit as gk
import pandas as pd
from gtfs_kit.feed import Feed
from gtfs_kit.miscellany import restrict_to_dates
from pandas import DataFrame, Series

from gtfs_fiddler.gtfs_time import GtfsTime


class GtfsFiddler:
    """
    Built on top of gtfs_kit.Feed to:
    - Provide typed access to the feed's members (autocompletion!)
    - Densify a feed by copying trips (and adjusting the copies' times)
    """

    def __init__(self, p: Path, dist_units: str, date: date | None = None):
        self._original_feed = gk.read_feed(p, dist_units=dist_units)
        self._original_feed.validate()
        if date is not None:
            datestr = date.isoformat().replace("-", "")
            self._feed = restrict_to_dates(self._original_feed, [datestr])
        else:
            self._feed = self._original_feed
        # self._sorted_trips = GtfsFiddler._update_sorted_trips(self._feed)

    def sorted_trips(self) -> DataFrame:
        trip_stats = self._feed.compute_trip_stats()
        trip2service = self._feed.trips[["trip_id", "service_id", "trip_headsign"]]
        df = trip_stats.join(trip2service.set_index("trip_id"), on="trip_id")
        df.start_time = df.start_time.apply(GtfsTime)
        df.end_time = df.end_time.apply(GtfsTime)
        return df.sort_values(by=["route_id", "direction_id", "start_time"])

    @property
    def feed(self) -> Feed:
        return self._feed

    @property
    def routes(self) -> DataFrame:
        return self._feed.routes

    @property
    def trips(self) -> DataFrame:
        return self._feed.trips

    def trips_for_route(self, route_id, direction_id) -> DataFrame:
        df = self._feed.trips
        return df[(df.route_id == route_id) & (df.direction_id == direction_id)]

    # @property
    # def sorted_trips(self) -> DataFrame:
    #    return self._sorted_trips

    @property
    def stop_times(self) -> DataFrame:
        return self._feed.stop_times

    def tripcount_per_route_and_service(self) -> Series:
        return self.trips.groupby(["route_id", "service_id"]).size()

    def ensure_earliest_departure(self, time: GtfsTime):
        """
        In case the earliest trip departs later than the given time,
        this trip is copied and set to start at that time.
        """
        # TODO avoid using sorted_trips?
        t = self.sorted_trips()
        first_trip = t.groupby(["route_id", "direction_id"]).first()
        trips_to_adjust = first_trip[first_trip.start_time > time].trip_id
        print(f"need to copy {len(trips_to_adjust)} trips")

        dup_trips = self.trips.set_index("trip_id").loc[trips_to_adjust]
        dup_trips = dup_trips.copy().reset_index()
        dup_trips.trip_id = dup_trips.trip_id + "#early"

        self._feed.trips = pd.concat([self.trips, dup_trips])
        # for route_id, direction_id in routes_to_adjust.index:
        # copy first trip to earliest departure
        # copy and adjust stop_times

    def ensure_latest_departure(self, time: GtfsTime):
        """
        In case the latest trip departs earlier than the given time,
        this trip is copied and set to start at that time.
        """
        pass

    def ensure_max_trip_interval(self, minutes: int):
        """
        For each interval (between two trips) larger than the given maximum
        new trip(s) are inserted by duplicating the first trip.

        Note, that this only works reliably if the feed was reduced to a single day.
        Otherwise the trips sorted by start time will be intermixed for different days.
        """
        pass
