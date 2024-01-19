from pathlib import Path

import pytest
from datetime import date
from gtfs_fiddler.fiddle import GtfsFiddler, filter_by_route
from gtfs_fiddler.gtfs_time import GtfsTime

CAIRNS_GTFS = Path("./data/cairns_gtfs.zip")
SUNDAY = date(2014, 6, 1)
DIST_UNIT = "km"  # actually irrelevant, no distances specified in the cairns gtfs


def test_basic_loading():
    cairns_all = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT)
    assert len(cairns_all.routes) == 22
    assert len(cairns_all.trips) == 1339
    assert len(cairns_all.stop_times) == 37790


def test_loading_for_one_day():
    cairns_single_sunday = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT, SUNDAY)
    assert len(cairns_single_sunday.routes) == 14
    assert len(cairns_single_sunday.trips) == 266


def test_trips_with_times_basic():
    cairns_all = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT)
    trips_with_times = cairns_all.trips_with_times()

    assert len(trips_with_times) == 1339
    speed_median = trips_with_times.speed.median()
    # speed in kph
    assert 0 < speed_median and speed_median < 50


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


def test_ensure_max_trip_interval():
    fiddler = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT, SUNDAY)
    route_id = "110-423"
    direction_id = 0
    original_departures = [GtfsTime(f"{h}:16:00") for h in range(7, 23)]
    assert _all_departures(fiddler, route_id, direction_id) == original_departures

    fiddler.ensure_max_trip_interval(90)
    assert (
        _all_departures(fiddler, route_id, direction_id) == original_departures
    ), "no extra trips needed, no change expected"

    fiddler.ensure_max_trip_interval(30)
    expected_departures = [GtfsTime(f"{h}:46:00") for h in range(7, 22)]
    expected_departures.extend(original_departures)
    expected_departures = sorted(expected_departures)
    assert _all_departures(fiddler, route_id, direction_id) == expected_departures


def _all_departures(fiddler: GtfsFiddler, route_id, direction_id) -> list[GtfsTime]:
    return list(
        filter_by_route(fiddler.trips_with_times(), route_id, direction_id).start_time
    )


def _earliest_departure(fiddler: GtfsFiddler, route_id, direction_id) -> GtfsTime:
    return __departure(fiddler, route_id, direction_id, 0)


def _latest_departure(fiddler: GtfsFiddler, route_id, direction_id) -> GtfsTime:
    return __departure(fiddler, route_id, direction_id, -1)


def __departure(fiddler: GtfsFiddler, route_id, direction_id, index) -> GtfsTime:
    df = fiddler.trips_with_times()
    df = df[(df.route_id == route_id) & (df.direction_id == direction_id)]
    return df.iloc[index].start_time
