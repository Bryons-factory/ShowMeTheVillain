"""
═══════════════════════════════════════════════════════════════════════════════
FILE: models.py
PURPOSE: Define data models and validation rules
═══════════════════════════════════════════════════════════════════════════════

WHAT THIS FILE DOES:
- Defines Pydantic models for data validation
- Ensures incoming API data matches expected structure
- Provides type hints for the entire application
- Validates coordinates, threat levels, and other fields

WHAT IT CONNECTS TO:
- api_client.py: Validates raw PhishStats API responses
- services/phishing_service.py: Uses these models to validate processed data
- database.py: Maps models to database tables
- routes/: Defines request/response schemas

ARCHITECTURE:
    Raw API Response
         ↓
    api_client.py
         ↓
    models.PhishingIncident (THIS FILE - validates data)
         ↓
    services/phishing_service.py
         ↓
    routes/phishing.py
         ↓
    Frontend JSON response

HOW TO USE:
    from models import PhishingIncident
    
    # Validate and create a model
    incident = PhishingIncident(
        url="http://phishing-site.com",
        latitude=40.7128,
        longitude=-74.0060,
        threat_level="high"
    )
    
    # Pydantic automatically validates the data
    # If invalid, raises ValidationError

═══════════════════════════════════════════════════════════════════════════════
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class PhishingIncident(BaseModel):
    """
    Represents a single phishing incident from the PhishStats API.
    
    Attributes:
        id: Unique identifier for this incident
        url: The malicious URL detected
        latitude: Geographic latitude (between -90 and 90)
        longitude: Geographic longitude (between -180 and 180)
        threat_level: Severity (low, medium, high, critical)
        company: Company/brand being targeted (e.g., "PayPal", "Apple")
        detected_at: When this incident was detected
        country: Country of origin (2-letter code or full name)
        isp: Internet Service Provider
    """
    
    id: Optional[int] = None
    url: str = Field(..., min_length=1)
    latitude: float = Field(..., ge=-90, le=90)  # Validate range
    longitude: float = Field(..., ge=-180, le=180)  # Validate range
    threat_level: str = Field(default="unknown")
    company: Optional[str] = None
    detected_at: Optional[datetime] = None
    country: Optional[str] = None
    isp: Optional[str] = None
    
    @validator('threat_level')
    def validate_threat_level(cls, v):
        """Ensure threat level is one of the allowed values."""
        allowed = ['low', 'medium', 'high', 'critical', 'unknown']
        if v.lower() not in allowed:
            raise ValueError(f"threat_level must be one of {allowed}")
        return v.lower()
    
    class Config:
        """Pydantic config for this model."""
        json_schema_extra = {
            "example": {
                "id": 123,
                "url": "http://malicious-site.com",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "threat_level": "high",
                "company": "PayPal",
                "detected_at": "2026-02-21T10:30:00Z",
                "country": "United States",
                "isp": "ISP Name"
            }
        }


class HeatmapCoordinate(BaseModel):
    """
    Represents a single coordinate point for the heatmap.
    
    The frontend expects this simple format: [latitude, longitude]
    """
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    
    class Config:
        json_schema_extra = {
            "example": {
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        }


class HeatmapData(BaseModel):
    """
    Response format for heatmap data endpoint.
    
    The frontend requests: GET /api/phishing/heatmap
    And receives this response containing all coordinates
    """
    coordinates: List[List[float]]  # [[lat, lon], [lat, lon], ...]
    incident_count: int = Field(..., ge=0)
    last_updated: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "coordinates": [
                    [40.7128, -74.0060],
                    [51.5074, -0.1278],
                    [48.8566, 2.3522]
                ],
                "incident_count": 3,
                "last_updated": "2026-02-21T10:30:00Z"
            }
        }


class ThreatStatistics(BaseModel):
    """
    Response format for threat analytics endpoint.
    
    Aggregates statistics about phishing threats
    """
    total_incidents: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    top_targeted_companies: List[str]
    most_active_countries: List[str]
    last_updated: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_incidents": 1000,
                "critical_count": 50,
                "high_count": 200,
                "medium_count": 400,
                "low_count": 350,
                "top_targeted_companies": ["PayPal", "Apple", "Microsoft"],
                "most_active_countries": ["United States", "China", "Russia"],
                "last_updated": "2026-02-21T10:30:00Z"
            }
        }


class FilterRequest(BaseModel):
    """
    Request body for filtering incidents.
    
    The frontend sends this with filters like:
    POST /api/phishing/filter
    {
        "threat_level": "high",
        "company": "PayPal",
        "country": "United States"
    }
    """
    threat_level: Optional[str] = None
    company: Optional[str] = None
    country: Optional[str] = None
    isp: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
