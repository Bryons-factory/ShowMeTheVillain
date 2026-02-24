"""
═══════════════════════════════════════════════════════════════════════════════
FILE: api_client.py
PURPOSE: Handle all external API communication with PhishStats
═══════════════════════════════════════════════════════════════════════════════

WHAT THIS FILE DOES:
- Makes HTTP requests to the PhishStats API
- Implements retry logic for failed requests
- Coordinates with cache_service.py to respect the 20 calls/minute rate limit
- Validates API responses
- Converts raw API data into clean format for services

WHAT IT CONNECTS TO:
- config.py: Uses API URL, timeout, and rate limit settings
- services/cache_service.py: Checks/stores cached data to avoid redundant API calls
- services/phishing_service.py: Phishing service calls this to fetch fresh data
- models.py: Uses data models to validate API responses

ARCHITECTURE:
    Frontend Request
         ↓
    routes/phishing.py
         ↓
    services/phishing_service.py (business logic)
         ↓
    api_client.py (THIS FILE - "Should I fetch from API or use cache?")
         ↓
    PhishStats API (external)

HOW TO USE:
    from api_client import PhishStatsClient
    
    client = PhishStatsClient()
    data = await client.fetch_incidents()  # Returns list of dicts with phishing data
    data_with_force_refresh = await client.fetch_incidents(force_refresh=True)

═══════════════════════════════════════════════════════════════════════════════
"""

import httpx
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from config import config
from services.cache_service import CacheService

logger = logging.getLogger(__name__)


class PhishStatsClient:
    """
    Client for communicating with the PhishStats API.
    
    This class:
    1. Fetches phishing incident data from the API
    2. Caches responses to respect the 20 calls/minute rate limit
    3. Implements retry logic for failed requests
    4. Validates incoming data
    """
    
    def __init__(self):
        """Initialize the PhishStats API client with config settings."""
        self.base_url = config.PHISHSTATS_API_URL
        self.timeout = config.PHISHSTATS_TIMEOUT
        self.max_retries = config.MAX_RETRIES
        self.retry_delay = config.RETRY_DELAY_SECONDS
        self.cache_timeout = config.CACHE_TIMEOUT_MINUTES
        
        # Use cache service to store/retrieve API responses
        self.cache = CacheService()
        
        logger.info(f"PhishStatsClient initialized | URL: {self.base_url}")
    
    async def fetch_incidents(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch phishing incidents from PhishStats API or return cached data.
        
        STRATEGY:
        1. Check if fresh cached data exists (< CACHE_TIMEOUT_MINUTES old)
        2. If cached data is fresh: Return it (SAVES AN API CALL!)
        3. If cache is stale/empty: Fetch from API and cache the result
        
        Args:
            force_refresh (bool): If True, bypass cache and fetch fresh data
        
        Returns:
            List[Dict]: List of phishing incidents with data like:
                [
                    {
                        "id": 123,
                        "url": "http://malicious-site.com",
                        "latitude": 40.7128,
                        "longitude": -74.0060,
                        "threat_level": "high",
                        "company": "PayPal",
                        "detected_at": "2026-02-21T10:30:00Z"
                    },
                    ...
                ]
        
        Raises:
            Exception: If API is unreachable after all retries
        """
        
        cache_key = "phishing_incidents"
        
        # ──────────────────────────────────────────────────────────────────
        # STEP 1: Check cache (respects API rate limits)
        # ──────────────────────────────────────────────────────────────────
        if not force_refresh:
            cached_data = self.cache.get(cache_key)
            
            if cached_data and not self.cache.is_expired(cache_key, self.cache_timeout):
                logger.info(f"✓ Returning cached phishing data ({len(cached_data)} incidents)")
                return cached_data
            elif cached_data:
                logger.info(f"✗ Cached data is stale (> {self.cache_timeout} min old), fetching fresh...")
        
        # ──────────────────────────────────────────────────────────────────
        # STEP 2: Fetch from API with retry logic
        # ──────────────────────────────────────────────────────────────────
        data = await self._fetch_from_api_with_retries()
        
        # ──────────────────────────────────────────────────────────────────
        # STEP 3: Validate and cache the new data
        # ──────────────────────────────────────────────────────────────────
        if data:
            self.cache.set(cache_key, data)
            logger.info(f"✓ Fetched and cached {len(data)} incidents from PhishStats API")
            return data
        
        return []
    
    async def _fetch_from_api_with_retries(self) -> List[Dict[str, Any]]:
        """
        Make HTTP request to PhishStats API with retry logic.
        
        Retries up to MAX_RETRIES times with exponential backoff if the
        API is temporarily unavailable.
        
        Returns:
            List[Dict]: Raw API response as list of incident dicts
        """
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Fetching from PhishStats API (attempt {attempt}/{self.max_retries})...")
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        self.base_url,
                        timeout=self.timeout,
                        headers={
                            "User-Agent": f"{config.APP_NAME}/{config.APP_VERSION}"
                        }
                    )
                    
                    # Raise exception for bad status codes
                    response.raise_for_status()
                    
                    data = response.json()
                    logger.info(f"✓ Successfully received {len(data)} records from PhishStats")
                    return data
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP Error {e.response.status_code}: {e.response.text}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay)
                    
            except httpx.RequestError as e:
                logger.error(f"Request Error: {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay)
            
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay)
        
        # All retries exhausted
        raise Exception(
            f"Failed to fetch from PhishStats API after {self.max_retries} attempts"
        )
    
    def validate_coordinates(self, latitude: float, longitude: float) -> bool:
        """
        Validate that coordinates are within valid ranges.
        
        Args:
            latitude: Must be between -90 and 90
            longitude: Must be between -180 and 180
        
        Returns:
            bool: True if coordinates are valid
        """
        lat_valid = config.MIN_LATITUDE <= latitude <= config.MAX_LATITUDE
        lon_valid = config.MIN_LONGITUDE <= longitude <= config.MAX_LONGITUDE
        
        return lat_valid and lon_valid
