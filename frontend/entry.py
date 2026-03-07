from workers import WorkerEntrypoint, Response
import json

ALLOWED_ORIGINS = {
    "https://showmethevillain.pages.dev",
}


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        origin = request.headers.get("Origin", "")

        # Handle CORS preflight requests
        if request.method == "OPTIONS":
            preflight_headers = {
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": request.headers.get("Access-Control-Request-Headers", ""),
                "Access-Control-Max-Age": "86400",
            }
            if origin in ALLOWED_ORIGINS:
                preflight_headers["Access-Control-Allow-Origin"] = origin
                preflight_headers["Vary"] = "Origin"
            return Response("", headers=preflight_headers)

        # In a real app, pull this from Cloudflare D1 or KV
        villain_data = [
            {"lat": 44.5191, "lon": -88.0198, "intensity": 10, "name": "The Glitch"},
            {"lat": 44.5133, "lon": -88.0150, "intensity": 5, "name": "Null Pointer"}
        ]

        response_headers = {
            "Content-Type": "application/json",
        }
        if origin in ALLOWED_ORIGINS:
            response_headers["Access-Control-Allow-Origin"] = origin
            response_headers["Vary"] = "Origin"

        return Response(
            json.dumps(villain_data),
            headers=response_headers,
        )