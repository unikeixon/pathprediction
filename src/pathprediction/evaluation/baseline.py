"""Physics baselines: predict the future from the current state, with no learning,
and measure how far each prediction lands from the real position."""

import numpy as np
import pandas as pd

ktMS = 1852 / 3600  # one knot is 1852 m per hour
nmM = 1852.0           # one nautical mile in metres

state_columns = ["lat", "lon", "alt_baro_ft", "gs_kt", "track_deg", "vrate_fpm"]


def get_geod():
    """WGS84 ellipsoid, for exact distances and azimuths."""
    from pyproj import Geod
    return Geod(ellps="WGS84")


def _to_ns(series):
    """Same time resolution everywhere, so tables can be joined on time."""
    return series.astype("datetime64[ns, UTC]")


def attach_state_and_truth(cases, tracks, horizon_min):
    """For the cases with a real future at this horizon, add the state at t0
    and the true position at t0 + horizon."""
    tracks = tracks.assign(time=_to_ns(tracks["time"]))
    chosen = cases.loc[cases[f"has_{horizon_min}min"], ["segment_id", "icao", "t0"]]
    chosen = chosen.assign(t0=_to_ns(chosen["t0"]))

    now = tracks[["segment_id", "time"] + state_columns].rename(columns={"time": "t0"})
    merged = chosen.merge(now, on=["segment_id", "t0"], how="left")

    merged["t_future"] = merged["t0"] + pd.Timedelta(minutes=horizon_min)
    future = tracks[["segment_id", "time", "lat", "lon", "alt_baro_ft"]].rename(
        columns={"time": "t_future", "lat": "lat_true", "lon": "lon_true", "alt_baro_ft": "alt_true_ft"}
    )
    return merged.merge(future, on=["segment_id", "t_future"], how="left")


def predict_constant_velocity(state, horizon_min, geod, use_vertical_rate=False):
    """Keep ground speed and track constant. Altitude stays constant, or follows the
    current vertical rate if `use_vertical_rate` is True."""
    distance_m = state["gs_kt"].to_numpy() * ktMS * horizon_min * 60
    lon_pred, lat_pred, _ = geod.fwd(
        state["lon"].to_numpy(), state["lat"].to_numpy(), state["track_deg"].to_numpy(), distance_m
    )
    alt_pred = state["alt_baro_ft"].to_numpy()
    if use_vertical_rate:
        alt_pred = alt_pred + state["vrate_fpm"].to_numpy() * horizon_min
    return lat_pred, lon_pred, alt_pred


def compute_errors(state, lat_pred, lon_pred, alt_pred, geod):
    """Error = real position minus predicted position, split along and across the
    aircraft's track at t0. Positive along: the aircraft is ahead of the prediction.
    Positive cross: the aircraft is to the right of the prediction."""
    azimuth, _, distance_m = geod.inv(lon_pred, lat_pred, state["lon_true"].to_numpy(), state["lat_true"].to_numpy())
    east = distance_m * np.sin(np.radians(azimuth))
    north = distance_m * np.cos(np.radians(azimuth))
    theta = np.radians(state["track_deg"].to_numpy())
    return pd.DataFrame({
        "along_nm": (east * np.sin(theta) + north * np.cos(theta)) / nmM,
        "cross_nm": (east * np.cos(theta) - north * np.sin(theta)) / nmM,
        "dist_nm": distance_m / nmM,
        "vert_ft": state["alt_true_ft"].to_numpy() - alt_pred,
    }, index=state.index)


def evaluate_baseline(cases, tracks, horizons_min, geod=None, use_vertical_rate=False):
    """Run the baseline for every horizon and return one row per (case, horizon)."""
    geod = geod or get_geod()
    needed = state_columns + ["lat_true", "lon_true", "alt_true_ft"]
    results = []
    for horizon in horizons_min:
        state = attach_state_and_truth(cases, tracks, horizon).dropna(subset=needed)
        lat_pred, lon_pred, alt_pred = predict_constant_velocity(state, horizon, geod, use_vertical_rate)
        errors = compute_errors(state, lat_pred, lon_pred, alt_pred, geod)
        out = state[["segment_id", "icao", "t0", "alt_baro_ft", "vrate_fpm"]].copy()
        out["horizon_min"] = horizon
        # Flight phase at the moment of prediction (not in the future).
        out["phase"] = np.select([out["vrate_fpm"] > 500, out["vrate_fpm"] < -500], ["climb", "descent"], default="level")
        results.append(pd.concat([out, errors], axis=1))
    return pd.concat(results, ignore_index=True)


def summarize(errors, by=("horizon_min",)):
    """Median, 90th percentile and RMSE of the distance error, plus mean absolute errors."""
    grouped = errors.groupby(list(by), observed=True)
    return pd.DataFrame({
        "cases": grouped.size(),
        "dist_median_nm": grouped["dist_nm"].median(),
        "dist_p90_nm": grouped["dist_nm"].quantile(0.9),
        "dist_rmse_nm": grouped["dist_nm"].agg(lambda x: float(np.sqrt((x ** 2).mean()))),
        "along_mae_nm": grouped["along_nm"].agg(lambda x: x.abs().mean()),
        "cross_mae_nm": grouped["cross_nm"].agg(lambda x: x.abs().mean()),
        "vert_mae_ft": grouped["vert_ft"].agg(lambda x: x.abs().mean()),
    }).round(2)