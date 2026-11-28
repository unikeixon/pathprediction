from pathlib import Path

import pandas as pd

from pathprediction.cleaning.resample import resample_segments
from pathprediction.cleaning.segments import clean_points, drop_short_segments, split_segments

project_root = Path(__file__).resolve().parents[1]
points = pd.read_parquet(project_root / "data" / "points_2025_07_15.parquet")

clean = clean_points(points)
segmented = split_segments(clean)        # new segment after a gap of more than 60 s
kept = drop_short_segments(segmented)    # drop segments shorter than 5 min
print("Segments:", kept["segment_id"].nunique(), "| points:", len(kept), "of", len(points))

tracks = resample_segments(kept)
print("Resampled rows:", len(tracks))
print(tracks["gap_s"].describe())
print("Rows more than 10 s from a real observation (%):", round(100 * (tracks["gap_s"] > 10).mean(), 2))

output_path = project_root / "data" / "tracks_2025_07_15.parquet"
tracks.to_parquet(output_path, index=False)
print("Saved:", output_path)