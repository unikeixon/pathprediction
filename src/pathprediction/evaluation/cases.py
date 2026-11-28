"""Define the prediction cases: when do we ask the model to predict, and how far ahead."""

import numpy as np
import pandas as pd
from pandas.plotting._matplotlib import hist

horizons = (1, 2, 5, 10, 15, 20)  # how far ahead we predict, in minutes
cases = 60                      # one prediction case per minute along each segment
history = 120                        # observed past required before a case (2 min)

epoch = pd.Timestamp("1970-01-01", tz="UTC")


def build_cases(tracks, horizons_min=horizons, every_s=cases, history_s=history):
    """Return one row per case: segment, aircraft, instant t0, and for each horizon
    whether the real future exists (`has_<h>min`), so the error can be measured."""
    seconds = (tracks["time"] - epoch).dt.total_seconds()
    bounds = seconds.groupby(tracks["segment_id"]).agg(["min", "max"])
    icao = tracks.groupby("segment_id")["icao"].first()

    pieces = []
    for segment_id, t_start, t_end in zip(bounds.index, bounds["min"], bounds["max"]):
        first = np.ceil((t_start + history_s) / every_s) * every_s
        t0 = np.arange(first, t_end + 1, every_s)
        if len(t0) == 0:
            continue
        pieces.append(pd.DataFrame({
            "segment_id": segment_id, "icao": icao[segment_id], "t0_s": t0, "t_end_s": t_end,
        }))
    cases = pd.concat(pieces, ignore_index=True)

    for h in horizons_min:
        cases[f"has_{h}min"] = cases["t0_s"] + h * 60 <= cases["t_end_s"]
    cases["t0"] = pd.to_datetime(cases["t0_s"], unit="s", utc=True)
    return cases.drop(columns=["t0_s", "t_end_s"])