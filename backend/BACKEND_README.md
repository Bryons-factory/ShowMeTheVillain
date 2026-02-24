"""
═══════════════════════════════════════════════════════════════════════════════
FILE: BACKEND_README.md
PURPOSE: Complete guide to the Phish 'N Heat backend architecture
═══════════════════════════════════════════════════════════════════════════════
"""

# Phish 'N Heat Backend - Complete Documentation

## Overview

The backend is designed with **clean separation of concerns** following a **3-tier layered architecture**:

```
PRESENTATION LAYER
├── routes/phishing.py       (HTTP endpoints for phishing data)
└── routes/analytics.py      (HTTP endpoints for analytics)
          ↓
BUSINESS LOGIC LAYER
├── services/phishing_service.py     (Fetch, filter, validate incidents)
├── services/cache_service.py        (Respect API rate limits)
└── services/analytics_service.py    (Analyze and aggregate data)
          ↓
DATA ACCESS LAYER
├── api_client.py           (PhishStats API communication)
├── database.py             (Cloudflare D1 storage)
└── config.py               (Centralized settings)
```

## Directory Structure

```
backend/
├── config.py                          # Centralized configuration
├── api_client.py                      # PhishStats API wrapper
├── models.py                          # Data validation models (Pydantic)
├── database.py                        # Database operations
├── main.py                            # FastAPI application entry point
├── requirements.txt                   # Python dependencies
│
├── services/
│   ├── __init__.py
│   ├── cache_service.py               # Caching layer (respects rate limits)
│   ├── phishing_service.py            # Business logic for incidents
│   └── analytics_service.py           # Analytics and insights
│
├── routes/
│   ├── __init__.py
│   ├── phishing.py                    # /api/phishing/* endpoints
│   └── analytics.py                   # /api/analytics/* endpoints
│
└── migrations/
    └── 001_initial_schema.sql         # Database schema
```

## File Connections & Data Flow

### 1. Configuration Layer: `config.py`
**Purpose**: Single source of truth for all settings

**Provides**:
- API URL and timeout values
- Rate limit settings (20 calls/minute)
- Cache timeout (5 minutes)
- Database connection strings
- CORS and hosting settings

**Used by**: Every other module imports `config` to get settings

```
config.py
  ↓ (provides settings to)
  ├─ api_client.py
  ├─ database.py
  ├─ main.py
  └─ services/
```

---

### 2. External API Communication: `api_client.py`
**Purpose**: Talk to PhishStats API while respecting rate limits

**What it does**:
1. Checks cache_service for fresh data (< 5 min old)
2. If cache is fresh → return it (no API call!)
3. If cache is stale → fetch from PhishStats API
4. Validates incident data
5. Stores in cache_service

**Uses**: config.py, services/cache_service.py

**Called by**: services/phishing_service.py

```
phishing_service.py
  ↓ (calls)
api_client.py
  ├─ Uses: config.PHISHSTATS_API_URL, config.PHISHSTATS_TIMEOUT
  ├─ Checks: cache_service.is_expired()
  └─ Stores: cache_service.set()
```

---

### 3. Caching Layer: `services/cache_service.py`
**Purpose**: Simple in-memory cache to respect API rate limits

**Key methods**:
- `set(key, value)` - Store data with timestamp
- `get(key)` - Retrieve cached data
- `is_expired(key, timeout_minutes)` - Check if data is fresh
- `clear()` - Clear cache entries

**Why it matters**:
- PhishStats allows 20 calls/minute
- Caching prevents wasting API calls
- With 5-minute cache, 1 request → data serves 300 users!

```
api_client.py
  → cache_service.get() → YES: return cached data
                        → NO: fetch from API
  → cache_service.set() → store with timestamp
```

---

### 4. Business Logic: `services/phishing_service.py`
**Purpose**: Core logic for handling phishing data

**Key methods**:
- `get_all_incidents()` - Fetch and validate all incidents
- `get_heatmap_data(threat_level, limit)` - Get coordinates for map
- `get_filtered_incidents(threat_level, company, country, isp)` - Filter data
- `get_threat_statistics()` - Aggregate statistics

**Uses**: api_client.py, models.py

**Called by**: routes/phishing.py

**Data flow**:
```
Frontend calls: GET /api/phishing/heatmap?threat_level=high
              ↓
routes/phishing.py
              ↓
phishing_service.get_heatmap_data(threat_level="high")
              ├─ api_client.fetch_incidents()
              │   ├─ cache_service.get()
              │   ├─ PhishStats API if needed
              │   └─ cache_service.set()
              ├─ Validate with models.PhishingIncident
              ├─ Filter by threat_level
              └─ Extract coordinates [[lat, lon], ...]
              ↓
Return HeatmapData to frontend
```

---

### 5. Analytics Logic: `services/analytics_service.py`
**Purpose**: Generate insights and statistics

**Key methods**:
- `get_threat_overview()` - Complete overview
- `get_threat_levels_distribution()` - Count by severity
- `get_top_threat_regions(limit)` - Top countries
- `get_most_targeted_companies(limit)` - Most impersonated brands
- `get_threat_hotspots(limit)` - Regional threat breakdown
- `get_isp_threat_rankings(limit)` - ISPs with most activity

**Uses**: services/phishing_service.py

**Called by**: routes/analytics.py

```
Frontend calls: GET /api/analytics/overview
              ↓
routes/analytics.py
              ↓
analytics_service.get_threat_overview()
              ├─ phishing_service.get_all_incidents()
              ├─ Count by threat_level
              ├─ Count by company
              ├─ Count by country
              ├─ Count by ISP
              └─ Return aggregated statistics
              ↓
Frontend displays charts and insights
```

---

### 6. Data Models: `models.py`
**Purpose**: Validate data using Pydantic

**Models defined**:
- `PhishingIncident` - Single incident with validation
- `HeatmapData` - Response for heatmap endpoint
- `HeatmapCoordinate` - Single map coordinate
- `ThreatStatistics` - Aggregated threat stats
- `FilterRequest` - Request body for filters

**How it's used**:
```python
# Pydantic automatically validates
incident = PhishingIncident(**api_response)
# Raises ValidationError if invalid latitude/longitude/etc
```

**Used by**: api_client.py, services/, routes/

---

### 7. Database Layer: `database.py`
**Purpose**: Persistent storage in Cloudflare D1

**Key methods**:
- `add_incident(incident)` - Store an incident
- `get_incidents(limit, offset, threat_level)` - Query incidents
- `get_incident_count()` - Total count
- `update_cache_metadata()` - Track cache updates
- `clear_old_incidents(days)` - Clean up old data

**Tables**:
1. `phishing_incidents` - Stores incident data
2. `cache_metadata` - Tracks last API fetch
3. `request_logs` - Optional: logs API requests

**Used by**: services/ (for historical analysis)

---

### 8. HTTP Routes: `routes/phishing.py`
**Purpose**: Define REST API endpoints for phishing data

**Endpoints**:
```
GET /api/phishing/               - Get all incidents
GET /api/phishing/heatmap        - Get coordinates for heatmap
GET /api/phishing/filtered       - Get with advanced filters
GET /api/phishing/stats          - Get threat statistics
GET /api/phishing/refresh        - Force cache refresh
```

**Pattern**:
```python
@router.get("/phishing/heatmap")
async def get_heatmap_data(threat_level: Optional[str] = None):
    heatmap = await phishing_service.get_heatmap_data(threat_level)
    return heatmap
```

**Connects**: routes/phishing.py → services/phishing_service.py

---

### 9. Analytics Routes: `routes/analytics.py`
**Purpose**: Define REST API endpoints for analytics

**Endpoints**:
```
GET /api/analytics/overview              - Complete overview
GET /api/analytics/threat-distribution   - By threat level
GET /api/analytics/top-regions          - Top countries
GET /api/analytics/top-companies        - Most targeted brands
GET /api/analytics/threat-hotspots      - Regional breakdown
GET /api/analytics/isp-rankings         - ISPs with most activity
```

**Connects**: routes/analytics.py → services/analytics_service.py

---

### 10. Application Setup: `main.py`
**Purpose**: Initialize and run FastAPI application

**What it does**:
1. Creates FastAPI app
2. Registers routes (phishing, analytics)
3. Configures CORS for frontend
4. Provides health check and info endpoints
5. Starts server on port 8000

**Endpoints provided**:
```
GET /              - Welcome message
GET /health        - Health check
GET /info          - App information
GET /docs          - Swagger UI (auto-generated)
GET /redoc         - ReDoc (auto-generated)
```

---

## Data Flow Examples

### Example 1: Frontend Requests Heatmap
```
Frontend:
  fetch('/api/phishing/heatmap?threat_level=high')
  
Backend Flow:
  1. main.py receives GET request
  2. routes/phishing.py matches endpoint
  3. Calls: phishing_service.get_heatmap_data(threat_level="high")
  4. phishing_service calls: api_client.fetch_incidents()
  5. api_client checks: cache_service.is_expired("phishing_incidents", 5)?
     → If fresh: return cached data (FAST!)
     → If stale: Make HTTP request to PhishStats API
  6. api_client validates data with models.PhishingIncident
  7. api_client stores in cache_service.set()
  8. phishing_service filters by threat_level="high"
  9. phishing_service extracts [[lat, lon], ...]
  10. routes/phishing.py returns HeatmapData JSON
  
Frontend Receives:
  {
    "coordinates": [[40.7128, -74.0060], ...],
    "incident_count": 342,
    "last_updated": "2026-02-21T10:30:00Z"
  }
```

### Example 2: Frontend Requests Analytics
```
Frontend:
  fetch('/api/analytics/overview')
  
Backend Flow:
  1. routes/analytics.py receives request
  2. Calls: analytics_service.get_threat_overview()
  3. analytics_service calls: phishing_service.get_all_incidents()
  4. (Same as Example 1 - uses cache)
  5. analytics_service analyzes incidents:
     - Count by threat_level
     - Count by company (top 5)
     - Count by country (top 5)
     - Count by ISP (top 5)
     - Group by country with threat breakdowns
  6. Returns aggregated statistics
  
Frontend Receives:
  {
    "total_incidents": 1000,
    "threat_distribution": {"critical": 50, "high": 200, ...},
    "top_regions": [["United States", 450], ...],
    "top_companies": [["PayPal", 145], ...],
    "hotspots": [...],
    "last_updated": "2026-02-21T10:30:00Z"
  }
```

---

## Getting Started

### 1. Install Dependencies
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Set Up Database
```bash
# Create data directory
mkdir data

# Initialize database
sqlite3 data/phishing.db < migrations/001_initial_schema.sql
```

### 3. Run the Backend
```bash
python main.py
# Server starts on http://localhost:8000
```

### 4. Access Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- API Info: http://localhost:8000/info

### 5. Test an Endpoint
```bash
# Get heatmap data
curl "http://localhost:8000/api/phishing/heatmap"

# Get analytics overview
curl "http://localhost:8000/api/analytics/overview"

# Get threat statistics
curl "http://localhost:8000/api/phishing/stats"
```

---

## Architecture Principles

1. **Separation of Concerns**
   - Routes: Only handle HTTP
   - Services: Only handle business logic
   - API Client: Only handle external communication
   - Database: Only handle persistence

2. **Dependency Injection**
   - config.py provides settings to all layers
   - Services are initialized once and reused

3. **Caching Strategy**
   - Respects 20 calls/minute API limit
   - 5-minute cache timeout (configurable)
   - Cache bypassed on force_refresh

4. **Data Validation**
   - Pydantic validates all incoming data
   - Invalid coordinates automatically rejected
   - Threat levels restricted to allowed values

5. **Frontend Agnosticism**
   - Frontend doesn't know about PhishStats API
   - Frontend doesn't handle rate limiting
   - Frontend doesn't manage cache
   - Backend is the "source of truth"

---

## What Each File Does (Quick Reference)

| File | Purpose | Connects To |
|------|---------|-------------|
| config.py | Settings hub | Everything |
| api_client.py | PhishStats API wrapper | cache_service, models |
| models.py | Data validation | api_client, services, routes |
| database.py | Persistent storage | services |
| services/cache_service.py | Caching with timestamps | api_client |
| services/phishing_service.py | Core business logic | api_client, models, database |
| services/analytics_service.py | Analytics & insights | phishing_service |
| routes/phishing.py | HTTP endpoints for incidents | phishing_service |
| routes/analytics.py | HTTP endpoints for analytics | analytics_service |
| main.py | FastAPI app initialization | routes, config |
| requirements.txt | Python dependencies | pip install |
| migrations/001_initial_schema.sql | Database schema | database.py |

---

## Next Steps for Your Team

1. **Ethan** (API Handling):
   - Verify api_client.py handles PhishStats response format
   - Add any missing fields from API responses to models.py

2. **Thomas** (Backend/Database):
   - Connect to actual Cloudflare D1 (replace SQLite in production)
   - Add database query optimizations
   - Implement backup/retention policies

3. **Matthew** (Frontend Integration):
   - Test each endpoint with frontend
   - Verify CORS is working
   - Implement error handling in frontend

4. **Bryon** (Architecture/Hosting):
   - Set up Cloudflare deployment
   - Configure environment variables
   - Monitor API rate limits

---

## Environment Variables (Create .env file)

```
DEBUG=True
LOG_LEVEL=INFO
CLOUDFLARE_D1_CONNECTION=your_cloudflare_connection_string
DATABASE_PATH=./data/phishing.db
FRONTEND_ORIGIN=http://localhost:3000
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
```

---

## Questions?

Each file has detailed docstrings explaining:
- What the file does
- What other files it connects to
- How to use it
- Example usage

Read the docstring at the top of each file for more details!
