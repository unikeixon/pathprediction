import time
from pathlib import Path

from pathprediction.ingestion.airports import load_zone_airports
from pathprediction.zone import zone_bbox
from pathprediction.ingestion.daily_archive import scan_day

project_root = Path(__file__).resolve().parents[1]
tar_path = project_root / "data" / "day_2025_07_15.tar"
output_path = project_root / "data" / "points_2025_07_15.parquet"

airports, runways = load_zone_airports()
bbox = zone_bbox(airports, margin_nm=120)

start = time.perf_counter()
df = scan_day(tar_path, bbox)  # no max_files: the whole day
print("Minutes:", round((time.perf_counter() - start) / 60, 1))

df.to_parquet(output_path, index=False)
print("Saved:", output_path)
print("Rows:", len(df), "| aircraft:", df["icao"].nunique())
print("File size (MB):", round(output_path.stat().st_size / 1e6, 1))
print(df["source"].value_counts())