"""Runtime parameter registry for discovered heat pump elements.

This module provides a registry that stores parameter elements discovered from
the heat pump at runtime, with fallback to static parameter definitions when
elements are not discovered.

The registry enables the CAN communication layer to use dynamic idx values
that may differ between firmware versions, while maintaining compatibility
with the static parameter database for known parameters.
"""

import logging
from typing import Dict, List, Optional

from .element_discovery import DiscoveredElement
from .parameter_defaults import PARAMETER_DEFAULTS

# Build a lookup dict from the parameter defaults list
_STATIC_PARAMS = {p["text"].upper(): p for p in PARAMETER_DEFAULTS}

logger = logging.getLogger(__name__)


class RuntimeParameterRegistry:
    """Registry for heat pump parameters with discovery support.

    Stores discovered elements from the heat pump and provides lookup by name.
    When an element is not discovered, falls back to static parameter definitions
    from parameter_data.py.

    Attributes:
        use_static_fallback: Whether to fall back to static parameter data
            when a parameter is not found in the discovered elements.
    """

    def __init__(self, use_static_fallback: bool = True):
        """Initialize the registry.

        Args:
            use_static_fallback: If True (default), look up parameters in
                static parameter_data.py when not found in discovered elements.
        """
        self._elements: Dict[str, DiscoveredElement] = {}
        self.use_static_fallback = use_static_fallback

    @property
    def count(self) -> int:
        """Return the number of discovered elements in the registry."""
        return len(self._elements)

    def register(self, element: DiscoveredElement) -> None:
        """Register a discovered element.

        Args:
            element: The discovered element to register. If an element with
                the same name already exists, it will be overwritten.
        """
        # Normalize name to uppercase for case-insensitive lookup
        key = element.text.upper()
        self._elements[key] = element
        logger.debug(f"Registered element: {element.text} (idx={element.idx})")

    def register_all(self, elements: List[DiscoveredElement]) -> None:
        """Register multiple elements at once.

        Args:
            elements: List of discovered elements to register.
        """
        for element in elements:
            self.register(element)

    def clear(self) -> None:
        """Remove all discovered elements from the registry.

        This does not affect static fallback behavior - after clearing,
        lookups will still fall back to static data if enabled.
        """
        self._elements.clear()
        logger.debug("Cleared all discovered elements from registry")

    def get_by_name(self, name: str) -> Optional[DiscoveredElement]:
        """Look up a parameter by name.

        Lookup is case-insensitive. If the parameter was discovered from the
        heat pump, returns the discovered element. Otherwise, if static fallback
        is enabled, returns a DiscoveredElement constructed from static data.

        Args:
            name: The parameter name to look up (case-insensitive).

        Returns:
            DiscoveredElement if found, None otherwise.
        """
        # Normalize to uppercase for lookup
        key = name.upper()

        # First check discovered elements
        if key in self._elements:
            return self._elements[key]

        # Fall back to static data if enabled
        if self.use_static_fallback:
            return self._get_from_static(key)

        return None

    def _get_from_static(self, name: str) -> Optional[DiscoveredElement]:
        """Get a parameter from static parameter_defaults.py.

        Args:
            name: The parameter name (already uppercase).

        Returns:
            DiscoveredElement constructed from static data, or None if not found.
        """
        # Look up in static parameters dict
        if name not in _STATIC_PARAMS:
            return None

        param = _STATIC_PARAMS[name]

        # Construct a DiscoveredElement from static data
        # Static data format: {'idx': int, 'extid': str, 'min': int, 'max': int, ...}
        return DiscoveredElement(
            idx=param["idx"],
            extid=param["extid"],
            text=param["text"],
            min_value=param.get("min", 0),
            max_value=param.get("max", 0),
        )

    def get_all_discovered(self) -> List[DiscoveredElement]:
        """Get all discovered elements.

        Returns:
            List of all elements that were discovered from the heat pump.
            Does not include static fallback elements.
        """
        return list(self._elements.values())
