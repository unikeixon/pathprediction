"""Geographic limits of the study zone, computed from airport coordinates."""

import math

nmXdeg_lat = 60.0  # one degree of latitude is about 60 nautical miles


def zone_bbox(airports, margin_nm):
    """Return the bounding box that contains all airports plus a margin in NM."""
    lat_margin = margin_nm / nmXdeg_lat
    mean_lat = airports["latitude_deg"].mean()
    # A degree of longitude shrinks with latitude, so the margin in degrees grows.
    lon_margin = margin_nm / (nmXdeg_lat * math.cos(math.radians(mean_lat)))
    return {
        "lat_min": float(airports["latitude_deg"].min() - lat_margin),
        "lat_max": float(airports["latitude_deg"].max() + lat_margin),
        "lon_min": float(airports["longitude_deg"].min() - lon_margin),
        "lon_max": float(airports["longitude_deg"].max() + lon_margin),
    }