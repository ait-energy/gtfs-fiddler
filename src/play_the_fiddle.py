"""
Reduce GTFS feed to a single day and densify trips for that day
"""

import logging
import sys
from datetime import date
from pathlib import Path
import argparse
from gtfs_fiddler.fiddle import GtfsFiddler
from gtfs_fiddler.gtfs_time import GtfsTime

logFormat = "%(asctime)s %(name)s %(levelname)s | %(message)s"
logging.basicConfig(format=logFormat, datefmt="%Y-%m-%d %H:%M:%S", level=logging.INFO)

logger = logging.getLogger(__name__)


def main(args):
    print(args)
    in_file = Path(args.in_gtfs)
    out_file = Path(args.out_gtfs)
    the_date = date.fromisoformat(args.date)

    logger.info(f"loading {in_file} (reducing it to {the_date})")
    fiddler = GtfsFiddler(in_file, args.dist_unit, the_date)
    logger.info(f"ensure earliest departure")
    fiddler.ensure_earliest_departure(GtfsTime("05:00"))
    logger.info(f"ensure latest departure")
    fiddler.ensure_latest_departure(GtfsTime("23:00"))
    logger.info(f"ensure max trip interval")
    fiddler.ensure_max_trip_interval(5)
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
    args = parser.parse_args()

    main(args)
