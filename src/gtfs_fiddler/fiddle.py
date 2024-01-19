import math
from datetime import date
from pathlib import Path
from typing import Hashable

import gtfs_kit as gk
import pandas as pd
from gtfs_kit.feed import Feed
from gtfs_kit.miscellany import restrict_to_dates
from pandas import DataFrame, Series

from gtfs_fiddler.gtfs_time import GtfsTime


def trips_for_route(trips: DataFrame, route_id, direction_id):
    return trips[(trips.route_id == route_id) & (trips.direction_id == direction_id)]


def make_unique(s: Series):
    """
    Make all entries in a series of strings unique by adding number suffixes.
    """
    suffixes = cumcount(s).astype(str)
    suffixes.loc[suffixes == "1"] = ""
    return s + suffixes


def cumcount(s: Series):
    return s.to_frame(name="x").groupby(by="x").cumcount().add(1)


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

    def trips_enriched(self) -> DataFrame:
        """
        Returns trips with added start and end time, time to next trip,
        and distances
        """
        trip_stats = self._feed.compute_trip_stats()
        # add missing columns again
        trip2service = self._feed.trips[
            ["trip_id", "service_id", "trip_headsign", "block_id"]
        ]
        df = trip_stats.join(trip2service.set_index("trip_id"), on="trip_id")
        df.start_time = df.start_time.apply(GtfsTime)
        df.end_time = df.end_time.apply(GtfsTime)

        def time_to_next_trip(df):
            start = df.start_time.reset_index(drop=True)
            next_start = df.start_time[1:].reset_index(drop=True)
            return next_start - start

        df["time_to_next_trip"] = (
            df.groupby(["route_id", "direction_id"]).apply(time_to_next_trip).values
        )

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
        new trip(s) are inserted by copying the first trip (as often as required).

        Note, that this only works reliably if the feed was reduced to a single day.
        Otherwise the trips sorted by start time will be intermixed for different days.
        """
        suffix = "#densify"
        # get trips enriched with arrival/departure times
        t = self.trips_enriched()
        t = t[t.time_to_next_trip > GtfsTime(minutes * 60)]

        # multiply trips as required, calculate their time shift
        # and add them to the trips df
        t["repeats"] = t.time_to_next_trip.apply(
            lambda x: math.ceil(x.seconds_of_day / (minutes * 60)) - 1
        )
        t["offset_seconds"] = t.apply(
            lambda x: int(x.time_to_next_trip.seconds_of_day / (x.repeats + 1)), axis=1
        )
        t = t.loc[t.index.repeat(t.repeats)]
        t = t.rename(columns={"trip_id": "trip_id_original"})
        t["trip_id"] = t.trip_id_original + suffix
        ccount = cumcount(t.trip_id)
        t["trip_id"] = t["trip_id"] + ccount.astype(str)
        t["offset_seconds"] = t["offset_seconds"] * ccount
        self._feed.trips = pd.concat([self.trips, t[self.trips.columns]]).reset_index(
            drop=True
        )

        # copy required start times
        st = self.stop_times.set_index("trip_id")
        st.arrival_time = st.arrival_time.apply(GtfsTime)
        st.departure_time = st.departure_time.apply(GtfsTime)
        st = st.sort_values(["trip_id", "stop_sequence"])

        def teh_lambda(s):
            df = st.loc[s.trip_id_original]
            df = GtfsFiddler._adjust_stop_times(
                df, adjustment_seconds=s.offset_seconds
            ).reset_index()
            df.trip_id = s.trip_id
            return df

        collected_stop_times = t[
            ["trip_id", "trip_id_original", "offset_seconds"]
        ].apply(teh_lambda, axis=1)

        collected_stop_times = list(collected_stop_times)
        collected_stop_times.append(self.stop_times)
        new_st = pd.concat(collected_stop_times).reset_index(drop=True)
        new_st.arrival_time = new_st.arrival_time.apply(str)
        new_st.departure_time = new_st.departure_time.apply(str)
        self._feed.stop_times = new_st.sort_values(["trip_id", "stop_sequence"])

    def _ensure_earliest_or_latest_departure(
        self, target_time: GtfsTime, earliest: bool
    ):
        suffix = "#early" if earliest else "#late"
        # get trips enriched with arrival/departure times
        t = self.trips_enriched()

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
        self._feed.trips = pd.concat([self.trips, dup_trips]).reset_index(drop=True)

        # also copy and adjust relevant stop times
        st = self.stop_times.set_index("trip_id")
        dup_times = st.loc[trips_to_adjust].copy().reset_index()
        dup_times.trip_id = dup_times.trip_id + suffix
        dup_times.arrival_time = dup_times.arrival_time.apply(GtfsTime)
        dup_times.departure_time = dup_times.departure_time.apply(GtfsTime)
        dup_times = dup_times.sort_values(["trip_id", "stop_sequence"])
        dup_times = dup_times.groupby("trip_id").apply(
            lambda df: GtfsFiddler._adjust_stop_times(df, desired_start=target_time)
        )
        dup_times.arrival_time = dup_times.arrival_time.apply(str)
        dup_times.departure_time = dup_times.departure_time.apply(str)
        self._feed.stop_times = pd.concat([self.stop_times, dup_times]).reset_index(
            drop=True
        )

    @staticmethod
    def _adjust_stop_times(
        stop_times: DataFrame,
        adjustment_seconds: int | None = None,
        desired_start: GtfsTime | None = None,
    ):
        """
        set the departure time of the first stop to the desired start time
        and adjust all other departure and arrival times accordingly
        """
        if adjustment_seconds is not None:
            adjustment = GtfsTime(adjustment_seconds)
        else:
            adjustment = desired_start - stop_times.iloc[0].departure_time

        stop_times.arrival_time = stop_times.arrival_time + adjustment
        stop_times.departure_time = stop_times.departure_time + adjustment
        return stop_times
