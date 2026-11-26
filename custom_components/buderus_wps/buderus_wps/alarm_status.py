"""Alarm-pending status of the heat pump (Rego 1000), issue #25.

The stored alarm log is not readable over CAN. What the pump does expose is
one status value, parameter RTU800B_SYSTEM_STATUS (look it up by name: the
index differs per firmware):

    4  unconfirmed alarm popups exist on the panel
    3  short step while the last popup is being confirmed
    0  very short step right after 3
    1  no pending alarms

Any other value has not been observed and is treated as unknown.
"""

from typing import Any, Optional

SYSTEM_STATUS_PARAM = "RTU800B_SYSTEM_STATUS"

STATUS_ALARM_PENDING = 4
STATUS_NOT_PENDING = frozenset({0, 1, 3})


def alarm_pending(status: Optional[int]) -> Optional[bool]:
    """Map a raw system status to "alarm pending".

    Returns True for 4, False for 0/1/3 and None for no reading or a value
    whose meaning is unknown.
    """
    if status == STATUS_ALARM_PENDING:
        return True
    if status in STATUS_NOT_PENDING:
        return False
    return None


def parse_system_status(decoded: Any) -> Optional[int]:
    """Turn a decoded parameter value into a raw status, or None.

    Only whole numbers count as a reading. bool is rejected although it is an
    int subclass: a True/False answer is not a status value.
    """
    if isinstance(decoded, bool):
        return None
    if isinstance(decoded, int):
        return decoded
    if isinstance(decoded, float) and decoded.is_integer():
        return int(decoded)
    return None
