from workers import WorkerEntrypoint, Response
import json

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        # In a real app, pull this from Cloudflare D1 or KV
        villain_data = [
            {"lat": 44.5191, "lon": -88.0198, "intensity": 10, "name": "The Glitch"},
            {"lat": 44.5133, "lon": -88.0150, "intensity": 5, "name": "Null Pointer"}
        ]
        return Response(
            json.dumps(villain_data),
            headers={"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        )