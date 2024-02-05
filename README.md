# Gtfs Fiddler

Using [gtfs_kit](https://github.com/mrcagney/gtfs_kit) to edit GTFS files:

1. Add additional trips
  - Earliest trip in the morning (for a specific time) with `GtfsFiddler.ensure_earliest_departure`
  - Latest trip in the evening (for a specific time) with `GtfsFiddler.ensure_latest_departure`
  - Trips to shorten intervals (for a specified maximum interval duration) with `GtfsFiddler.ensure_max_trip_interval`
2. Increase speed of trips (for a specified average speed between two stops) with `GtfsFiddler.ensure_min_speed`

Also it provides typed access to the more of the feed's members (for autocompletion in IDE :)

The helper method `fiddle.compute_stop_time_stats` supplements the gtfs_kit utils.
