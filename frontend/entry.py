import asyncio
import json
import logging
import os

from workers import WorkerEntrypoint, Response

logger = logging.getLogger(__name__)

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


def _proxy_backend_sync(url: str) -> str:
    """Blocking HTTP GET; run via asyncio.to_thread from async fetch."""
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    req = Request(url, headers={"User-Agent": "ShowMeTheVillain-Worker"})
    try:
        with urlopen(req, timeout=15) as resp:
            code = resp.getcode()
            body = resp.read().decode("utf-8")
    except HTTPError as e:
        snippet = ""
        try:
            snippet = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        raise RuntimeError(f"upstream HTTP {e.code}: {snippet or e.reason}") from e
    except URLError as e:
        raise RuntimeError(f"upstream connection error: {e.reason}") from e

    if code >= 400:
        raise RuntimeError(f"upstream HTTP {code}")
    return body


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

        cors_json = {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        }

        # Optional BFF: set BACKEND_MAP_URL to full URL e.g. https://api.example.com/api/phishing/map-points?limit=800
        backend_url = (os.environ.get("BACKEND_MAP_URL") or "").strip()
        if backend_url:
            try:
                body = await asyncio.to_thread(_proxy_backend_sync, backend_url)
                return Response(body, headers=cors_json)
            except Exception as e:
                logger.exception("BACKEND_MAP_URL proxy failed")
                err = json.dumps(
                    {"error": "backend_proxy_failed", "detail": str(e)}
                )
                return Response(err, status=502, headers=cors_json)

        return Response(
            json.dumps(VILLAIN_DATA),
            headers=cors_json,
        )
