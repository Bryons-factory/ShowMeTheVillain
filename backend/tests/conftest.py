import pytest
from datetime import datetime
from models import PhishingIncident, MapPoint


@pytest.fixture
def sample_incident():
    return PhishingIncident(
        id=1,
        url="http://phishing-example.com",
        latitude=40.7128,
        longitude=-74.0060,
        threat_level="high",
        company="PayPal",
        country="United States",
        isp="Example ISP",
        detected_at=datetime(2026, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def sample_incidents():
    return [
        PhishingIncident(
            id=1, url="http://p1.com", latitude=40.7128, longitude=-74.0060,
            threat_level="critical", company="PayPal", country="United States", isp="ISP-A",
        ),
        PhishingIncident(
            id=2, url="http://p2.com", latitude=51.5074, longitude=-0.1278,
            threat_level="high", company="Apple", country="United Kingdom", isp="ISP-B",
        ),
        PhishingIncident(
            id=3, url="http://p3.com", latitude=48.8566, longitude=2.3522,
            threat_level="low", company="PayPal", country="France", isp="ISP-A",
        ),
        PhishingIncident(
            id=4, url="http://p4.com", latitude=35.6762, longitude=139.6503,
            threat_level="moderate", company="Microsoft", country="Japan", isp="ISP-C",
        ),
        PhishingIncident(
            id=5, url="http://p5.com", latitude=-33.8688, longitude=151.2093,
            threat_level="critical", company="PayPal", country="Australia", isp="ISP-B",
        ),
    ]


@pytest.fixture
def sample_map_point():
    return MapPoint(
        lat=40.7128,
        lon=-74.0060,
        intensity=8,
        name="PayPal",
        threat_level="high",
        company="PayPal",
        country="United States",
        isp="Example ISP",
    )
