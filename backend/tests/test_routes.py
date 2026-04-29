import pytest
from unittest.mock import AsyncMock, patch
from starlette.testclient import TestClient
from datetime import datetime

from main import app
import routes.phishing as phishing_routes
import routes.analytics as analytics_routes
from models import MapPoint, HeatmapData, ThreatStatistics


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class TestAppEndpoints:
    def test_health_returns_healthy(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "healthy"
        assert "version" in body
        assert "timestamp" in body

    def test_root_returns_welcome(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "message" in r.json()

    def test_info_has_endpoints(self, client):
        r = client.get("/info")
        assert r.status_code == 200
        body = r.json()
        assert "endpoints" in body
        assert "phishing" in body["endpoints"]
        assert "analytics" in body["endpoints"]


class TestPhishingRoutes:
    def test_map_points_success(self, client, sample_map_point):
        with patch.object(
            phishing_routes.phishing_service,
            "get_map_points",
            AsyncMock(return_value=[sample_map_point]),
        ):
            r = client.get("/api/phishing/map-points")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["threat_level"] == "high"
        assert data[0]["lat"] == 40.7128

    def test_map_points_empty_result(self, client):
        with patch.object(
            phishing_routes.phishing_service,
            "get_map_points",
            AsyncMock(return_value=[]),
        ):
            r = client.get("/api/phishing/map-points")
        assert r.status_code == 200
        assert r.json() == []

    def test_map_points_invalid_limit_returns_422(self, client):
        r = client.get("/api/phishing/map-points?limit=0")
        assert r.status_code == 422

    def test_map_points_limit_too_high_returns_422(self, client):
        r = client.get("/api/phishing/map-points?limit=9999")
        assert r.status_code == 422

    def test_map_points_service_error_returns_500(self, client):
        with patch.object(
            phishing_routes.phishing_service,
            "get_map_points",
            AsyncMock(side_effect=Exception("API failure")),
        ):
            r = client.get("/api/phishing/map-points")
        assert r.status_code == 500

    def test_heatmap_success(self, client):
        heatmap = HeatmapData(
            coordinates=[[40.7, -74.0], [51.5, -0.1]],
            incident_count=2,
            last_updated=datetime.now(),
        )
        with patch.object(
            phishing_routes.phishing_service,
            "get_heatmap_data",
            AsyncMock(return_value=heatmap),
        ):
            r = client.get("/api/phishing/heatmap")
        assert r.status_code == 200
        body = r.json()
        assert body["incident_count"] == 2
        assert len(body["coordinates"]) == 2

    def test_heatmap_invalid_limit_returns_422(self, client):
        r = client.get("/api/phishing/heatmap?limit=0")
        assert r.status_code == 422

    def test_get_all_incidents_success(self, client, sample_incidents):
        with patch.object(
            phishing_routes.phishing_service,
            "get_filtered_incidents",
            AsyncMock(return_value=sample_incidents),
        ):
            r = client.get("/api/phishing/")
        assert r.status_code == 200
        assert len(r.json()) == len(sample_incidents)

    def test_stats_success(self, client):
        stats = ThreatStatistics(
            total_incidents=100,
            critical_count=10,
            high_count=30,
            low_count=60,
            top_targeted_companies=["PayPal"],
            most_active_countries=["US"],
            last_updated=datetime.now(),
        )
        with patch.object(
            phishing_routes.phishing_service,
            "get_threat_statistics",
            AsyncMock(return_value=stats),
        ):
            r = client.get("/api/phishing/stats")
        assert r.status_code == 200
        body = r.json()
        assert body["total_incidents"] == 100
        assert body["critical_count"] == 10

    def test_filtered_success(self, client, sample_incidents):
        critical = [i for i in sample_incidents if i.threat_level == "critical"]
        with patch.object(
            phishing_routes.phishing_service,
            "get_filtered_incidents",
            AsyncMock(return_value=critical),
        ):
            r = client.get("/api/phishing/filtered?threat_level=critical")
        assert r.status_code == 200
        assert len(r.json()) == 2


class TestAnalyticsRoutes:
    def test_analytics_health(self, client):
        r = client.get("/api/analytics/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_overview_success(self, client):
        mock_overview = {
            "total_incidents": 5,
            "threat_distribution": {"critical": 2, "high": 1, "low": 1, "moderate": 1},
            "top_regions": [["US", 1]],
            "top_companies": [["PayPal", 3]],
            "top_isps": [["ISP-A", 2]],
            "hotspots": [],
            "last_updated": datetime.now().isoformat(),
        }
        with patch.object(
            analytics_routes.analytics_service,
            "get_threat_overview",
            AsyncMock(return_value=mock_overview),
        ):
            r = client.get("/api/analytics/overview")
        assert r.status_code == 200
        body = r.json()
        assert body["total_incidents"] == 5
        assert "threat_distribution" in body

    def test_threat_distribution_success(self, client):
        dist = {"critical": 2, "high": 1, "low": 1, "moderate": 1, "elevated": 0, "none": 0, "unknown": 0}
        with patch.object(
            analytics_routes.analytics_service,
            "get_threat_levels_distribution",
            AsyncMock(return_value=dist),
        ):
            r = client.get("/api/analytics/threat-distribution")
        assert r.status_code == 200
        assert r.json()["critical"] == 2

    def test_top_regions_success(self, client):
        with patch.object(
            analytics_routes.analytics_service,
            "get_top_threat_regions",
            AsyncMock(return_value=[("US", 5), ("UK", 2)]),
        ):
            r = client.get("/api/analytics/top-regions")
        assert r.status_code == 200
        data = r.json()
        assert data[0] == ["US", 5]

    def test_top_regions_invalid_limit_returns_422(self, client):
        r = client.get("/api/analytics/top-regions?limit=0")
        assert r.status_code == 422

    def test_top_companies_success(self, client):
        with patch.object(
            analytics_routes.analytics_service,
            "get_most_targeted_companies",
            AsyncMock(return_value=[("PayPal", 3)]),
        ):
            r = client.get("/api/analytics/top-companies")
        assert r.status_code == 200
        assert r.json()[0] == ["PayPal", 3]

    def test_isp_rankings_success(self, client):
        with patch.object(
            analytics_routes.analytics_service,
            "get_isp_threat_rankings",
            AsyncMock(return_value=[("ISP-A", 2)]),
        ):
            r = client.get("/api/analytics/isp-rankings")
        assert r.status_code == 200
        assert r.json()[0] == ["ISP-A", 2]

    def test_threat_hotspots_success(self, client):
        hotspots = [{"country": "US", "total_incidents": 3, "critical": 1, "high": 2, "medium": 0, "low": 0}]
        with patch.object(
            analytics_routes.analytics_service,
            "get_threat_hotspots",
            AsyncMock(return_value=hotspots),
        ):
            r = client.get("/api/analytics/threat-hotspots")
        assert r.status_code == 200
        assert r.json()[0]["country"] == "US"
