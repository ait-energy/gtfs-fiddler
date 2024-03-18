"""
Reduce GTFS feed to a single day and densify trips for that day
"""

import logging
import sys
from datetime import date
from pathlib import Path
import argparse
from gtfs_fiddler.fiddle import FiddleFilter, GtfsFiddler
from gtfs_fiddler.gtfs_time import GtfsTime

logFormat = "%(asctime)s %(name)s %(levelname)s | %(message)s"
logging.basicConfig(format=logFormat, datefmt="%Y-%m-%d %H:%M:%S", level=logging.INFO)

logger = logging.getLogger(__name__)


def main(args):
    # early conversion of arguments to fail fast (if wrong)
    in_file = Path(args.in_gtfs)
    out_file = Path(args.out_gtfs)
    the_date = date.fromisoformat(args.date)
    route_types = (
        None
        if args.filter_route_types is None
        else [int(v) for v in args.filter_route_types.split(",")]
    )
    route_ids = (
        None
        if args.filter_route_ids is None
        else [v.strip() for v in args.filter_route_ids.split(",")]
    )
    route_short_names = (
        None
        if args.filter_route_short_names is None
        else [v.strip() for v in args.filter_route_short_names.split(",")]
    )
    filter = FiddleFilter(
        route_types=route_types,
        route_ids=route_ids,
        route_short_names=route_short_names,
    )
    earliest_departure = (
        GtfsTime(args.earliest_departure)
        if args.earliest_departure is not None
        else None
    )
    latest_departure = (
        GtfsTime(args.latest_departure) if args.latest_departure is not None else None
    )

    logger.info(f"loading {in_file} (reducing it to {the_date})")
    fiddler = GtfsFiddler(in_file, args.dist_unit, the_date)

    if earliest_departure is not None:
        logger.info(f"ensure earliest departure at {earliest_departure}")
        fiddler.ensure_earliest_departure(earliest_departure, filter)

    if latest_departure is not None:
        logger.info(f"ensure latest departure at {latest_departure}")
        fiddler.ensure_latest_departure(latest_departure, filter)

    if args.interval_minutes is not None:
        logger.info(f"ensure max trip interval: {args.interval_minutes} minutes")
        fiddler.ensure_max_trip_interval(args.interval_minutes, filter)

    # logger.info(f"increasing speed of buses and trams")
    # fiddler.ensure_min_speed(route_type2speed={0: 25, 3: 25})

    # logger.info(f"increasing speed of selected routes (SHOW Salzburg)")
    # route_ids = ["42", "s7v4", "rc3d", "nq8b", "w1k2", "tcn7"]
    # fiddler.ensure_min_speed(route_id2speed={id: 50 for id in route_ids})

    logger.info(f"writing result to {out_file}")
    fiddler.feed.write(out_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("in_gtfs", type=str, help="path to input GTFS file")
    parser.add_argument(
        "date", type=str, help="single date (YYYY-MM-DD) the input GTFS is reduced to"
    )
    parser.add_argument("out_gtfs", type=str, help="path to output GTFS file")
    parser.add_argument(
        "--dist-unit",
        type=str,
        default="km",
        help="distance unit (used in the input GTFS file)",
    )
    parser.add_argument(
        "--filter-route-types",
        type=str,
        default=None,
        help="only affect certain route types (comma-separated list)",
    )
    parser.add_argument(
        "--filter-route-ids",
        type=str,
        default=None,
        help="only affect certain routes (comma-separated list)",
    )
    parser.add_argument(
        "--filter-route-short-names",
        type=str,
        default=None,
        help="only affect certain routes (comma-separated list)",
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=None,
        help="ensure maximum duration of intervals (between two trips)",
    )
    parser.add_argument(
        "--earliest-departure",
        type=str,
        default=None,
        help="ensure earliest departure per route and direction (hh:mm)",
    )
    parser.add_argument(
        "--latest-departure",
        type=str,
        default=None,
        help="ensure latest departure per route and direction (hh:mm)",
    )
    args = parser.parse_args()

    main(args)
