from workers import WorkerEntrypoint, Response
import json

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        # 1. Answer the invisible CORS "Preflight" request from the browser
        if request.method == "OPTIONS":
            return Response(
                "",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Access-Control-Max-Age": "86400"  # Caches this permission for 24 hours
                }
            )

        # 2. In a real app, pull this from Cloudflare D1 or KV
        villain_data = [
            {"lat": 44.5191, "lon": -88.0198, "intensity": 10, "name": "The Glitch"},
            {"lat": 44.5133, "lon": -88.0150, "intensity": 5, "name": "Null Pointer"}
        ]

        # 3. Send the actual data with the permission slip
        return Response(
            json.dumps(villain_data),
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        )