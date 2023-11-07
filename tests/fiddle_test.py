from pathlib import Path

import pytest

from gtfs_fiddler.fiddle import GtfsFiddler

CAIRNS_GTFS = Path("./data/cairns_gtfs.zip")
STATIC_CAIRNS = GtfsFiddler(CAIRNS_GTFS)


def test_route_count():
    assert len(STATIC_CAIRNS.routes) == 22


def test_trip_count():
    assert len(STATIC_CAIRNS.trips) == 1339


def test_stop_times_count():
    assert len(STATIC_CAIRNS.stop_times) == 37790


def test_trips_to_be_densified():
    groups = STATIC_CAIRNS._trips_to_be_densified()
    assert len(groups[("110-423", "CNS2014-CNS_MUL-Weekday-00")]) == 59
    assert len(groups[("110-423", "CNS2014-CNS_MUL-Saturday-00")]) == 34
    assert (
        not ("131N-423", "CNS2014-CNS_MUL-Weekday-00") in groups
    ), "only a single trip for this route+service combination - must be ignored"

    assert len(groups) == 55


def test_sorted_trips():
    st = STATIC_CAIRNS.sorted_trips
    assert len(st) == 1339
    assert False, "TODO more asserts.. "


@pytest.mark.parametrize("multiplier", [2, 3])
def test_densify_by_multiplier(multiplier):
    cairns = GtfsFiddler(CAIRNS_GTFS)
    tripcounts = cairns.tripcount_per_route_and_service()
    assert tripcounts.loc[("131N-423", "CNS2014-CNS_MUL-Weekday-00")] == 1
    assert tripcounts.loc[("110-423", "CNS2014-CNS_MUL-Weekday-00")] == 59
    assert tripcounts.loc[("110-423", "CNS2014-CNS_MUL-Saturday-00")] == 34

    cairns.densify(multiplier)

    tripcounts = cairns.tripcount_per_route_and_service()
    assert tripcounts.loc[("131N-423", "CNS2014-CNS_MUL-Weekday-00")] == 1
    assert tripcounts.loc[("110-423", "CNS2014-CNS_MUL-Weekday-00")] == 59 * multiplier
    assert tripcounts.loc[("110-423", "CNS2014-CNS_MUL-Saturday-00")] == 34 * multiplier


def test_densify_but_properly():
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
