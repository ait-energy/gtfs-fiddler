import math

import numpy as np
import pytest

from gtfs_fiddler.gtfs_time import GtfsTime


def test_floats_are_rounded():
    assert GtfsTime(123.456).seconds_of_day == 123
    assert GtfsTime(123.98).seconds_of_day == 124


def test_float_nan_is_allowed():
    time = GtfsTime(math.nan)
    assert math.isnan(time.seconds_of_day)


def test_invalid_string_format():
    with pytest.raises(ValueError):
        GtfsTime("235900")


def test_int_constructor():
    assert GtfsTime(1000).seconds_of_day == 1000


def test_constructor_with_self_type():
    assert GtfsTime(GtfsTime(1000)).seconds_of_day == 1000


def test_regular_constructor():
    assert GtfsTime("00:00:00").seconds_of_day == 0


def test_regular_constructor2():
    time = GtfsTime("10:30:59")
    assert time.seconds_of_day == 10 * 60 * 60 + 30 * 60 + 59


def test_equals():
    assert GtfsTime("00:30:00") == GtfsTime(30 * 60)


def test_not_equals():
    assert not GtfsTime("00:30:00") == GtfsTime(30 * 60 + 1)


def test_subtraction():
    assert GtfsTime("09:00:00") - GtfsTime("08:59:00") == GtfsTime("00:01:00")
    assert GtfsTime("09:00:00") - 8 * 60 * 60 - 59 * 60 == GtfsTime("00:01:00")
    assert GtfsTime("09:00:00") - 1.23 == GtfsTime("08:59:59")
    assert GtfsTime("09:00:00") - 1.6 == GtfsTime("08:59:58")


def test_addition():
    assert GtfsTime("09:00:00") + GtfsTime("01:01:01") == GtfsTime("10:01:01")
    assert GtfsTime("09:00:00") + 1 * 60 * 60 + 1 * 60 + 1 == GtfsTime("10:01:01")
    assert GtfsTime("09:00:00") + 1.23 == GtfsTime("09:00:01")
    assert GtfsTime("09:00:00") + 1.60 == GtfsTime("09:00:02")


def test_beyond_24h():
    assert GtfsTime("23:59:59") + GtfsTime("10:00:00") == GtfsTime("33:59:59")


def test_repr():
    assert repr(GtfsTime("5:01")) == "05:01:00"


def test_to_gtfs_kit_raw():
    assert math.isnan(GtfsTime(np.nan).to_gtfs_kit_raw())
    assert GtfsTime("05:00").to_gtfs_kit_raw() == "05:00:00"


def test_less_than():
    assert GtfsTime("00:00:00") < GtfsTime("01:00:00")
    assert GtfsTime("01:00:00") < GtfsTime("01:00:01")


def test_greater_than():
    assert GtfsTime("24:00:00") > GtfsTime("01:00:00")
    assert GtfsTime("02:00:00") > GtfsTime("01:00:01")
