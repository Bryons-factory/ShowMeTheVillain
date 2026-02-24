"""
═══════════════════════════════════════════════════════════════════════════════
FILE: database.py
PURPOSE: Handle all Cloudflare D1 database operations
═══════════════════════════════════════════════════════════════════════════════

WHAT THIS FILE DOES:
- Connects to Cloudflare D1 (serverless SQL database)
- Manages database schema and migrations
- Provides methods for CRUD operations (Create, Read, Update, Delete)
- Stores phishing incidents for historical analysis
- Manages cache metadata for tracking API call patterns

WHAT IT CONNECTS TO:
- config.py: Uses CLOUDFLARE_D1_CONNECTION setting
- models.py: Stores/retrieves data following these models
- services/phishing_service.py: May query historical data
- services/analytics_service.py: Queries historical trends

ARCHITECTURE:
    api_client.py fetches fresh data from PhishStats API
         ↓
    services/phishing_service.py processes it
         ↓
    database.py (THIS FILE) stores it persistently
         ↓
    services/analytics_service.py queries historical data
         ↓
    Frontend gets historical trends and analytics

DATABASE SCHEMA:
    Table: phishing_incidents
    - id: Unique incident ID
    - url: Malicious URL
    - latitude, longitude: Geographic location
    - threat_level: Severity (low, medium, high, critical)
    - company: Targeted company
    - country: Country of origin
    - isp: Internet Service Provider
    - detected_at: When incident was detected
    - created_at: When we stored it
    
    Table: cache_metadata
    - api_source: Which API this cache entry is for
    - last_fetch: Last time we fetched from API
    - incident_count: How many incidents stored

HOW TO USE:
    from database import Database
    
    db = Database()
    
    # Store an incident
    await db.add_incident({
        "url": "http://phishing.com",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "threat_level": "high",
        "company": "PayPal"
    })
    
    # Query incidents
    incidents = await db.get_incidents(limit=100)
    
    # Update cache metadata
    await db.update_cache_metadata("phishstats", 342)

═══════════════════════════════════════════════════════════════════════════════
"""

import logging
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime

from config import config

logger = logging.getLogger(__name__)


class Database:
    """
    Database interface for Cloudflare D1.
    
    Handles all persistent storage of phishing incidents and cache metadata.
    
    Note: For production, connect to actual Cloudflare D1 via API.
    For development, using SQLite as a mock.
    """
    
    def __init__(self):
        """Initialize database connection."""
        self.connection_string = config.CLOUDFLARE_D1_CONNECTION
        self.db_path = config.DATABASE_PATH
        
        # Initialize schema if not exists
        self._initialize_schema()
        
        logger.info(f"Database initialized | Path: {self.db_path}")
    
    def _initialize_schema(self) -> None:
        """Create tables if they don't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create phishing_incidents table
            cursor.execute("""
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
                )
            """)
            
            # Create cache_metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache_metadata (
                    api_source TEXT PRIMARY KEY,
                    last_fetch TIMESTAMP,
                    incident_count INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            
            logger.info("✓ Database schema initialized")
            
        except Exception as e:
            logger.error(f"✗ Error initializing schema: {e}")
            raise
    
    async def add_incident(self, incident: Dict[str, Any]) -> int:
        """
        Store a phishing incident in the database.
        
        Args:
            incident: Dictionary with incident data
                {
                    "url": "...",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "threat_level": "high",
                    "company": "PayPal",
                    "country": "United States",
                    "isp": "ISP Name",
                    "detected_at": "2026-02-21T10:30:00Z"
                }
        
        Returns:
            int: ID of inserted incident
        
        Example:
            incident_id = await db.add_incident({
                "url": "http://phishing.com",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "threat_level": "high"
            })
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO phishing_incidents 
                (url, latitude, longitude, threat_level, company, country, isp, detected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                incident.get("url"),
                incident.get("latitude"),
                incident.get("longitude"),
                incident.get("threat_level", "unknown"),
                incident.get("company"),
                incident.get("country"),
                incident.get("isp"),
                incident.get("detected_at")
            ))
            
            conn.commit()
            incident_id = cursor.lastrowid
            conn.close()
            
            logger.info(f"✓ Stored incident ID: {incident_id}")
            return incident_id
            
        except Exception as e:
            logger.error(f"✗ Error adding incident: {e}")
            raise
    
    async def get_incidents(
        self,
        limit: int = 100,
        offset: int = 0,
        threat_level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query incidents from database.
        
        Args:
            limit: Maximum results
            offset: Number of results to skip (for pagination)
            threat_level: Optional filter by threat level
        
        Returns:
            List of incident dictionaries
        
        Example:
            incidents = await db.get_incidents(limit=50, threat_level="high")
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Return rows as dicts
            cursor = conn.cursor()
            
            query = "SELECT * FROM phishing_incidents WHERE 1=1"
            params = []
            
            if threat_level:
                query += " AND threat_level = ?"
                params.append(threat_level)
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            incidents = [dict(row) for row in rows]
            logger.info(f"✓ Retrieved {len(incidents)} incidents")
            return incidents
            
        except Exception as e:
            logger.error(f"✗ Error retrieving incidents: {e}")
            raise
    
    async def get_incident_count(self) -> int:
        """
        Get total number of incidents in database.
        
        Returns:
            int: Total incident count
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM phishing_incidents")
            count = cursor.fetchone()[0]
            conn.close()
            
            logger.info(f"✓ Total incidents in DB: {count}")
            return count
            
        except Exception as e:
            logger.error(f"✗ Error counting incidents: {e}")
            raise
    
    async def update_cache_metadata(
        self,
        api_source: str,
        incident_count: int
    ) -> None:
        """
        Update cache metadata to track API call patterns.
        
        Args:
            api_source: Which API (e.g., "phishstats")
            incident_count: How many incidents were fetched
        
        Example:
            await db.update_cache_metadata("phishstats", 342)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Upsert (update or insert)
            cursor.execute("""
                INSERT OR REPLACE INTO cache_metadata 
                (api_source, last_fetch, incident_count, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                api_source,
                datetime.now(),
                incident_count,
                datetime.now()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✓ Updated cache metadata for {api_source}: {incident_count} incidents")
            
        except Exception as e:
            logger.error(f"✗ Error updating cache metadata: {e}")
            raise
    
    async def clear_old_incidents(self, days: int = 30) -> int:
        """
        Delete incidents older than specified days.
        
        Useful for keeping database size manageable.
        
        Args:
            days: Delete incidents older than this many days
        
        Returns:
            int: Number of incidents deleted
        
        Example:
            deleted = await db.clear_old_incidents(days=30)
            print(f"Deleted {deleted} old incidents")
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM phishing_incidents 
                WHERE created_at < datetime('now', '-' || ? || ' days')
            """, (days,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"✓ Deleted {deleted_count} incidents older than {days} days")
            return deleted_count
            
        except Exception as e:
            logger.error(f"✗ Error clearing old incidents: {e}")
            raise
