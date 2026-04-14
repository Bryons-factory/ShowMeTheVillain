import os
import plotly.express as px
import pandas as pd
import requests


def get_villain_map():
    base = os.getenv("VILLAIN_API_BASE", "http://127.0.0.1:8000").rstrip("/")
    response = requests.get(f"{base}/api/phishing/map-points", timeout=30)
    response.raise_for_status()
    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(
            "Failed to decode JSON from map-points API response"
        ) from exc
    df = pd.DataFrame(data)

    # 2. Build the Plotly Map
    fig = px.density_mapbox(
        df, lat='lat', lon='lon', z='intensity',
        hover_name='name',
        radius=20, zoom=10,
        mapbox_style="open-street-map"
    )

    # 3. Handle the "Zoom Detail" (Drill Down)
    # This stores extra data for when you implement the deep-detail zoom later
    fig.update_traces(customdata=df['name'])

    return fig