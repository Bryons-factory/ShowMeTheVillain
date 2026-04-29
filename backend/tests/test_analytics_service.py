import pytest
from unittest.mock import AsyncMock
from services.analytics_service import AnalyticsService


@pytest.fixture
def analytics(sample_incidents):
    svc = AnalyticsService()
    svc.phishing_service.get_all_incidents = AsyncMock(return_value=sample_incidents)
    return svc


class TestGetThreatLevelsDistribution:
    async def test_counts_all_levels(self, analytics):
        dist = await analytics.get_threat_levels_distribution()
        assert dist["critical"] == 2
        assert dist["high"] == 1
        assert dist["low"] == 1
        assert dist["moderate"] == 1
        assert dist["elevated"] == 0
        assert dist["none"] == 0
        assert dist["unknown"] == 0

    async def test_returns_all_level_keys(self, analytics):
        dist = await analytics.get_threat_levels_distribution()
        expected_keys = {"critical", "high", "elevated", "moderate", "low", "none", "unknown"}
        assert set(dist.keys()) == expected_keys

    async def test_empty_incidents_all_zeros(self):
        svc = AnalyticsService()
        svc.phishing_service.get_all_incidents = AsyncMock(return_value=[])
        dist = await svc.get_threat_levels_distribution()
        assert all(v == 0 for v in dist.values())


class TestGetTopThreatRegions:
    async def test_returns_sorted_by_count(self, analytics):
        regions = await analytics.get_top_threat_regions()
        counts = [count for _, count in regions]
        assert counts == sorted(counts, reverse=True)

    async def test_respects_limit(self, analytics):
        regions = await analytics.get_top_threat_regions(limit=2)
        assert len(regions) <= 2

    async def test_returns_tuples_of_country_count(self, analytics):
        regions = await analytics.get_top_threat_regions()
        for entry in regions:
            assert len(entry) == 2
            assert isinstance(entry[0], str)
            assert isinstance(entry[1], int)

    async def test_empty_incidents_returns_empty(self):
        svc = AnalyticsService()
        svc.phishing_service.get_all_incidents = AsyncMock(return_value=[])
        regions = await svc.get_top_threat_regions()
        assert regions == []

    async def test_excludes_incidents_with_no_country(self, analytics, sample_incidents):
        from models import PhishingIncident
        no_country = PhishingIncident(
            url="http://x.com", latitude=0.0, longitude=0.0, threat_level="low"
        )
        svc = AnalyticsService()
        svc.phishing_service.get_all_incidents = AsyncMock(return_value=sample_incidents + [no_country])
        regions = await svc.get_top_threat_regions()
        countries = [c for c, _ in regions]
        assert None not in countries


class TestGetMostTargetedCompanies:
    async def test_paypal_is_top_company(self, analytics):
        companies = await analytics.get_most_targeted_companies()
        assert companies[0][0] == "PayPal"
        assert companies[0][1] == 3

    async def test_sorted_by_count(self, analytics):
        companies = await analytics.get_most_targeted_companies()
        counts = [c for _, c in companies]
        assert counts == sorted(counts, reverse=True)

    async def test_respects_limit(self, analytics):
        companies = await analytics.get_most_targeted_companies(limit=1)
        assert len(companies) == 1

    async def test_empty_incidents_returns_empty(self):
        svc = AnalyticsService()
        svc.phishing_service.get_all_incidents = AsyncMock(return_value=[])
        companies = await svc.get_most_targeted_companies()
        assert companies == []


class TestGetThreatHotspots:
    async def test_returns_list_of_dicts(self, analytics):
        hotspots = await analytics.get_threat_hotspots()
        assert isinstance(hotspots, list)
        for h in hotspots:
            assert "country" in h
            assert "total_incidents" in h

    async def test_sorted_by_total_incidents(self, analytics):
        hotspots = await analytics.get_threat_hotspots()
        totals = [h["total_incidents"] for h in hotspots]
        assert totals == sorted(totals, reverse=True)

    async def test_respects_limit(self, analytics):
        hotspots = await analytics.get_threat_hotspots(limit=2)
        assert len(hotspots) <= 2

    async def test_incident_counts_are_non_negative(self, analytics):
        hotspots = await analytics.get_threat_hotspots()
        for h in hotspots:
            assert h["total_incidents"] >= 0

    async def test_groups_by_country(self, analytics, sample_incidents):
        hotspots = await analytics.get_threat_hotspots()
        us_hotspot = next((h for h in hotspots if h["country"] == "United States"), None)
        assert us_hotspot is not None
        assert us_hotspot["total_incidents"] == 1


class TestGetIspThreatRankings:
    async def test_sorted_by_count(self, analytics):
        isps = await analytics.get_isp_threat_rankings()
        counts = [c for _, c in isps]
        assert counts == sorted(counts, reverse=True)

    async def test_isp_a_is_top(self, analytics):
        isps = await analytics.get_isp_threat_rankings()
        assert isps[0][0] == "ISP-A"
        assert isps[0][1] == 2

    async def test_respects_limit(self, analytics):
        isps = await analytics.get_isp_threat_rankings(limit=1)
        assert len(isps) == 1

    async def test_empty_incidents_returns_empty(self):
        svc = AnalyticsService()
        svc.phishing_service.get_all_incidents = AsyncMock(return_value=[])
        isps = await svc.get_isp_threat_rankings()
        assert isps == []


class TestGetThreatOverview:
    async def test_overview_has_all_required_keys(self, analytics):
        overview = await analytics.get_threat_overview()
        required_keys = {
            "total_incidents", "threat_distribution", "top_regions",
            "top_companies", "top_isps", "hotspots", "last_updated",
        }
        assert required_keys.issubset(overview.keys())

    async def test_total_incidents_matches_sample(self, analytics, sample_incidents):
        overview = await analytics.get_threat_overview()
        assert overview["total_incidents"] == len(sample_incidents)

    async def test_top_regions_is_list(self, analytics):
        overview = await analytics.get_threat_overview()
        assert isinstance(overview["top_regions"], list)

    async def test_threat_distribution_has_correct_counts(self, analytics):
        overview = await analytics.get_threat_overview()
        dist = overview["threat_distribution"]
        assert dist["critical"] == 2
        assert dist["high"] == 1
