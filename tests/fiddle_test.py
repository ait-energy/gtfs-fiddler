from pathlib import Path

import pytest

from gtfs_fiddler.fiddle import Fiddle

CAIRNS_GTFS = Path("./data/cairns_gtfs.zip")
STATIC_CAIRNS = Fiddle(CAIRNS_GTFS)


def test_route_count():
    assert len(STATIC_CAIRNS.get_routes()) == 22


def test_trip_count():
    assert len(STATIC_CAIRNS.get_trips()) == 1339


def test_stop_times_count():
    assert len(STATIC_CAIRNS.get_stop_times()) == 37790


def test_trips_to_be_densified():
    groups = STATIC_CAIRNS._trips_to_be_densified()
    assert len(groups[("110-423", "CNS2014-CNS_MUL-Weekday-00")]) == 59
    assert len(groups[("110-423", "CNS2014-CNS_MUL-Saturday-00")]) == 34
    assert (
        not ("131N-423", "CNS2014-CNS_MUL-Weekday-00") in groups
    ), "only a single trip for this route+service combination - must be ignored"

    assert len(groups) == 55


@pytest.mark.parametrize("multiplier", [2, 3])
def test_densify_by_multiplier(multiplier):
    cairns = Fiddle(CAIRNS_GTFS)
    tripcounts = cairns.tripcount_per_route_and_service()
    assert tripcounts.loc[("131N-423", "CNS2014-CNS_MUL-Weekday-00")] == 1
    assert tripcounts.loc[("110-423", "CNS2014-CNS_MUL-Weekday-00")] == 59
    assert tripcounts.loc[("110-423", "CNS2014-CNS_MUL-Saturday-00")] == 34

    cairns.densify(multiplier)

    tripcounts = cairns.tripcount_per_route_and_service()
    assert tripcounts.loc[("131N-423", "CNS2014-CNS_MUL-Weekday-00")] == 1
    assert tripcounts.loc[("110-423", "CNS2014-CNS_MUL-Weekday-00")] == 59 * multiplier
    assert tripcounts.loc[("110-423", "CNS2014-CNS_MUL-Saturday-00")] == 34 * multiplier
