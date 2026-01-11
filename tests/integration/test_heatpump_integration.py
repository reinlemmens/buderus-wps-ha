"""Integration tests for HeatPump data loading scenarios.

Tests T049: Verify HeatPump correctly loads from cache → discovery → fallback.

These tests cover:
- Cache hit scenario (valid cache loads without discovery)
- Discovery scenario (no cache, discovery succeeds)
- Fallback scenario (no cache, discovery fails)
- Force discovery bypass (cache ignored when force_discovery=True)
- Data source property reporting
"""

from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch


# Mock CAN adapter for testing
class MockCANAdapter:
    """Mock CAN adapter that simulates discovery protocol responses."""

    def __init__(self, should_succeed: bool = True, element_count: int = 3):
        """Initialize mock adapter.

        Args:
            should_succeed: Whether discovery should succeed
            element_count: Number of elements to return
        """
        self.should_succeed = should_succeed
        self.element_count = element_count
        self.connected = False
        self._calls: list[dict[str, Any]] = []

    async def connect(self) -> None:
        """Simulate connection."""
        self.connected = True
        self._calls.append({"method": "connect"})

    async def disconnect(self) -> None:
        """Simulate disconnection."""
        self.connected = False
        self._calls.append({"method": "disconnect"})

    async def send_message(self, can_id: int, data: bytes) -> None:
        """Record sent message."""
        self._calls.append({"method": "send", "can_id": can_id, "data": data})

    async def receive_message(self, timeout: float = 5.0) -> Optional[dict]:
        """Simulate receiving a message."""
        if not self.should_succeed:
            return None
        return {"can_id": 0x09FD7FE0, "data": b"\x00\x00\x00\x03"}


class TestHeatPumpCacheHit:
    """Test HeatPump loads from valid cache without discovery."""

    def test_loads_from_valid_cache(self, tmp_path):
        """Verify HeatPump uses cache when available and valid."""
        from buderus_wps.cache import ParameterCache
        from buderus_wps.parameter import HeatPump

        # Create valid cache
        cache_path = tmp_path / "params.json"
        cache = ParameterCache(cache_path)
        test_params = [
            {
                "idx": 0,
                "extid": "814A53C66A0802",
                "min": 0,
                "max": 0,
                "format": "int",
                "read": 0,
                "text": "CACHED_PARAM_0",
            },
            {
                "idx": 1,
                "extid": "61E1E1FC660023",
                "min": 0,
                "max": 5,
                "format": "int",
                "read": 0,
                "text": "CACHED_PARAM_1",
            },
        ]
        cache.save(test_params)

        # Initialize HeatPump with cache path
        heat_pump = HeatPump(cache_path=cache_path)

        # Verify loaded from cache
        assert heat_pump.data_source == "cache"
        assert not heat_pump.using_fallback
        assert heat_pump.parameter_count() == 2
        assert heat_pump.has_parameter_name("CACHED_PARAM_0")
        assert heat_pump.has_parameter_name("CACHED_PARAM_1")

    def test_cache_hit_does_not_trigger_discovery(self, tmp_path):
        """Verify discovery is not attempted when cache is valid."""
        from buderus_wps.cache import ParameterCache
        from buderus_wps.parameter import HeatPump

        # Create valid cache
        cache_path = tmp_path / "params.json"
        cache = ParameterCache(cache_path)
        test_params = [
            {
                "idx": 0,
                "extid": "814A53C66A0802",
                "min": 0,
                "max": 0,
                "format": "int",
                "read": 0,
                "text": "TEST_PARAM",
            },
        ]
        cache.save(test_params)

        # Create mock adapter that would fail if called
        mock_adapter = MockCANAdapter(should_succeed=False)

        # Initialize with valid cache - adapter should not be used
        heat_pump = HeatPump(adapter=mock_adapter, cache_path=cache_path)

        assert heat_pump.data_source == "cache"
        # Adapter should not have been called
        assert len(mock_adapter._calls) == 0


class TestHeatPumpDiscovery:
    """Test HeatPump discovery when cache is unavailable."""

    def test_uses_discovery_when_no_cache(self, tmp_path):
        """Verify HeatPump uses discovery when cache doesn't exist."""
        from buderus_wps.parameter import HeatPump

        cache_path = tmp_path / "nonexistent.json"

        # Mock the discovery to return test parameters
        mock_params = [
            {
                "idx": 0,
                "extid": "814A53C66A0802",
                "min": 0,
                "max": 0,
                "format": "int",
                "read": 0,
                "text": "DISCOVERED_PARAM_0",
            },
        ]

        with patch("buderus_wps.discovery.ParameterDiscovery") as MockDiscovery:
            mock_discovery = MagicMock()
            mock_discovery.discover = AsyncMock(return_value=mock_params)
            MockDiscovery.return_value = mock_discovery

            mock_adapter = MockCANAdapter()
            heat_pump = HeatPump(adapter=mock_adapter, cache_path=cache_path)

            assert heat_pump.data_source == "discovery"
            assert not heat_pump.using_fallback

    def test_discovery_result_saved_to_cache(self, tmp_path):
        """Verify discovered parameters are cached for next time."""
        from buderus_wps.cache import ParameterCache
        from buderus_wps.parameter import HeatPump

        cache_path = tmp_path / "new_cache.json"

        mock_params = [
            {
                "idx": 0,
                "extid": "814A53C66A0802",
                "min": 0,
                "max": 0,
                "format": "int",
                "read": 0,
                "text": "DISCOVERED_AND_CACHED",
            },
        ]

        with patch("buderus_wps.discovery.ParameterDiscovery") as MockDiscovery:
            mock_discovery = MagicMock()
            mock_discovery.discover = AsyncMock(return_value=mock_params)
            MockDiscovery.return_value = mock_discovery

            mock_adapter = MockCANAdapter()
            HeatPump(adapter=mock_adapter, cache_path=cache_path)

            # Verify cache was created
            assert cache_path.exists()
            cache = ParameterCache(cache_path)
            loaded = cache.load()
            assert loaded is not None
            assert len(loaded) == 1
            assert loaded[0]["text"] == "DISCOVERED_AND_CACHED"


class TestHeatPumpFallback:
    """Test HeatPump fallback to static data."""

    def test_uses_fallback_when_no_adapter(self):
        """Verify HeatPump falls back to static data with no adapter."""
        from buderus_wps.parameter import HeatPump

        # No adapter, no cache - should use fallback
        heat_pump = HeatPump()

        assert heat_pump.data_source == "fallback"
        assert heat_pump.using_fallback
        # Should have all 1789 parameters from static data
        assert heat_pump.parameter_count() == 1784  # 1788 - 4 duplicates

    def test_uses_fallback_when_discovery_fails(self, tmp_path):
        """Verify HeatPump falls back to static when discovery fails."""
        from buderus_wps.parameter import HeatPump

        cache_path = tmp_path / "nonexistent.json"

        with patch("buderus_wps.discovery.ParameterDiscovery") as MockDiscovery:
            mock_discovery = MagicMock()
            mock_discovery.discover = AsyncMock(
                side_effect=Exception("Discovery failed")
            )
            MockDiscovery.return_value = mock_discovery

            mock_adapter = MockCANAdapter()
            heat_pump = HeatPump(adapter=mock_adapter, cache_path=cache_path)

            assert heat_pump.data_source == "fallback"
            assert heat_pump.using_fallback
            assert heat_pump.parameter_count() == 1784  # 1788 - 4 duplicates

    def test_uses_fallback_when_cache_invalid(self, tmp_path):
        """Verify HeatPump falls back when cache is corrupted."""
        from buderus_wps.parameter import HeatPump

        # Create corrupted cache
        cache_path = tmp_path / "corrupted.json"
        cache_path.write_text("{ invalid json")

        # No adapter provided - should fallback to static
        heat_pump = HeatPump(cache_path=cache_path)

        assert heat_pump.data_source == "fallback"
        assert heat_pump.using_fallback


class TestHeatPumpForceDiscovery:
    """Test force_discovery parameter."""

    def test_force_discovery_ignores_cache(self, tmp_path):
        """Verify force_discovery=True ignores valid cache."""
        from buderus_wps.cache import ParameterCache
        from buderus_wps.parameter import HeatPump

        # Create valid cache with different parameters
        cache_path = tmp_path / "params.json"
        cache = ParameterCache(cache_path)
        cache_params = [
            {
                "idx": 0,
                "extid": "814A53C66A0802",
                "min": 0,
                "max": 0,
                "format": "int",
                "read": 0,
                "text": "OLD_CACHED_PARAM",
            },
        ]
        cache.save(cache_params)

        # Mock discovery to return different parameters
        discovered_params = [
            {
                "idx": 0,
                "extid": "814A53C66A0802",
                "min": 0,
                "max": 0,
                "format": "int",
                "read": 0,
                "text": "FRESH_DISCOVERED_PARAM",
            },
        ]

        with patch("buderus_wps.discovery.ParameterDiscovery") as MockDiscovery:
            mock_discovery = MagicMock()
            mock_discovery.discover = AsyncMock(return_value=discovered_params)
            MockDiscovery.return_value = mock_discovery

            mock_adapter = MockCANAdapter()
            heat_pump = HeatPump(
                adapter=mock_adapter, cache_path=cache_path, force_discovery=True
            )

            # Should use discovery, not cache
            assert heat_pump.data_source == "discovery"
            assert heat_pump.has_parameter_name("FRESH_DISCOVERED_PARAM")
            assert not heat_pump.has_parameter_name("OLD_CACHED_PARAM")

    def test_force_discovery_updates_cache(self, tmp_path):
        """Verify force_discovery updates existing cache."""
        from buderus_wps.cache import ParameterCache
        from buderus_wps.parameter import HeatPump

        # Create initial cache
        cache_path = tmp_path / "params.json"
        cache = ParameterCache(cache_path)
        cache.save(
            [
                {
                    "idx": 0,
                    "extid": "000",
                    "min": 0,
                    "max": 0,
                    "format": "int",
                    "read": 0,
                    "text": "OLD",
                }
            ]
        )

        # Mock discovery
        new_params = [
            {
                "idx": 0,
                "extid": "814A53C66A0802",
                "min": 0,
                "max": 100,
                "format": "int",
                "read": 0,
                "text": "UPDATED",
            },
        ]

        with patch("buderus_wps.discovery.ParameterDiscovery") as MockDiscovery:
            mock_discovery = MagicMock()
            mock_discovery.discover = AsyncMock(return_value=new_params)
            MockDiscovery.return_value = mock_discovery

            mock_adapter = MockCANAdapter()
            HeatPump(adapter=mock_adapter, cache_path=cache_path, force_discovery=True)

            # Verify cache was updated
            loaded = cache.load()
            assert loaded[0]["text"] == "UPDATED"
            assert loaded[0]["max"] == 100


class TestHeatPumpDataSourceProperty:
    """Test data_source property values."""

    def test_data_source_cache(self, tmp_path):
        """Verify data_source returns 'cache' when loaded from cache."""
        from buderus_wps.cache import ParameterCache
        from buderus_wps.parameter import HeatPump

        cache_path = tmp_path / "params.json"
        cache = ParameterCache(cache_path)
        cache.save(
            [
                {
                    "idx": 0,
                    "extid": "814A53C66A0802",
                    "min": 0,
                    "max": 0,
                    "format": "int",
                    "read": 0,
                    "text": "CACHED",
                }
            ]
        )

        heat_pump = HeatPump(cache_path=cache_path)
        assert heat_pump.data_source == "cache"

    def test_data_source_discovery(self, tmp_path):
        """Verify data_source returns 'discovery' when discovered."""
        from buderus_wps.parameter import HeatPump

        cache_path = tmp_path / "nonexistent.json"

        with patch("buderus_wps.discovery.ParameterDiscovery") as MockDiscovery:
            mock_discovery = MagicMock()
            mock_discovery.discover = AsyncMock(
                return_value=[
                    {
                        "idx": 0,
                        "extid": "814A53C66A0802",
                        "min": 0,
                        "max": 0,
                        "format": "int",
                        "read": 0,
                        "text": "DISCOVERED",
                    }
                ]
            )
            MockDiscovery.return_value = mock_discovery

            mock_adapter = MockCANAdapter()
            heat_pump = HeatPump(adapter=mock_adapter, cache_path=cache_path)
            assert heat_pump.data_source == "discovery"

    def test_data_source_fallback(self):
        """Verify data_source returns 'fallback' when using static data."""
        from buderus_wps.parameter import HeatPump

        heat_pump = HeatPump()
        assert heat_pump.data_source == "fallback"


class TestHeatPumpUsingFallbackProperty:
    """Test using_fallback property."""

    def test_using_fallback_false_with_cache(self, tmp_path):
        """Verify using_fallback is False when loaded from cache."""
        from buderus_wps.cache import ParameterCache
        from buderus_wps.parameter import HeatPump

        cache_path = tmp_path / "params.json"
        cache = ParameterCache(cache_path)
        cache.save(
            [
                {
                    "idx": 0,
                    "extid": "814A53C66A0802",
                    "min": 0,
                    "max": 0,
                    "format": "int",
                    "read": 0,
                    "text": "CACHED",
                }
            ]
        )

        heat_pump = HeatPump(cache_path=cache_path)
        assert heat_pump.using_fallback is False

    def test_using_fallback_false_with_discovery(self, tmp_path):
        """Verify using_fallback is False when discovered."""
        from buderus_wps.parameter import HeatPump

        cache_path = tmp_path / "nonexistent.json"

        with patch("buderus_wps.discovery.ParameterDiscovery") as MockDiscovery:
            mock_discovery = MagicMock()
            mock_discovery.discover = AsyncMock(
                return_value=[
                    {
                        "idx": 0,
                        "extid": "814A53C66A0802",
                        "min": 0,
                        "max": 0,
                        "format": "int",
                        "read": 0,
                        "text": "DISCOVERED",
                    }
                ]
            )
            MockDiscovery.return_value = mock_discovery

            mock_adapter = MockCANAdapter()
            heat_pump = HeatPump(adapter=mock_adapter, cache_path=cache_path)
            assert heat_pump.using_fallback is False

    def test_using_fallback_true_with_static(self):
        """Verify using_fallback is True when using static data."""
        from buderus_wps.parameter import HeatPump

        heat_pump = HeatPump()
        assert heat_pump.using_fallback is True


class TestHeatPumpBackwardsCompatibility:
    """Test backwards compatibility with existing code."""

    def test_default_init_still_works(self):
        """Verify HeatPump() still works with no arguments."""
        from buderus_wps.parameter import HeatPump

        heat_pump = HeatPump()
        assert heat_pump.parameter_count() == 1784  # 1788 - 4 duplicates
        assert heat_pump.has_parameter_name("ACCESS_LEVEL")

    def test_existing_methods_still_work(self):
        """Verify all existing methods work after changes."""
        from buderus_wps.parameter import HeatPump

        heat_pump = HeatPump()

        # Test all existing methods
        assert heat_pump.get_parameter_by_index(1).text == "ACCESS_LEVEL"
        assert heat_pump.get_parameter_by_name("ACCESS_LEVEL").idx == 1
        assert heat_pump.has_parameter_index(1) is True
        assert heat_pump.has_parameter_name("ACCESS_LEVEL") is True
        assert len(heat_pump.list_all_parameters()) == 1784  # 1788 - 4 duplicates
        assert len(heat_pump.list_writable_parameters()) > 0
        assert len(heat_pump.list_readonly_parameters()) > 0


class TestHeatPumpLogging:
    """Test logging of data source selection."""

    def test_logs_cache_hit(self, tmp_path, caplog):
        """Verify cache hit is logged."""
        import logging

        from buderus_wps.cache import ParameterCache
        from buderus_wps.parameter import HeatPump

        cache_path = tmp_path / "params.json"
        cache = ParameterCache(cache_path)
        cache.save(
            [
                {
                    "idx": 0,
                    "extid": "814A53C66A0802",
                    "min": 0,
                    "max": 0,
                    "format": "int",
                    "read": 0,
                    "text": "CACHED",
                }
            ]
        )

        with caplog.at_level(logging.INFO):
            HeatPump(cache_path=cache_path)

        assert any("cache" in record.message.lower() for record in caplog.records)

    def test_logs_fallback(self, caplog):
        """Verify fallback is logged as warning."""
        import logging

        from buderus_wps.parameter import HeatPump

        with caplog.at_level(logging.WARNING):
            HeatPump()

        assert any("fallback" in record.message.lower() for record in caplog.records)
