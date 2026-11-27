"""Mixed heating circuit room sensor diagnostics and acknowledgement (#22).

PROTOCOL (hardware-verified 2026-11-22, Logatherm WPS 17-1 with two external
mixing modules E13/C3 and E14/C4):

- The pump's ``MV_*_n`` parameters are indexed by *mixed circuit* slot n:
  slot 1 = C2, slot 2 = C3, slot 3 = C4 (matched against room temperatures
  and setpoints).
- ``MV_T5_ACKNOWLEDGED_BITMASK`` (idx 1826) is the installer menu setting
  "Cn room -> Acknowledge room sensor", one bit per circuit at bit
  ``circuit - 1`` (C2 = 0x2, C3 = 0x4, C4 = 0x8). Toggling the panel setting
  flips the bit 1:1 within ~10 s.
- While a circuit's bit is clear the pump does not use the room thermostat:
  ``MV_T5_ATTENUATED_n`` sits at the 20.0 °C default and room influence and
  the room setpoint (including HA's room setpoint control) have no effect.
- ``MV_T5_ACTUAL_n`` reads 0xDEAD when the pump has no own room value for the
  circuit; ``MV_T1_SETPOINT_n`` is the circuit's supply temperature target.

All values are 'int' format; temperatures are in 0.1 °C.

The parameter definitions carry min = max = 0, so the generic write path
treats idx 1826 as read-only. Writes go through ``HeatPump.write_raw_value``
and are verified by reading the bitmask back.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ROOM_SENSOR_ACK_PARAM = "MV_T5_ACKNOWLEDGED_BITMASK"

# Diagnostic value keys (also used in BuderusData.mixed_circuit_values).
VALUE_ROOM_TEMP_USED = "room_temp_used"
VALUE_ROOM_SENSOR = "room_sensor"
VALUE_SUPPLY_TARGET = "supply_target"


@dataclass(frozen=True)
class MixedCircuit:
    """Pump parameters for one mixed heating circuit."""

    circuit: int
    slot: int

    @property
    def ack_bit(self) -> int:
        """Bit of this circuit in MV_T5_ACKNOWLEDGED_BITMASK."""
        return 1 << (self.circuit - 1)

    @property
    def params(self) -> dict[str, str]:
        """Diagnostic value key -> pump parameter name."""
        return {
            VALUE_ROOM_TEMP_USED: f"MV_T5_ATTENUATED_{self.slot}",
            VALUE_ROOM_SENSOR: f"MV_T5_ACTUAL_{self.slot}",
            VALUE_SUPPLY_TARGET: f"MV_T1_SETPOINT_{self.slot}",
        }


MIXED_CIRCUITS: dict[int, MixedCircuit] = {
    2: MixedCircuit(2, 1),
    3: MixedCircuit(3, 2),
    4: MixedCircuit(4, 3),
}


def is_acknowledged(mask: int | None, circuit: int) -> bool | None:
    """Return whether ``circuit``'s room sensor is acknowledged in ``mask``."""
    if mask is None:
        return None
    return bool(mask & MIXED_CIRCUITS[circuit].ack_bit)


def with_acknowledged(mask: int, circuit: int, acknowledged: bool) -> int:
    """Return ``mask`` with only ``circuit``'s bit set or cleared."""
    bit = MIXED_CIRCUITS[circuit].ack_bit
    return (mask | bit) if acknowledged else (mask & ~bit & 0xFFFF)


def decode_bitmask(raw: Any) -> int | None:
    """Decode a MV_T5_ACKNOWLEDGED_BITMASK read; None if not an integer."""
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if not 0 <= value <= 0xFFFF:
        return None
    return value


def decode_temperature(raw: Any) -> float | None:
    """Decode an 'int' 0.1 °C circuit temperature read.

    Returns None for missing values, 0xDEAD (decoded upstream as None) and
    values outside a plausible range.
    """
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value: float = int(raw) / 10.0
    except (TypeError, ValueError):
        return None
    if not -50.0 <= value <= 100.0:
        return None
    return value
