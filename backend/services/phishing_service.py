"""
═══════════════════════════════════════════════════════════════════════════════
FILE: services/phishing_service.py
PURPOSE: Core business logic for handling phishing data
═══════════════════════════════════════════════════════════════════════════════

WHAT THIS FILE DOES:
- Fetches raw data from api_client.py
- Processes and validates incident data
- Filters incidents by threat level, company, country, etc.
- Transforms data into formats needed by frontend (heatmap coordinates, stats)
- Acts as the "middle layer" between raw API and routes

WHAT IT CONNECTS TO:
- api_client.py: Calls fetch_incidents() to get raw data
- models.py: Validates data using PhishingIncident model
- database.py: Stores/retrieves data from Cloudflare D1
- routes/phishing.py: Called by routes to fetch/filter data
- config.py: Uses validation limits

ARCHITECTURE:
    Frontend calls: GET /api/phishing/heatmap?threat_level=high
         ↓
    routes/phishing.py receives request
         ↓
    phishing_service.py (THIS FILE) does the work:
         1. Calls api_client to fetch/check cache
         2. Validates incident coordinates
         3. Filters by parameters
         4. Transforms to heatmap format [[lat, lon], ...]
         ↓
    Returns clean data to route
         ↓
    routes/phishing.py returns JSON to frontend

HOW TO USE:
    from services.phishing_service import PhishingService
    
    service = PhishingService()
    
    # Get all incidents
    incidents = await service.get_all_incidents()
    
    # Get heatmap coordinates
    coords = await service.get_heatmap_data(threat_level="high")
    # Returns: [[40.7128, -74.0060], [51.5074, -0.1278], ...]
    
    # Filter incidents
    filtered = await service.get_filtered_incidents(
        threat_level="critical",
        company="PayPal",
        limit=50
    )

═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from api_client import PhishStatsClient
from models import PhishingIncident, HeatmapData, ThreatStatistics
from config import config

logger = logging.getLogger(__name__)


class PhishingService:
    """
    Service layer for phishing incident management.
    
    This class:
    - Fetches data from PhishStats API via api_client
    - Validates incident data
    - Filters and processes incidents
    - Prepares data in formats needed by frontend
    """
    
    def __init__(self):
        """Initialize the service with API client."""
        self.api_client = PhishStatsClient()
        logger.info("PhishingService initialized")
    
    async def get_all_incidents(self) -> List[PhishingIncident]:
        """
        Get all phishing incidents from cache or API.
        
        Returns:
            List of validated PhishingIncident objects
        
        Example:
            incidents = await service.get_all_incidents()
            print(f"Found {len(incidents)} incidents")
        """
        logger.info("Fetching all incidents...")
        
        try:
            # Fetch raw data from API (with caching)
            raw_data = await self.api_client.fetch_incidents()
            
            # Validate each incident
            validated_incidents = []
            for item in raw_data:
                try:
                    incident = PhishingIncident(**item)
                    validated_incidents.append(incident)
                except Exception as e:
                    logger.warning(f"Skipping invalid incident: {e}")
            
            logger.info(f"✓ Processed {len(validated_incidents)} valid incidents")
            return validated_incidents
            
        except Exception as e:
            logger.error(f"✗ Error fetching incidents: {e}")
            raise
    
    async def get_heatmap_data(
        self,
        threat_level: Optional[str] = None,
        limit: int = 100
    ) -> HeatmapData:
        """
        Get heatmap coordinates for the frontend.
        
        Transforms incidents into simple [latitude, longitude] pairs
        that the frontend can directly feed to the Folium heatmap.
        
        Args:
            threat_level: Optional filter (low, medium, high, critical)
            limit: Maximum number of coordinates to return
        
        Returns:
            HeatmapData object containing coordinates and metadata
        
        Example:
            heatmap = await service.get_heatmap_data(threat_level="high")
            # heatmap.coordinates = [[40.7128, -74.0060], [51.5074, -0.1278], ...]
            # heatmap.incident_count = 342
        """
        logger.info(f"Getting heatmap data (threat_level={threat_level}, limit={limit})...")
        
        try:
            # Get all incidents
            incidents = await self.get_all_incidents()
            
            # Filter by threat level if specified
            if threat_level:
                incidents = [
                    inc for inc in incidents 
                    if inc.threat_level == threat_level.lower()
                ]
            
            # Limit results
            incidents = incidents[:limit]
            
            # Extract coordinates: [[lat, lon], [lat, lon], ...]
            coordinates = [
                [inc.latitude, inc.longitude]
                for inc in incidents
                if inc.latitude is not None and inc.longitude is not None
            ]
            
            heatmap = HeatmapData(
                coordinates=coordinates,
                incident_count=len(incidents),
                last_updated=datetime.now()
            )
            
            logger.info(f"✓ Generated heatmap with {len(coordinates)} coordinates")
            return heatmap
            
        except Exception as e:
            logger.error(f"✗ Error generating heatmap: {e}")
            raise
    
    async def get_filtered_incidents(
        self,
        threat_level: Optional[str] = None,
        company: Optional[str] = None,
        country: Optional[str] = None,
        isp: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[PhishingIncident]:
        """
        Get incidents with multiple filter options.
        
        Args:
            threat_level: Filter by threat level (low, medium, high, critical)
            company: Filter by targeted company
            country: Filter by country of origin
            isp: Filter by Internet Service Provider
            limit: Maximum results to return
            offset: Skip this many results (for pagination)
        
        Returns:
            Filtered list of PhishingIncident objects
        
        Example:
            incidents = await service.get_filtered_incidents(
                threat_level="critical",
                company="PayPal",
                limit=50
            )
        """
        logger.info(f"Filtering incidents: threat={threat_level}, company={company}, country={country}")
        
        try:
            # Get all incidents
            incidents = await self.get_all_incidents()
            
            # Apply filters
            if threat_level:
                incidents = [
                    inc for inc in incidents 
                    if inc.threat_level == threat_level.lower()
                ]
            
            if company:
                incidents = [
                    inc for inc in incidents 
                    if inc.company and inc.company.lower() == company.lower()
                ]
            
            if country:
                incidents = [
                    inc for inc in incidents 
                    if inc.country and inc.country.lower() == country.lower()
                ]
            
            if isp:
                incidents = [
                    inc for inc in incidents 
                    if inc.isp and inc.isp.lower() == isp.lower()
                ]
            
            # Apply pagination
            incidents = incidents[offset:offset + limit]
            
            logger.info(f"✓ Returned {len(incidents)} filtered incidents")
            return incidents
            
        except Exception as e:
            logger.error(f"✗ Error filtering incidents: {e}")
            raise
    
    async def get_threat_statistics(self) -> ThreatStatistics:
        """
        Generate threat statistics for analytics dashboard.
        
        Returns:
            ThreatStatistics object with aggregated threat data
        
        Example:
            stats = await service.get_threat_statistics()
            print(f"Critical threats: {stats.critical_count}")
            print(f"Top targets: {stats.top_targeted_companies}")
        """
        logger.info("Computing threat statistics...")
        
        try:
            incidents = await self.get_all_incidents()
            
            # Count by threat level
            threat_counts = {
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0
            }
            
            companies = {}
            countries = {}
            
            for incident in incidents:
                # Count threat levels
                level = incident.threat_level.lower()
                if level in threat_counts:
                    threat_counts[level] += 1
                
                # Count companies
                if incident.company:
                    companies[incident.company] = companies.get(incident.company, 0) + 1
                
                # Count countries
                if incident.country:
                    countries[incident.country] = countries.get(incident.country, 0) + 1
            
            # Get top 5 for each
            top_companies = sorted(companies.items(), key=lambda x: x[1], reverse=True)[:5]
            top_countries = sorted(countries.items(), key=lambda x: x[1], reverse=True)[:5]
            
            stats = ThreatStatistics(
                total_incidents=len(incidents),
                critical_count=threat_counts['critical'],
                high_count=threat_counts['high'],
                medium_count=threat_counts['medium'],
                low_count=threat_counts['low'],
                top_targeted_companies=[c[0] for c in top_companies],
                most_active_countries=[c[0] for c in top_countries],
                last_updated=datetime.now()
            )
            
            logger.info(f"✓ Generated threat statistics")
            return stats
            
        except Exception as e:
            logger.error(f"✗ Error generating statistics: {e}")
            raise
