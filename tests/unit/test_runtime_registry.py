"""Unit tests for RuntimeParameterRegistry.

Tests the runtime parameter registry that stores discovered elements from the
heat pump and provides lookup with fallback to static defaults.

Protocol Reference: FHEM 26_KM273v018.pm lines 2052-2164
"""

from buderus_wps.element_discovery import DiscoveredElement
from buderus_wps.runtime_registry import RuntimeParameterRegistry


class TestRuntimeParameterRegistryLookup:
    """Tests for RuntimeParameterRegistry lookup by name (T053)."""

    def test_lookup_discovered_element_by_name(self):
        """Look up a parameter that was discovered from the heat pump."""
        registry = RuntimeParameterRegistry()

        # Register a discovered element
        element = DiscoveredElement(
            idx=2480,  # Different from static value
            extid="E1263DCA71010F",
            text="XDHW_TIME",
            min_value=0,
            max_value=48,
        )
        registry.register(element)

        # Look up by name
        result = registry.get_by_name("XDHW_TIME")

        assert result is not None
        assert result.idx == 2480
        assert result.text == "XDHW_TIME"

    def test_lookup_is_case_insensitive(self):
        """Parameter name lookup should be case-insensitive."""
        registry = RuntimeParameterRegistry()

        element = DiscoveredElement(
            idx=100,
            extid="AABBCCDDEEFF00",
            text="TEST_PARAM",
            min_value=0,
            max_value=100,
        )
        registry.register(element)

        # Look up with different cases
        assert registry.get_by_name("TEST_PARAM") is not None
        assert registry.get_by_name("test_param") is not None
        assert registry.get_by_name("Test_Param") is not None

    def test_lookup_nonexistent_returns_none(self):
        """Looking up a non-existent parameter returns None."""
        registry = RuntimeParameterRegistry()

        result = registry.get_by_name("NONEXISTENT_PARAM")

        assert result is None

    def test_register_multiple_elements(self):
        """Register and look up multiple elements."""
        registry = RuntimeParameterRegistry()

        elements = [
            DiscoveredElement(
                idx=100, extid="AA" * 7, text="PARAM_A", min_value=0, max_value=10
            ),
            DiscoveredElement(
                idx=101, extid="BB" * 7, text="PARAM_B", min_value=-10, max_value=10
            ),
            DiscoveredElement(
                idx=102, extid="CC" * 7, text="PARAM_C", min_value=0, max_value=100
            ),
        ]

        for elem in elements:
            registry.register(elem)

        assert registry.get_by_name("PARAM_A").idx == 100
        assert registry.get_by_name("PARAM_B").idx == 101
        assert registry.get_by_name("PARAM_C").idx == 102

    def test_register_overwrites_existing(self):
        """Registering an element with the same name overwrites the previous one."""
        registry = RuntimeParameterRegistry()

        # Register initial element
        elem1 = DiscoveredElement(
            idx=100, extid="AA" * 7, text="TEST_PARAM", min_value=0, max_value=10
        )
        registry.register(elem1)

        # Register element with same name but different idx
        elem2 = DiscoveredElement(
            idx=200, extid="BB" * 7, text="TEST_PARAM", min_value=0, max_value=20
        )
        registry.register(elem2)

        # Should have the new value
        result = registry.get_by_name("TEST_PARAM")
        assert result.idx == 200
        assert result.max_value == 20

    def test_count_returns_number_of_registered_elements(self):
        """The count property returns the number of registered elements."""
        registry = RuntimeParameterRegistry()

        assert registry.count == 0

        registry.register(
            DiscoveredElement(
                idx=100, extid="AA" * 7, text="P1", min_value=0, max_value=10
            )
        )
        assert registry.count == 1

        registry.register(
            DiscoveredElement(
                idx=101, extid="BB" * 7, text="P2", min_value=0, max_value=10
            )
        )
        assert registry.count == 2


class TestRuntimeParameterRegistryFallback:
    """Tests for RuntimeParameterRegistry fallback to static defaults (T054)."""

    def test_fallback_to_static_when_not_discovered(self):
        """Fall back to static parameter_data when element not discovered."""
        registry = RuntimeParameterRegistry(use_static_fallback=True)

        # Look up a parameter that exists in static data but not discovered
        # XDHW_TIME exists in parameter_data.py with idx=2475
        result = registry.get_by_name("XDHW_TIME")

        assert result is not None
        # The fallback should return a DiscoveredElement-compatible object
        assert hasattr(result, "idx")
        assert hasattr(result, "text")

    def test_discovered_takes_precedence_over_static(self):
        """Discovered elements take precedence over static defaults."""
        registry = RuntimeParameterRegistry(use_static_fallback=True)

        # Register a discovered element with different idx than static
        element = DiscoveredElement(
            idx=2480,  # Different from static value of 2475
            extid="E1263DCA71010F",
            text="XDHW_TIME",
            min_value=0,
            max_value=48,
        )
        registry.register(element)

        result = registry.get_by_name("XDHW_TIME")

        # Should use discovered value, not static
        assert result.idx == 2480

    def test_no_fallback_when_disabled(self):
        """When fallback is disabled, only discovered elements are returned."""
        registry = RuntimeParameterRegistry(use_static_fallback=False)

        # Don't register anything - should return None even for known params
        result = registry.get_by_name("XDHW_TIME")

        assert result is None

    def test_fallback_enabled_by_default(self):
        """Static fallback should be enabled by default."""
        registry = RuntimeParameterRegistry()

        # Without registering, should fall back to static for known params
        result = registry.get_by_name("XDHW_TIME")

        assert result is not None

    def test_static_fallback_returns_compatible_object(self):
        """Static fallback returns object with same interface as DiscoveredElement."""
        registry = RuntimeParameterRegistry(use_static_fallback=True)

        result = registry.get_by_name("XDHW_TIME")

        # Check it has all the required attributes
        assert hasattr(result, "idx")
        assert hasattr(result, "extid")
        assert hasattr(result, "text")
        assert hasattr(result, "min_value")
        assert hasattr(result, "max_value")
        assert hasattr(result, "can_id")


class TestRuntimeParameterRegistryBulkOperations:
    """Tests for bulk operations on RuntimeParameterRegistry."""

    def test_register_all_from_list(self):
        """Register multiple elements at once."""
        registry = RuntimeParameterRegistry()

        elements = [
            DiscoveredElement(
                idx=100, extid="AA" * 7, text="PARAM_A", min_value=0, max_value=10
            ),
            DiscoveredElement(
                idx=101, extid="BB" * 7, text="PARAM_B", min_value=0, max_value=10
            ),
            DiscoveredElement(
                idx=102, extid="CC" * 7, text="PARAM_C", min_value=0, max_value=10
            ),
        ]

        registry.register_all(elements)

        assert registry.count == 3
        assert registry.get_by_name("PARAM_A") is not None
        assert registry.get_by_name("PARAM_B") is not None
        assert registry.get_by_name("PARAM_C") is not None

    def test_clear_removes_all_discovered(self):
        """Clear removes all discovered elements but doesn't affect fallback."""
        registry = RuntimeParameterRegistry(use_static_fallback=True)

        # Register some elements
        registry.register(
            DiscoveredElement(
                idx=100, extid="AA" * 7, text="CUSTOM_PARAM", min_value=0, max_value=10
            )
        )
        registry.register(
            DiscoveredElement(
                idx=2480, extid="BB" * 7, text="XDHW_TIME", min_value=0, max_value=48
            )
        )

        assert registry.count == 2

        # Clear
        registry.clear()

        assert registry.count == 0

        # Custom param should be gone
        assert registry.get_by_name("CUSTOM_PARAM") is None

        # But static fallback should still work
        result = registry.get_by_name("XDHW_TIME")
        assert result is not None
        # Should be static value now (idx=2475), not our registered 2480
        assert result.idx == 2475

    def test_get_all_discovered(self):
        """Get all discovered elements as a list."""
        registry = RuntimeParameterRegistry()

        elements = [
            DiscoveredElement(
                idx=100, extid="AA" * 7, text="PARAM_A", min_value=0, max_value=10
            ),
            DiscoveredElement(
                idx=101, extid="BB" * 7, text="PARAM_B", min_value=0, max_value=10
            ),
        ]

        registry.register_all(elements)

        all_elements = registry.get_all_discovered()

        assert len(all_elements) == 2
        names = {e.text for e in all_elements}
        assert names == {"PARAM_A", "PARAM_B"}
