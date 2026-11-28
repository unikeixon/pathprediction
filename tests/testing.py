import time
from pathprediction.ingestion.airports import load_zone_airports
from pathprediction.zone import zone_bbox
from pathprediction.ingestion.daily_archive import scan_day

airports, runways = load_zone_airports()
bbox = zone_bbox(airports, margin_nm=120)
print(bbox)

start = time.perf_counter()
df = scan_day(tar_path, bbox, max_files=2000)
print("Seconds:", round(time.perf_counter() - start, 1))
print("Rows:", len(df), "| aircraft:", df["icao"].nunique() if len(df) else 0)
print(df["source"].value_counts())