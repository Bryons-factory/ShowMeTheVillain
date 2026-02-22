# Phish 'N Heat Backend - Quick Start Guide

## 5-Minute Setup

### 1. Install Python Dependencies
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Initialize Database
```bash
mkdir data
sqlite3 data/phishing.db < migrations/001_initial_schema.sql
```

### 3. Run the Server
```bash
python main.py
```

You should see:
```
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 4. Test It
Open in your browser:
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

---

## Understanding the Architecture

### The Question the Frontend Never Has to Ask:
**"Where do I get the phishing data? How do I handle rate limits? Should I cache?"**

**Answer:** "Just call `/api/phishing/heatmap` - the backend handles EVERYTHING"

### Three Layers:
```
Routes (HTTP) → Services (Business Logic) → API Client/Database (External)
```

### How Caching Works:
1. Frontend calls `/api/phishing/heatmap`
2. Backend checks: "Do we have fresh data (< 5 min old)?"
3. **YES** → Return it immediately (no API call needed!)
4. **NO** → Fetch from PhishStats, cache it, return it

This respects the 20 calls/minute API limit!

---

## File by File

### config.py
All settings in ONE place. No magic strings scattered everywhere.

```python
from config import config
print(config.PHISHSTATS_API_URL)  # "https://phishstats.info..."
```

### api_client.py
Talks to PhishStats. Uses cache to avoid wasting API calls.

```python
client = PhishStatsClient()
data = await client.fetch_incidents()  # Checks cache first!
```

### services/phishing_service.py
The "smart layer" that does the actual work.

```python
service = PhishingService()
heatmap = await service.get_heatmap_data(threat_level="high")
# Returns: {coordinates: [[lat, lon], ...], incident_count: 342, ...}
```

### services/analytics_service.py
Analyzes the phishing data for insights.

```python
analytics = AnalyticsService()
overview = await analytics.get_threat_overview()
# Returns: {total_incidents, threat_distribution, top_companies, ...}
```

### routes/phishing.py & routes/analytics.py
The "front door" - what the frontend actually calls.

```
GET /api/phishing/heatmap?threat_level=high
GET /api/phishing/filtered?company=PayPal
GET /api/analytics/top-regions?limit=5
```

### main.py
Starts the server and connects everything.

```bash
python main.py  # Starts FastAPI on port 8000
```

---

## What Your Frontend Needs to Know

Your frontend only needs to call endpoints. It NEVER needs to:
- Call PhishStats API directly ❌
- Manage rate limits ❌
- Implement caching logic ❌
- Handle retries ❌

The backend does all that. Frontend just:

```javascript
// Get heatmap data
fetch('/api/phishing/heatmap?threat_level=high')
  .then(r => r.json())
  .then(data => {
    // data.coordinates = [[lat, lon], [lat, lon], ...]
    // Draw on map!
  })

// Get analytics
fetch('/api/analytics/overview')
  .then(r => r.json())
  .then(data => {
    // data.total_incidents, data.top_companies, etc
    // Show charts!
  })
```

That's it!

---

## Troubleshooting

### Server won't start?
```bash
# Check if port 8000 is in use
# Or specify different port:
python main.py --port 9000
```

### ModuleNotFoundError?
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

### Database not found?
```bash
# Initialize it
mkdir data
sqlite3 data/phishing.db < migrations/001_initial_schema.sql
```

### API returns empty data?
```bash
# Force refresh cache
curl http://localhost:8000/api/phishing/refresh
```

---

## API Endpoints Cheat Sheet

### Phishing Data
- `GET /api/phishing/` - All incidents (with limit, offset, threat_level)
- `GET /api/phishing/heatmap` - Coordinates for map
- `GET /api/phishing/filtered` - Advanced filters (company, country, isp)
- `GET /api/phishing/stats` - Threat statistics
- `GET /api/phishing/refresh` - Force API refresh

### Analytics
- `GET /api/analytics/overview` - Everything at a glance
- `GET /api/analytics/threat-distribution` - Counts by severity
- `GET /api/analytics/top-regions` - Top countries
- `GET /api/analytics/top-companies` - Most targeted brands
- `GET /api/analytics/threat-hotspots` - Regional breakdown
- `GET /api/analytics/isp-rankings` - ISPs with most activity

### System
- `GET /health` - Is server running?
- `GET /info` - API information
- `GET /docs` - Interactive API docs (Swagger UI)

---

## Example: Getting Started in Python

```python
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        # Get heatmap data
        response = await client.get("http://localhost:8000/api/phishing/heatmap")
        heatmap = response.json()
        print(f"Found {heatmap['incident_count']} incidents")
        print(f"Coordinates: {heatmap['coordinates'][:3]}...")  # First 3
        
        # Get analytics
        response = await client.get("http://localhost:8000/api/analytics/overview")
        analytics = response.json()
        print(f"\nTotal incidents: {analytics['total_incidents']}")
        print(f"Top companies: {analytics['top_companies']}")

asyncio.run(main())
```

---

## For Each Team Member

### Ethan (API Handling)
- Review `api_client.py` - does it parse the PhishStats response correctly?
- Check `models.py` - do the fields match what PhishStats sends?
- Test: `curl http://localhost:8000/api/phishing/`

### Thomas (Database/Backend)
- Review `database.py` - ready to connect to actual Cloudflare D1?
- Check `migrations/001_initial_schema.sql` - do we need more fields?
- Consider: Query optimization, backup strategy

### Matthew (Frontend Integration)
- Review `routes/phishing.py` and `routes/analytics.py` - match your needs?
- Test each endpoint from your React code
- Verify CORS is working: `GET /health` should work from frontend

### Bryon (DevOps/Hosting)
- Set up Cloudflare D1 and update `config.CLOUDFLARE_D1_CONNECTION`
- Configure environment variables (see backend/BACKEND_README.md)
- Deploy to Cloudflare Workers

---

## Remember

The backend is **THE SOURCE OF TRUTH**. The frontend is just a beautiful visualization of data the backend provides.

If the frontend needs data, it asks the backend. The backend figures out whether to use cache, fetch from API, or query the database.

Frontend: "Give me heatmap data for critical threats"
Backend: "Coming right up!" (and handles all the complexity behind the scenes)

---

## Next Steps

1. ✅ Backend is ready to run
2. ⬜ Connect frontend to these endpoints
3. ⬜ Set up Cloudflare D1 database
4. ⬜ Deploy to production

Questions? Check the docstring at the top of each file!
