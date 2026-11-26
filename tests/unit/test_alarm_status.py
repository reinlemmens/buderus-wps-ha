"""Unit tests for the alarm-pending system status mapping (issue #25)."""

import pytest
from buderus_wps.alarm_status import (
    STATUS_ALARM_PENDING,
    SYSTEM_STATUS_PARAM,
    alarm_pending,
    parse_system_status,
)


def test_constants():
    assert SYSTEM_STATUS_PARAM == "RTU800B_SYSTEM_STATUS"
    assert STATUS_ALARM_PENDING == 4


@pytest.mark.parametrize(
    "status,expected",
    [
        (4, True),
        (0, False),
        (1, False),
        (3, False),
        (2, None),
        (5, None),
        (255, None),
        (None, None),
    ],
)
def test_alarm_pending(status, expected):
    assert alarm_pending(status) is expected


@pytest.mark.parametrize(
    "decoded,expected",
    [
        (4, 4),
        (0, 0),
        (4.0, 4),
        (None, None),
        (4.5, None),
        ("4", None),
        (True, None),
        (b"\x04", None),
    ],
)
def test_parse_system_status(decoded, expected):
    assert parse_system_status(decoded) == expected


def test_exported_from_package():
    import buderus_wps

    assert buderus_wps.alarm_pending(4) is True
    assert buderus_wps.SYSTEM_STATUS_PARAM == "RTU800B_SYSTEM_STATUS"
