"""Resample irregular ADS-B points onto a regular time grid, segment by segment."""

import numpy as np
import pandas as pd

step = 10  # grid spacing in seconds

# Columns interpolated linearly. Track is an angle and is handled separately.
linear_columns = ["lat", "lon", "alt_baro_ft", "gs_kt", "vrate_fpm"]

epoch = pd.Timestamp("1970-01-01", tz="UTC")


def _interp(t_obs, values, grid):
    """Linear interpolation that ignores missing values; all NaN if fewer than 2 are valid."""
    valid = ~np.isnan(values)
    if valid.sum() < 2:
        return np.full(grid.shape, np.nan)
    return np.interp(grid, t_obs[valid], values[valid])


def _interp_angle(t_obs, degrees, grid):
    """Interpolate an angle in degrees through its sine and cosine, so 359 -> 1 works."""
    radians = np.radians(degrees)
    sin = _interp(t_obs, np.sin(radians), grid)
    cos = _interp(t_obs, np.cos(radians), grid)
    return np.degrees(np.arctan2(sin, cos)) % 360


def _distance_to_nearest(t_obs, grid):
    """Seconds between each grid time and the closest real observation."""
    idx = np.clip(np.searchsorted(t_obs, grid), 1, len(t_obs) - 1)
    return np.minimum(np.abs(grid - t_obs[idx - 1]), np.abs(t_obs[idx] - grid))


def resample_segments(df, step_s=step):
    """Return a DataFrame on a regular grid (multiples of `step_s` seconds, shared by all
    aircraft). `gap_s` tells how far each row is from a real observation: 0 means measured,
    larger values mean interpolated."""
    pieces = []
    for segment_id, seg in df.groupby("segment_id"):
        seg = seg.sort_values("time")
        t_obs = (seg["time"] - epoch).dt.total_seconds().to_numpy()
        if len(t_obs) < 2:
            continue
        grid = np.arange(np.ceil(t_obs[0] / step_s) * step_s, np.floor(t_obs[-1] / step_s) * step_s + 1, step_s)
        if len(grid) == 0:
            continue
        out = {"segment_id": segment_id, "icao": seg["icao"].iloc[0]}
        out["time"] = pd.to_datetime(grid, unit="s", utc=True)
        for column in linear_columns:
            out[column] = _interp(t_obs, seg[column].to_numpy(dtype=float), grid)
        out["track_deg"] = _interp_angle(t_obs, seg["track_deg"].to_numpy(dtype=float), grid)
        out["gap_s"] = _distance_to_nearest(t_obs, grid)
        pieces.append(pd.DataFrame(out))
    return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()