from reactpy import component, html, run, hooks
import folium
from folium.plugins import HeatMap, MarkerCluster
import pandas as pd
import requests


@component
def App():
    # 1. DATA STATE MANAGEMENT (Ethan & Thomas)
    # -------------------------------------------------------------------
    phish_data, set_phish_data = hooks.use_state([])

    # This hook fetches the data from the PhishStats API once on startup
    @hooks.use_effect(dependencies=[])
    async def fetch_phish_data():
        try:
            # Fetching the last 100 incidents (per your proposal size limits)
            response = requests.get("https://phishstats.info:20443/api/v1/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                # We only need [lat, lon] for the heatmap
                coords = [[item['latitude'], item['longitude']] for item in data if item.get('latitude')]
                set_phish_data(coords)
        except Exception as e:
            print(f"Error fetching data: {e}")

    # 2. MAP COMPONENT (Bryon)
    # -------------------------------------------------------------------
    @component
    def MapView(data):
        if not data:
            return html.div({"style": {"padding": "20px"}}, "📡 Connecting to PhishStats API...")

        # Initialize the world map
        m = folium.Map(location=[20, 0], zoom_start=2, tiles="cartodb positron")

        # --- INSERTED CODE: HEATMAP LOGIC ---
        # HeatMap takes a list of [lat, lon] points
        HeatMap(data, radius=15, blur=10).add_to(m)

        # Optional: Add MarkerCluster for "digging in" (Matthew's suggestion)
        marker_cluster = MarkerCluster().add_to(m)
        for lat, lon in data[:50]:  # Limiting to 50 markers for performance
            folium.Marker([lat, lon], popup="Phishing Detected").add_to(marker_cluster)
        # ---------------------------------------

        return html.div({
            "dangerouslySetInnerHTML": {"__html": m._repr_html_()},
            "style": {"height": "80vh", "width": "100%"}
        })

    return html.div(
        {"style": {"font-family": "Arial", "padding": "20px"}},
        html.h1("ShowMeTheVillain: Global Phishing Tracker"),
        html.p(f"Tracking {len(phish_data)} active global threats"),
        MapView(phish_data),

        # --- INSERTED CODE: FILTERING UI (Matthew) ---
        html.div(
            {"style": {"margin-top": "20px"}},
            html.button({"on_click": lambda event: set_phish_data([])}, "Refresh Data"),
            html.span(" | Filters: [High Threat] [Recent] [Specific ISP]")
        )
        # --------------------------------------
    )


if __name__ == "__main__":
    run(App)