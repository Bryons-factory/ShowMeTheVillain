import pytest
from unittest.mock import AsyncMock
from models import PhishingIncident, MapPoint
from services.phishing_service import PhishingService, _incident_to_map_point, _THREAT_INTENSITY


@pytest.fixture
def service():
    svc = PhishingService()
    return svc


def _raw(incidents):
    return [inc.model_dump() for inc in incidents]


class TestGetAllIncidents:
    async def test_returns_validated_incidents(self, service, sample_incidents):
        service.api_client.fetch_incidents = AsyncMock(return_value=_raw(sample_incidents))
        result = await service.get_all_incidents()
        assert len(result) == len(sample_incidents)
        assert all(isinstance(i, PhishingIncident) for i in result)

    async def test_skips_invalid_incident_data(self, service):
        raw = [
            {"url": "http://valid.com", "latitude": 40.0, "longitude": -74.0, "threat_level": "high"},
            {"url": "", "latitude": 40.0, "longitude": -74.0},  # invalid: empty url
            {"latitude": 40.0, "longitude": -74.0},             # invalid: missing url
        ]
        service.api_client.fetch_incidents = AsyncMock(return_value=raw)
        result = await service.get_all_incidents()
        assert len(result) == 1
        assert result[0].url == "http://valid.com"

    async def test_returns_empty_list_when_no_incidents(self, service):
        service.api_client.fetch_incidents = AsyncMock(return_value=[])
        result = await service.get_all_incidents()
        assert result == []


class TestGetFilteredIncidents:
    async def test_no_filters_returns_all(self, service, sample_incidents):
        service.api_client.fetch_incidents = AsyncMock(return_value=_raw(sample_incidents))
        result = await service.get_filtered_incidents()
        assert len(result) == len(sample_incidents)

    async def test_filter_by_threat_level(self, service, sample_incidents):
        service.api_client.fetch_incidents = AsyncMock(return_value=_raw(sample_incidents))
        result = await service.get_filtered_incidents(threat_level="critical")
        assert all(i.threat_level == "critical" for i in result)
        assert len(result) == 2  # ids 1 and 5

    async def test_filter_by_company(self, service, sample_incidents):
        service.api_client.fetch_incidents = AsyncMock(return_value=_raw(sample_incidents))
        result = await service.get_filtered_incidents(company="PayPal")
        assert all(i.company == "PayPal" for i in result)
        assert len(result) == 3  # ids 1, 3, 5

    async def test_filter_by_company_case_insensitive(self, service, sample_incidents):
        service.api_client.fetch_incidents = AsyncMock(return_value=_raw(sample_incidents))
        result = await service.get_filtered_incidents(company="paypal")
        assert len(result) == 3

    async def test_filter_by_country(self, service, sample_incidents):
        service.api_client.fetch_incidents = AsyncMock(return_value=_raw(sample_incidents))
        result = await service.get_filtered_incidents(country="France")
        assert len(result) == 1
        assert result[0].country == "France"

    async def test_filter_by_isp(self, service, sample_incidents):
        service.api_client.fetch_incidents = AsyncMock(return_value=_raw(sample_incidents))
        result = await service.get_filtered_incidents(isp="ISP-A")
        assert len(result) == 2  # ids 1 and 3

    async def test_combined_filters(self, service, sample_incidents):
        service.api_client.fetch_incidents = AsyncMock(return_value=_raw(sample_incidents))
        result = await service.get_filtered_incidents(threat_level="critical", company="PayPal")
        assert len(result) == 2
        for i in result:
            assert i.threat_level == "critical"
            assert i.company == "PayPal"

    async def test_combined_no_matches(self, service, sample_incidents):
        service.api_client.fetch_incidents = AsyncMock(return_value=_raw(sample_incidents))
        result = await service.get_filtered_incidents(company="Apple", country="France")
        assert result == []

    async def test_limit_respected(self, service, sample_incidents):
        service.api_client.fetch_incidents = AsyncMock(return_value=_raw(sample_incidents))
        result = await service.get_filtered_incidents(limit=2)
        assert len(result) == 2

    async def test_offset_skips_results(self, service, sample_incidents):
        service.api_client.fetch_incidents = AsyncMock(return_value=_raw(sample_incidents))
        all_results = await service.get_filtered_incidents()
        offset_results = await service.get_filtered_incidents(offset=2)
        assert offset_results == all_results[2:]

    async def test_nonexistent_filter_returns_empty(self, service, sample_incidents):
        service.api_client.fetch_incidents = AsyncMock(return_value=_raw(sample_incidents))
        result = await service.get_filtered_incidents(company="Nonexistent Corp")
        assert result == []


class TestGetMapPoints:
    async def test_returns_map_points(self, service, sample_incidents):
        service.api_client.fetch_incidents = AsyncMock(return_value=_raw(sample_incidents))
        result = await service.get_map_points()
        assert len(result) == len(sample_incidents)
        assert all(isinstance(p, MapPoint) for p in result)

    async def test_filters_are_forwarded(self, service, sample_incidents):
        service.api_client.fetch_incidents = AsyncMock(return_value=_raw(sample_incidents))
        result = await service.get_map_points(threat_level="critical")
        assert all(p.threat_level == "critical" for p in result)
        assert len(result) == 2

    async def test_limit_respected(self, service, sample_incidents):
        service.api_client.fetch_incidents = AsyncMock(return_value=_raw(sample_incidents))
        result = await service.get_map_points(limit=3)
        assert len(result) == 3


class TestIncidentToMapPoint:
    def test_intensity_mapping_critical(self):
        inc = PhishingIncident(url="http://x.com", latitude=0.0, longitude=0.0, threat_level="critical")
        pt = _incident_to_map_point(inc)
        assert pt is not None
        assert pt.intensity == _THREAT_INTENSITY["critical"]

    def test_intensity_mapping_high(self):
        inc = PhishingIncident(url="http://x.com", latitude=0.0, longitude=0.0, threat_level="high")
        pt = _incident_to_map_point(inc)
        assert pt.intensity == _THREAT_INTENSITY["high"]

    def test_intensity_mapping_low(self):
        inc = PhishingIncident(url="http://x.com", latitude=0.0, longitude=0.0, threat_level="low")
        pt = _incident_to_map_point(inc)
        assert pt.intensity == _THREAT_INTENSITY["low"]

    def test_uses_company_as_label_when_present(self):
        inc = PhishingIncident(
            url="http://x.com", latitude=0.0, longitude=0.0, threat_level="high", company="PayPal"
        )
        pt = _incident_to_map_point(inc)
        assert pt.name == "PayPal"

    def test_uses_url_as_label_when_no_company(self):
        inc = PhishingIncident(url="http://x.com", latitude=0.0, longitude=0.0, threat_level="high")
        pt = _incident_to_map_point(inc)
        assert "http://x.com" in pt.name

    def test_preserves_coordinates(self):
        inc = PhishingIncident(url="http://x.com", latitude=40.7128, longitude=-74.0060, threat_level="low")
        pt = _incident_to_map_point(inc)
        assert pt.lat == 40.7128
        assert pt.lon == -74.0060

    def test_preserves_filter_fields(self):
        inc = PhishingIncident(
            url="http://x.com", latitude=0.0, longitude=0.0, threat_level="high",
            company="Apple", country="US", isp="ISP-X"
        )
        pt = _incident_to_map_point(inc)
        assert pt.company == "Apple"
        assert pt.country == "US"
        assert pt.isp == "ISP-X"


class TestGetThreatStatistics:
    async def test_counts_by_threat_level(self, service, sample_incidents):
        service.api_client.fetch_incidents = AsyncMock(return_value=_raw(sample_incidents))
        stats = await service.get_threat_statistics()
        assert stats.critical_count == 2
        assert stats.high_count == 1
        assert stats.low_count == 1
        assert stats.moderate_count == 1
        assert stats.total_incidents == 5

    async def test_top_targeted_companies(self, service, sample_incidents):
        service.api_client.fetch_incidents = AsyncMock(return_value=_raw(sample_incidents))
        stats = await service.get_threat_statistics()
        assert stats.top_targeted_companies[0] == "PayPal"  # PayPal appears 3 times

    async def test_most_active_countries(self, service, sample_incidents):
        service.api_client.fetch_incidents = AsyncMock(return_value=_raw(sample_incidents))
        stats = await service.get_threat_statistics()
        assert len(stats.most_active_countries) > 0

    async def test_empty_incidents_produces_zero_counts(self, service):
        service.api_client.fetch_incidents = AsyncMock(return_value=[])
        stats = await service.get_threat_statistics()
        assert stats.total_incidents == 0
        assert stats.critical_count == 0
        assert stats.top_targeted_companies == []
