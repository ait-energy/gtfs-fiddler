import logging
import sys
from datetime import date
from pathlib import Path

import gtfs_kit as gk
from gtfs_kit.miscellany import restrict_to_dates

from gtfs_fiddler.fiddle import GtfsFiddler
from gtfs_fiddler.gtfs_time import GtfsTime

logFormat = "%(asctime)s %(name)s %(levelname)s | %(message)s"
logging.basicConfig(format=logFormat, datefmt="%Y-%m-%d %H:%M:%S", level=logging.INFO)

logger = logging.getLogger(__name__)


def reduce_gtfs(in_file: Path, out_file: Path):
    logger.info(f"loading {in_file}")
    feed = gk.read_feed(in_file, dist_units="m")
    feed.describe()

    fiddler = GtfsFiddler(in_file, "m")  # , date(2022, 6, 7))
    fiddler.ensure_earliest_departure(GtfsTime("05:00"))

    fiddler.feed.write(out_file)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        "call with exactly two arguments: input and output gtfs.zip"

    reduce_gtfs(Path(sys.argv[1]), Path(sys.argv[2]))
