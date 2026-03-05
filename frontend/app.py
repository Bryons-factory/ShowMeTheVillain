import plotly.express as px
import pandas as pd
import requests


def get_villain_map():
    # 1. Fetch data from your Cloudflare Worker URL
    response = requests.get("https://villain-api.your-subdomain.workers.dev")
    df = pd.DataFrame(response.json())

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