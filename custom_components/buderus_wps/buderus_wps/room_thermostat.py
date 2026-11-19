"""Room setpoint control by impersonating a room thermostat on the CAN bus.

PROTOCOL (hardware-verified 2026-11-19, Logatherm WPS 17-1 with RC10/RTU800B
room units and two external mixing modules):

- Each room thermostat is a CAN node on base 0x0060-0x0063 (circuit 1-4). It is
  the master of its circuit's room setpoint: when the knob is turned it sends
  a data frame ``0x0C048060 | n`` (idx 18) with the new setpoint as a 2-byte
  big-endian signed value in 0.1 °C. It sends only on change, not periodically.
- The circuit's mixing module (base 0x0402 = E13/C3, 0x0403 = E14/C4) echoes
  the value (idx 239) within a second and broadcasts the setpoint it runs on
  as idx 107 about every 32 s. The pump mirrors it into
  ``MV_T5_SETPOINT_ACTUAL_n``.
- Sending the same frame from the USBtin has the identical effect, and the
  thermostat's own display follows the new value.
- The pump-side ``MV_T5_SETPOINT_n`` parameters are NOT the command path: the
  thermostat's value overrides them. The ``*_GLOBAL`` room parameters are the
  pump menu's edit buffer for whichever circuit is selected; never write them.

Only C3 and C4 (the circuits with an external mixing module) are verified.
C1 and C2 are regulated inside the pump and their thermostat path is untested.
"""

from __future__ import annotations

import struct
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

from .can_message import CANMessage

THERMOSTAT_SETPOINT_IDX = 18
MODULE_ACTIVE_SETPOINT_IDX = 107

ROOM_SETPOINT_MIN = 15.0
ROOM_SETPOINT_MAX = 25.0
ROOM_SETPOINT_STEP = 0.5

# Change limit per circuit; each change is a user-level thermostat action.
ROOM_SETPOINT_MAX_WRITES = 6
ROOM_SETPOINT_WINDOW_S = 3600.0


@dataclass(frozen=True)
class RoomCircuit:
    """CAN addressing for one heating circuit's room setpoint."""

    circuit: int
    thermostat_base: int
    module_base: int
    pump_active_param: str  # RTR-readable copy of the setpoint in use (int, 0.1 °C)


ROOM_SETPOINT_CIRCUITS: dict[int, RoomCircuit] = {
    3: RoomCircuit(3, 0x0062, 0x0402, "MV_T5_SETPOINT_ACTUAL_2"),
    4: RoomCircuit(4, 0x0063, 0x0403, "MV_T5_SETPOINT_ACTUAL_3"),
}


def thermostat_setpoint_can_id(circuit: int) -> int:
    """CAN ID the circuit's room thermostat uses to announce a new setpoint."""
    rc = ROOM_SETPOINT_CIRCUITS[circuit]
    return 0x0C000000 | (THERMOSTAT_SETPOINT_IDX << 14) | rc.thermostat_base


def validate_room_setpoint(circuit: int, temp: float) -> int:
    """Validate a room setpoint and return its raw 0.1 °C value.

    Raises:
        ValueError: unsupported circuit, out of range, or not a 0.5 °C step.
    """
    if circuit not in ROOM_SETPOINT_CIRCUITS:
        raise ValueError(
            f"Room setpoint control not supported for circuit {circuit}; "
            f"supported: {sorted(ROOM_SETPOINT_CIRCUITS)}"
        )
    if not ROOM_SETPOINT_MIN <= temp <= ROOM_SETPOINT_MAX:
        raise ValueError(
            f"Room setpoint must be between {ROOM_SETPOINT_MIN:.1f} and "
            f"{ROOM_SETPOINT_MAX:.1f}°C, got {temp}"
        )
    halves = temp / ROOM_SETPOINT_STEP
    if abs(halves - round(halves)) > 1e-6:
        raise ValueError(f"Room setpoint must be a multiple of 0.5°C, got {temp}")
    return int(round(temp * 10))


def build_room_setpoint_frame(circuit: int, temp: float) -> CANMessage:
    """Build the thermostat data frame that sets ``circuit`` to ``temp`` °C."""
    raw = validate_room_setpoint(circuit, temp)
    return CANMessage(
        arbitration_id=thermostat_setpoint_can_id(circuit),
        data=struct.pack(">h", raw),
        is_extended_id=True,
    )


def decode_active_setpoint(raw: Any) -> float | None:
    """Decode a pump ``MV_T5_SETPOINT_ACTUAL_n`` read (int, 0.1 °C).

    Returns None for missing values or sentinels outside a plausible range.
    """
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value: float = int(raw) / 10.0
    except (TypeError, ValueError):
        return None
    if not 5.0 <= value <= 35.0:
        return None
    return value


class WriteRateLimiter:
    """Sliding-window limit on writes per key (e.g. per circuit)."""

    def __init__(
        self,
        max_writes: int = ROOM_SETPOINT_MAX_WRITES,
        window_s: float = ROOM_SETPOINT_WINDOW_S,
    ) -> None:
        self.max_writes = max_writes
        self.window_s = window_s
        self._writes: dict[int, deque[float]] = {}

    def _prune(self, key: int, now: float) -> deque[float]:
        q = self._writes.setdefault(key, deque())
        while q and now - q[0] >= self.window_s:
            q.popleft()
        return q

    def allowed(self, key: int, now: float | None = None) -> bool:
        """True if another write for ``key`` fits in the window."""
        now = time.monotonic() if now is None else now
        return len(self._prune(key, now)) < self.max_writes

    def record(self, key: int, now: float | None = None) -> None:
        """Record a write for ``key``."""
        now = time.monotonic() if now is None else now
        self._prune(key, now).append(now)

    def retry_after(self, key: int, now: float | None = None) -> float:
        """Seconds until the next write for ``key`` is allowed (0 if now)."""
        now = time.monotonic() if now is None else now
        q = self._prune(key, now)
        if len(q) < self.max_writes:
            return 0.0
        return max(0.0, self.window_s - (now - q[0]))
