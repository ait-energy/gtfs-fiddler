from pathlib import Path
from pandas import Series
from pandas.testing import assert_frame_equal, assert_series_equal
import pytest
import math
from datetime import date
from gtfs_fiddler.fiddle import GtfsFiddler, make_unique, trips_for_route
from gtfs_fiddler.gtfs_time import GtfsTime

CAIRNS_GTFS = Path("./data/cairns_gtfs.zip")
SUNDAY = date(2014, 6, 1)
DIST_UNIT = "km"  # actually irrelevant, no distances specified in the cairns gtfs


def test_make_unique():
    s = Series("a a b a b c d c c e a a".split())
    expected = Series("a a2 b a3 b2 c d c2 c3 e a4 a5".split())

    assert_series_equal(expected, make_unique(s))


def test_basic_loading():
    cairns_all = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT)
    assert len(cairns_all.routes) == 22
    assert len(cairns_all.trips) == 1339
    assert len(cairns_all.stop_times) == 37790


def test_loading_for_one_day():
    cairns_single_sunday = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT, SUNDAY)
    assert len(cairns_single_sunday.routes) == 14
    assert len(cairns_single_sunday.trips) == 266


def test_trips_enriched_basic():
    cairns_all = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT)
    trips_with_times = cairns_all.trips_enriched()

    assert len(trips_with_times) == 1339
    speed_median = trips_with_times.speed.median()
    # speed in kph
    assert 0 < speed_median and speed_median < 50


def test_trips_enriched__time_to_next_trip():
    cairns_single_sunday = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT, SUNDAY)
    trips_enriched = cairns_single_sunday.trips_enriched()

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
    # assert _all_departures(fiddler, route_id, direction_id) == expected_departures
    # FIXME test times!


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
    # FIXME test times!


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
