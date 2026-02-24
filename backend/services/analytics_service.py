"""
═══════════════════════════════════════════════════════════════════════════════
FILE: services/analytics_service.py
PURPOSE: Generate analytics and insights from phishing data
═══════════════════════════════════════════════════════════════════════════════

WHAT THIS FILE DOES:
- Analyzes phishing incident trends over time
- Identifies high-risk regions and companies
- Computes threat score distributions
- Generates data for charts, graphs, and dashboards
- Provides insights to help data brokers and reporters

WHAT IT CONNECTS TO:
- services/phishing_service.py: Gets raw incidents for analysis
- database.py: Can retrieve historical data for trend analysis
- routes/analytics.py: Calls these methods to serve analytics endpoints
- models.py: Returns ThreatStatistics and other data models

ARCHITECTURE:
    Frontend: "Show me threat trends"
         ↓
    routes/analytics.py receives request
         ↓
    analytics_service.py (THIS FILE):
         1. Calls phishing_service to get incidents
         2. Analyzes patterns and trends
         3. Computes statistics and rankings
         ↓
    Returns analytics data
         ↓
    Frontend displays charts and insights

HOW TO USE:
    from services.analytics_service import AnalyticsService
    
    analytics = AnalyticsService()
    
    # Get threat statistics
    stats = await analytics.get_threat_levels_distribution()
    # Returns: {"critical": 50, "high": 200, "medium": 400, "low": 350}
    
    # Get top threat regions
    regions = await analytics.get_top_threat_regions(limit=5)
    # Returns: [("United States", 450), ("China", 120), ...]
    
    # Get most targeted companies
    companies = await analytics.get_most_targeted_companies(limit=10)
    # Returns: [("PayPal", 145), ("Apple", 98), ...]

═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from typing import Dict, List, Tuple, Any
from collections import Counter
from datetime import datetime, timedelta

from services.phishing_service import PhishingService

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service for generating analytics and insights from phishing data.
    
    This class provides methods for:
    - Aggregating threat data
    - Finding trends and patterns
    - Ranking regions and companies
    - Computing risk metrics
    """
    
    def __init__(self):
        """Initialize with phishing service."""
        self.phishing_service = PhishingService()
        logger.info("AnalyticsService initialized")
    
    async def get_threat_levels_distribution(self) -> Dict[str, int]:
        """
        Get count of incidents by threat level.
        
        Returns:
            Dictionary with threat level counts
            e.g., {"critical": 50, "high": 200, "medium": 400, "low": 350}
        
        Example:
            distribution = await analytics.get_threat_levels_distribution()
            print(distribution)
            # Output: {"critical": 50, "high": 200, "medium": 400, "low": 350}
        """
        logger.info("Computing threat level distribution...")
        
        try:
            incidents = await self.phishing_service.get_all_incidents()
            
            distribution = {
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0,
                'unknown': 0
            }
            
            for incident in incidents:
                level = incident.threat_level.lower()
                if level in distribution:
                    distribution[level] += 1
            
            logger.info(f"✓ Threat distribution: {distribution}")
            return distribution
            
        except Exception as e:
            logger.error(f"✗ Error computing threat distribution: {e}")
            raise
    
    async def get_top_threat_regions(self, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Get regions with the most phishing incidents.
        
        Args:
            limit: How many top regions to return
        
        Returns:
            List of (country, count) tuples, sorted by count descending
            e.g., [("United States", 450), ("China", 120), ("Russia", 98), ...]
        
        Example:
            regions = await analytics.get_top_threat_regions(limit=5)
            for country, count in regions:
                print(f"{country}: {count} incidents")
        """
        logger.info(f"Computing top {limit} threat regions...")
        
        try:
            incidents = await self.phishing_service.get_all_incidents()
            
            # Count incidents by country
            country_counts = Counter()
            for incident in incidents:
                if incident.country:
                    country_counts[incident.country] += 1
            
            # Get top N
            top_regions = country_counts.most_common(limit)
            
            logger.info(f"✓ Top regions: {top_regions}")
            return top_regions
            
        except Exception as e:
            logger.error(f"✗ Error computing top regions: {e}")
            raise
    
    async def get_most_targeted_companies(self, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Get companies that are most frequently targeted by phishers.
        
        Args:
            limit: How many top companies to return
        
        Returns:
            List of (company, count) tuples, sorted by count descending
            e.g., [("PayPal", 145), ("Apple", 98), ("Microsoft", 87), ...]
        
        Example:
            companies = await analytics.get_most_targeted_companies(limit=10)
            for company, count in companies:
                print(f"{company}: {count} phishing attempts")
        """
        logger.info(f"Computing top {limit} targeted companies...")
        
        try:
            incidents = await self.phishing_service.get_all_incidents()
            
            # Count incidents by company
            company_counts = Counter()
            for incident in incidents:
                if incident.company:
                    company_counts[incident.company] += 1
            
            # Get top N
            top_companies = company_counts.most_common(limit)
            
            logger.info(f"✓ Top companies: {top_companies}")
            return top_companies
            
        except Exception as e:
            logger.error(f"✗ Error computing top companies: {e}")
            raise
    
    async def get_threat_hotspots(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get geographic hotspots of phishing activity.
        
        Groups incidents by country and threat level to identify
        the most dangerous regions.
        
        Args:
            limit: Maximum number of hotspots to return
        
        Returns:
            List of dicts with region data:
            [
                {
                    "country": "United States",
                    "total_incidents": 450,
                    "critical": 50,
                    "high": 200,
                    "medium": 150,
                    "low": 50
                },
                ...
            ]
        
        Example:
            hotspots = await analytics.get_threat_hotspots(limit=5)
            for hotspot in hotspots:
                print(f"{hotspot['country']}: {hotspot['total_incidents']} incidents")
        """
        logger.info(f"Computing {limit} threat hotspots...")
        
        try:
            incidents = await self.phishing_service.get_all_incidents()
            
            # Group by country and threat level
            hotspots_dict = {}
            
            for incident in incidents:
                country = incident.country or "Unknown"
                threat_level = incident.threat_level.lower()
                
                if country not in hotspots_dict:
                    hotspots_dict[country] = {
                        "country": country,
                        "total_incidents": 0,
                        "critical": 0,
                        "high": 0,
                        "medium": 0,
                        "low": 0
                    }
                
                hotspots_dict[country]["total_incidents"] += 1
                if threat_level in hotspots_dict[country]:
                    hotspots_dict[country][threat_level] += 1
            
            # Sort by total incidents and limit
            hotspots = sorted(
                hotspots_dict.values(),
                key=lambda x: x["total_incidents"],
                reverse=True
            )[:limit]
            
            logger.info(f"✓ Identified {len(hotspots)} threat hotspots")
            return hotspots
            
        except Exception as e:
            logger.error(f"✗ Error computing hotspots: {e}")
            raise
    
    async def get_isp_threat_rankings(self, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Get Internet Service Providers (ISPs) with the most phishing activity.
        
        Useful for identifying which ISPs are sources of most attacks.
        
        Args:
            limit: How many top ISPs to return
        
        Returns:
            List of (ISP, count) tuples
            e.g., [("ISP1", 200), ("ISP2", 150), ...]
        
        Example:
            isps = await analytics.get_isp_threat_rankings(limit=10)
            for isp, count in isps:
                print(f"{isp}: {count} phishing attempts")
        """
        logger.info(f"Computing top {limit} ISP threat rankings...")
        
        try:
            incidents = await self.phishing_service.get_all_incidents()
            
            # Count incidents by ISP
            isp_counts = Counter()
            for incident in incidents:
                if incident.isp:
                    isp_counts[incident.isp] += 1
            
            # Get top N
            top_isps = isp_counts.most_common(limit)
            
            logger.info(f"✓ Top ISPs: {top_isps}")
            return top_isps
            
        except Exception as e:
            logger.error(f"✗ Error computing ISP rankings: {e}")
            raise
    
    async def get_threat_overview(self) -> Dict[str, Any]:
        """
        Get a comprehensive overview of all threat data.
        
        Returns:
            Dictionary with all key metrics:
            {
                "total_incidents": 1000,
                "threat_distribution": {"critical": 50, ...},
                "top_regions": [("US", 450), ...],
                "top_companies": [("PayPal", 145), ...],
                "top_isps": [("ISP1", 200), ...],
                "last_updated": "2026-02-21T10:30:00Z"
            }
        
        Example:
            overview = await analytics.get_threat_overview()
            print(f"Total threats: {overview['total_incidents']}")
        """
        logger.info("Generating comprehensive threat overview...")
        
        try:
            incidents = await self.phishing_service.get_all_incidents()
            
            overview = {
                "total_incidents": len(incidents),
                "threat_distribution": await self.get_threat_levels_distribution(),
                "top_regions": await self.get_top_threat_regions(limit=5),
                "top_companies": await self.get_most_targeted_companies(limit=5),
                "top_isps": await self.get_isp_threat_rankings(limit=5),
                "hotspots": await self.get_threat_hotspots(limit=10),
                "last_updated": datetime.now().isoformat()
            }
            
            logger.info(f"✓ Threat overview generated")
            return overview
            
        except Exception as e:
            logger.error(f"✗ Error generating overview: {e}")
            raise
