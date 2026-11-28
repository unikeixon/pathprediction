"""Draw the zone's airports and runways on an interactive map."""
# Imports
from pathlib import Path
import plotly.graph_objects as go
from pathprediction.ingestion.airports import endpoint, load_zone_airports

output_directory = Path(__file__).resolve().parents[2] / "output"

margin_deg = 1.5  # Space around the airports, in degrees.


def build_zone_map(airports, runways):
    """Return a plotly figure with the airports and their runways."""
    fig = go.Figure()

    # Runways: one line per runway, joining its two ends.
    for closed, color, label in [(0, "crimson", "Open runway"), (1, "grey", "Closed runway")]:
        subset = runways[runways["closed"] == closed].dropna(subset=endpoint)
        lats, lons = [], []
        for row in subset.itertuples():
            lats += [row.le_latitude_deg, row.he_latitude_deg, None]  # None = break between lines
            lons += [row.le_longitude_deg, row.he_longitude_deg, None]
        fig.add_trace(go.Scattergeo(
            lat=lats, lon=lons, mode="lines",
            line=dict(width=4, color=color), name=label, hoverinfo="skip",
        ))

    # Airports: one marker each, with its code as label.
    fig.add_trace(go.Scattergeo(
        lat=airports["latitude_deg"], lon=airports["longitude_deg"],
        mode="markers+text", text=airports["ident"], textposition="top right",
        marker=dict(size=8, color="navy"), name="Airports",
        hovertext=airports["name"], hoverinfo="text",
    ))

    # Map frame computed from the airports, with a margin around them.
    lat_min, lat_max = airports["latitude_deg"].min(), airports["latitude_deg"].max()
    lon_min, lon_max = airports["longitude_deg"].min(), airports["longitude_deg"].max()
    fig.update_geos(
        projection_type="mercator",
        resolution=50,
        lataxis_range=[float(lat_min - margin_deg), float(lat_max + margin_deg)],
        lonaxis_range=[float(lon_min - margin_deg), float(lon_max + margin_deg)],
        showland=True, landcolor="rgb(243,243,243)",
        showocean=True, oceancolor="rgb(220,235,245)",
        showcoastlines=True, showcountries=True,
    )
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    return fig

def add_tracks(fig, df, max_aircraft=200):
    """Draw each aircraft's positions as a thin line on the map."""
    for icao, track in list(df.groupby("icao"))[:max_aircraft]:
        track = track.sort_values("time")
        # Start a new line segment wherever two positions are more than 120 s apart,
        # so gaps are not joined by a false straight line.
        segment_id = (track["time"].diff().dt.total_seconds() > 120).cumsum()
        lats, lons = [], []
        for _, segment in track.groupby(segment_id):
            lats += list(segment["lat"]) + [None]
            lons += list(segment["lon"]) + [None]
        fig.add_trace(go.Scattergeo(
            lat=lats, lon=lons, mode="lines",
            line=dict(width=1), name=icao, showlegend=False,
            hovertext=icao, hoverinfo="text",
        ))
    return fig

if __name__ == "__main__":
    zone_airports, zone_runways = load_zone_airports()
    figure = build_zone_map(zone_airports, zone_runways)
    output_directory.mkdir(exist_ok=True)
    figure.write_html(output_directory / "map.html", config={"scrollZoom": True})