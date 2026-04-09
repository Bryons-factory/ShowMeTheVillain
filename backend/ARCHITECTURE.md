# Backend Architecture - Visual Summary

## The Big Picture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         YOUR FRONTEND (map.py)                       │
│                     "Show me the phishing threats!"                  │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              │ HTTP/JSON
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                        YOUR BACKEND (main.py)                       │
│                                                                       │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐             │
│  │   Routes     │   │  Services    │   │ API Client   │             │
│  │              │   │              │   │              │             │
│  │ /phishing    │──▶│ phishing_    │──▶│ PhishStats   │             │
│  │ /analytics   │   │ service      │   │ API Wrapper  │             │
│  │              │   │              │   │              │             │
│  │              │   │ analytics_   │   │ + Caching!   │             │
│  │              │   │ service      │   │              │             │
│  └──────────────┘   └──────────────┘   └──────────────┘             │
│                                                │                    │
│                                                │                    │
│  ┌───────────────────────────────────────────▼──────────────┐       │
│  │              CACHING LAYER                               │       │
│  │  (Respects 20 calls/minute - the SMART part!)           │       │
│  │                                                           │       │
│  │  "Do we have fresh data? (< 5 minutes old?)"            │       │
│  │    YES → Return it (NO API CALL!)                        │       │
│  │    NO  → Fetch from API, cache it, return it            │       │
│  └───────────────────────────────────────────────────────────┘       │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

**Note:** Persistent phishing rows for the **hosted map** live in **Cloudflare D1** (`phishing_links`), written by the **TypeScript Worker** in `backend/data-extraction-worker` and read by that Worker’s **`GET /`** handler. The FastAPI stack above uses **PhishStats + cache** only; it does not query D1 in the current Python code. See **Cloudflare: D1 and map data** below.

---

## Cloudflare: D1 and map data

| Piece | Role |
|--------|------|
| **`backend/data-extraction-worker`** | Cron ingests PhishStats → D1; **`fetch`** serves map JSON from D1 (`GET /`, optional `?limit=`). |
| **Cloudflare Pages** | `frontend/index.html` with `data-source=worker` and `api-base` = that Worker’s HTTPS URL (see `frontend/scripts/patch_pages_meta.py` + CI). |
| **FastAPI** (`main.py`) | `/api/phishing/map-points` and related routes use **`api_client.fetch_incidents()`**, not D1. Use for local dev or API consumers that hit your Python server. |
| **`frontend/entry.py` (Python Worker)** | Optional BFF: demo JSON or proxy via `BACKEND_MAP_URL`; **not** the primary map source when Pages targets the D1 Worker. |

---

## What Each Component Does

### Frontend (Your Existing map.py)
```
Responsibilities:
✓ Display heatmap
✓ Show statistics
✓ Handle user clicks

Does NOT need to worry about:
✗ Calling PhishStats API
✗ Rate limiting
✗ Caching
✗ Data validation
✗ Filtering logic
```

### Routes Layer
```
Responsibilities:
✓ Receive HTTP requests
✓ Parse query parameters
✓ Call service methods
✓ Format JSON responses

Does NOT do:
✗ Business logic
✗ Data processing
✗ External API calls
✗ Database queries directly
```

### Services Layer
```
Responsibilities:
✓ Implement business logic
✓ Filter data
✓ Transform data
✓ Aggregate statistics
✓ Call api_client or database

Does NOT do:
✗ Handle HTTP
✗ Talk to external APIs directly
✗ Manage caching (that's api_client's job)
```

### API Client Layer
```
Responsibilities:
✓ Talk to PhishStats API
✓ Manage caching (THE KEY!)
✓ Implement retry logic
✓ Validate incoming data

Does NOT do:
✗ Handle HTTP responses to frontend
✗ Filter data
✗ Store in database
✗ Business logic
```

### Caching Layer
```
Responsibilities:
✓ Store responses with timestamps
✓ Check if data is fresh
✓ Return cached data if fresh
✓ Track cache age

Does NOT do:
✗ Make API calls
✗ Filter data
✗ Process data
```

---

## Data Flow: Request to Response

**Hosted Pages map:** The static app calls **`GET {api-base}/`** (Worker, `data-source=worker`) and receives a JSON array of map rows from **D1**; filters run in the browser.

**FastAPI path:** When the frontend uses `data-source=api`, it calls `GET /api/phishing/map-points`; **`api_client.fetch_incidents()`** and cache apply, then incidents map to `MapPoint` JSON.

The following walkthrough uses the legacy **heatmap** endpoint for illustration (`HeatmapData` with `coordinates` only).

### Request 1: Get Heatmap (Cache Hit - FAST!)

```
Time: 10:00:00

Frontend Request:
  GET /api/phishing/heatmap?threat_level=high

         │
         ▼
Route Handler (phishing.py):
  "Okay, I'll get heatmap data with threat_level=high"
  Calls: phishing_service.get_heatmap_data(threat_level="high")

         │
         ▼
PhishingService:
  "I need incidents from the API..."
  Calls: api_client.fetch_incidents()

         │
         ▼
API Client:
  "Wait, let me check cache_service first..."
  Calls: cache_service.is_expired("phishing_incidents", timeout=5)?
  
         │
         ▼
Cache Service:
  "Last fetch was at 09:57:00..."
  "That's only 3 minutes ago!"
  "Data is FRESH! Return it!"

         │
         ▼
API Client:
  "Great! Got cached data without making an API call!"
  Returns: [incident1, incident2, ...]

         │
         ▼
PhishingService:
  "Now I'll filter by threat_level and extract coordinates..."
  Transforms: 
    [incident1, incident2, ...] 
    → [[40.7128, -74.0060], [51.5074, -0.1278], ...]

         │
         ▼
Route Handler:
  Returns: HeatmapData JSON

         │
         ▼
Frontend:
  Receives in ~50ms and draws map!
  
  ✨ FAST because: NO API CALL MADE!
```

---

### Request 2: Get Heatmap (Cache Miss - First call)

```
Time: 10:10:00

Frontend Request:
  GET /api/phishing/heatmap?threat_level=high

         │
         ▼
Cache Service:
  "Data was last fetched at 10:00:00..."
  "That's 10 minutes ago! (> 5 minute timeout)"
  "Data is STALE! Need fresh data."

         │
         ▼
API Client:
  "Okay, going to PhishStats API..."
  Makes HTTP GET to: https://phishstats.info:20443/api/v1/

         │
         ▼
PhishStats API Response:
  [raw incident data with 200+ records]

         │
         ▼
API Client:
  ✓ Validates data with models.PhishingIncident
  ✓ Stores in cache_service.set()
  Returns: [incident1, incident2, ...]

         │
         ▼
PhishingService:
  Filters and transforms...
  Returns: [[lat, lon], ...]

         │
         ▼
Frontend:
  Receives in ~500ms (API call took time)
  
  Next requests in next 5 minutes will be FAST (cached)!
```

---

## Rate Limit Protection

### Without Our Backend
```
Frontend makes API calls directly:
  User 1: GET PhishStats API ✓
  User 2: GET PhishStats API ✓
  User 3: GET PhishStats API ✓
  ...
  User 20: GET PhishStats API ✓ (limit reached!)
  User 21: GET PhishStats API ✗ (BLOCKED)
  
  Problem: 21+ users can't access data!
```

### With Our Backend & Caching
```
User 1: GET /api/phishing/heatmap
  └─ Backend: Check cache? NO (first request)
  └─ Backend: Fetch from API (1 API call) ✓
  └─ Backend: Cache it for 5 minutes
  └─ User 1: Gets data in ~500ms

User 2: GET /api/phishing/heatmap (1 sec later)
  └─ Backend: Check cache? YES! (cached 1 sec ago)
  └─ Backend: Return cached data (0 API calls)
  └─ User 2: Gets data in ~50ms ✨

User 3-300: Same as User 2
  └─ All served from cache!

5 minutes later...

User 301: GET /api/phishing/heatmap
  └─ Backend: Check cache? NO (5+ minutes old)
  └─ Backend: Fetch from API (2 API calls total) ✓
  └─ Backend: Cache it for 5 minutes
  └─ User 301: Gets data in ~500ms

Benefit: 1 API call serves 300 users instead of 300 API calls!
```

---

## File Responsibility Matrix

```
                     Routes  Services  API Client  Database  Config
Receive HTTP        ✓       ✗         ✗           ✗         ✗
Call Services       ✓       ✗         ✗           ✗         ✗
Implement Logic     ✗       ✓         ✗           ✗         ✗
Filter Data         ✗       ✓         ✗           ✗         ✗
Transform Data      ✗       ✓         ✗           ✗         ✗
Call External API   ✗       ✗         ✓           ✗         ✗
Manage Cache        ✗       ✗         ✓           ✗         ✗
Retry Logic         ✗       ✗         ✓           ✗         ✗
Validate Data       ✗       ✗         ✓           ✗         ✗
Store Data          ✗       ✗         ✗           ✓         ✗
Query Data          ✗       ✓         ✗           ✓         ✗
Provide Settings    ✗       ✗         ✗           ✗         ✓
```

---

## Setup Flow

```
Step 1: Install Dependencies
  pip install -r requirements.txt
  └─ Installs: fastapi, uvicorn, httpx, pydantic, etc

Step 2: Initialize Database
  sqlite3 data/phishing.db < migrations/001_initial_schema.sql
  └─ Creates: phishing_incidents table, cache_metadata table, indexes

Step 3: Start Server
  python main.py
  └─ Initializes: FastAPI app, registers routes, starts server

Step 4: Server Ready!
  http://localhost:8000/docs
  └─ Access: Swagger UI, try out endpoints!
```

---

## Request Examples

### Example 1: Get Heatmap for High Threats
```
REQUEST:
  GET /api/phishing/heatmap?threat_level=high

RESPONSE:
  {
    "coordinates": [
      [40.7128, -74.0060],
      [51.5074, -0.1278],
      [48.8566, 2.3522]
    ],
    "incident_count": 3,
    "last_updated": "2026-02-21T10:30:00Z"
  }
```

### Example 2: Get All Statistics
```
REQUEST:
  GET /api/phishing/stats

RESPONSE:
  {
    "total_incidents": 1000,
    "critical_count": 50,
    "high_count": 200,
    "medium_count": 400,
    "low_count": 350,
    "top_targeted_companies": ["PayPal", "Apple", "Microsoft"],
    "most_active_countries": ["United States", "China", "Russia"],
    "last_updated": "2026-02-21T10:30:00Z"
  }
```

### Example 3: Get Analytics Overview
```
REQUEST:
  GET /api/analytics/overview

RESPONSE:
  {
    "total_incidents": 1000,
    "threat_distribution": {
      "critical": 50,
      "high": 200,
      "medium": 400,
      "low": 350
    },
    "top_regions": [
      ["United States", 450],
      ["China", 120],
      ["Russia", 98]
    ],
    "top_companies": [
      ["PayPal", 145],
      ["Apple", 98],
      ["Microsoft", 87]
    ],
    "hotspots": [...],
    "last_updated": "2026-02-21T10:30:00Z"
  }
```

---

## Key Numbers

```
API Rate Limit:        20 calls/minute
Cache Timeout:         5 minutes
Requests per minute:   ∞ (served from cache!)
API calls with cache:  1 per 5 minutes
Without cache would be: 300+ per 5 minutes (BLOCKED!)

Performance:
  - With cache hit: ~50ms response time
  - Without cache: ~500ms response time (API call)
  - Speedup: 10x faster when cached!
```

---

## Code Organization

```
Each file has 3 sections:

1. DOCSTRING (400+ lines explaining everything)
   - What the file does
   - What other files it connects to
   - How to use it
   - Example usage

2. IMPORTS (what it needs)
   - config, models, services, etc

3. IMPLEMENTATION (actual code)
   - Classes
   - Functions
   - Methods

Total: ~1800 lines of code + ~1500 lines of docs = FULLY DOCUMENTED!
```

---

## Why This Architecture?

```
Separation of Concerns:
  ✓ Each file has ONE clear responsibility
  ✓ Easy to modify without breaking others
  ✓ Easy to test individually
  ✓ Easy to understand at a glance

Layered Design:
  ✓ Routes only care about HTTP
  ✓ Services only care about logic
  ✓ API Client only cares about PhishStats
  ✓ Each layer independent

Scalability:
  ✓ Cache prevents API exhaustion
  ✓ Database enables growth
  ✓ Services reusable across endpoints
  ✓ Ready to scale with traffic

Maintainability:
  ✓ 100% documented
  ✓ Type hints for IDE support
  ✓ Consistent patterns throughout
  ✓ Easy for new developers to understand

Frontend Agnosticism:
  ✓ Hosted map does not call PhishStats from the browser
  ✓ FastAPI still hides PhishStats + cache for api-mode clients
  ✓ Rate limiting remains in api_client for Python path
```

---

## Next: What Your Team Does

```
Ethan (ingest):
  └─ data-extraction-worker: PhishStats paging + cron (src/phishstats.ts, cursor.ts)

Thomas (D1):
  └─ schema.sql, D1 migrations, MAP_POINTS_SELECT_SQL / UPSERT alignment in queries.ts

Matt (map feed + ingest binds):
  └─ transform.ts, map-points.ts, Worker fetch handler

Bryon (frontend / DevOps):
  └─ Pages meta, CI, wrangler deploys; FastAPI for local api-mode dev

Matthew (UI):
  └─ Map + filters in frontend/index.html (consumes JSON array from Worker or FastAPI)
```

---

**See also:** [`backend/data-extraction-worker/README.md`](data-extraction-worker/README.md) for D1 ingest + map HTTP API.
