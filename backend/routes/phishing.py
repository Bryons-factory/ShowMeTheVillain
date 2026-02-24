"""
═══════════════════════════════════════════════════════════════════════════════
FILE: routes/phishing.py
PURPOSE: Define HTTP endpoints for phishing data
═══════════════════════════════════════════════════════════════════════════════

WHAT THIS FILE DOES:
- Defines API endpoints that the frontend calls
- Routes HTTP requests to appropriate service methods
- Handles request parameters and validation
- Returns JSON responses to the frontend

WHAT IT CONNECTS TO:
- services/phishing_service.py: Calls these services for business logic
- models.py: Uses Pydantic models for request/response validation
- main.py: Registers these routes with FastAPI

ARCHITECTURE:
    Frontend Request: GET /api/phishing/heatmap?threat_level=high
         ↓
    routes/phishing.py (THIS FILE) receives request
         ↓
    Calls services/phishing_service.py
         ↓
    Returns JSON response to frontend
         ↓
    Frontend renders heatmap

API ENDPOINTS PROVIDED:
    GET /api/phishing/
        - Get all phishing incidents
        - Query params: limit, offset, threat_level
    
    GET /api/phishing/heatmap
        - Get coordinates for heatmap visualization
        - Query params: threat_level, limit
    
    GET /api/phishing/filtered
        - Get incidents with multiple filters
        - Query params: threat_level, company, country, isp, limit, offset
    
    GET /api/phishing/{id}
        - Get a single incident by ID

HOW TO USE:
    These endpoints are automatically registered with FastAPI in main.py
    
    Frontend can call:
        - fetch('/api/phishing/heatmap')
        - fetch('/api/phishing/?limit=100&threat_level=high')
        - fetch('/api/phishing/filtered?company=PayPal')

═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from typing import Optional
from fastapi import APIRouter, Query, HTTPException

from services.phishing_service import PhishingService
from models import PhishingIncident, HeatmapData

logger = logging.getLogger(__name__)

# Create FastAPI router for phishing endpoints
router = APIRouter()

# Initialize service
phishing_service = PhishingService()


@router.get("/phishing/", response_model=list)
async def get_all_incidents(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    threat_level: Optional[str] = Query(None)
):
    """
    Get all phishing incidents (with optional filtering).
    
    This endpoint returns all incidents or a filtered subset.
    
    Args:
        limit: How many results to return (max 1000)
        offset: Number of results to skip (for pagination)
        threat_level: Optional filter (low, medium, high, critical)
    
    Returns:
        List of PhishingIncident objects
    
    Example:
        GET /api/phishing/?limit=50&threat_level=high
        
        Response:
        [
            {
                "id": 1,
                "url": "http://phishing.com",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "threat_level": "high",
                "company": "PayPal"
            },
            ...
        ]
    """
    try:
        logger.info(f"GET /api/phishing/ | limit={limit}, offset={offset}, threat_level={threat_level}")
        
        incidents = await phishing_service.get_filtered_incidents(
            threat_level=threat_level,
            limit=limit,
            offset=offset
        )
        
        return [incident.dict() for incident in incidents]
        
    except Exception as e:
        logger.error(f"✗ Error in get_all_incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/phishing/heatmap", response_model=HeatmapData)
async def get_heatmap_data(
    threat_level: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get heatmap coordinates for visualization.
    
    Returns coordinates in the format [[latitude, longitude], ...]
    that can be directly fed to Folium or other mapping libraries.
    
    Args:
        threat_level: Optional filter (low, medium, high, critical)
        limit: Maximum coordinates to return
    
    Returns:
        HeatmapData object with:
        - coordinates: List of [lat, lon] pairs
        - incident_count: How many incidents
        - last_updated: Timestamp
    
    Example:
        GET /api/phishing/heatmap?threat_level=critical
        
        Response:
        {
            "coordinates": [
                [40.7128, -74.0060],
                [51.5074, -0.1278],
                [48.8566, 2.3522]
            ],
            "incident_count": 3,
            "last_updated": "2026-02-21T10:30:00Z"
        }
    """
    try:
        logger.info(f"GET /api/phishing/heatmap | threat_level={threat_level}, limit={limit}")
        
        heatmap_data = await phishing_service.get_heatmap_data(
            threat_level=threat_level,
            limit=limit
        )
        
        return heatmap_data
        
    except Exception as e:
        logger.error(f"✗ Error in get_heatmap_data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/phishing/filtered", response_model=list)
async def get_filtered_incidents(
    threat_level: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    isp: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Get incidents with advanced filtering options.
    
    Args:
        threat_level: Filter by threat level (low, medium, high, critical)
        company: Filter by targeted company (e.g., "PayPal")
        country: Filter by country of origin (e.g., "United States")
        isp: Filter by Internet Service Provider
        limit: Maximum results
        offset: Number of results to skip
    
    Returns:
        List of PhishingIncident objects matching filters
    
    Example:
        GET /api/phishing/filtered?company=PayPal&threat_level=critical&limit=50
        
        Response:
        [
            {
                "id": 1,
                "url": "http://phishing.com",
                "company": "PayPal",
                "threat_level": "critical",
                ...
            }
        ]
    """
    try:
        logger.info(f"GET /api/phishing/filtered | threat={threat_level}, company={company}, country={country}")
        
        incidents = await phishing_service.get_filtered_incidents(
            threat_level=threat_level,
            company=company,
            country=country,
            isp=isp,
            limit=limit,
            offset=offset
        )
        
        return [incident.dict() for incident in incidents]
        
    except Exception as e:
        logger.error(f"✗ Error in get_filtered_incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/phishing/stats")
async def get_statistics():
    """
    Get threat statistics (counts by threat level, top companies, etc).
    
    Returns:
        ThreatStatistics object with aggregated data
    
    Example:
        GET /api/phishing/stats
        
        Response:
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
    """
    try:
        logger.info(f"GET /api/phishing/stats")
        
        stats = await phishing_service.get_threat_statistics()
        
        return stats.dict()
        
    except Exception as e:
        logger.error(f"✗ Error in get_statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/phishing/refresh")
async def refresh_data():
    """
    Force refresh of phishing data from the API.
    
    Bypasses cache and fetches fresh data from PhishStats.
    Useful for testing or when cache timeout might be too long.
    
    Returns:
        Message indicating refresh status
    
    Example:
        GET /api/phishing/refresh
        
        Response:
        {
            "status": "success",
            "message": "Data refreshed",
            "incident_count": 342
        }
    """
    try:
        logger.info(f"GET /api/phishing/refresh (forcing cache bypass)")
        
        incidents = await phishing_service.api_client.fetch_incidents(force_refresh=True)
        
        return {
            "status": "success",
            "message": "Data refreshed from PhishStats API",
            "incident_count": len(incidents)
        }
        
    except Exception as e:
        logger.error(f"✗ Error in refresh_data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
