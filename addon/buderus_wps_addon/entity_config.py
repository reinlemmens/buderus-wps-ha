"""Entity configuration for MQTT Discovery.

Defines all sensor and control entities that will be published to Home Assistant
via MQTT Discovery protocol.
"""

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class EntityConfig:
    """Configuration for an MQTT Discovery entity."""

    entity_id: str
    entity_type: str  # sensor, binary_sensor, switch, select, number
    name: str
    device_class: str | None = None
    unit: str | None = None
    state_class: str | None = None

    # Topic configuration
    state_topic: str = ""
    command_topic: str | None = None

    # Value handling
    value_template: str | None = None
    options: list[str] | None = None
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None

    # Source configuration
    parameter_name: str | None = None
    broadcast_idx: int | None = None
    use_menu_api: bool = False

    def __post_init__(self) -> None:
        """Set default state topic if not provided."""
        if not self.state_topic:
            self.state_topic = f"buderus_wps/{self.entity_type}/{self.entity_id}/state"
        if self.command_topic is None and self.entity_type in ("switch", "select", "number"):
            if self.parameter_name or self.use_menu_api:
                self.command_topic = f"buderus_wps/{self.entity_type}/{self.entity_id}/set"


# Temperature Sensors (Read-Only)
# Source: CAN bus broadcasts with known indexes
TEMPERATURE_SENSORS: list[EntityConfig] = [
    EntityConfig(
        entity_id="outdoor_temp",
        entity_type="sensor",
        name="Outdoor Temperature",
        device_class="temperature",
        unit="°C",
        state_class="measurement",
        broadcast_idx=12,
    ),
    EntityConfig(
        entity_id="supply_temp",
        entity_type="sensor",
        name="Supply Temperature",
        device_class="temperature",
        unit="°C",
        state_class="measurement",
        broadcast_idx=13,
    ),
    EntityConfig(
        entity_id="return_temp",
        entity_type="sensor",
        name="Return Temperature",
        device_class="temperature",
        unit="°C",
        state_class="measurement",
        broadcast_idx=14,
    ),
    EntityConfig(
        entity_id="dhw_temp",
        entity_type="sensor",
        name="Hot Water Temperature",
        device_class="temperature",
        unit="°C",
        state_class="measurement",
        broadcast_idx=15,
    ),
    EntityConfig(
        entity_id="buffer_top_temp",
        entity_type="sensor",
        name="Buffer Top Temperature",
        device_class="temperature",
        unit="°C",
        state_class="measurement",
        broadcast_idx=16,
    ),
    EntityConfig(
        entity_id="buffer_bottom_temp",
        entity_type="sensor",
        name="Buffer Bottom Temperature",
        device_class="temperature",
        unit="°C",
        state_class="measurement",
        broadcast_idx=17,
    ),
]

# Binary Sensors (Read-Only)
# Source: MenuAPI status
BINARY_SENSORS: list[EntityConfig] = [
    EntityConfig(
        entity_id="compressor",
        entity_type="binary_sensor",
        name="Compressor",
        device_class="running",
        use_menu_api=True,
    ),
]

# Select Entities (Read/Write)
# Source: Direct parameter read/write
SELECT_ENTITIES: list[EntityConfig] = [
    EntityConfig(
        entity_id="heating_season_mode",
        entity_type="select",
        name="Heating Season Mode",
        options=["Winter", "Automatic", "Summer"],
        parameter_name="HEATING_SEASON_MODE",
    ),
    EntityConfig(
        entity_id="dhw_program_mode",
        entity_type="select",
        name="DHW Program Mode",
        options=["Automatic", "Always On", "Always Off"],
        parameter_name="DHW_PROGRAM_MODE",
    ),
]

# Switch Entities (Read/Write)
# Source: Direct parameter read/write
SWITCH_ENTITIES: list[EntityConfig] = [
    EntityConfig(
        entity_id="holiday_mode",
        entity_type="switch",
        name="Holiday Mode",
        parameter_name="HOLIDAY_ACTIVE_GLOBAL",
    ),
]

# Number Entities (Read/Write)
# Source: MenuAPI for extra hot water controls
NUMBER_ENTITIES: list[EntityConfig] = [
    EntityConfig(
        entity_id="extra_dhw_duration",
        entity_type="number",
        name="Extra Hot Water Duration",
        unit="h",
        min_value=0,
        max_value=48,
        step=1,
        use_menu_api=True,
    ),
    EntityConfig(
        entity_id="extra_dhw_target",
        entity_type="number",
        name="Extra Hot Water Target",
        device_class="temperature",
        unit="°C",
        min_value=50.0,
        max_value=65.0,
        step=0.5,
        use_menu_api=True,
    ),
]

# All entities combined
ALL_ENTITIES: list[EntityConfig] = (
    TEMPERATURE_SENSORS + BINARY_SENSORS + SELECT_ENTITIES + SWITCH_ENTITIES + NUMBER_ENTITIES
)


# Value mappings for select entities
# Maps HA option string → parameter value
HEATING_SEASON_MODE_MAP: dict[str, int] = {
    "Winter": 0,  # Forced heating - heating always enabled
    "Automatic": 1,  # Normal operation - based on outdoor temp
    "Summer": 2,  # No heating - hot water only
}

DHW_PROGRAM_MODE_MAP: dict[str, int] = {
    "Automatic": 0,  # Normal - follows time program
    "Always On": 1,  # DHW always active
    "Always Off": 2,  # No DHW heating
}

# Reverse mappings for parameter value → HA option
HEATING_SEASON_MODE_REVERSE: dict[int, str] = {v: k for k, v in HEATING_SEASON_MODE_MAP.items()}
DHW_PROGRAM_MODE_REVERSE: dict[int, str] = {v: k for k, v in DHW_PROGRAM_MODE_MAP.items()}


def get_entity_by_id(entity_id: str) -> EntityConfig | None:
    """Get an entity configuration by its ID."""
    for entity in ALL_ENTITIES:
        if entity.entity_id == entity_id:
            return entity
    return None


def get_entities_by_type(entity_type: str) -> list[EntityConfig]:
    """Get all entities of a specific type."""
    return [e for e in ALL_ENTITIES if e.entity_type == entity_type]


def get_controllable_entities() -> list[EntityConfig]:
    """Get all entities that can receive commands."""
    return [e for e in ALL_ENTITIES if e.command_topic is not None]


def map_option_to_value(entity_id: str, option: str) -> int | None:
    """Map a select option to its parameter value."""
    if entity_id == "heating_season_mode":
        return HEATING_SEASON_MODE_MAP.get(option)
    elif entity_id == "dhw_program_mode":
        return DHW_PROGRAM_MODE_MAP.get(option)
    return None


def map_value_to_option(entity_id: str, value: int) -> str | None:
    """Map a parameter value to its select option."""
    if entity_id == "heating_season_mode":
        return HEATING_SEASON_MODE_REVERSE.get(value)
    elif entity_id == "dhw_program_mode":
        return DHW_PROGRAM_MODE_REVERSE.get(value)
    return None
