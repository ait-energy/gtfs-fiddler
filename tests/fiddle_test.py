from pathlib import Path
from pandas import DataFrame, Series
from pandas.testing import assert_frame_equal, assert_series_equal
import pytest
import math
from datetime import date
from gtfs_fiddler.fiddle import (
    GtfsFiddler,
    compute_stop_time_stats,
    make_unique,
    trips_for_route,
)
from gtfs_fiddler.gtfs_time import GtfsTime
import pandas as pd

CAIRNS_GTFS = Path("./data/cairns_gtfs.zip")
SUNDAY = date(2014, 6, 1)
DIST_UNIT = "km"  # actually irrelevant, no distances specified in the cairns gtfs


def test_make_unique():
    s = Series("a a b a b c d c c e a a".split())
    expected = Series("a a2 b a3 b2 c d c2 c3 e a4 a5".split())

    assert_series_equal(expected, make_unique(s))


def test_compute_stop_time_stats():
    feed = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT).feed

    # first trip of route "110-423", 0
    # "CNS2014-CNS_MUL-Sunday-00-4165971"
    # add fake distances for one trip
    st_orig = feed.stop_times.set_index("trip_id")
    st_orig.loc["CNS2014-CNS_MUL-Sunday-00-4165971", "shape_dist_traveled"] = (
        Series(
            [
                "0.0",
                "0.0",
                "0.722",
                "1.69",
                "2.15",
                "3.38",
                "4.29",
                "4.5",
                "4.92",
                "5.45",
                "5.83",
                "6.11",
                "6.92",
                "nan",
                "nan",
                "11.0",
                "12.2",
                "13.7",
                "15.1",
                "16.7",
                "27.9",
                "27.9",
                "28.4",
                "28.4",
                "28.8",
                "29.0",
                "29.5",
                "29.5",
                "29.9",
                "30.3",
                "30.3",
                "31.0",
                "31.3",
                "31.5",
                "32.0",
            ]
        )
        .astype(float)
        .values
    )
    feed.stop_times = st_orig.reset_index()

    st = compute_stop_time_stats(feed)
    assert len(feed.stop_times) == len(st)
    assert (
        set(["seconds_to_next_stop", "dist_to_next_stop", "speed"]) - set(st.columns)
        == set()
    )

    assert list(
        st.set_index("trip_id")
        .loc["CNS2014-CNS_MUL-Sunday-00-4165971"]
        .speed.apply(lambda v: f"{v:.2f}")
    ) == [
        "nan",
        "21.66",
        "29.04",
        "27.60",
        "36.90",
        "27.30",
        "12.60",
        "25.20",
        "31.80",
        "22.80",
        "16.80",
        "48.60",
        "nan",
        "nan",
        "61.20",
        "36.00",
        "45.00",
        "42.00",
        "32.00",
        "48.00",
        "nan",
        "30.00",
        "nan",
        "24.00",
        "12.00",
        "30.00",
        "nan",
        "24.00",
        "24.00",
        "nan",
        "21.00",
        "18.00",
        "12.00",
        "15.00",
        "nan",
    ]


def test_init__full_feed():
    fiddler = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT)
    assert len(fiddler.routes) == 22
    assert len(fiddler.trips) == 1339
    assert len(fiddler.stop_times) == 37790


def test_init__single_sunday_only():
    fiddler = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT, SUNDAY)
    assert len(fiddler.routes) == 14
    assert len(fiddler.trips) == 266


def test_trips_enriched_basic():
    fiddler = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT)
    trips_with_times = fiddler.trips_enriched()

    assert len(trips_with_times) == 1339
    speed_median = trips_with_times.speed.median()
    # speed in kph
    assert 0 < speed_median and speed_median < 50


def test_trips_enriched__time_to_next_trip():
    fiddler = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT, SUNDAY)
    trips_enriched = fiddler.trips_enriched()

    times = trips_for_route(trips_enriched, "110-423", 0).time_to_next_trip
    assert len(times) == 16
    expected = [GtfsTime("1:00") for _ in range(0, 15)]
    assert list(times[:-1]) == expected, "one hour between all trips"
    assert math.isnan(times.iloc[15]), "except the last one of course"

    times = trips_for_route(trips_enriched, "123-423", 0).time_to_next_trip
    assert len(times) == 11
    expected = [GtfsTime("1:30") for _ in range(1, 10)]
    assert times.iloc[0] == GtfsTime("1:00"), "one hour for first trip"
    assert list(times[1:-1]) == expected, "90 minutes for all other trips"
    assert math.isnan(times.iloc[10]), "except the last one of course"


def test_ensure_earliest_departure():
    fiddler = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT, SUNDAY)
    route_id = "110-423"
    direction_id = 0

    # state before adding new trips
    assert len(fiddler.trips_for_route(route_id, direction_id)) == 16
    assert _earliest_departure(fiddler, route_id, direction_id) == GtfsTime("7:16")

    fiddler.ensure_earliest_departure(GtfsTime("5:00"))
    # state after adding new trips
    assert len(fiddler.trips_for_route(route_id, direction_id)) == 17
    assert _earliest_departure(fiddler, route_id, direction_id) == GtfsTime("5:00")

    fiddler.ensure_earliest_departure(GtfsTime("5:00"))
    # trips already added, should not change anything
    assert len(fiddler.trips_for_route(route_id, direction_id)) == 17
    assert _earliest_departure(fiddler, route_id, direction_id) == GtfsTime("5:00")

    fiddler.ensure_earliest_departure(GtfsTime("4:00"))
    # even earlier time should lead to one more trip
    assert len(fiddler.trips_for_route(route_id, direction_id)) == 18
    assert _earliest_departure(fiddler, route_id, direction_id) == GtfsTime("4:00")


def test_ensure_latest_departure():
    fiddler = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT, SUNDAY)
    route_id = "110-423"
    direction_id = 0

    # state before adding new trips
    assert len(fiddler.trips_for_route(route_id, direction_id)) == 16
    assert _latest_departure(fiddler, route_id, direction_id) == GtfsTime("22:16")

    fiddler.ensure_latest_departure(GtfsTime("23:00"))
    # state after adding new trips
    assert len(fiddler.trips_for_route(route_id, direction_id)) == 17
    assert _latest_departure(fiddler, route_id, direction_id) == GtfsTime("23:00")

    fiddler.ensure_latest_departure(GtfsTime("23:00"))
    # trips already added, should not change anything
    assert len(fiddler.trips_for_route(route_id, direction_id)) == 17
    assert _latest_departure(fiddler, route_id, direction_id) == GtfsTime("23:00")

    fiddler.ensure_latest_departure(GtfsTime("25:25"))
    # even earlier time should lead to one more trip
    assert len(fiddler.trips_for_route(route_id, direction_id)) == 18
    assert _latest_departure(fiddler, route_id, direction_id) == GtfsTime("25:25")


def test_ensure_max_trip_interval__exact_split():
    fiddler = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT, SUNDAY)
    route_id = "110-423"
    direction_id = 0
    original_departures = [GtfsTime(f"{h}:16:00") for h in range(7, 23)]
    assert len(fiddler.trips_for_route(route_id, direction_id)) == 16
    assert _all_departures(fiddler, route_id, direction_id) == original_departures

    fiddler.ensure_max_trip_interval(90)
    assert len(fiddler.trips_for_route(route_id, direction_id)) == 16
    assert (
        _all_departures(fiddler, route_id, direction_id) == original_departures
    ), "no extra trips needed, no change expected"

    fiddler.ensure_max_trip_interval(30)
    assert len(fiddler.trips_for_route(route_id, direction_id)) == 16 * 2 - 1
    expected_departures = [GtfsTime(f"{h}:46:00") for h in range(7, 22)]
    expected_departures.extend(original_departures)
    expected_departures = sorted(expected_departures)
    assert _all_departures(fiddler, route_id, direction_id) == expected_departures


def test_ensure_max_trip_interval__inexact_split():
    fiddler = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT, SUNDAY)
    route_id = "110-423"
    direction_id = 0
    original_departures = [GtfsTime(f"{h}:16:00") for h in range(7, 23)]
    assert len(fiddler.trips_for_route(route_id, direction_id)) == 16
    assert _all_departures(fiddler, route_id, direction_id) == original_departures

    # for a max 19 minute interval we need to add three trips resulting in a 15 minute interval
    fiddler.ensure_max_trip_interval(19)
    assert len(fiddler.trips_for_route(route_id, direction_id)) == 16 * 4 - 3
    expected_departures = list(original_departures)
    expected_departures.extend([GtfsTime(f"{h}:31:00") for h in range(7, 22)])
    expected_departures.extend([GtfsTime(f"{h}:46:00") for h in range(7, 22)])
    expected_departures.extend([GtfsTime(f"{h}:01:00") for h in range(8, 23)])
    expected_departures = sorted(expected_departures)
    assert _all_departures(fiddler, route_id, direction_id) == expected_departures


def test_combination_of_different_ensures():
    fiddler = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT, SUNDAY)
    route_id = "123-423"
    direction_id = 0

    original_departures = [GtfsTime(f"08:10")]
    original_departures.extend([GtfsTime("09:10") + 90 * 60 * v for v in range(0, 10)])
    assert len(fiddler.trips_for_route(route_id, direction_id)) == 11
    assert _all_departures(fiddler, route_id, direction_id) == original_departures

    fiddler.ensure_earliest_departure(GtfsTime("3:00"))
    fiddler.ensure_latest_departure(GtfsTime("23:30"))
    fiddler.ensure_max_trip_interval(10)
    expected_departures = [GtfsTime("3:00")]
    while expected_departures[-1] < GtfsTime("23:30"):
        expected_departures.append(expected_departures[-1] + 10 * 60)
    assert _all_departures(fiddler, route_id, direction_id) == expected_departures


def _all_departures(fiddler: GtfsFiddler, route_id, direction_id) -> list[GtfsTime]:
    return list(
        trips_for_route(fiddler.trips_enriched(), route_id, direction_id).start_time
    )


def _earliest_departure(fiddler: GtfsFiddler, route_id, direction_id) -> GtfsTime:
    return __departure(fiddler, route_id, direction_id, 0)


def _latest_departure(fiddler: GtfsFiddler, route_id, direction_id) -> GtfsTime:
    return __departure(fiddler, route_id, direction_id, -1)


def __departure(fiddler: GtfsFiddler, route_id, direction_id, index) -> GtfsTime:
    df = fiddler.trips_enriched()
    df = df[(df.route_id == route_id) & (df.direction_id == direction_id)]
    return df.iloc[index].start_time


def test_ensure_min_speed():
    fiddler = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT)
    original_st = fiddler.stop_times.copy()

    # empty request, should not change anything
    fiddler.ensure_min_speed({})
    assert_frame_equal(fiddler.stop_times, original_st)

    # change all busses to travel at >= 50 kph
    fiddler.ensure_min_speed({3: 50})
    assert len(fiddler.stop_times) == len(original_st)


def test_ensure_min_speed_of_trip():
    fiddler = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT)

    # first trip of route "110-423", 0
    # "CNS2014-CNS_MUL-Sunday-00-4165971"

    # add a 30 secs stay (to check that stays are retained)
    idx = fiddler.stop_times[
        fiddler.stop_times.trip_id == "CNS2014-CNS_MUL-Sunday-00-4165971"
    ].index
    assert fiddler.stop_times.loc[idx[2]].departure_time == "07:18:00"
    fiddler.stop_times.loc[idx[2], "departure_time"] = "07:18:30"

    st = compute_stop_time_stats(fiddler.feed)
    st = st[st.trip_id == "CNS2014-CNS_MUL-Sunday-00-4165971"]

    actual = st[
        [
            "stop_id",
            "stop_sequence",
            # "dist_to_next_stop",
            # "seconds_to_next_stop",
            "arrival_time",
            "departure_time",
        ]
    ].copy()
    # speed up line to 25 kph
    st_25 = GtfsFiddler._ensure_min_speed_of_trip(st, 25)
    actual["arrival_time_25"] = st_25.arrival_time
    actual["departure_time_25"] = st_25.departure_time
    # speed up line to 50 kph
    st_50 = GtfsFiddler._ensure_min_speed_of_trip(st, 50)
    actual["arrival_time_50"] = st_50.arrival_time
    actual["departure_time_50"] = st_50.departure_time
    # actual.to_csv("/tmp/export.csv", index=False)

    # check if results are as expected.
    # the expected df was checked for these details:
    # - for stop 15 arrival+departure time should be missing (as in the original)
    # - all other arrival+departure times must be set
    # - the 30 second stay at stop 3 must be retained
    # - between stops 14-16 the bus drives on a motorway at high speed.
    #   .. we must not reduce the speed there even if this specific
    #   trip makes this complicated because for stop 15 no
    #   arrival and departure time is set!

    assert_frame_equal_to_csv(
        actual, Path("./tests/data/test_ensure_min_speed_of_trip.csv")
    )


def assert_frame_equal_to_csv(df: DataFrame, path: Path):
    actual = df.astype(str).reset_index(drop=True)
    expected = pd.read_csv(path, dtype=str, keep_default_na=False)
    assert_frame_equal(actual, expected)
