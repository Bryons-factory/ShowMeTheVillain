-- ═══════════════════════════════════════════════════════════════════════════════
-- FILE: migrations/001_initial_schema.sql
-- PURPOSE: Database schema initialization for Cloudflare D1
-- ═══════════════════════════════════════════════════════════════════════════════
-- 
-- WHAT THIS FILE DOES:
-- - Defines the structure of the phishing_incidents table
-- - Defines the structure of the cache_metadata table
-- - Creates indexes for fast querying
-- - Sets up constraints and relationships
--
-- WHAT IT CONNECTS TO:
-- - database.py: Executes these schema creation statements
-- - api_client.py: Stores data from API responses in these tables
-- - services/: Query data from these tables
--
-- HOW TO USE:
-- For development (SQLite):
--     sqlite3 data/phishing.db < migrations/001_initial_schema.sql
--
-- For production (Cloudflare D1):
--     wrangler d1 execute <database-name> < migrations/001_initial_schema.sql
--
-- ═══════════════════════════════════════════════════════════════════════════════


-- ──────────────────────────────────────────────────────────────────────────────
-- TABLE: phishing_incidents
-- 
-- PURPOSE: Store individual phishing incidents
--
-- COLUMNS:
--   - id: Unique identifier (Primary Key)
--   - url: The malicious URL detected
--   - latitude: Geographic latitude (-90 to 90)
--   - longitude: Geographic longitude (-180 to 180)
--   - threat_level: Severity (low, medium, high, critical)
--   - company: Company/brand being targeted (e.g., "PayPal")
--   - country: Country/region of origin
--   - isp: Internet Service Provider
--   - detected_at: When PhishStats detected this incident
--   - created_at: When we stored it in the database
--   - updated_at: Last time we updated this record
-- ──────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS phishing_incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    threat_level TEXT DEFAULT 'unknown',
    company TEXT,
    country TEXT,
    isp TEXT,
    detected_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for faster queries
-- These speed up filtering by common fields
CREATE INDEX IF NOT EXISTS idx_threat_level 
    ON phishing_incidents(threat_level);

CREATE INDEX IF NOT EXISTS idx_company 
    ON phishing_incidents(company);

CREATE INDEX IF NOT EXISTS idx_country 
    ON phishing_incidents(country);

CREATE INDEX IF NOT EXISTS idx_isp 
    ON phishing_incidents(isp);

CREATE INDEX IF NOT EXISTS idx_created_at 
    ON phishing_incidents(created_at);

-- Index for geographic queries (heatmap)
CREATE INDEX IF NOT EXISTS idx_coordinates 
    ON phishing_incidents(latitude, longitude);


-- ──────────────────────────────────────────────────────────────────────────────
-- TABLE: cache_metadata
--
-- PURPOSE: Track when we last fetched from the API and how many items were cached
--
-- This table helps us:
-- 1. Know when the cache was last updated
-- 2. Track how many incidents are in each cache
-- 3. Implement intelligent cache invalidation
--
-- COLUMNS:
--   - api_source: Which API (e.g., "phishstats")
--   - last_fetch: Timestamp of last API fetch
--   - incident_count: How many incidents were fetched
--   - updated_at: When this metadata was last updated
-- ──────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS cache_metadata (
    api_source TEXT PRIMARY KEY,
    last_fetch TIMESTAMP,
    incident_count INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ──────────────────────────────────────────────────────────────────────────────
-- TABLE: request_logs (Optional - for analytics)
--
-- PURPOSE: Log all API requests for analytics and monitoring
--
-- This helps track:
-- - Which endpoints are called most
-- - When users are accessing the system
-- - Performance metrics
--
-- COLUMNS:
--   - id: Unique log entry ID
--   - endpoint: Which API endpoint was called
--   - method: HTTP method (GET, POST, etc)
--   - status_code: HTTP response code
--   - response_time_ms: How long the request took
--   - timestamp: When the request happened
-- ──────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS request_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    status_code INTEGER,
    response_time_ms INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_endpoint_logs 
    ON request_logs(endpoint, timestamp);


-- ──────────────────────────────────────────────────────────────────────────────
-- Verification Queries
-- ──────────────────────────────────────────────────────────────────────────────
-- To verify the schema was created, you can run:
--   SELECT name FROM sqlite_master WHERE type='table';
--   .schema phishing_incidents
--   .schema cache_metadata
--   .indices
-- ──────────────────────────────────────────────────────────────────────────────
