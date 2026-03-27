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


async def _proxy_backend(url: str) -> str:
    """Async HTTP GET using the Workers runtime fetch API (non-blocking, no threads)."""
    from js import fetch as js_fetch

    try:
        resp = await js_fetch(url, method="GET")
    except Exception as e:
        raise RuntimeError(f"fetch failed for {url}: {e}") from e
    if not resp.ok:
        raise RuntimeError(f"upstream HTTP {resp.status} from {url}")
    return await resp.text()


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
                body = await _proxy_backend(backend_url)
                return Response(body, headers=cors_json)
            except Exception as e:
                logger.exception("BACKEND_MAP_URL proxy failed")
                error_payload = {"error": "backend_proxy_failed"}
                if os.environ.get("WORKER_DEBUG") == "1":
                    error_payload["detail"] = str(e)
                err = json.dumps(error_payload)
                return Response(err, status=502, headers=cors_json)

        return Response(
            json.dumps(VILLAIN_DATA),
            headers=cors_json,
        )
