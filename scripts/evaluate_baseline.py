from pathlib import Path

import pandas as pd

from pathprediction.evaluation.baseline import evaluate_baseline, summarize
from pathprediction.evaluation.cases import horizons, build_cases

project_root = Path(__file__).resolve().parents[1]
tracks = pd.read_parquet(project_root / "data" / "tracks_2025_07_15.parquet")

# Drop the segments that have no speed at all
no_speed = tracks.groupby("segment_id")["gs_kt"].apply(lambda s: s.isna().all())
tracks = tracks[~tracks["segment_id"].isin(no_speed[no_speed].index)]

cases = build_cases(tracks)
errors_alt = evaluate_baseline(cases, tracks, horizons)                               # altitude constant
errors_vrate = evaluate_baseline(cases, tracks, horizons, use_vertical_rate=True)     # altitude follows vertical rate

print("\n=== Constant speed and track, altitude constant ===")
print(summarize(errors_alt).to_string())

print("\n=== Vertical error (mean absolute, ft) ===")
print(pd.DataFrame({
    "constant_altitude": summarize(errors_alt)["vert_mae_ft"],
    "constant_vertical_rate": summarize(errors_vrate)["vert_mae_ft"],
}).to_string())

print("\n=== By flight phase ===")
print(summarize(errors_alt, by=("phase", "horizon_min")).to_string())