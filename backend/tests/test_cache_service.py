import pytest
from datetime import datetime, timedelta
from services.cache_service import CacheService


@pytest.fixture
def cache():
    return CacheService()


class TestCacheServiceSetGet:
    def test_set_and_get_returns_stored_value(self, cache):
        cache.set("key1", [1, 2, 3])
        assert cache.get("key1") == [1, 2, 3]

    def test_get_missing_key_returns_none(self, cache):
        assert cache.get("nonexistent") is None

    def test_set_overwrites_existing_value(self, cache):
        cache.set("key1", "original")
        cache.set("key1", "updated")
        assert cache.get("key1") == "updated"

    def test_set_stores_any_type(self, cache):
        cache.set("list", [1, 2, 3])
        cache.set("dict", {"a": 1})
        cache.set("string", "hello")
        assert cache.get("list") == [1, 2, 3]
        assert cache.get("dict") == {"a": 1}
        assert cache.get("string") == "hello"


class TestCacheServiceExpiry:
    def test_is_expired_fresh_data_returns_false(self, cache):
        cache.set("key1", "value")
        assert cache.is_expired("key1", timeout_minutes=5) is False

    def test_is_expired_stale_data_returns_true(self, cache):
        cache.set("key1", "value")
        cache._cache["key1"]["timestamp"] = datetime.now() - timedelta(minutes=10)
        assert cache.is_expired("key1", timeout_minutes=5) is True

    def test_is_expired_exactly_at_boundary(self, cache):
        cache.set("key1", "value")
        # Just over the boundary → expired
        cache._cache["key1"]["timestamp"] = datetime.now() - timedelta(minutes=5, seconds=1)
        assert cache.is_expired("key1", timeout_minutes=5) is True

    def test_is_expired_missing_key_returns_true(self, cache):
        assert cache.is_expired("nonexistent", timeout_minutes=5) is True

    def test_is_expired_respects_custom_timeout(self, cache):
        cache.set("key1", "value")
        # 1 minute old — not expired under 2-minute timeout, expired under 0.5-minute timeout
        cache._cache["key1"]["timestamp"] = datetime.now() - timedelta(minutes=1)
        assert cache.is_expired("key1", timeout_minutes=2) is False
        assert cache.is_expired("key1", timeout_minutes=0.5) is True


class TestCacheServiceClear:
    def test_clear_specific_key_removes_it(self, cache):
        cache.set("key1", "v1")
        cache.set("key2", "v2")
        cache.clear("key1")
        assert cache.get("key1") is None

    def test_clear_specific_key_does_not_affect_others(self, cache):
        cache.set("key1", "v1")
        cache.set("key2", "v2")
        cache.clear("key1")
        assert cache.get("key2") == "v2"

    def test_clear_nonexistent_key_is_safe(self, cache):
        cache.clear("nonexistent")  # should not raise

    def test_clear_all_removes_everything(self, cache):
        cache.set("key1", "v1")
        cache.set("key2", "v2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_clear_all_on_empty_cache_is_safe(self, cache):
        cache.clear()  # should not raise


class TestCacheServiceInfo:
    def test_get_cache_info_empty(self, cache):
        assert cache.get_cache_info() == {}

    def test_get_cache_info_has_keys(self, cache):
        cache.set("key1", [1, 2, 3])
        info = cache.get_cache_info()
        assert "key1" in info
        assert "timestamp" in info["key1"]
        assert "age_minutes" in info["key1"]
        assert "items" in info["key1"]

    def test_get_cache_info_item_count_for_list(self, cache):
        cache.set("key1", ["a", "b", "c"])
        info = cache.get_cache_info()
        assert info["key1"]["items"] == 3

    def test_get_cache_info_item_count_for_non_list(self, cache):
        cache.set("key1", {"a": 1})
        info = cache.get_cache_info()
        assert info["key1"]["items"] == 1

    def test_get_cache_info_age_is_non_negative(self, cache):
        cache.set("key1", "value")
        info = cache.get_cache_info()
        assert info["key1"]["age_minutes"] >= 0
