import pytest
from testBuilder import (
    getThreatLevel,
    isNull, isNone, isLow, isModerate, isElevated, isHigh, isCritical,
    isCountry, isIsp,
    intensityAbove, intensityBelow,
    JsonBuilder, JsonItem, location,
)


def make_item(**kwargs) -> JsonItem:
    defaults: JsonItem = {
        "lat": 40.7,
        "lon": -74.0,
        "intensity": 5.0,
        "name": "test-host.com",
        "threat_level": "high",
        "company": "PayPal",
        "country": "United States",
        "isp": "Example ISP",
    }
    defaults.update(kwargs)
    return defaults


def make_location(**kwargs) -> location:
    loc = location.__new__(location)
    loc.id = kwargs.get("id", 1)
    loc.url = kwargs.get("url", "http://test.com")
    loc.redirect_url = kwargs.get("redirect_url", "")
    loc.ip = kwargs.get("ip", "1.2.3.4")
    loc.countrycode = kwargs.get("countrycode", "US")
    loc.countryname = kwargs.get("countryname", "United States")
    loc.regioncode = kwargs.get("regioncode", "NY")
    loc.regionname = kwargs.get("regionname", "New York")
    loc.city = kwargs.get("city", "New York")
    loc.zipcode = kwargs.get("zipcode", "10001")
    loc.latitude = kwargs.get("latitude", 40.7128)
    loc.longitude = kwargs.get("longitude", -74.0060)
    loc.asn = kwargs.get("asn", "AS12345")
    loc.bgp = kwargs.get("bgp", "")
    loc.isp = kwargs.get("isp", "Example ISP")
    loc.title = kwargs.get("title", "")
    loc.date = kwargs.get("date", "2026-01-01")
    loc.date_update = kwargs.get("date_update", "2026-01-01")
    loc.hash = kwargs.get("hash", "abc123")
    loc.score = kwargs.get("score", 8.0)
    loc.host = kwargs.get("host", "phishing.com")
    loc.domain = kwargs.get("domain", "phishing.com")
    loc.tld = kwargs.get("tld", "com")
    loc.domain_registered_n_days_ago = kwargs.get("domain_registered_n_days_ago", 30)
    loc.screenshot = kwargs.get("screenshot", "")
    loc.abuse_contact = kwargs.get("abuse_contact", "")
    loc.ssl_issuer = kwargs.get("ssl_issuer", "")
    loc.ssl_subject = kwargs.get("ssl_subject", "")
    loc.rank_host = kwargs.get("rank_host", 0)
    loc.rank_domain = kwargs.get("rank_domain", 0)
    loc.n_times_seen_ip = kwargs.get("n_times_seen_ip", 1)
    loc.n_times_seen_host = kwargs.get("n_times_seen_host", 1)
    loc.n_times_seen_domain = kwargs.get("n_times_seen_domain", 1)
    loc.http_code = kwargs.get("http_code", 200)
    loc.http_server = kwargs.get("http_server", "")
    loc.google_safebrowsing = kwargs.get("google_safebrowsing", "")
    loc.virus_total = kwargs.get("virus_total", "")
    loc.abuse_ch_malware = kwargs.get("abuse_ch_malware", "")
    loc.vulns = kwargs.get("vulns", "")
    loc.ports = kwargs.get("ports", "")
    loc.os = kwargs.get("os", "")
    loc.tags = kwargs.get("tags", "")
    loc.technology = kwargs.get("technology", "")
    loc.page_text = kwargs.get("page_text", "")
    loc.ssl_fingerprint = kwargs.get("ssl_fingerprint", "")
    loc.inserted_at = kwargs.get("inserted_at", "2026-01-01")
    return loc


class TestGetThreatLevel:
    def test_score_zero_returns_none(self):
        assert getThreatLevel(0) == "none"

    def test_score_negative_returns_none(self):
        assert getThreatLevel(-5) == "none"

    def test_score_1_returns_low(self):
        assert getThreatLevel(1) == "low"

    def test_score_2_returns_low(self):
        assert getThreatLevel(2) == "low"

    def test_score_3_returns_moderate(self):
        assert getThreatLevel(3) == "moderate"

    def test_score_4_returns_moderate(self):
        assert getThreatLevel(4) == "moderate"

    def test_score_5_returns_elevated(self):
        assert getThreatLevel(5) == "elevated"

    def test_score_6_returns_elevated(self):
        assert getThreatLevel(6) == "elevated"

    def test_score_7_returns_high(self):
        assert getThreatLevel(7) == "high"

    def test_score_8_returns_high(self):
        assert getThreatLevel(8) == "high"

    def test_score_9_returns_critical(self):
        assert getThreatLevel(9) == "critical"

    def test_score_10_returns_critical(self):
        assert getThreatLevel(10) == "critical"

    def test_score_above_10_returns_unknown(self):
        assert getThreatLevel(11) == "unknown"

    def test_score_100_returns_unknown(self):
        assert getThreatLevel(100) == "unknown"


class TestFilterFunctions:
    def test_is_null_true_when_both_zero(self):
        assert isNull(make_item(lat=0, lon=0)) is True

    def test_is_null_false_when_nonzero_lat(self):
        assert isNull(make_item(lat=40.7, lon=0)) is False

    def test_is_null_false_when_nonzero_lon(self):
        assert isNull(make_item(lat=0, lon=-74.0)) is False

    def test_is_null_false_when_both_nonzero(self):
        assert isNull(make_item(lat=40.7, lon=-74.0)) is False

    def test_is_none_true(self):
        assert isNone(make_item(threat_level="none")) is True

    def test_is_none_false(self):
        assert isNone(make_item(threat_level="low")) is False

    def test_is_low_true(self):
        assert isLow(make_item(threat_level="low")) is True

    def test_is_low_false(self):
        assert isLow(make_item(threat_level="high")) is False

    def test_is_moderate_true(self):
        assert isModerate(make_item(threat_level="moderate")) is True

    def test_is_moderate_false(self):
        assert isModerate(make_item(threat_level="low")) is False

    def test_is_elevated_true(self):
        assert isElevated(make_item(threat_level="elevated")) is True

    def test_is_elevated_false(self):
        assert isElevated(make_item(threat_level="high")) is False

    def test_is_high_true(self):
        assert isHigh(make_item(threat_level="high")) is True

    def test_is_high_false(self):
        assert isHigh(make_item(threat_level="critical")) is False

    def test_is_critical_true(self):
        assert isCritical(make_item(threat_level="critical")) is True

    def test_is_critical_false(self):
        assert isCritical(make_item(threat_level="high")) is False

    def test_is_country_true_exact(self):
        assert isCountry(make_item(country="United States"), "United States") is True

    def test_is_country_true_case_insensitive(self):
        assert isCountry(make_item(country="United States"), "united states") is True

    def test_is_country_false(self):
        assert isCountry(make_item(country="France"), "United States") is False

    def test_is_isp_true_exact(self):
        assert isIsp(make_item(isp="Example ISP"), "Example ISP") is True

    def test_is_isp_true_case_insensitive(self):
        assert isIsp(make_item(isp="Example ISP"), "example isp") is True

    def test_is_isp_false(self):
        assert isIsp(make_item(isp="Other ISP"), "Example ISP") is False

    def test_intensity_above_true(self):
        assert intensityAbove(make_item(intensity=8), 5) is True

    def test_intensity_above_false_equal(self):
        assert intensityAbove(make_item(intensity=5), 5) is False

    def test_intensity_above_false_below(self):
        assert intensityAbove(make_item(intensity=3), 5) is False

    def test_intensity_below_true(self):
        assert intensityBelow(make_item(intensity=3), 5) is True

    def test_intensity_below_false_equal(self):
        assert intensityBelow(make_item(intensity=5), 5) is False

    def test_intensity_below_false_above(self):
        assert intensityBelow(make_item(intensity=8), 5) is False


class TestJsonBuilderCreateDataPoint:
    def test_creates_valid_json_item(self):
        loc = make_location(score=9.0, latitude=40.7, longitude=-74.0, host="phish.com",
                            countryname="United States", isp="ISP-A")
        builder = JsonBuilder.__new__(JsonBuilder)
        item = builder.createDataPoint(loc)
        assert item["lat"] == 40.7
        assert item["lon"] == -74.0
        assert item["intensity"] == 9.0
        assert item["threat_level"] == "critical"
        assert item["name"] == "phish.com"
        assert item["company"] == "phish.com"
        assert item["country"] == "United States"
        assert item["isp"] == "ISP-A"

    def test_threat_level_derived_from_score(self):
        loc = make_location(score=3.0)
        builder = JsonBuilder.__new__(JsonBuilder)
        item = builder.createDataPoint(loc)
        assert item["threat_level"] == "moderate"


class TestJsonBuilderFilters:
    @pytest.fixture
    def builder_with_items(self):
        builder = JsonBuilder.__new__(JsonBuilder)
        builder.items = [
            make_item(threat_level="none"),
            make_item(threat_level="low"),
            make_item(threat_level="moderate"),
            make_item(threat_level="elevated"),
            make_item(threat_level="high"),
            make_item(threat_level="critical"),
        ]
        return builder

    def test_filter_by_threat_level_critical(self, builder_with_items):
        result = builder_with_items.filterByThreatLevel("critical")
        assert len(result) == 1
        assert result[0]["threat_level"] == "critical"

    def test_filter_by_threat_level_case_insensitive(self, builder_with_items):
        result = builder_with_items.filterByThreatLevel("CRITICAL")
        assert len(result) == 1

    def test_filter_by_threat_level_unknown_returns_empty(self, builder_with_items):
        result = builder_with_items.filterByThreatLevel("danger")
        assert result == []

    def test_filter_by_country(self):
        builder = JsonBuilder.__new__(JsonBuilder)
        builder.items = [
            make_item(country="United States"),
            make_item(country="France"),
            make_item(country="United States"),
        ]
        result = builder.filterByCountry("United States")
        assert len(result) == 2

    def test_filter_by_isp(self):
        builder = JsonBuilder.__new__(JsonBuilder)
        builder.items = [
            make_item(isp="ISP-A"),
            make_item(isp="ISP-B"),
            make_item(isp="ISP-A"),
        ]
        result = builder.filterByIsp("ISP-A")
        assert len(result) == 2

    def test_filter_intensity_above(self):
        builder = JsonBuilder.__new__(JsonBuilder)
        builder.items = [
            make_item(intensity=3),
            make_item(intensity=7),
            make_item(intensity=9),
        ]
        result = builder.filterIntensityAbove(5)
        assert len(result) == 2
        assert all(i["intensity"] > 5 for i in result)

    def test_filter_intensity_below(self):
        builder = JsonBuilder.__new__(JsonBuilder)
        builder.items = [
            make_item(intensity=3),
            make_item(intensity=7),
            make_item(intensity=9),
        ]
        result = builder.filterIntensityBelow(5)
        assert len(result) == 1
        assert result[0]["intensity"] == 3
