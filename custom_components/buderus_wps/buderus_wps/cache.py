"""Buderus WPS Parameter Cache.

This module provides persistent caching of discovered parameters to avoid
the slow (~30 second) discovery protocol on every connection.

Cache structure (JSON):
{
    "version": "1.0.0",
    "created": "2025-12-18T10:30:00Z",
    "device_id": "BUDERUS_WPS_SN12345",
    "firmware": "v1.23",
    "checksum": "sha256:abc123...",
    "element_count": 1789,
    "parameters": [...]
}

Example:
    >>> cache = ParameterCache(Path("~/.cache/buderus/params.json"))
    >>> if cache.is_valid():
    ...     params = cache.load()
    ... else:
    ...     params = discover_from_device()
    ...     cache.save(params)
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class ParameterCache:
    """Manages persistent cache of discovered parameters.

    The cache stores parameter definitions in JSON format with checksum
    validation to detect corruption. This enables fast reconnection by
    avoiding the slow discovery protocol.

    Attributes:
        CACHE_VERSION: Current cache format version
        cache_path: Path to cache file

    Example:
        >>> cache = ParameterCache(Path("/tmp/params.json"))
        >>> cache.save([{"idx": 0, "text": "PARAM_0", ...}])
        >>> print(cache.is_valid())
        True
        >>> params = cache.load()
    """

    CACHE_VERSION = "1.0.0"

    def __init__(self, cache_path: Path):
        """Initialize cache with file path.

        Args:
            cache_path: Path to cache file (will be created on save)
        """
        self.cache_path = cache_path

    def is_valid(self) -> bool:
        """Check if cache exists and is valid.

        Validates:
        - File exists
        - Valid JSON structure
        - Version matches current version
        - Checksum validates parameters

        Returns:
            True if cache is valid and can be loaded
        """
        if not self.cache_path.exists():
            return False

        try:
            with open(self.cache_path) as f:
                data = json.load(f)

            # Check required fields
            if not isinstance(data, dict):
                return False

            if data.get("version") != self.CACHE_VERSION:
                return False

            if "parameters" not in data:
                return False

            if "checksum" not in data:
                return False

            # Validate checksum
            expected_checksum = self._compute_checksum(data["parameters"])
            if data["checksum"] != expected_checksum:
                return False

            return True

        except (json.JSONDecodeError, OSError, KeyError):
            return False

    def load(self) -> Optional[list[dict]]:
        """Load parameters from cache.

        Returns:
            List of parameter dicts if cache is valid, None otherwise
        """
        if not self.is_valid():
            return None

        try:
            with open(self.cache_path) as f:
                data = json.load(f)
            result: Optional[list[dict[Any, Any]]] = data.get("parameters")
            return result
        except (json.JSONDecodeError, OSError):
            return None

    def save(
        self,
        parameters: list[dict],
        device_id: Optional[str] = None,
        firmware: Optional[str] = None,
    ) -> bool:
        """Save parameters to cache.

        Creates or overwrites cache file with parameter data. Includes
        checksum for integrity validation on load.

        Args:
            parameters: List of parameter dicts
            device_id: Optional device identifier
            firmware: Optional firmware version

        Returns:
            True if save successful, False on error
        """
        try:
            # Ensure parent directory exists
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            # Build cache data
            data = {
                "version": self.CACHE_VERSION,
                "created": datetime.utcnow().isoformat(),
                "element_count": len(parameters),
                "checksum": self._compute_checksum(parameters),
                "parameters": parameters,
            }

            if device_id is not None:
                data["device_id"] = device_id

            if firmware is not None:
                data["firmware"] = firmware

            # Write to file
            with open(self.cache_path, "w") as f:
                json.dump(data, f, indent=2)

            return True

        except OSError:
            return False

    def invalidate(self) -> None:
        """Remove cache file.

        Call this when cache should be regenerated (e.g., firmware change).
        """
        try:
            if self.cache_path.exists():
                self.cache_path.unlink()
        except OSError:
            pass  # Ignore errors during invalidation

    @staticmethod
    def _compute_checksum(parameters: list[dict]) -> str:
        """Compute SHA256 checksum of parameters.

        Creates a deterministic hash of the parameter data for
        integrity validation.

        Args:
            parameters: List of parameter dicts

        Returns:
            Checksum string in format "sha256:hexdigest"
        """
        # Sort parameters by idx for deterministic ordering
        sorted_params = sorted(parameters, key=lambda p: p.get("idx", 0))

        # Create deterministic JSON representation
        json_str = json.dumps(sorted_params, sort_keys=True, separators=(",", ":"))

        # Compute SHA256
        digest = hashlib.sha256(json_str.encode("utf-8")).hexdigest()

        return f"sha256:{digest}"
