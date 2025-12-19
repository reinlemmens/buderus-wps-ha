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

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
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
        return 0x04003FE0 | (self.idx << 14)

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
        return 0x0C003FE0 | (self.idx << 14)

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
    """Container for all Buderus WPS heat pump parameters with indexed access.

    Provides efficient O(1) lookup of parameters by either index number or
    human-readable name. Supports loading parameters from multiple sources
    with priority: cache → discovery → static fallback.

    Attributes:
        data_source: String indicating where parameters were loaded from
            ('cache', 'discovery', or 'fallback')
        using_fallback: True if using static fallback data (no device/cache)

    Example:
        >>> heat_pump = HeatPump()
        >>> param = heat_pump.get_parameter_by_name("ACCESS_LEVEL")
        >>> print(f"{param.text}: {param.min}-{param.max}")
        ACCESS_LEVEL: 0-5
        >>> same_param = heat_pump.get_parameter_by_index(1)
        >>> assert param == same_param

    Example with cache and discovery:
        >>> heat_pump = HeatPump(
        ...     adapter=can_adapter,
        ...     cache_path=Path("~/.cache/buderus/params.json")
        ... )
        >>> if heat_pump.using_fallback:
        ...     print("Using fallback - some parameters may not match device")
    """

    def __init__(
        self,
        adapter: Optional[Any] = None,
        cache_path: Optional[Path] = None,
        force_discovery: bool = False
    ):
        """Initialize HeatPump with configurable data loading strategy.

        Parameters are loaded with the following priority:
        1. Cache (if valid and force_discovery=False)
        2. Discovery via CAN adapter (if adapter provided)
        3. Static fallback data from parameter_data.py

        Args:
            adapter: Optional CAN adapter for device discovery. If None,
                discovery is skipped and cache/fallback is used.
            cache_path: Optional path to cache file. If None, caching is
                disabled and parameters come from discovery or fallback.
            force_discovery: If True, ignore cache and always attempt
                discovery first (useful after firmware updates).
        """
        self._params_by_idx: Dict[int, Parameter] = {}
        self._params_by_name: Dict[str, Parameter] = {}
        self._source: str = "fallback"

        # Try loading in priority order: cache → discovery → fallback
        params_loaded = False

        # 1. Try loading from cache (unless force_discovery)
        if cache_path and not force_discovery:
            params_loaded = self._try_load_from_cache(cache_path)

        # 2. Try discovery if adapter provided and cache didn't work
        if not params_loaded and adapter is not None:
            params_loaded = self._try_discovery(adapter, cache_path)

        # 3. Fall back to static data
        if not params_loaded:
            self._load_fallback()

    def _try_load_from_cache(self, cache_path: Path) -> bool:
        """Attempt to load parameters from cache.

        Args:
            cache_path: Path to cache file

        Returns:
            True if successfully loaded from cache, False otherwise
        """
        try:
            from buderus_wps.cache import ParameterCache

            cache = ParameterCache(cache_path)
            if cache.is_valid():
                param_data = cache.load()
                if param_data:
                    self._load_from_list(param_data)
                    self._source = "cache"
                    logger.info(
                        "Loaded %d parameters from cache: %s",
                        len(param_data),
                        cache_path
                    )
                    return True
        except Exception as e:
            logger.warning("Failed to load from cache: %s", e)

        return False

    def _try_discovery(
        self,
        adapter: Any,
        cache_path: Optional[Path]
    ) -> bool:
        """Attempt to discover parameters from device.

        Args:
            adapter: CAN adapter for device communication
            cache_path: Optional path to save discovered parameters

        Returns:
            True if discovery successful, False otherwise
        """
        try:
            from buderus_wps.discovery import ParameterDiscovery

            discovery = ParameterDiscovery(adapter)

            # Run discovery (synchronously for now)
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            param_data = loop.run_until_complete(discovery.discover())

            if param_data:
                self._load_from_list(param_data)
                self._source = "discovery"
                logger.info("Discovered %d parameters from device", len(param_data))

                # Save to cache if path provided
                if cache_path:
                    self._save_to_cache(param_data, cache_path)

                return True
        except Exception as e:
            logger.warning("Discovery failed: %s", e)

        return False

    def _save_to_cache(
        self,
        param_data: List[Dict[str, Any]],
        cache_path: Path
    ) -> None:
        """Save discovered parameters to cache.

        Args:
            param_data: List of parameter dictionaries
            cache_path: Path to cache file
        """
        try:
            from buderus_wps.cache import ParameterCache

            cache = ParameterCache(cache_path)
            if cache.save(param_data):
                logger.info("Saved %d parameters to cache: %s", len(param_data), cache_path)
            else:
                logger.warning("Failed to save parameters to cache")
        except Exception as e:
            logger.warning("Failed to save to cache: %s", e)

    def _load_fallback(self) -> None:
        """Load parameters from static fallback data."""
        from buderus_wps.parameter_data import PARAMETER_DATA

        self._load_from_list(PARAMETER_DATA)
        self._source = "fallback"
        logger.warning(
            "Using static fallback data (%d parameters) - "
            "device discovery unavailable",
            len(PARAMETER_DATA)
        )

    def _load_from_list(self, param_data: List[Dict[str, Any]]) -> None:
        """Load parameters from a list of dictionaries.

        Args:
            param_data: List of parameter dictionaries with keys:
                idx, extid, min, max, format, read, text
        """
        self._params_by_idx.clear()
        self._params_by_name.clear()

        for data in param_data:
            param = Parameter(**data)
            self._params_by_idx[param.idx] = param
            self._params_by_name[param.text] = param

    @property
    def data_source(self) -> str:
        """Return the source of parameter data.

        Returns:
            'cache' if loaded from cache file,
            'discovery' if discovered from device,
            'fallback' if using static data
        """
        return self._source

    @property
    def using_fallback(self) -> bool:
        """Check if using static fallback data.

        Returns:
            True if using fallback (no device/cache), False otherwise
        """
        return self._source == "fallback"

    def get_parameter_by_index(self, idx: int) -> Parameter:
        """Get parameter by index number.

        Args:
            idx: Parameter index (e.g., 1 for ACCESS_LEVEL)

        Returns:
            Parameter object with all metadata

        Raises:
            KeyError: If index does not exist

        Example:
            >>> heat_pump = HeatPump()
            >>> param = heat_pump.get_parameter_by_index(1)
            >>> param.text
            'ACCESS_LEVEL'
        """
        return self._params_by_idx[idx]

    def get_parameter_by_name(self, name: str) -> Parameter:
        """Get parameter by human-readable name.

        Args:
            name: Parameter name (e.g., "ACCESS_LEVEL")

        Returns:
            Parameter object with all metadata

        Raises:
            KeyError: If name does not exist

        Example:
            >>> heat_pump = HeatPump()
            >>> param = heat_pump.get_parameter_by_name("ACCESS_LEVEL")
            >>> param.idx
            1
        """
        return self._params_by_name[name]

    def has_parameter_index(self, idx: int) -> bool:
        """Check if parameter index exists.

        Args:
            idx: Parameter index to check

        Returns:
            True if parameter exists, False otherwise

        Example:
            >>> heat_pump = HeatPump()
            >>> heat_pump.has_parameter_index(1)
            True
            >>> heat_pump.has_parameter_index(13)  # Gap in sequence
            False
        """
        return idx in self._params_by_idx

    def has_parameter_name(self, name: str) -> bool:
        """Check if parameter name exists.

        Args:
            name: Parameter name to check

        Returns:
            True if parameter exists, False otherwise

        Example:
            >>> heat_pump = HeatPump()
            >>> heat_pump.has_parameter_name("ACCESS_LEVEL")
            True
            >>> heat_pump.has_parameter_name("INVALID_NAME")
            False
        """
        return name in self._params_by_name

    def list_all_parameters(self) -> List[Parameter]:
        """Return all parameters sorted by index.

        Returns:
            List of all Parameter objects sorted by idx

        Example:
            >>> heat_pump = HeatPump()
            >>> params = heat_pump.list_all_parameters()
            >>> len(params)
            1789
            >>> params[0].idx
            0
        """
        return sorted(self._params_by_idx.values(), key=lambda p: p.idx)

    def list_writable_parameters(self) -> List[Parameter]:
        """Return only writable (read=0) parameters sorted by index.

        Returns:
            List of writable Parameter objects sorted by idx

        Example:
            >>> heat_pump = HeatPump()
            >>> writable = heat_pump.list_writable_parameters()
            >>> all(p.is_writable() for p in writable)
            True
        """
        return sorted(
            [p for p in self._params_by_idx.values() if p.is_writable()],
            key=lambda p: p.idx
        )

    def list_readonly_parameters(self) -> List[Parameter]:
        """Return only read-only (read!=0) parameters sorted by index.

        Returns:
            List of read-only Parameter objects sorted by idx

        Example:
            >>> heat_pump = HeatPump()
            >>> readonly = heat_pump.list_readonly_parameters()
            >>> all(not p.is_writable() for p in readonly)
            True
        """
        return sorted(
            [p for p in self._params_by_idx.values() if not p.is_writable()],
            key=lambda p: p.idx
        )

    def parameter_count(self) -> int:
        """Return total number of parameters.

        Returns:
            Total parameter count

        Example:
            >>> heat_pump = HeatPump()
            >>> heat_pump.parameter_count()
            1789
        """
        return len(self._params_by_idx)
