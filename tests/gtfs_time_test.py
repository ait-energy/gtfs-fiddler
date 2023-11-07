import pytest

from gtfs_fiddler.gtfs_time import GtfsTime


def test_no_floats_other_than_nan_allowed():
    with pytest.raises(ValueError):
        GtfsTime(float(123.456))


def test_float_nan_is_allowed():
    time = GtfsTime(float("nan"))
    assert time.seconds_of_day == -1


def test_invalid_string_format():
    with pytest.raises(ValueError):
        GtfsTime("235900")


def test_int_constructor():
    time = GtfsTime(1000)
    assert time.seconds_of_day == 1000


def test_regular_constructor():
    time = GtfsTime("00:00:00")
    assert time.seconds_of_day == 0


def test_regular_constructor2():
    time = GtfsTime("10:30:59")
    assert time.seconds_of_day == 10 * 60 * 60 + 30 * 60 + 59


def test_equals():
    assert GtfsTime("00:30:00") == GtfsTime(30 * 60)


def test_not_equals():
    assert not GtfsTime("00:30:00") == GtfsTime(30 * 60 + 1)


def test_subtraction():
    assert GtfsTime("09:00:00") - GtfsTime("08:59:00") == GtfsTime("00:01:00")


def test_addition():
    assert GtfsTime("09:00:00") + GtfsTime("01:01:01") == GtfsTime("10:01:01")


def test_beyond_24h():
    assert GtfsTime("23:59:59") + GtfsTime("10:00:00") == GtfsTime("33:59:59")
