import logging
import sys
from pathlib import Path

import gtfs_kit as gk
from gtfs_kit.miscellany import restrict_to_dates

logFormat = "%(asctime)s %(name)s %(levelname)s | %(message)s"
logging.basicConfig(format=logFormat, datefmt="%Y-%m-%d %H:%M:%S", level=logging.INFO)

logger = logging.getLogger(__name__)


def reduce_gtfs(in_file: Path, out_file: Path):
    logger.info(f"loading {in_file}")
    feed = gk.read_feed(in_file, dist_units="km")
    feed.describe()

    # logger.info("computing busiest date")
    # this takes ages.. didn't finish in 30 minutes for VOR :/
    # alternative approach: use pt2matsim to find out the busiest day.
    # busiest_date = feed.compute_busiest_date(feed.get_dates())
    busiest_date = "20220607"  # the date used by graphgen
    logger.info(f"reducing feed to trips on {busiest_date}")
    restricted_feed = restrict_to_dates(feed, [busiest_date])

    logger.info(f"writing reduced feed to {out_file}")
    restricted_feed.write(out_file)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        "call with exactly two arguments: input and output gtfs.zip"

    reduce_gtfs(Path(sys.argv[1]), Path(sys.argv[2]))
