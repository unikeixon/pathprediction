"""Read adsb.lol (readsb) trace files into tidy pandas tables."""

import pandas as pd

# Order of the fields in every trace point, as documented by readsb.
# Files generated in 2022 or later carry all 14 fields; older ones fewer.
trace_columns = [
    "offset_s",        # seconds after the file's base timestamp
    "lat",             # degrees
    "lon",             # degrees
    "alt_baro_ft",     # barometric altitude in feet, or "ground", or None
    "gs_kt",           # ground speed in knots
    "track_deg",       # track in degrees (true heading if on the ground)
    "flags",           # bit field, see below
    "vrate_fpm",       # vertical rate in feet per minute
    "details",         # dictionary with extra data, or None
    "source",          # type of position source (adsb_icao, mlat, ...)
    "alt_geom_ft",     # geometric altitude in feet
    "vrate_geom_fpm",  # geometric vertical rate in feet per minute
    "ias_kt",          # indicated airspeed in knots
    "roll_deg",        # roll angle in degrees
]

num_columns = [
    "alt_baro_ft", "gs_kt", "track_deg", "vrate_fpm",
    "alt_geom_ft", "vrate_geom_fpm", "ias_kt", "roll_deg",
]


def parse_trace(data):
    """Convert one aircraft-day (the decoded JSON dictionary) into a DataFrame."""
    n_fields = len(trace_columns)
    rows = [point[:n_fields] + [None] * (n_fields - len(point)) for point in data["trace"]]
    df = pd.DataFrame(rows, columns=trace_columns)

    df["icao"] = data["icao"]
    df["time"] = pd.to_datetime(data["timestamp"] + df["offset_s"], unit="s", utc=True).dt.round("ms")

    flags = df["flags"].fillna(0).astype(int)
    df["stale"] = (flags & 1) > 0      # no position received in the 20 s before this one
    df["new_leg"] = (flags & 2) > 0    # start of a new flight leg

    df["on_ground"] = df["alt_baro_ft"] == "ground"
    # Make every measurement a plain number; "ground" and missing values become NaN.
    for column in num_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    return df.drop(columns=["details", "flags"])