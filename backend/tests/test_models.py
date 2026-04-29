import pytest
from datetime import datetime
from pydantic import ValidationError
from models import PhishingIncident, MapPoint, HeatmapData, FilterRequest


class TestPhishingIncident:
    def test_valid_incident(self):
        incident = PhishingIncident(
            url="http://malicious.com",
            latitude=40.7128,
            longitude=-74.0060,
            threat_level="high",
            company="PayPal",
            country="United States",
            isp="Example ISP",
        )
        assert incident.url == "http://malicious.com"
        assert incident.threat_level == "high"

    def test_threat_level_normalized_to_lowercase(self):
        incident = PhishingIncident(
            url="http://test.com", latitude=0.0, longitude=0.0, threat_level="HIGH"
        )
        assert incident.threat_level == "high"

    def test_threat_level_invalid_raises(self):
        with pytest.raises(ValidationError):
            PhishingIncident(
                url="http://test.com", latitude=0.0, longitude=0.0, threat_level="danger"
            )

    def test_threat_level_defaults_to_unknown(self):
        incident = PhishingIncident(url="http://test.com", latitude=0.0, longitude=0.0)
        assert incident.threat_level == "unknown"

    def test_latitude_too_high_raises(self):
        with pytest.raises(ValidationError):
            PhishingIncident(url="http://test.com", latitude=91.0, longitude=0.0)

    def test_latitude_too_low_raises(self):
        with pytest.raises(ValidationError):
            PhishingIncident(url="http://test.com", latitude=-91.0, longitude=0.0)

    def test_longitude_too_high_raises(self):
        with pytest.raises(ValidationError):
            PhishingIncident(url="http://test.com", latitude=0.0, longitude=181.0)

    def test_longitude_too_low_raises(self):
        with pytest.raises(ValidationError):
            PhishingIncident(url="http://test.com", latitude=0.0, longitude=-181.0)

    def test_boundary_coordinates_valid(self):
        incident = PhishingIncident(
            url="http://test.com", latitude=90.0, longitude=180.0
        )
        assert incident.latitude == 90.0
        assert incident.longitude == 180.0

    def test_boundary_coordinates_min_valid(self):
        incident = PhishingIncident(
            url="http://test.com", latitude=-90.0, longitude=-180.0
        )
        assert incident.latitude == -90.0
        assert incident.longitude == -180.0

    def test_missing_url_raises(self):
        with pytest.raises(ValidationError):
            PhishingIncident(latitude=0.0, longitude=0.0)

    def test_empty_url_raises(self):
        with pytest.raises(ValidationError):
            PhishingIncident(url="", latitude=0.0, longitude=0.0)

    def test_optional_fields_default_none(self):
        incident = PhishingIncident(url="http://test.com", latitude=0.0, longitude=0.0)
        assert incident.id is None
        assert incident.company is None
        assert incident.country is None
        assert incident.isp is None
        assert incident.detected_at is None

    def test_all_valid_threat_levels(self):
        allowed = ["none", "low", "moderate", "elevated", "high", "critical", "unknown"]
        for level in allowed:
            inc = PhishingIncident(url="http://test.com", latitude=0.0, longitude=0.0, threat_level=level)
            assert inc.threat_level == level


class TestMapPoint:
    def test_valid_map_point(self):
        pt = MapPoint(
            lat=40.7128, lon=-74.0060, intensity=8,
            name="PayPal", threat_level="high",
            company="PayPal", country="US", isp="ISP",
        )
        assert pt.lat == 40.7128
        assert pt.intensity == 8

    def test_intensity_too_high_raises(self):
        with pytest.raises(ValidationError):
            MapPoint(lat=0.0, lon=0.0, intensity=11, name="X", threat_level="low")

    def test_intensity_too_low_raises(self):
        with pytest.raises(ValidationError):
            MapPoint(lat=0.0, lon=0.0, intensity=0, name="X", threat_level="low")

    def test_intensity_boundary_min_valid(self):
        pt = MapPoint(lat=0.0, lon=0.0, intensity=1, name="X", threat_level="low")
        assert pt.intensity == 1

    def test_intensity_boundary_max_valid(self):
        pt = MapPoint(lat=0.0, lon=0.0, intensity=10, name="X", threat_level="critical")
        assert pt.intensity == 10

    def test_lat_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            MapPoint(lat=91.0, lon=0.0, intensity=5, name="X", threat_level="low")

    def test_optional_fields_default_none(self):
        pt = MapPoint(lat=0.0, lon=0.0, intensity=5, name="X", threat_level="low")
        assert pt.company is None
        assert pt.country is None
        assert pt.isp is None


class TestHeatmapData:
    def test_valid_heatmap_data(self):
        hd = HeatmapData(
            coordinates=[[40.7, -74.0], [51.5, -0.1]],
            incident_count=2,
            last_updated=datetime.now(),
        )
        assert hd.incident_count == 2
        assert len(hd.coordinates) == 2

    def test_negative_incident_count_raises(self):
        with pytest.raises(ValidationError):
            HeatmapData(coordinates=[], incident_count=-1, last_updated=datetime.now())


class TestFilterRequest:
    def test_defaults(self):
        fr = FilterRequest()
        assert fr.limit == 100
        assert fr.offset == 0
        assert fr.threat_level is None
        assert fr.company is None
        assert fr.country is None
        assert fr.isp is None

    def test_limit_too_high_raises(self):
        with pytest.raises(ValidationError):
            FilterRequest(limit=1001)

    def test_limit_too_low_raises(self):
        with pytest.raises(ValidationError):
            FilterRequest(limit=0)

    def test_negative_offset_raises(self):
        with pytest.raises(ValidationError):
            FilterRequest(offset=-1)
