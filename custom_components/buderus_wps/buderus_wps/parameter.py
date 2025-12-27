"""Buderus WPS Heat Pump Parameter Class.

# PROTOCOL: This module represents parameters from the FHEM KM273_elements_default array.
# Source: fhem/26_KM273v018.pm

This module provides classes for representing and accessing Buderus WPS heat pump parameters.
The Parameter class represents a single configurable or readable value with metadata including
index, external ID, min/max constraints, format type, read-only flag, and human-readable name.

The HeatPump class provides a container for all parameters with efficient lookup by either
index number or parameter name. It supports loading parameters from multiple sources:
- Cache: Previously discovered parameters saved to disk
- Discovery: Live discovery from device via CAN bus
- Fallback: Static data from parameter_data.py

Classes:
    Parameter: Immutable dataclass representing a single heat pump parameter
    HeatPump: Container providing indexed access to all heat pump parameters

Example:
    >>> from buderus_wps.parameter import HeatPump
    >>> heat_pump = HeatPump()
    >>> param = heat_pump.get_parameter_by_name("ACCESS_LEVEL")
    >>> print(f"Valid range: {param.min}-{param.max}")
    Valid range: 0-5
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Parameter:
    """Represents a single Buderus WPS heat pump parameter.

    # PROTOCOL: Maps to entries in @KM273_elements_default from fhem/26_KM273v018.pm

    This class is immutable (frozen) to prevent accidental modification of parameter
    metadata. All attributes are preserved exactly as defined in the FHEM reference
    implementation.

    Attributes:
        idx: Sequential parameter index (may have gaps in sequence, e.g., 13 missing)
        extid: External ID - 14-character hex string for CAN addressing
        min: Minimum allowed value (can be negative for temperature parameters)
        max: Maximum allowed value (must be >= min)
        format: Data format type (e.g., "int", "temp")
        read: Read-only flag (0 = writable, 1 = read-only)
        text: Human-readable parameter name in ALL_CAPS_WITH_UNDERSCORES format

    Example:
        >>> param = Parameter(
        ...     idx=1,
        ...     extid="61E1E1FC660023",
        ...     min=0,
        ...     max=5,
        ...     format="int",
        ...     read=0,
        ...     text="ACCESS_LEVEL"
        ... )
        >>> param.is_writable()
        True
        >>> param.validate_value(3)
        True
        >>> param.validate_value(10)
        False
    """

    idx: int
    extid: str
    min: int
    max: int
    format: str
    read: int
    text: str

    def get_read_can_id(self) -> int:
        """Calculate CAN ID for read request.

        # PROTOCOL: Formula from fhem/26_KM273v018.pm:2229
        # rtr = 0x04003FE0 | (idx << 14)

        Returns:
            CAN ID for sending read requests to this parameter

        Example:
            >>> param = Parameter(idx=1, extid="...", min=0, max=5,
            ...                   format="int", read=0, text="ACCESS_LEVEL")
            >>> hex(param.get_read_can_id())
            '0x4007fe0'
        """
        from .can_ids import CAN_ID_READ_BASE

        return CAN_ID_READ_BASE | (self.idx << 14)

    def get_write_can_id(self) -> int:
        """Calculate CAN ID for write/response.

        # PROTOCOL: Formula from fhem/26_KM273v018.pm:2230
        # txd = 0x0C003FE0 | (idx << 14)

        Returns:
            CAN ID for sending write requests or receiving responses for this parameter

        Example:
            >>> param = Parameter(idx=1, extid="...", min=0, max=5,
            ...                   format="int", read=0, text="ACCESS_LEVEL")
            >>> hex(param.get_write_can_id())
            '0xc007fe0'
        """
        from .can_ids import CAN_ID_WRITE_BASE

        return CAN_ID_WRITE_BASE | (self.idx << 14)

    def is_writable(self) -> bool:
        """Check if parameter is writable (not read-only).

        Returns:
            True if parameter can be written (read=0), False if read-only (read=1)

        Example:
            >>> writable_param = Parameter(idx=1, extid="...", min=0, max=5,
            ...                            format="int", read=0, text="ACCESS_LEVEL")
            >>> writable_param.is_writable()
            True
            >>> readonly_param = Parameter(idx=22, extid="...", min=0, max=16777216,
            ...                            format="int", read=1, text="STATUS")
            >>> readonly_param.is_writable()
            False
        """
        return self.read == 0

    def validate_value(self, value: int) -> bool:
        """Validate if a value is within the allowed min/max range.

        Args:
            value: The value to validate

        Returns:
            True if min <= value <= max, False otherwise

        Example:
            >>> param = Parameter(idx=1, extid="...", min=0, max=5,
            ...                   format="int", read=0, text="ACCESS_LEVEL")
            >>> param.validate_value(3)
            True
            >>> param.validate_value(10)
            False
            >>> param.validate_value(-1)
            False
        """
        return self.min <= value <= self.max


class HeatPump:
    """Container for heat pump parameters with efficient lookup.

    Loads parameters from cache, discovery, or static fallback data.
    Provides lookup by name (case-insensitive) or index number.

    Attributes:
        data_source: Source of parameter data ("fallback", "cache", or "discovery")
        using_fallback: True if using static fallback data

    Example:
        >>> hp = HeatPump()
        >>> param = hp.get_parameter_by_name("ACCESS_LEVEL")
        >>> print(f"idx={param.idx}, range={param.min}-{param.max}")
        idx=1, range=0-5
    """

    def __init__(
        self,
        adapter: Any = None,
        cache_path: Optional[str] = None,
        force_discovery: bool = False,
    ):
        """Initialize HeatPump with parameter data.

        Args:
            adapter: Optional CAN adapter for discovery (not used in simplified mode)
            cache_path: Optional path to cached parameter JSON file.
                       If provided and exists, loads from cache.
            force_discovery: If True, skip cache and try discovery (requires adapter)
        """
        self._params_by_name: Dict[str, Parameter] = {}
        self._params_by_idx: Dict[int, Parameter] = {}
        self._data_source = "fallback"
        self._using_fallback = True
        self._adapter = adapter
        self._cache_path = cache_path

        # Try cache first if path provided and not forcing discovery
        if cache_path and not force_discovery:
            from pathlib import Path

            from .cache import ParameterCache

            cache_file = Path(cache_path)
            if cache_file.exists():
                try:
                    cache = ParameterCache(cache_file)
                    if cache.is_valid():
                        data = cache.load()
                        if data:
                            self._load_parameters(data)
                            self._data_source = "cache"
                            self._using_fallback = False
                            logger.info(
                                "Loaded %d parameters from cache",
                                len(self._params_by_idx),
                            )
                            return
                except Exception as e:
                    logger.warning("Failed to load cache: %s, using fallback", e)

        # Try discovery if adapter provided
        if adapter is not None:
            try:
                self._run_discovery()
                return
            except Exception as e:
                logger.warning("Discovery failed: %s, using fallback", e)

        # Load static fallback data
        self._load_fallback()
        logger.warning(
            "Using fallback parameter data (%d parameters)", len(self._params_by_idx)
        )

    def _run_discovery(self) -> None:
        """Run parameter discovery protocol."""
        import asyncio

        from .discovery import ParameterDiscovery

        discovery = ParameterDiscovery(self._adapter)

        # Run discovery
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        elements = loop.run_until_complete(discovery.discover())

        if not elements:
            raise RuntimeError("Discovery returned no elements")

        self._load_parameters(elements)
        self._data_source = "discovery"
        self._using_fallback = False
        logger.info("Discovered %d parameters from device", len(self._params_by_idx))

        # Save to cache if path provided
        if self._cache_path:
            self._save_cache(elements)

    def _save_cache(self, elements: List[Dict[str, Any]]) -> None:
        """Save discovered elements to cache file."""
        if not self._cache_path:
            return

        from pathlib import Path

        from .cache import ParameterCache

        try:
            cache_file = Path(self._cache_path)
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache = ParameterCache(cache_file)
            cache.save(elements)
            logger.info("Saved %d parameters to cache: %s", len(elements), cache_file)
        except Exception as e:
            logger.warning("Failed to save cache: %s", e)

    def _load_fallback(self) -> None:
        """Load parameters from static fallback data."""
        from .parameter_data import PARAMETER_DATA

        self._load_parameters(PARAMETER_DATA)
        self._data_source = "fallback"
        self._using_fallback = True
        logger.debug("Loaded %d parameters from fallback", len(self._params_by_idx))

    def _load_parameters(self, data: List[Dict[str, Any]]) -> None:
        """Load parameters from list of dicts."""
        self._params_by_name.clear()
        self._params_by_idx.clear()

        for item in data:
            try:
                param = Parameter(
                    idx=item["idx"],
                    extid=item["extid"],
                    min=item["min"],
                    max=item["max"],
                    format=item.get("format", "int"),
                    read=item.get("read", 0),
                    text=item["text"],
                )
                self._params_by_name[param.text.upper()] = param
                self._params_by_idx[param.idx] = param
            except (KeyError, TypeError) as e:
                logger.warning("Skipping invalid parameter: %s (%s)", item, e)

    @property
    def data_source(self) -> str:
        """Source of parameter data: 'fallback', 'cache', or 'discovery'."""
        return self._data_source

    @property
    def using_fallback(self) -> bool:
        """True if using static fallback data."""
        return self._using_fallback

    def parameter_count(self) -> int:
        """Return total number of loaded parameters."""
        return len(self._params_by_idx)

    def get_parameter_by_name(self, name: str) -> Parameter:
        """Look up parameter by name (case-insensitive).

        Args:
            name: Parameter name (e.g., "ACCESS_LEVEL")

        Returns:
            Parameter object

        Raises:
            KeyError: If parameter not found
        """
        param = self._params_by_name.get(name.upper())
        if param is None:
            raise KeyError(f"Unknown parameter: {name}")
        return param

    def get_parameter_by_index(self, idx: int) -> Parameter:
        """Look up parameter by index number.

        Args:
            idx: Parameter index (e.g., 1 for ACCESS_LEVEL)

        Returns:
            Parameter object

        Raises:
            KeyError: If parameter not found
        """
        param = self._params_by_idx.get(idx)
        if param is None:
            raise KeyError(f"Unknown parameter index: {idx}")
        return param

    def get_parameter(self, name_or_idx: Any) -> Optional[Parameter]:
        """Look up parameter by name or index.

        Args:
            name_or_idx: Parameter name (str) or index (int)

        Returns:
            Parameter object or None if not found
        """
        if isinstance(name_or_idx, str):
            return self._params_by_name.get(name_or_idx.upper())
        if isinstance(name_or_idx, int):
            return self._params_by_idx.get(name_or_idx)
        return None

    @property
    def parameters(self) -> List[Parameter]:
        """Return list of all parameters sorted by index (for CLI compatibility)."""
        return sorted(self._params_by_idx.values(), key=lambda p: p.idx)

    def all_parameters(self) -> List[Parameter]:
        """Return list of all parameters sorted by index."""
        return self.parameters

    def list_all_parameters(self) -> List[Parameter]:
        """Return list of all parameters sorted by index (alias for all_parameters)."""
        return self.all_parameters()

    def list_writable_parameters(self) -> List[Parameter]:
        """Return list of writable parameters (read=0) sorted by index."""
        return [p for p in self.all_parameters() if p.read == 0]

    def list_readonly_parameters(self) -> List[Parameter]:
        """Return list of read-only parameters (read=1) sorted by index."""
        return [p for p in self.all_parameters() if p.read == 1]

    def has_parameter_name(self, name: str) -> bool:
        """Check if parameter exists by name (case-insensitive).

        Args:
            name: Parameter name to check

        Returns:
            True if parameter exists, False otherwise
        """
        return name.upper() in self._params_by_name

    def has_parameter_index(self, idx: int) -> bool:
        """Check if parameter exists by index.

        Args:
            idx: Parameter index to check

        Returns:
            True if parameter exists, False otherwise
        """
        return idx in self._params_by_idx

    def update_from_discovery(self, discovered_elements: list) -> int:
        """Update parameter indices from discovered elements.

        Merges discovered elements with existing parameters. For each discovered
        element, if a parameter with matching text exists, its idx is updated
        to match the device's actual index.

        This is critical because different firmware versions may have different
        idx values for the same parameter names (e.g., XDHW_TIME at idx=2475
        in static defaults but idx=2480 on actual device).

        Args:
            discovered_elements: List of DiscoveredElement from element discovery
                Each element must have: idx, extid, text, min_value, max_value

        Returns:
            Number of parameters updated
        """
        updated = 0
        for elem in discovered_elements:
            name = elem.text.upper()
            if name in self._params_by_name:
                old_param = self._params_by_name[name]
                if old_param.idx != elem.idx:
                    # Create new parameter with updated idx from discovery
                    new_param = Parameter(
                        idx=elem.idx,
                        extid=elem.extid,
                        min=elem.min_value,
                        max=elem.max_value,
                        format=old_param.format,  # Keep format from static defaults
                        read=old_param.read,  # Keep read flag from static defaults
                        text=old_param.text,
                    )
                    # Update both lookups - remove old idx, add new
                    del self._params_by_idx[old_param.idx]
                    self._params_by_name[name] = new_param
                    self._params_by_idx[elem.idx] = new_param
                    logger.info(
                        "Updated %s: idx %d -> %d (CAN ID 0x%08X -> 0x%08X)",
                        old_param.text,
                        old_param.idx,
                        elem.idx,
                        0x04003FE0 | (old_param.idx << 14),
                        0x04003FE0 | (elem.idx << 14),
                    )
                    updated += 1
            else:
                # New parameter not in static defaults - add it
                new_param = Parameter(
                    idx=elem.idx,
                    extid=elem.extid,
                    min=elem.min_value,
                    max=elem.max_value,
                    format="int",  # Default format for unknown parameters
                    read=0,  # Assume writable
                    text=elem.text,
                )
                self._params_by_name[name] = new_param
                self._params_by_idx[elem.idx] = new_param
                logger.debug("Added discovered parameter: %s (idx=%d)", elem.text, elem.idx)

        if updated > 0:
            self._data_source = "discovery"
            self._using_fallback = False
            logger.info("Updated %d parameter indices from discovery", updated)

        return updated
