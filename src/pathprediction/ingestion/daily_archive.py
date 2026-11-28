"""Scan a daily adsb.lol archive and keep only the points inside a zone."""

import gzip
import json
import tarfile
from pathlib import Path

import pandas as pd

from pathprediction.ingestion.traces import parse_trace

prefix = "trace_full_"
suffix = ".json"


def read_trace_files(tar_path, max_files=None):
    """Yield (icao24, decoded JSON dictionary) for each aircraft file in the archive."""
    count = 0
    with tarfile.open(tar_path) as tar:
        for member in tar:
            name = Path(member.name).name
            if not (member.isfile() and name.startswith(prefix) and name.endswith(suffix)):
                continue
            icao = name[len(prefix):-len(suffix)]
            if icao.startswith("~"):  # temporary addresses, not real aircraft
                continue
            raw = tar.extractfile(member).read()
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            yield icao, json.loads(raw)
            count += 1
            if max_files is not None and count >= max_files:
                break


def touches_bbox(data, bbox):
    """Quick check, before building any table: does this aircraft enter the box?"""
    for point in data["trace"]:
        lat, lon = point[1], point[2]
        if lat is None or lon is None:
            continue
        if bbox["lat_min"] <= lat <= bbox["lat_max"] and bbox["lon_min"] <= lon <= bbox["lon_max"]:
            return True
    return False


def points_in_bbox(df, bbox):
    """Keep only the rows of a parsed trace that fall inside the box."""
    inside = df["lat"].between(bbox["lat_min"], bbox["lat_max"]) & df["lon"].between(
        bbox["lon_min"], bbox["lon_max"]
    )
    return df[inside]


def scan_day(tar_path, bbox, max_files=None, progress_every=5000):
    """Return one DataFrame with every point inside the box, for all aircraft of the day."""
    tables = []
    n_files = 0
    n_aircraft = 0
    for icao, data in read_trace_files(tar_path, max_files=max_files):
        n_files += 1
        if n_files % progress_every == 0:
            print(f"  read {n_files} aircraft files, {n_aircraft} inside the zone so far")
        if not touches_bbox(data, bbox):
            continue
        table = points_in_bbox(parse_trace(data), bbox)
        if not table.empty:
            tables.append(table)
            n_aircraft += 1
    print(f"Files read: {n_files} | aircraft inside the zone: {n_aircraft}")
    if not tables:
        return pd.DataFrame()
    return pd.concat(tables, ignore_index=True)