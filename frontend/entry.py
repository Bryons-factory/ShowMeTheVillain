from workers import WorkerEntrypoint, Response
import json
import os

# Demo points when FastAPI is unavailable; same shape as GET /api/phishing/map-points
VILLAIN_DATA = [
    {
        "lat": 44.5191,
        "lon": -88.0198,
        "intensity": 10,
        "name": "The Glitch",
        "threat_level": "critical",
        "company": "The Glitch",
        "country": "United States",
        "isp": "Demo ISP East",
    },
    {
        "lat": 44.5133,
        "lon": -88.0150,
        "intensity": 5,
        "name": "Null Pointer",
        "threat_level": "medium",
        "company": "Null Pointer",
        "country": "United States",
        "isp": "Demo ISP East",
    },
    {
        "lat": 51.5074,
        "lon": -0.1278,
        "intensity": 8,
        "name": "London Phish",
        "threat_level": "high",
        "company": "Acme Bank",
        "country": "United Kingdom",
        "isp": "UK Telecom Demo",
    },
]


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        if request.method == "OPTIONS":
            return Response(
                "",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Access-Control-Max-Age": "86400",
                },
            )

        # Optional BFF: set BACKEND_MAP_URL to full URL e.g. https://api.example.com/api/phishing/map-points?limit=800
        backend_url = (os.environ.get("BACKEND_MAP_URL") or "").strip()
        if backend_url:
            try:
                from urllib.request import Request, urlopen

                req = Request(backend_url, headers={"User-Agent": "ShowMeTheVillain-Worker"})
                with urlopen(req, timeout=15) as resp:
                    body = resp.read().decode("utf-8")
                return Response(
                    body,
                    headers={
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                    },
                )
            except Exception:
                pass

        return Response(
            json.dumps(VILLAIN_DATA),
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
        )
