"""
═══════════════════════════════════════════════════════════════════════════════
FILE: services/cache_service.py
PURPOSE: Manage caching to respect API rate limits
═══════════════════════════════════════════════════════════════════════════════

WHAT THIS FILE DOES:
- Stores API responses in memory with timestamps
- Checks if cached data is still "fresh" (< CACHE_TIMEOUT_MINUTES old)
- Prevents unnecessary API calls (respects 20 calls/minute limit)
- Simple in-memory cache (can be upgraded to Redis later)

WHAT IT CONNECTS TO:
- config.py: Uses CACHE_TIMEOUT_MINUTES setting
- api_client.py: Checks/stores cached data before hitting the API
- services/phishing_service.py: May check cache status

ARCHITECTURE:
    api_client.py checks:
    "Is the data in cache fresh?"
         ↓
    cache_service.py (THIS FILE) answers:
    "Yes, here it is" OR "No, it's stale"
         ↓
    api_client.py decides:
    "Return cached data" OR "Fetch from API"

HOW TO USE:
    from services.cache_service import CacheService
    
    cache = CacheService()
    
    # Store data
    cache.set("phishing_incidents", [{"url": "...", "lat": 40.7}, ...])
    
    # Retrieve data
    data = cache.get("phishing_incidents")
    
    # Check if data is fresh (< 5 minutes old)
    if cache.is_expired("phishing_incidents", 5):
        print("Data is stale, need to refresh")

═══════════════════════════════════════════════════════════════════════════════
"""

from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """
    Simple in-memory cache for API responses.
    
    This prevents hitting the PhishStats API more than 20 times per minute.
    
    Future enhancement: Replace with Redis for distributed caching across
    multiple backend instances.
    """
    
    def __init__(self):
        """Initialize the cache storage."""
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def set(self, key: str, value: Any) -> None:
        """
        Store a value in cache with current timestamp.
        
        Args:
            key: Unique cache key (e.g., "phishing_incidents")
            value: Data to cache
        
        Example:
            cache.set("phishing_incidents", [{"id": 1, ...}, {"id": 2, ...}])
        """
        self._cache[key] = {
            "value": value,
            "timestamp": datetime.now()
        }
        logger.info(f"✓ Cached '{key}' at {self._cache[key]['timestamp']}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from cache (if it exists).
        
        Does NOT check if data is fresh - use is_expired() for that.
        
        Args:
            key: Cache key to retrieve
        
        Returns:
            Cached value if exists, None otherwise
        
        Example:
            data = cache.get("phishing_incidents")
            if data:
                print(f"Found {len(data)} cached incidents")
        """
        if key in self._cache:
            return self._cache[key]["value"]
        logger.warning(f"✗ Cache miss for key: '{key}'")
        return None
    
    def is_expired(self, key: str, timeout_minutes: int) -> bool:
        """
        Check if cached data is stale (older than timeout_minutes).
        
        Args:
            key: Cache key to check
            timeout_minutes: How old (in minutes) before data is considered stale
        
        Returns:
            True if data is missing or stale, False if data is fresh
        
        Example:
            # Check if cache is older than 5 minutes
            if cache.is_expired("phishing_incidents", 5):
                print("Need to fetch fresh data from API")
            else:
                print("Cached data is still fresh, use it")
        """
        if key not in self._cache:
            logger.warning(f"✗ Key not in cache: '{key}'")
            return True
        
        cached_time = self._cache[key]["timestamp"]
        age_minutes = (datetime.now() - cached_time).total_seconds() / 60
        
        is_stale = age_minutes > timeout_minutes
        
        if is_stale:
            logger.info(f"✗ Cache expired: '{key}' is {age_minutes:.1f}min old (timeout={timeout_minutes}min)")
        else:
            logger.info(f"✓ Cache fresh: '{key}' is {age_minutes:.1f}min old (timeout={timeout_minutes}min)")
        
        return is_stale
    
    def clear(self, key: Optional[str] = None) -> None:
        """
        Clear cache entries.
        
        Args:
            key: Specific key to clear, or None to clear entire cache
        
        Example:
            cache.clear("phishing_incidents")  # Clear one entry
            cache.clear()  # Clear everything
        """
        if key:
            if key in self._cache:
                del self._cache[key]
                logger.info(f"✓ Cleared cache key: '{key}'")
        else:
            self._cache.clear()
            logger.info(f"✓ Cleared entire cache")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get information about what's currently in cache.
        
        Useful for debugging and monitoring.
        
        Returns:
            Dictionary with cache statistics
        
        Example:
            info = cache.get_cache_info()
            print(info)
            # Output: {
            #     "phishing_incidents": {
            #         "timestamp": "2026-02-21 10:30:00",
            #         "size": 342,
            #         "age_minutes": 2.5
            #     }
            # }
        """
        info = {}
        now = datetime.now()
        
        for key, data in self._cache.items():
            timestamp = data["timestamp"]
            age_minutes = (now - timestamp).total_seconds() / 60
            value = data["value"]
            
            # Estimate size
            size = len(value) if isinstance(value, list) else 1
            
            info[key] = {
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "age_minutes": round(age_minutes, 2),
                "items": size
            }
        
        return info
