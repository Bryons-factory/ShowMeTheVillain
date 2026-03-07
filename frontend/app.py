import plotly.express as px
import pandas as pd
import requests


def get_villain_map():
    # 1. Fetch data from your Cloudflare Worker URL
    response = requests.get("https://showmethevillain.tloveseework.workers.dev", timeout=10)

    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch villain data: HTTP {response.status_code}")

    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError("Failed to parse villain data as JSON") from exc

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