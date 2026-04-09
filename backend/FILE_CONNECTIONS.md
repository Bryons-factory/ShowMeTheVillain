# File Connections Overview

## Complete Architecture Map

```
┌─────────────────────────────────────────────────────────────────┐
│         FRONTEND (index.html / Pages)                            │
│  Hosted map: GET {D1 Worker}/  (data-source=worker, D1 JSON)     │
│  FastAPI mode: GET /api/phishing/map-points, /heatmap, analytics  │
└─────────────────┬───────────────────────────────────────────────┘
                  │ HTTP/JSON
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  data-extraction-worker (Cloudflare): cron → D1; fetch → map JSON│
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      main.py (FastAPI, optional local/API clients)│
│  ├─ Initializes FastAPI                                          │
│  ├─ Registers routes                                             │
│  ├─ Configures CORS                                              │
│  └─ Starts server on :8000                                       │
└─────────────────┬───────────────────────────────────────────────┘
                  │
        ┌─────────┴──────────┐
        ▼                    ▼
   routes/              routes/
   phishing.py          analytics.py
   (HTTP layer)         (HTTP layer)
        │                    │
        ├─ GET /api/phishing/ │ ├─ GET /api/analytics/overview
        ├─ GET /map-points    │ ├─ GET /threat-distribution
        ├─ GET /heatmap       │ ├─ GET /top-regions
        ├─ GET /filtered      │ ├─ GET /top-companies
        ├─ GET /stats         │ ├─ GET /threat-hotspots
        └─ GET /refresh       │ └─ GET /isp-rankings
        │                    │
        └─────────┬──────────┘
                  ▼ (calls methods)
        ┌─────────────────────────────┐
        │  BUSINESS LOGIC LAYER       │
        │                             │
        │  phishing_service.py        │
        │  ├─ get_all_incidents()     │
        │  ├─ get_heatmap_data()      │
        │  ├─ get_filtered_incidents()│
        │  └─ get_threat_statistics() │
        │                             │
        │  analytics_service.py       │
        │  ├─ get_threat_overview()   │
        │  ├─ get_top_regions()       │
        │  ├─ get_top_companies()     │
        │  └─ get_threat_hotspots()   │
        └──────────┬──────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
   api_client.py         D1 via data-extraction-worker
   (PhishStats + cache)  (not queried by Python services today)
        │
        ├─ config.py
        │  └─ PHISHSTATS_API_URL
        │  └─ API_RATE_LIMIT (20/min)
        │  └─ CACHE_TIMEOUT (5 min)
        │
        ├─ cache_service.py
        │  ├─ get() - check cache
        │  ├─ set() - store cache
        │  └─ is_expired() - check freshness
        │
        └─ models.py
           └─ validate incident data
               └─ ensure valid lat/lon
               └─ ensure valid threat_level
```

---

## What Each File Communicates With

### config.py (Settings Hub)
```
Provides settings to:
├─ api_client.py (API URL, timeout)
├─ main.py (host, port, CORS)
└─ services/ (all app settings)
```

### api_client.py (External API Wrapper)
```
Uses:
├─ config.py (for API URL, timeout)
├─ cache_service.py (check/store cache)
└─ models.py (validate data)

Called by:
└─ services/phishing_service.py
```

### cache_service.py (Rate Limit Handler)
```
Called by:
└─ api_client.py

Prevents exceeding 20 calls/minute by:
├─ Storing responses with timestamps
├─ Checking if data is fresh (< 5 min old)
└─ Returning cached data if fresh
```

### models.py (Data Validation)
```
Used by:
├─ api_client.py (validate API responses)
├─ services/ (validate processed data)
└─ routes/ (define request/response schemas)

Ensures:
├─ Coordinates are valid (-90 to 90 lat, -180 to 180 lon)
├─ Threat levels are valid (low/medium/high/critical)
└─ All required fields are present
```

### Cloudflare D1 (`data-extraction-worker/`)
```
Writes: cron ingest → phishing_links
Reads: GET / → map JSON for Pages (data-source=worker)

Not used by: services/phishing_service.py (uses api_client only)
```

### services/phishing_service.py (Core Business Logic)
```
Uses:
├─ api_client.py (get raw incidents)
├─ models.py (validate incidents)

Called by:
├─ routes/phishing.py (HTTP endpoints)
└─ services/analytics_service.py (for analysis)

Provides:
├─ get_all_incidents()
├─ get_heatmap_data()
├─ get_map_points()
├─ get_filtered_incidents()
└─ get_threat_statistics()
```

### services/analytics_service.py (Insights & Analysis)
```
Uses:
└─ services/phishing_service.py (get incidents to analyze)

Called by:
└─ routes/analytics.py (HTTP endpoints)

Provides:
├─ get_threat_overview()
├─ get_top_threat_regions()
├─ get_most_targeted_companies()
├─ get_threat_hotspots()
└─ get_isp_threat_rankings()
```

### routes/phishing.py (HTTP Endpoints)
```
Uses:
├─ services/phishing_service.py (get data)
└─ models.py (validate responses)

Registered in:
└─ main.py

Endpoints:
├─ GET /api/phishing/
├─ GET /api/phishing/map-points
├─ GET /api/phishing/heatmap
├─ GET /api/phishing/filtered
├─ GET /api/phishing/stats
└─ GET /api/phishing/refresh
```

### routes/analytics.py (HTTP Endpoints)
```
Uses:
├─ services/analytics_service.py (get analytics)
└─ models.py (validate responses)

Registered in:
└─ main.py

Endpoints:
├─ GET /api/analytics/overview
├─ GET /api/analytics/threat-distribution
├─ GET /api/analytics/top-regions
├─ GET /api/analytics/top-companies
├─ GET /api/analytics/threat-hotspots
└─ GET /api/analytics/isp-rankings
```

### main.py (Application Hub)
```
Initializes:
├─ FastAPI application
├─ CORS middleware
├─ Route registration (phishing, analytics)
└─ Server startup

Imports from:
├─ config.py
├─ routes/phishing.py
└─ routes/analytics.py

Provides:
├─ GET / (welcome)
├─ GET /health (status check)
├─ GET /info (API information)
├─ GET /docs (Swagger UI)
└─ GET /redoc (ReDoc)
```

### requirements.txt (Dependencies)
```
Core packages:
├─ fastapi (web framework)
├─ uvicorn (ASGI server)
├─ httpx (async HTTP client)
├─ pydantic (data validation)
└─ python-dateutil (date utilities)

Testing:
├─ pytest
└─ pytest-asyncio

Code quality:
├─ black (formatter)
├─ flake8 (linter)
└─ mypy (type checker)
```

### migrations/001_initial_schema.sql (optional local SQLite)
```
Legacy / local experiments — not wired to phishing_service.
Production rows: data-extraction-worker/schema.sql → D1 phishing_links
```

---

## Data Flow Examples

### Example 1: Map points (ShowMeTheVillain UI)
```
Production (Pages, data-source=worker):
Frontend
  ↓ GET https://<data-extraction-worker>/?limit=800
data-extraction-worker (fetch)
  ├─ D1 MAP_POINTS_SELECT_SQL
  └─ map-points.ts → JSON array
  ↓
Plotly map + client-side toolbar filters

Local FastAPI (data-source=api):
Frontend
  ↓ GET /api/phishing/map-points?limit=500
phishing_service.get_map_points → api_client.fetch_incidents() → MapPoint
```

### Example 1b: Heatmap Request (legacy)
```
Frontend
  ↓ GET /api/phishing/heatmap?threat_level=high
main.py
  ↓ routes/phishing.py
phishing_service.get_heatmap_data(threat_level="high")
  ├─ api_client.fetch_incidents()
  │  ├─ cache_service.is_expired()? → YES
  │  ├─ PhishStats API
  │  └─ cache_service.set()
  ├─ models.PhishingIncident (validate)
  ├─ Filter by threat_level
  └─ Extract [[lat, lon], ...]
  ↓
HeatmapData response
  ↓
Frontend renders map
```

### Example 2: Cache Hit (Fast Path)
```
Frontend
  ↓ GET /api/phishing/heatmap
main.py → routes/phishing.py
  ↓
phishing_service.get_heatmap_data()
  ├─ api_client.fetch_incidents()
  │  ├─ cache_service.is_expired()? → NO (still fresh)
  │  └─ Return cached data (NO API CALL!)
  ├─ models.PhishingIncident (validate)
  └─ Extract coordinates
  ↓
Response sent immediately (milliseconds!)
```

### Example 3: Analytics Request
```
Frontend
  ↓ GET /api/analytics/overview
main.py → routes/analytics.py
  ↓
analytics_service.get_threat_overview()
  ├─ phishing_service.get_all_incidents()
  │  └─ api_client.fetch_incidents() (same as above, uses cache)
  ├─ Count by threat_level
  ├─ Count by company
  ├─ Count by country
  ├─ Count by ISP
  └─ Return aggregated data
  ↓
Frontend displays charts
```

---

## Key Insight: Separation of Concerns

```
WHO HANDLES WHAT:

API Client (api_client.py)
├─ "Should I fetch from API or use cache?"
├─ "Did the API respond successfully?"
└─ "Is this data valid?"

Services (phishing_service.py, analytics_service.py)
├─ "How do I filter this data?"
├─ "How do I transform this for the frontend?"
└─ "What insights can I provide?"

Routes (routes/*.py)
├─ "What parameters did the frontend send?"
├─ "What response format should I return?"
└─ "How do I handle errors?"

D1 Worker (data-extraction-worker)
├─ "Ingest PhishStats into phishing_links"
└─ "Serve map rows from D1 on GET /"

Frontend (index.html)
├─ "Just get the data and show it on the map!"
├─ "Don't worry about rate limits"
└─ "Don't worry about caching"
```

---

## File Summary Table

| File | Lines | Purpose | Main Connections |
|------|-------|---------|-------------------|
| config.py | 120 | Settings hub | Everything |
| api_client.py | 200 | PhishStats API wrapper | cache_service, models |
| models.py | 180 | Data validation | api_client, routes, services |
| data-extraction-worker/ | — | D1 ingest + map API | D1, Pages |
| services/cache_service.py | 150 | Caching layer | api_client |
| services/phishing_service.py | 280 | Core business logic | api_client, models |
| services/analytics_service.py | 250 | Analytics engine | phishing_service |
| routes/phishing.py | 200 | HTTP endpoints | phishing_service, models |
| routes/analytics.py | 220 | HTTP endpoints | analytics_service |
| main.py | 180 | App initialization | routes, config |
| TOTAL | ~1850 | Complete backend | Fully documented |

---

## How to Read the Code

1. **Start with main.py** - Understand the overall structure
2. **Read routes/** - See what endpoints are available
3. **Read services/** - Understand the business logic
4. **Read api_client.py** - Understand external API handling
5. **Read config.py** - Understand settings
6. **Read models.py** - Understand data structures

Each file has a detailed docstring at the top explaining its purpose and connections!
