"""
Configuration API Contract

This module defines the public API contract for the sensor configuration
and installation settings feature. Implementation must conform to these
interfaces.

Feature: 009-sensor-config
Date: 2024-12-02
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class SensorType(Enum):
    """Known sensor types that can be mapped from CAN broadcasts."""
    OUTDOOR = "outdoor"
    SUPPLY = "supply"
    RETURN_TEMP = "return_temp"
    DHW = "dhw"
    BRINE_IN = "brine_in"


class CircuitType(Enum):
    """Heating circuit types."""
    VENTILO = "ventilo"
    FLOOR_HEATING = "floor_heating"
    UNKNOWN = "unknown"


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
    circuit_type: CircuitType = CircuitType.UNKNOWN
    apartment: Optional[str] = None
    label: Optional[str] = None

    def __post_init__(self) -> None:
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
        # Default labels
        defaults = {
            "outdoor": "Outdoor Temperature",
            "supply": "Supply Temperature",
            "return_temp": "Return Temperature",
            "dhw": "Hot Water Temperature",
            "brine_in": "Brine Inlet Temperature",
        }
        return defaults.get(sensor, sensor.replace("_", " ").title())


# Module-level functions (public API)

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

    Logs:
        Warning if falling back to defaults
        Warning for invalid entries (which are skipped)
    """
    # Implementation contract - actual implementation in buderus_wps/config.py
    raise NotImplementedError("Contract only - see buderus_wps/config.py")


def get_default_config() -> InstallationConfig:
    """Get the default configuration with built-in sensor mappings.

    Returns:
        InstallationConfig with default values based on verified
        CAN broadcast mappings from actual hardware testing.
    """
    # Implementation contract - actual implementation in buderus_wps/config.py
    raise NotImplementedError("Contract only - see buderus_wps/config.py")


def get_default_sensor_map() -> Dict[Tuple[int, int], str]:
    """Get default sensor mappings as a dictionary.

    This provides the verified CAN broadcast to sensor mappings
    without loading a full configuration.

    Returns:
        Dict mapping (base, idx) tuples to sensor names
    """
    # Implementation contract - actual implementation in buderus_wps/config.py
    raise NotImplementedError("Contract only - see buderus_wps/config.py")
