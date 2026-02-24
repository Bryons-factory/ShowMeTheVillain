"""
═══════════════════════════════════════════════════════════════════════════════
FILE: routes/analytics.py
PURPOSE: Define HTTP endpoints for analytics and insights
═══════════════════════════════════════════════════════════════════════════════

WHAT THIS FILE DOES:
- Defines API endpoints for analytics dashboards
- Provides insights like top threat regions, most targeted companies
- Returns aggregated and statistical data
- Enables data brokers and reporters to visualize threat patterns

WHAT IT CONNECTS TO:
- services/analytics_service.py: Calls analytics methods
- models.py: Returns structured response models
- main.py: Registers these routes with FastAPI

ARCHITECTURE:
    Frontend Request: GET /api/analytics/overview
         ↓
    routes/analytics.py (THIS FILE) receives request
         ↓
    Calls services/analytics_service.py
         ↓
    Returns JSON response with aggregated data
         ↓
    Frontend displays charts, graphs, dashboards

API ENDPOINTS PROVIDED:
    GET /api/analytics/overview
        - Get comprehensive threat overview
    
    GET /api/analytics/threat-distribution
        - Count of incidents by threat level
    
    GET /api/analytics/top-regions
        - Regions with most phishing activity
    
    GET /api/analytics/top-companies
        - Most frequently targeted companies
    
    GET /api/analytics/threat-hotspots
        - Geographic hotspots with threat levels
    
    GET /api/analytics/isp-rankings
        - ISPs with most phishing activity

HOW TO USE:
    These endpoints are automatically registered with FastAPI in main.py
    
    Frontend can call:
        - fetch('/api/analytics/overview')
        - fetch('/api/analytics/top-regions?limit=10')
        - fetch('/api/analytics/threat-distribution')

═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from typing import Optional
from fastapi import APIRouter, Query, HTTPException

from services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

# Create FastAPI router for analytics endpoints
router = APIRouter()

# Initialize service
analytics_service = AnalyticsService()


@router.get("/analytics/overview")
async def get_threat_overview():
    """
    Get comprehensive overview of all threat data.
    
    Returns aggregated statistics, top threats, hotspots, and trends.
    
    Returns:
        Dictionary with all key analytics metrics
    
    Example:
        GET /api/analytics/overview
        
        Response:
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
                ...
            ],
            "top_companies": [
                ["PayPal", 145],
                ["Apple", 98],
                ...
            ],
            "top_isps": [
                ["ISP1", 200],
                ["ISP2", 150],
                ...
            ],
            "hotspots": [...],
            "last_updated": "2026-02-21T10:30:00Z"
        }
    """
    try:
        logger.info("GET /api/analytics/overview")
        
        overview = await analytics_service.get_threat_overview()
        
        return overview
        
    except Exception as e:
        logger.error(f"✗ Error in get_threat_overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/threat-distribution")
async def get_threat_distribution():
    """
    Get count of incidents by threat level.
    
    Shows how threats are distributed across severity levels.
    Useful for understanding overall threat landscape.
    
    Returns:
        Dictionary with counts for each threat level
    
    Example:
        GET /api/analytics/threat-distribution
        
        Response:
        {
            "critical": 50,
            "high": 200,
            "medium": 400,
            "low": 350,
            "unknown": 0
        }
    """
    try:
        logger.info("GET /api/analytics/threat-distribution")
        
        distribution = await analytics_service.get_threat_levels_distribution()
        
        return distribution
        
    except Exception as e:
        logger.error(f"✗ Error in get_threat_distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/top-regions")
async def get_top_regions(
    limit: int = Query(10, ge=1, le=100)
):
    """
    Get regions with the most phishing incidents.
    
    Identifies geographic hotspots of phishing activity.
    Useful for targeting regional threat response efforts.
    
    Args:
        limit: Number of top regions to return (default 10, max 100)
    
    Returns:
        List of [country, incident_count] pairs, sorted by count descending
    
    Example:
        GET /api/analytics/top-regions?limit=5
        
        Response:
        [
            ["United States", 450],
            ["China", 120],
            ["Russia", 98],
            ["India", 87],
            ["Brazil", 65]
        ]
    """
    try:
        logger.info(f"GET /api/analytics/top-regions | limit={limit}")
        
        regions = await analytics_service.get_top_threat_regions(limit=limit)
        
        # Convert tuples to lists for JSON serialization
        return [[country, count] for country, count in regions]
        
    except Exception as e:
        logger.error(f"✗ Error in get_top_regions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/top-companies")
async def get_top_companies(
    limit: int = Query(10, ge=1, le=100)
):
    """
    Get companies that are most frequently targeted by phishers.
    
    Shows which brands/companies phishers impersonate most often.
    Useful for alerting companies of increased phishing activity.
    
    Args:
        limit: Number of top companies to return (default 10, max 100)
    
    Returns:
        List of [company, attempt_count] pairs, sorted by count descending
    
    Example:
        GET /api/analytics/top-companies?limit=10
        
        Response:
        [
            ["PayPal", 145],
            ["Apple", 98],
            ["Microsoft", 87],
            ["Amazon", 76],
            ["Google", 65],
            ...
        ]
    """
    try:
        logger.info(f"GET /api/analytics/top-companies | limit={limit}")
        
        companies = await analytics_service.get_most_targeted_companies(limit=limit)
        
        # Convert tuples to lists for JSON serialization
        return [[company, count] for company, count in companies]
        
    except Exception as e:
        logger.error(f"✗ Error in get_top_companies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/threat-hotspots")
async def get_threat_hotspots(
    limit: int = Query(10, ge=1, le=100)
):
    """
    Get geographic hotspots of phishing activity with threat breakdowns.
    
    For each region, shows the distribution of threat levels.
    Identifies the most dangerous geographic areas.
    
    Args:
        limit: Number of hotspots to return (default 10, max 100)
    
    Returns:
        List of hotspot objects with regional threat data
    
    Example:
        GET /api/analytics/threat-hotspots?limit=5
        
        Response:
        [
            {
                "country": "United States",
                "total_incidents": 450,
                "critical": 50,
                "high": 200,
                "medium": 150,
                "low": 50
            },
            {
                "country": "China",
                "total_incidents": 120,
                "critical": 25,
                "high": 60,
                "medium": 30,
                "low": 5
            },
            ...
        ]
    """
    try:
        logger.info(f"GET /api/analytics/threat-hotspots | limit={limit}")
        
        hotspots = await analytics_service.get_threat_hotspots(limit=limit)
        
        return hotspots
        
    except Exception as e:
        logger.error(f"✗ Error in get_threat_hotspots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/isp-rankings")
async def get_isp_rankings(
    limit: int = Query(10, ge=1, le=100)
):
    """
    Get Internet Service Providers (ISPs) with most phishing activity.
    
    Identifies which ISPs are sources of the most phishing attacks.
    Useful for identifying compromised networks or bad actors.
    
    Args:
        limit: Number of top ISPs to return (default 10, max 100)
    
    Returns:
        List of [ISP, attack_count] pairs, sorted by count descending
    
    Example:
        GET /api/analytics/isp-rankings?limit=10
        
        Response:
        [
            ["ISP1 Name", 200],
            ["ISP2 Name", 150],
            ["ISP3 Name", 120],
            ...
        ]
    """
    try:
        logger.info(f"GET /api/analytics/isp-rankings | limit={limit}")
        
        isps = await analytics_service.get_isp_threat_rankings(limit=limit)
        
        # Convert tuples to lists for JSON serialization
        return [[isp, count] for isp, count in isps]
        
    except Exception as e:
        logger.error(f"✗ Error in get_isp_rankings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/health")
async def analytics_health():
    """
    Check if analytics service is operational.
    
    Simple health check endpoint for monitoring.
    
    Returns:
        Status message
    
    Example:
        GET /api/analytics/health
        
        Response:
        {
            "status": "healthy",
            "service": "analytics",
            "timestamp": "2026-02-21T10:30:00Z"
        }
    """
    try:
        logger.info("GET /api/analytics/health")
        
        from datetime import datetime
        
        return {
            "status": "healthy",
            "service": "analytics",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"✗ Error in analytics_health: {e}")
        raise HTTPException(status_code=500, detail=str(e))
