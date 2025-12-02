"""Configuration module for Buderus WPS heat pump.

This module provides:
- Sensor broadcast mapping configuration (CAN address to sensor name)
- Installation-specific circuit configuration
- DHW (domestic hot water) distribution settings
- Custom sensor labels

Configuration can be loaded from:
1. Explicit path via load_config(path=...)
2. BUDERUS_WPS_CONFIG environment variable
3. ./buderus-wps.yaml (current directory)
4. ~/.config/buderus-wps/config.yaml (XDG standard)
5. Built-in defaults (no file needed)

Security: All YAML loading uses yaml.safe_load() to prevent code execution.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class SensorType(Enum):
    """Known sensor types that can be mapped from CAN broadcasts."""

    OUTDOOR = "outdoor"
    SUPPLY = "supply"
    RETURN_TEMP = "return_temp"
    DHW = "dhw"
    BRINE_IN = "brine_in"


class HeatingType(Enum):
    """Heating delivery types for circuits.

    Note: This is different from buderus_wps.enums.CircuitType which
    describes mixing valve configuration (UNMIXED/MIXED).
    """

    VENTILO = "ventilo"
    FLOOR_HEATING = "floor_heating"
    UNKNOWN = "unknown"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class SensorMapping:
    """Maps a CAN broadcast address to a sensor type.

    Attributes:
        base: CAN message base address (0x0000-0xFFFF)
        idx: Parameter index within message (0-2047)
        sensor: The sensor type this address represents
    """

    base: int
    idx: int
    sensor: SensorType

    def __post_init__(self) -> None:
        """Validate field values."""
        if not 0 <= self.base <= 0xFFFF:
            raise ValueError(f"base must be 0-65535, got {self.base}")
        if not 0 <= self.idx <= 2047:
            raise ValueError(f"idx must be 0-2047, got {self.idx}")

    @property
    def key(self) -> Tuple[int, int]:
        """Return (base, idx) tuple for use as dictionary key."""
        return (self.base, self.idx)


@dataclass
class CircuitConfig:
    """Configuration for a heating circuit.

    Attributes:
        number: Circuit number (1-4)
        circuit_type: Type of heating circuit
        apartment: Optional apartment identifier
        label: Optional custom display label
    """

    number: int
    heating_type: HeatingType = HeatingType.UNKNOWN
    apartment: Optional[str] = None
    label: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate field values."""
        if not 1 <= self.number <= 4:
            raise ValueError(f"number must be 1-4, got {self.number}")


@dataclass
class DHWConfig:
    """Domestic hot water distribution configuration.

    Attributes:
        apartments: List of apartments with DHW access.
                   If empty/None, all apartments have access.
    """

    apartments: Optional[List[str]] = None

    def has_access(self, apartment: str) -> bool:
        """Check if an apartment has DHW access.

        Args:
            apartment: Apartment identifier to check

        Returns:
            True if apartment has DHW access, False otherwise
        """
        if self.apartments is None:
            return True  # Default: all apartments have access
        return apartment in self.apartments


@dataclass
class InstallationConfig:
    """Complete installation configuration.

    Attributes:
        version: Configuration file version (for compatibility)
        sensor_mappings: List of CAN address to sensor mappings
        circuits: List of heating circuit configurations
        dhw: DHW distribution configuration
        labels: Custom sensor display labels
    """

    version: str = "1.0"
    sensor_mappings: List[SensorMapping] = field(default_factory=list)
    circuits: List[CircuitConfig] = field(default_factory=list)
    dhw: DHWConfig = field(default_factory=DHWConfig)
    labels: Dict[str, str] = field(default_factory=dict)

    def get_sensor_map(self) -> Dict[Tuple[int, int], str]:
        """Get sensor mappings as a dictionary.

        Returns:
            Dict mapping (base, idx) tuples to sensor names
        """
        return {m.key: m.sensor.value for m in self.sensor_mappings}

    def get_circuit(self, number: int) -> Optional[CircuitConfig]:
        """Get circuit configuration by number.

        Args:
            number: Circuit number (1-4)

        Returns:
            CircuitConfig if found, None otherwise
        """
        for circuit in self.circuits:
            if circuit.number == number:
                return circuit
        return None

    def get_circuits_by_apartment(self, apartment: str) -> List[CircuitConfig]:
        """Get all circuits serving an apartment.

        Args:
            apartment: Apartment identifier

        Returns:
            List of CircuitConfig for the apartment
        """
        return [c for c in self.circuits if c.apartment == apartment]

    def get_label(self, sensor: str) -> str:
        """Get display label for a sensor.

        Args:
            sensor: Sensor name (outdoor, supply, etc.)

        Returns:
            Custom label if defined, otherwise formatted default
        """
        if sensor in self.labels:
            return self.labels[sensor]
        return DEFAULT_SENSOR_LABELS.get(sensor, sensor.replace("_", " ").title())


# =============================================================================
# Constants
# =============================================================================

# Default sensor display labels
DEFAULT_SENSOR_LABELS: Dict[str, str] = {
    "outdoor": "Outdoor Temperature",
    "supply": "Supply Temperature",
    "return_temp": "Return Temperature",
    "dhw": "Hot Water Temperature",
    "brine_in": "Brine Inlet Temperature",
}

# Default sensor mappings verified against actual CAN bus traffic (2024-12-02)
# Multiple sources for same sensor provide resilience to intermittent broadcasts
DEFAULT_SENSOR_MAPPINGS: List[SensorMapping] = [
    # GT2 - Outdoor temperature
    SensorMapping(base=0x0402, idx=38, sensor=SensorType.OUTDOOR),
    # GT3 - DHW tank temperature (broadcasts from multiple circuits)
    SensorMapping(base=0x0060, idx=58, sensor=SensorType.DHW),
    SensorMapping(base=0x0061, idx=58, sensor=SensorType.DHW),
    SensorMapping(base=0x0062, idx=58, sensor=SensorType.DHW),
    SensorMapping(base=0x0063, idx=58, sensor=SensorType.DHW),
    # GT1 - Brine inlet temperature
    SensorMapping(base=0x0060, idx=12, sensor=SensorType.BRINE_IN),
    SensorMapping(base=0x0061, idx=12, sensor=SensorType.BRINE_IN),
    SensorMapping(base=0x0063, idx=12, sensor=SensorType.BRINE_IN),
    # GT8 - Supply/flow temperature
    SensorMapping(base=0x0270, idx=1, sensor=SensorType.SUPPLY),
    SensorMapping(base=0x0270, idx=7, sensor=SensorType.SUPPLY),
    # GT9 - Return temperature
    SensorMapping(base=0x0270, idx=0, sensor=SensorType.RETURN_TEMP),
]


# =============================================================================
# Helper Functions
# =============================================================================


def _find_config_file() -> Optional[Path]:
    """Find configuration file using search order.

    Search order:
    1. BUDERUS_WPS_CONFIG environment variable
    2. ./buderus-wps.yaml (current directory)
    3. ~/.config/buderus-wps/config.yaml (XDG standard)

    Returns:
        Path to config file if found, None otherwise
    """
    # Check environment variable
    env_path = os.environ.get("BUDERUS_WPS_CONFIG")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path
        logger.warning(f"BUDERUS_WPS_CONFIG points to non-existent file: {env_path}")

    # Check current directory
    local_path = Path("buderus-wps.yaml")
    if local_path.exists():
        return local_path

    # Check XDG config directory
    xdg_path = Path.home() / ".config" / "buderus-wps" / "config.yaml"
    if xdg_path.exists():
        return xdg_path

    return None


def _parse_sensor_mappings(data: List[dict]) -> List[SensorMapping]:
    """Parse sensor mappings from YAML data.

    Args:
        data: List of mapping dictionaries from YAML

    Returns:
        List of validated SensorMapping objects
    """
    mappings = []
    for item in data:
        try:
            base = item.get("base", 0)
            idx = item.get("idx", 0)
            sensor_str = item.get("sensor", "")

            # Handle hex strings for base
            if isinstance(base, str):
                base = int(base, 16) if base.startswith("0x") else int(base)

            # Validate sensor type
            try:
                sensor = SensorType(sensor_str)
            except ValueError:
                logger.warning(f"Unknown sensor type '{sensor_str}', skipping mapping")
                continue

            mapping = SensorMapping(base=base, idx=idx, sensor=sensor)
            mappings.append(mapping)
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid sensor mapping: {item}, error: {e}")
            continue

    return mappings


def _parse_circuits(data: List[dict]) -> List[CircuitConfig]:
    """Parse circuit configurations from YAML data.

    Args:
        data: List of circuit dictionaries from YAML

    Returns:
        List of validated CircuitConfig objects
    """
    circuits = []
    for item in data:
        try:
            number = item.get("number", 0)
            type_str = item.get("type", "unknown")
            apartment = item.get("apartment")
            label = item.get("label")

            # Validate heating type
            try:
                heating_type = HeatingType(type_str)
            except ValueError:
                logger.warning(f"Unknown heating type '{type_str}', using UNKNOWN")
                heating_type = HeatingType.UNKNOWN

            circuit = CircuitConfig(
                number=number,
                heating_type=heating_type,
                apartment=apartment,
                label=label,
            )
            circuits.append(circuit)
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid circuit config: {item}, error: {e}")
            continue

    return circuits


def _parse_dhw(data: dict) -> DHWConfig:
    """Parse DHW configuration from YAML data.

    Args:
        data: DHW dictionary from YAML

    Returns:
        DHWConfig object
    """
    apartments = data.get("apartments")
    if apartments is not None and not isinstance(apartments, list):
        logger.warning(f"Invalid DHW apartments format: {apartments}, using default")
        apartments = None
    return DHWConfig(apartments=apartments)


def _parse_labels(data: dict) -> Dict[str, str]:
    """Parse custom labels from YAML data.

    Args:
        data: Labels dictionary from YAML

    Returns:
        Dict of sensor name to custom label
    """
    labels = {}
    for key, value in data.items():
        if isinstance(value, str):
            labels[key] = value
        else:
            logger.warning(f"Invalid label for '{key}': {value}, skipping")
    return labels


# =============================================================================
# Public API
# =============================================================================


def get_default_sensor_map() -> Dict[Tuple[int, int], str]:
    """Get default sensor mappings as a dictionary.

    This provides the verified CAN broadcast to sensor mappings
    without loading a full configuration.

    Returns:
        Dict mapping (base, idx) tuples to sensor names
    """
    return {m.key: m.sensor.value for m in DEFAULT_SENSOR_MAPPINGS}


def get_default_config() -> InstallationConfig:
    """Get the default configuration with built-in sensor mappings.

    Returns:
        InstallationConfig with default values based on verified
        CAN broadcast mappings from actual hardware testing.
    """
    return InstallationConfig(
        version="1.0",
        sensor_mappings=list(DEFAULT_SENSOR_MAPPINGS),
        circuits=[],
        dhw=DHWConfig(),
        labels={},
    )


def load_config(path: Optional[str] = None) -> InstallationConfig:
    """Load configuration from file.

    Searches for configuration in order:
    1. Explicit path if provided
    2. BUDERUS_WPS_CONFIG environment variable
    3. ./buderus-wps.yaml (current directory)
    4. ~/.config/buderus-wps/config.yaml (XDG standard)
    5. Returns default configuration if no file found

    Args:
        path: Optional explicit path to configuration file

    Returns:
        InstallationConfig loaded from file or defaults
    """
    # Find config file
    config_path: Optional[Path] = None
    if path:
        config_path = Path(path)
        if not config_path.exists():
            logger.warning(f"Config file not found: {path}, using defaults")
            return get_default_config()
    else:
        config_path = _find_config_file()

    if config_path is None:
        logger.debug("No config file found, using defaults")
        return get_default_config()

    # Load and parse YAML
    try:
        with open(config_path, "r") as f:
            # SECURITY: Use safe_load to prevent code execution
            data = yaml.safe_load(f)

        if data is None:
            logger.warning(f"Empty config file: {config_path}, using defaults")
            return get_default_config()

        if not isinstance(data, dict):
            logger.warning(f"Invalid config format in {config_path}, using defaults")
            return get_default_config()

    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error in {config_path}: {e}, using defaults")
        return get_default_config()
    except OSError as e:
        logger.error(f"Error reading config file {config_path}: {e}, using defaults")
        return get_default_config()

    # Parse configuration sections
    version = data.get("version", "1.0")

    # Parse sensor mappings (use defaults if not specified)
    sensor_data = data.get("sensor_mappings", [])
    if sensor_data:
        sensor_mappings = _parse_sensor_mappings(sensor_data)
    else:
        sensor_mappings = list(DEFAULT_SENSOR_MAPPINGS)

    # Parse circuits
    circuit_data = data.get("circuits", [])
    circuits = _parse_circuits(circuit_data) if circuit_data else []

    # Parse DHW
    dhw_data = data.get("dhw", {})
    dhw = _parse_dhw(dhw_data) if dhw_data else DHWConfig()

    # Parse labels
    label_data = data.get("labels", {})
    labels = _parse_labels(label_data) if label_data else {}

    logger.info(f"Loaded config from {config_path}")
    return InstallationConfig(
        version=version,
        sensor_mappings=sensor_mappings,
        circuits=circuits,
        dhw=dhw,
        labels=labels,
    )
