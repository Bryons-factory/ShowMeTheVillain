"""
═══════════════════════════════════════════════════════════════════════════════
FILE: config.py
PURPOSE: Centralized configuration and settings management
═══════════════════════════════════════════════════════════════════════════════

WHAT THIS FILE DOES:
- Defines all hardcoded values, environment variables, and settings
- Acts as a single source of truth for the entire backend
- Stores API credentials, timeouts, rate limits, and database connections
- Keeps sensitive data organized and easy to modify

WHAT IT CONNECTS TO:
- api_client.py: Provides API URLs, timeouts, and rate limits
- database.py: Provides database connection strings
- services/: All services use these settings
- main.py: Initializes with these settings

HOW TO USE:
    from config import config
    
    # Access any setting
    api_url = config.PHISHSTATS_API_URL
    timeout = config.PHISHSTATS_TIMEOUT
    cache_time = config.CACHE_TIMEOUT_MINUTES

═══════════════════════════════════════════════════════════════════════════════
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    """
    Central configuration object for the entire Phish 'N Heat backend.
    All values should be defined here and passed to other modules.
    """
    
    # ──────────────────────────────────────────────────────────────────────────
    # PHISHSTATS API CONFIGURATION
    # These settings control how we communicate with the PhishStats API
    # ──────────────────────────────────────────────────────────────────────────
    PHISHSTATS_API_URL: str = "https://phishstats.info:20443/api/v1/"
    PHISHSTATS_API_KEY: str = os.getenv("PHISHSTATS_API_KEY", "")  # If API requires key
    PHISHSTATS_TIMEOUT: int = 10  # seconds - how long to wait for API response
    
    # ──────────────────────────────────────────────────────────────────────────
    # RATE LIMITING & CACHING
    # These settings ensure we respect the 20 calls/minute limit from PhishStats
    # and cache data efficiently
    # ──────────────────────────────────────────────────────────────────────────
    API_RATE_LIMIT: int = 20  # calls per minute allowed by PhishStats
    CACHE_TIMEOUT_MINUTES: int = 5  # how long to cache data before refreshing
    MAX_RETRIES: int = 3  # retry failed API calls this many times
    RETRY_DELAY_SECONDS: int = 2  # wait this long between retries
    
    # ──────────────────────────────────────────────────────────────────────────
    # DATABASE CONFIGURATION
    # These settings connect to Cloudflare D1 for persistent data storage
    # ──────────────────────────────────────────────────────────────────────────
    CLOUDFLARE_D1_CONNECTION: str = os.getenv("CLOUDFLARE_D1_CONNECTION", "")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "./data/phishing.db")
    
    # ──────────────────────────────────────────────────────────────────────────
    # APPLICATION SETTINGS
    # General app behavior and logging
    # ──────────────────────────────────────────────────────────────────────────
    DEBUG: bool = os.getenv("DEBUG", "False") == "True"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    APP_NAME: str = "Phish 'N Heat Backend"
    APP_VERSION: str = "1.0.0"
    
    # ──────────────────────────────────────────────────────────────────────────
    # FRONTEND CORS & HOSTING
    # Settings for frontend-backend communication
    # ──────────────────────────────────────────────────────────────────────────
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    
    # ──────────────────────────────────────────────────────────────────────────
    # DATA VALIDATION LIMITS
    # These limits ensure data quality and prevent outliers
    # ──────────────────────────────────────────────────────────────────────────
    MAX_LATITUDE: float = 90.0
    MIN_LATITUDE: float = -90.0
    MAX_LONGITUDE: float = 180.0
    MIN_LONGITUDE: float = -180.0
    MAX_INCIDENTS_PER_REQUEST: int = 1000  # prevent excessive data transfers


# Single global instance used throughout the application
config = Settings()

# Print configuration on startup (for debugging, remove in production)
if config.DEBUG:
    print(f"[DEBUG] {config.APP_NAME} v{config.APP_VERSION} initialized")
    print(f"[DEBUG] PhishStats API URL: {config.PHISHSTATS_API_URL}")
    print(f"[DEBUG] Cache timeout: {config.CACHE_TIMEOUT_MINUTES} minutes")
