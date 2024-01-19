from datetime import date
from pathlib import Path
from typing import Hashable

import gtfs_kit as gk
import pandas as pd
from gtfs_kit.feed import Feed
from gtfs_kit.miscellany import restrict_to_dates
from pandas import DataFrame, Series

from gtfs_fiddler.gtfs_time import GtfsTime


def filter_by_route(df: DataFrame, route_id, direction_id):
    return df[(df.route_id == route_id) & (df.direction_id == direction_id)]


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

    def trips_with_times(self) -> DataFrame:
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

    @property
    def stop_times(self) -> DataFrame:
        return self._feed.stop_times

    def tripcount_per_route_and_service(self) -> Series:
        return self.trips.groupby(["route_id", "service_id"]).size()

    def ensure_earliest_departure(self, target_time: GtfsTime):
        """
        In case the earliest trip departs later than the given time,
        this trip is copied and set to start at that time.
        """
        self._ensure_earliest_or_latest_departure(target_time, True)

    def ensure_latest_departure(self, target_time: GtfsTime):
        """
        In case the latest trip departs earlier than the given time,
        this trip is copied and set to start at that time.
        """
        self._ensure_earliest_or_latest_departure(target_time, False)

    def ensure_max_trip_interval(self, minutes: int):
        """
        For each interval (between two trips) larger than the given maximum
        new trip(s) are inserted by duplicating the first trip.

        Note, that this only works reliably if the feed was reduced to a single day.
        Otherwise the trips sorted by start time will be intermixed for different days.
        """

        pass

    def _ensure_earliest_or_latest_departure(
        self, target_time: GtfsTime, earliest: bool
    ):
        suffix = "#early" if earliest else "#late"
        # get trips enriched with arrival/departure times
        t = self.trips_with_times()

        # find the first/last trip of routes that need adjustment
        if earliest:
            first_trip = t.groupby(["route_id", "direction_id"]).first()
            trips_to_adjust = first_trip[first_trip.start_time > target_time].trip_id
        else:
            last_trip = t.groupby(["route_id", "direction_id"]).last()
            trips_to_adjust = last_trip[last_trip.start_time < target_time].trip_id

        # copy and adjust these trips, add them to the feed's trips
        dup_trips = self.trips.set_index("trip_id").loc[trips_to_adjust]
        dup_trips = dup_trips.copy().reset_index()
        dup_trips.trip_id = dup_trips.trip_id + suffix
        self._feed.trips = pd.concat([self.trips, dup_trips])

        # also copy and adjust relevant stop times
        st = self.stop_times.set_index("trip_id")
        dup_times = st.loc[trips_to_adjust].copy().reset_index()
        dup_times.trip_id = dup_times.trip_id + suffix
        dup_times.arrival_time = dup_times.arrival_time.apply(GtfsTime)
        dup_times.departure_time = dup_times.departure_time.apply(GtfsTime)
        dup_times = dup_times.sort_values(["trip_id", "stop_sequence"])
        dup_times = dup_times.groupby("trip_id").apply(
            lambda df: GtfsFiddler._adjust_stop_times(df, target_time)
        )
        dup_times.arrival_time = dup_times.arrival_time.apply(str)
        dup_times.departure_time = dup_times.departure_time.apply(str)
        self._feed.stop_times = pd.concat([self._feed.stop_times, dup_times])

    @staticmethod
    def _adjust_stop_times(stop_times: DataFrame, desired_start: GtfsTime):
        """
        set the departure time of the first stop to the desired start time
        and adjust all other departure and arrival times accordingly
        """
        adjustment = stop_times.iloc[0].departure_time - desired_start
        stop_times.arrival_time = stop_times.arrival_time - adjustment
        stop_times.departure_time = stop_times.departure_time - adjustment
        return stop_times
