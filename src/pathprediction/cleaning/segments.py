"""Clean ADS-B points and split them into continuous flight segments."""

import pandas as pd

MAX_GAP_S = 60  # a gap longer than this starts a new segment


def clean_points(df):
    """Drop ground points, missing positions and repeated timestamps; sort the rest."""
    df = df[~df["on_ground"]]
    df = df.dropna(subset=["lat", "lon"])
    df = df.sort_values(["icao", "time"])
    df = df.drop_duplicates(subset=["icao", "time"], keep="first")
    return df.reset_index(drop=True)


def split_segments(df, max_gap_s=MAX_GAP_S):
    """Add a `segment_id` column. A new segment starts for a new aircraft,
    after a long gap, or where the data flags the start of a new leg."""
    gap = df.groupby("icao")["time"].diff().dt.total_seconds()
    starts_new = gap.isna() | (gap > max_gap_s) | df["new_leg"]
    df = df.copy()
    df["segment_id"] = starts_new.cumsum()
    return df


def segment_summary(df):
    """One row per segment: aircraft, number of points and duration in minutes."""
    grouped = df.groupby("segment_id")
    return pd.DataFrame({
        "icao": grouped["icao"].first(),
        "n_points": grouped.size(),
        "duration_min": (grouped["time"].max() - grouped["time"].min()).dt.total_seconds() / 60,
    })