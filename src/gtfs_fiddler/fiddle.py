import logging
import math
from collections.abc import Collection
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import gtfs_kit as gk
import gtfs_kit.helpers as hp
import pandas as pd
from gtfs_kit.feed import Feed
from gtfs_kit.miscellany import restrict_to_dates
from gtfs_kit.stop_times import append_dist_to_stop_times
from pandas import DataFrame, Series

from gtfs_fiddler.gtfs_time import GtfsTime

logger = logging.getLogger(__name__)


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


def compute_stop_time_stats(feed: Feed):
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

    # ffill arrival and departure times for distance / seconds computation
    # but keep the original to set it before returning
    arrival_time_orig = st.arrival_time.apply(GtfsTime)
    departure_time_orig = st.departure_time.apply(GtfsTime)
    st.arrival_time = st.arrival_time.ffill().apply(GtfsTime)
    st.departure_time = st.departure_time.ffill().apply(GtfsTime)

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

    st.arrival_time = arrival_time_orig
    st.departure_time = departure_time_orig
    return st


@dataclass(frozen=True)
class FiddleFilter:
    """
    Specify which routes should be affected.
    If both types and ids are given they are combined with AND (not OR).
    """

    route_types: Collection[int] | None = None
    route_ids: Collection[str] | None = None
    route_short_names: Collection[str] | None = None


NO_FILTER = FiddleFilter()


class GtfsFiddler:
    """
    Built on top of gtfs_kit.Feed to:

    1. Add additional trips
       - Earliest trip in the morning (for a specific time) with `GtfsFiddler.ensure_earliest_departure`
       - Latest trip in the evening (for a specific time) with `GtfsFiddler.ensure_latest_departure`
       - Trips to shorten intervals (for a specified maximum interval duration) with `GtfsFiddler.ensure_max_trip_interval`
    2. Increase speed of trips (for a specified average speed between two stops) with `GtfsFiddler.ensure_min_speed`

    All `ensure_*` methods take a `FiddleFilter` that can be omitted to affect all routes,
    or specified to only affect specific route types or ids.

    Also it provides typed access to the more of the feed's members (for autocompletion in IDE :)
    """

    def __init__(self, p: Path, dist_units: str, restrict_to_date: date | None = None):
        self._original_feed = gk.read_feed(p, dist_units=dist_units)
        self._original_feed.validate()
        if restrict_to_date is not None:
            datestr = restrict_to_date.isoformat().replace("-", "")
            self._feed = restrict_to_dates(self._original_feed, [datestr])
        else:
            self._feed = self._original_feed
        # self._sorted_trips = GtfsFiddler._update_sorted_trips(self._feed)

    def trips_enriched(self, filter: FiddleFilter = NO_FILTER) -> DataFrame:
        """
        Returns trips with added start and end time, time to next trip,
        and distances.
        Sorted by route_id, direction_id, start_time.
        """
        # TODO actually we don't need the distance for most calls
        # of this method. avoiding these calculations could improve runtimes.

        trip_stats = self._feed.compute_trip_stats()
        old_len = len(trip_stats)
        if filter.route_types is not None:
            trip_stats = trip_stats.query("route_type in @filter.route_types")
        if filter.route_ids is not None:
            trip_stats = trip_stats.query("route_id in @filter.route_ids")
        if filter.route_short_names is not None:
            trip_stats = trip_stats.query(
                "route_short_name in @filter.route_short_names"
            )

        logger.info(f"after filtering {len(trip_stats)}/{old_len} trips remain")

        # add all columns previously present again
        missing_cols = set(self._feed.trips.columns) - set(trip_stats.columns)
        missing_cols.add("trip_id")
        trip2service = self._feed.trips[sorted(missing_cols)]
        df = trip_stats.join(trip2service.set_index("trip_id"), on="trip_id")
        df.start_time = df.start_time.apply(GtfsTime)
        df.end_time = df.end_time.apply(GtfsTime)

        if len(df) == 0:
            return df

        def time_to_next_trip(df):
            start = df.start_time.reset_index(drop=True)
            next_start = df.start_time[1:].reset_index(drop=True)
            return next_start - start

        df = df.sort_values(by=["route_id", "direction_id", "start_time"])
        df["time_to_next_trip"] = (
            df.groupby(["route_id", "direction_id"], dropna=False)
            .apply(time_to_next_trip)
            .values
        )

        return df

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
        return trips_for_route(self._feed.trips, route_id, direction_id)

    @property
    def stop_times(self) -> DataFrame:
        return self._feed.stop_times

    def tripcount_per_route_and_service(self) -> Series:
        return self.trips.groupby(["route_id", "service_id"]).size()

    @property
    def agency(self) -> DataFrame:
        return self._feed.agency

    def ensure_earliest_departure(
        self, target_time: GtfsTime, filter: FiddleFilter = NO_FILTER
    ):
        """
        In case the earliest trip (per route_id + direction_id)
        departs later than the given time,
        this trip is copied and set to start at that time.
        """
        self._ensure_earliest_or_latest_departure(target_time, filter, True)

    def ensure_latest_departure(
        self, target_time: GtfsTime, filter: FiddleFilter = NO_FILTER
    ):
        """
        In case the latest trip (per route_id + direction_id)
        departs earlier than the given time,
        this trip is copied and set to start at that time.
        """
        self._ensure_earliest_or_latest_departure(target_time, filter, False)

    def ensure_max_trip_interval(self, minutes: int, filter: FiddleFilter = NO_FILTER):
        """
        For each interval (between two trips per route_id + direction_id) larger than the given maximum
        new trip(s) are inserted by copying the first trip (as often as required).

        Note, that this only works reliably if the feed was reduced to a single day.
        Otherwise the trips sorted by start time will be intermixed for different days.
        """
        suffix = "#densify"
        # get trips enriched with arrival/departure times
        t = self.trips_enriched(filter)
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

        def _lambda(s):
            df = st.loc[s.trip_id_original]
            df = GtfsFiddler._adjust_stop_times(
                df, adjustment_seconds=s.offset_seconds
            ).reset_index()
            df.trip_id = s.trip_id
            return df

        collected_stop_times = t[
            ["trip_id", "trip_id_original", "offset_seconds"]
        ].apply(_lambda, axis=1)
        new_st = pd.concat(list(collected_stop_times))
        new_st.arrival_time = new_st.arrival_time.apply(str)
        new_st.departure_time = new_st.departure_time.apply(str)

        all_st = pd.concat([self.stop_times, new_st]).reset_index(drop=True)
        self._feed.stop_times = all_st.sort_values(["trip_id", "stop_sequence"])

        logger.info(f"added {len(t)} trips")

    def _ensure_earliest_or_latest_departure(
        self, target_time: GtfsTime, filter: FiddleFilter, earliest: bool
    ):
        suffix = "#early" if earliest else "#late"
        # get trips enriched with arrival/departure times
        t = self.trips_enriched(filter)

        # find the first/last trip of routes that need adjustment
        if earliest:
            first_trip = t.groupby(["route_id", "direction_id"], dropna=False).first()
            trips_to_adjust = first_trip[first_trip.start_time > target_time].trip_id
        else:
            last_trip = t.groupby(["route_id", "direction_id"], dropna=False).last()
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
        dup_times.arrival_time = dup_times.arrival_time.apply(GtfsTime.to_gtfs_kit_raw)
        dup_times.departure_time = dup_times.departure_time.apply(
            GtfsTime.to_gtfs_kit_raw
        )
        self._feed.stop_times = pd.concat([self.stop_times, dup_times]).reset_index(
            drop=True
        )

        logger.info(f"added {len(dup_trips)} trips")

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

    def ensure_min_speed(
        self,
        route_type2speed: dict[int, float] | None = None,
        route_id2speed: dict[str, float] | None = None,
    ):
        """
        Override the original travel times of selected trips with travel times
        calculated from the given speeds and the departure time
        of the first stop. If the original travel time was shorter
        than the one calculated with the given speed it is left intact.

        Both route types and ids can be used together to select which routes are affected.
        Speed must be given either mph or kph depending on the feed's distance unit.
        """
        st = compute_stop_time_stats(self.feed)
        trip2route = self.trips.join(
            self.routes.set_index("route_id").route_type, on="route_id"
        )[["trip_id", "route_id", "route_type"]]
        st = st.join(trip2route.set_index("trip_id"), on="trip_id")

        def adjust_trips_for_route_type(df):
            route_type = int(df.name)
            if route_type not in route_type2speed:
                return df
            speed = route_type2speed[route_type]
            new_df = df.groupby("trip_id").apply(
                lambda v: GtfsFiddler._ensure_min_speed_of_trip(v, speed),
            )
            return new_df.reset_index(drop=True)

        # TODO check performance
        def adjust_trips_for_route_id(df):
            route_id = str(df.name)
            if route_id not in route_id2speed:
                return df
            speed = route_id2speed[route_id]
            new_df = df.groupby("trip_id").apply(
                lambda v: GtfsFiddler._ensure_min_speed_of_trip(v, speed),
            )
            return new_df.reset_index(drop=True)

        new_st = st
        if route_type2speed is not None:
            new_st = new_st.groupby("route_type").apply(adjust_trips_for_route_type)
        if route_id2speed is not None:
            new_st = new_st.groupby("route_id").apply(adjust_trips_for_route_id)

        # convert GtfsTime back to str, clean unnecessary cols, sort
        new_st = new_st[self.stop_times.columns]
        new_st.arrival_time = new_st.arrival_time.apply(GtfsTime.to_gtfs_kit_raw)
        new_st.departure_time = new_st.departure_time.apply(GtfsTime.to_gtfs_kit_raw)
        new_st = new_st.sort_values(["trip_id", "stop_sequence"]).reset_index(drop=True)
        self.feed.stop_times = new_st.reset_index(drop=True)

    @staticmethod
    def _ensure_min_speed_of_trip(df: DataFrame, speed: float) -> DataFrame:
        """
        Adjust stop times (of a single trip).
        Reduces the time between two stops if traveling
        at the provided speed is faster. In case the original
        travel time was faster it is not changed.

        Requires output of `compute_stop_time_stats` (and not raw trips)

        Returns a copy of the input df with
        changed "arrival_time" and "departure_time"
        """
        seconds_to_next_stop_new = (df.dist_to_next_stop / speed) * 3600
        seconds_to_next_stop_min = pd.DataFrame(
            [df.seconds_to_next_stop.values, seconds_to_next_stop_new.values]
        ).min()
        traveltime_cumsum = seconds_to_next_stop_min.shift(periods=1).cumsum()
        traveltime_cumsum.iloc[0] = 0

        stay_seconds = (df.departure_time - df.arrival_time).apply(
            lambda v: v.seconds_of_day
        )
        first_arrival_time = df.iloc[0].arrival_time
        df = df.copy()
        df["arrival_time"] = (
            traveltime_cumsum.apply(GtfsTime) + first_arrival_time
        ).values
        # guarantee that missing values in original feed stay missing
        df.loc[stay_seconds.isna(), "arrival_time"] = GtfsTime(math.nan)
        df["departure_time"] = df.arrival_time + stay_seconds
        return df
