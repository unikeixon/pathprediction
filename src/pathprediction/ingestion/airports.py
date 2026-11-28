"""Download OurAirports data and select the airports and runways of a zone."""
# Imports
import datetime
import urllib.request
from pathlib import Path

import pandas as pd
from pygments.styles import default

# Project root / data. Computed from this file's location, so it works
# no matter where the script is launched from.
data_directory = Path(__file__).resolve().parents[3] / "data"

urls = {
    "airports.csv": "https://davidmegginson.github.io/ourairports-data/airports.csv",
    "runways.csv": "https://davidmegginson.github.io/ourairports-data/runways.csv",
}

# Default zone: Catalonia, Balearic Islands, Valencian Community.
regions = ("ES-CT", "ES-IB", "ES-VC")

# Official Spanish aerodrome codes: four letters starting with "LE".
pattern = r"^LE[A-Z]{2}$"

airport_type = ("large_airport", "medium_airport")

airport_columns = [
    "ident", "name", "type", "iso_region", "municipality",
    "latitude_deg", "longitude_deg", "elevation_ft",
]

runway_columns = [
    "airport_ident", "length_ft", "surface", "closed",
    "le_ident", "le_latitude_deg", "le_longitude_deg", "le_heading_degT",
    "he_ident", "he_latitude_deg", "he_longitude_deg", "he_heading_degT",
]

endpoint = [
    "le_latitude_deg", "le_longitude_deg",
    "he_latitude_deg", "he_longitude_deg",
]


def download_airports():
    """Download airports.csv and runways.csv into data/ and log source and date."""
    data_directory.mkdir(exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = []
    for filename, url in urls.items():
        urllib.request.urlretrieve(url, data_directory / filename)
        lines.append(f"{filename}\t{url}\tdownloaded {today}")
    (data_directory / "SOURCES.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_zone_airports(
    regions=regions,
    country="ES",
    ident_pattern=pattern,
):
    """Return (airports, runways) for the given regions.

    Both are pandas DataFrames. Runways keep their `closed` flag and any
    missing coordinates as NaN: nothing is filled in or invented.
    """
    airports = pd.read_csv(data_directory / "airports.csv", low_memory=False)
    runways = pd.read_csv(data_directory / "runways.csv", low_memory=False)

    in_zone = (airports["iso_country"] == country) & airports["iso_region"].isin(regions)
    has_official_code = airports["ident"].str.match(ident_pattern, na=False)
    is_airport = airports["type"].isin(airport_type)

    selected = airports[in_zone & has_official_code & is_airport]
    selected = selected[airport_columns].sort_values(["iso_region", "ident"])

    zone_runways = runways[runways["airport_ident"].isin(selected["ident"])]
    zone_runways = zone_runways[runway_columns].sort_values("airport_ident")

    return selected.reset_index(drop=True), zone_runways.reset_index(drop=True)


def print_summary(airports, runways):
    """Print the counts used to check the selection."""
    print("Airports:", len(airports))
    print(airports["iso_region"].value_counts().sort_index().to_string())
    print("Runways:", len(runways))
    print("Closed runways:", int((runways["closed"] == 1).sum()))
    print("Runways without endpoint coordinates:",
          int(runways[endpoint].isna().any(axis=1).sum()))
    without_runways = sorted(set(airports["ident"]) - set(runways["airport_ident"]))
    print("Airports without runways:", without_runways)


if __name__ == "__main__":
    # Run download_airports() once first if data/ is empty.
    zone_airports, zone_runways = load_zone_airports()
    print_summary(zone_airports, zone_runways)