import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from api_client import PhishStatsClient


@pytest.fixture
def client():
    return PhishStatsClient()


@pytest.fixture
def raw_incident():
    return {
        "id": 1,
        "url": "http://phishing.com",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "threat_level": "high",
        "company": "PayPal",
        "country": "United States",
        "isp": "Example ISP",
    }


def _make_httpx_mock(json_data):
    """Build a mock that mimics async with httpx.AsyncClient() as c: await c.get(...)"""
    mock_response = MagicMock()
    mock_response.json.return_value = json_data
    mock_response.raise_for_status = MagicMock()

    mock_httpx = AsyncMock()
    mock_httpx.get = AsyncMock(return_value=mock_response)
    mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
    mock_httpx.__aexit__ = AsyncMock(return_value=False)
    return mock_httpx


class TestValidateCoordinates:
    def test_valid_coordinates(self, client):
        assert client.validate_coordinates(40.7128, -74.0060) is True

    def test_valid_zero_coordinates(self, client):
        assert client.validate_coordinates(0.0, 0.0) is True

    def test_latitude_too_high(self, client):
        assert client.validate_coordinates(91.0, 0.0) is False

    def test_latitude_too_low(self, client):
        assert client.validate_coordinates(-91.0, 0.0) is False

    def test_longitude_too_high(self, client):
        assert client.validate_coordinates(0.0, 181.0) is False

    def test_longitude_too_low(self, client):
        assert client.validate_coordinates(0.0, -181.0) is False

    def test_boundary_max_valid(self, client):
        assert client.validate_coordinates(90.0, 180.0) is True

    def test_boundary_min_valid(self, client):
        assert client.validate_coordinates(-90.0, -180.0) is True

    def test_lat_exactly_at_max(self, client):
        assert client.validate_coordinates(90.0, 0.0) is True

    def test_lon_exactly_at_max(self, client):
        assert client.validate_coordinates(0.0, 180.0) is True


class TestFetchIncidentsCaching:
    async def test_returns_cached_data_when_fresh(self, client, raw_incident):
        client.cache.set("phishing_incidents", [raw_incident])

        with patch.object(client, "_fetch_from_api_with_retries", new_callable=AsyncMock) as mock_api:
            result = await client.fetch_incidents()

        mock_api.assert_not_called()
        assert result == [raw_incident]

    async def test_fetches_from_api_when_cache_empty(self, client, raw_incident):
        with patch.object(
            client, "_fetch_from_api_with_retries", new_callable=AsyncMock, return_value=[raw_incident]
        ) as mock_api:
            result = await client.fetch_incidents()

        mock_api.assert_called_once()
        assert result == [raw_incident]

    async def test_force_refresh_bypasses_fresh_cache(self, client, raw_incident):
        fresh_data = [raw_incident]
        api_data = [{**raw_incident, "id": 99}]
        client.cache.set("phishing_incidents", fresh_data)

        with patch.object(
            client, "_fetch_from_api_with_retries", new_callable=AsyncMock, return_value=api_data
        ) as mock_api:
            result = await client.fetch_incidents(force_refresh=True)

        mock_api.assert_called_once()
        assert result == api_data

    async def test_caches_result_after_api_fetch(self, client, raw_incident):
        with patch.object(
            client, "_fetch_from_api_with_retries", new_callable=AsyncMock, return_value=[raw_incident]
        ):
            await client.fetch_incidents()

        cached = client.cache.get("phishing_incidents")
        assert cached == [raw_incident]

    async def test_returns_empty_list_when_api_returns_empty(self, client):
        with patch.object(
            client, "_fetch_from_api_with_retries", new_callable=AsyncMock, return_value=[]
        ):
            result = await client.fetch_incidents()

        assert result == []


class TestFetchFromApiWithRetries:
    async def test_success_on_first_attempt(self, client, raw_incident):
        mock_httpx = _make_httpx_mock([raw_incident])

        with patch("api_client.httpx.AsyncClient", return_value=mock_httpx):
            result = await client._fetch_from_api_with_retries()

        assert result == [raw_incident]
        assert mock_httpx.get.call_count == 1

    async def test_success_after_two_failures(self, client, raw_incident):
        mock_response = MagicMock()
        mock_response.json.return_value = [raw_incident]
        mock_response.raise_for_status = MagicMock()

        call_count = 0

        async def get_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.RequestError("Connection failed")
            return mock_response

        mock_httpx = AsyncMock()
        mock_httpx.get = get_side_effect
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=False)

        with patch("api_client.httpx.AsyncClient", return_value=mock_httpx), \
             patch("api_client.asyncio.sleep", new_callable=AsyncMock):
            result = await client._fetch_from_api_with_retries()

        assert result == [raw_incident]
        assert call_count == 3

    async def test_all_retries_exhausted_raises(self, client):
        mock_httpx = AsyncMock()
        mock_httpx.get = AsyncMock(side_effect=httpx.RequestError("Connection failed"))
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=False)

        with patch("api_client.httpx.AsyncClient", return_value=mock_httpx), \
             patch("api_client.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(Exception, match="Failed to fetch from PhishStats API after"):
                await client._fetch_from_api_with_retries()

    async def test_sleep_called_between_retries(self, client):
        mock_httpx = AsyncMock()
        mock_httpx.get = AsyncMock(side_effect=httpx.RequestError("Connection failed"))
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=False)

        sleep_mock = AsyncMock()
        with patch("api_client.httpx.AsyncClient", return_value=mock_httpx), \
             patch("api_client.asyncio.sleep", sleep_mock):
            with pytest.raises(Exception):
                await client._fetch_from_api_with_retries()

        # Sleep called between retries (max_retries - 1 times = 2 times for 3 retries)
        assert sleep_mock.call_count == client.max_retries - 1
