from pathlib import Path

import pytest
from datetime import date
from gtfs_fiddler.fiddle import GtfsFiddler
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


def test_sorted_trips_basic():
    cairns_all = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT)
    sorted_trips = cairns_all.sorted_trips()

    assert len(sorted_trips) == 1339
    speed_median = sorted_trips.speed.median()
    # speed in kph
    assert 0 < speed_median and speed_median < 50


def test_ensure_earliest_departure():
    fiddler = GtfsFiddler(CAIRNS_GTFS, DIST_UNIT, SUNDAY)
    route_id = "110-423"
    direction_id = 0
    assert len(fiddler.trips_for_route(route_id, direction_id)) == 16
    assert _earliest_dep(fiddler, route_id, direction_id) == GtfsTime("7:16")

    fiddler.ensure_earliest_departure(GtfsTime("5:00"))
    assert len(fiddler.trips_for_route(route_id, direction_id)) == 17
    assert _earliest_dep(fiddler, route_id, direction_id) == GtfsTime("5:00")


def _earliest_dep(fiddler: GtfsFiddler, route_id, direction_id):
    df = fiddler.sorted_trips()
    df[(df.route_id == route_id) & (df.direction_id == direction_id)]
    return df.iloc[0].start_time


def xxx_test_densify_but_properly():
    assert False
    # TODO use the SORTED trips in Fiddle to insert new trips.
    # (probably also for route+service pairs
    # with only a single trip (let's just duplicate it after 1 hour or so))

    # .. for each duplication take the trip before and after.
    # calc the difference between the trips' start time and divide it by the densify factor
    # for each duplication:
    #   add a suffix to the prev trip
    #   clone the stop_times for the prev trip but add the diff to the times

    # duplicate after the last trip? yeah maybe.. just use the previous time between trips
    # -> this would also lead to a simple duplication of trips.. maybe more what one would expect
    # than the exception for single route+service trips?
