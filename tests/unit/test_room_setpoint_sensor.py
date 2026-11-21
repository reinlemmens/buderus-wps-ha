"""Room setpoint sensors show the setpoint the circuit actually runs on (#19).

The old sensors read broadcast idx 33 on bases 0x0060-0x0063, which turned out
to track room temperature + ~1.4 K and never followed the thermostat. The
sensors now read the pump's MV_T5_SETPOINT_ACTUAL_n copy (the same value the
room setpoint number entities show), and exist only for circuits where that
source is hardware-verified.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.buderus_wps import sensor as sensor_platform
from custom_components.buderus_wps.buderus_wps.config import get_default_sensor_map
from custom_components.buderus_wps.buderus_wps.room_thermostat import (
    ROOM_SETPOINT_CIRCUITS,
)
from custom_components.buderus_wps.const import DOMAIN
from custom_components.buderus_wps.sensor import BuderusRoomSetpointSensor


class TestRoomSetpointSensor:
    def test_value_is_active_setpoint_not_broadcast(self, mock_coordinator):
        mock_coordinator.data.room_setpoint_active = {3: 25.0, 4: 18.5}
        # A stale idx-33 value in temperatures must not leak through.
        mock_coordinator.data.temperatures["setpoint_c4"] = 25.0

        assert BuderusRoomSetpointSensor(mock_coordinator, 3).native_value == 25.0
        assert BuderusRoomSetpointSensor(mock_coordinator, 4).native_value == 18.5

    def test_value_none_when_setpoint_unknown(self, mock_coordinator):
        mock_coordinator.data.room_setpoint_active = {}
        assert BuderusRoomSetpointSensor(mock_coordinator, 3).native_value is None

    def test_value_none_when_disconnected(self, mock_coordinator_disconnected):
        sensor = BuderusRoomSetpointSensor(mock_coordinator_disconnected, 3)
        assert sensor.native_value is None

    def test_keeps_existing_entity_identity(self, mock_coordinator):
        sensor = BuderusRoomSetpointSensor(mock_coordinator, 4)
        assert sensor._attr_unique_id.endswith("_temp_setpoint_c4")
        assert sensor._attr_name == "Room Setpoint C4"


class TestSetup:
    @pytest.mark.asyncio
    async def test_setpoint_sensors_only_for_verified_circuits(self, mock_coordinator):
        mock_coordinator.parameter_allowlist = []
        entry = MagicMock()
        entry.entry_id = "e1"
        hass = MagicMock()
        hass.data = {DOMAIN: {"e1": {"coordinator": mock_coordinator}}}
        added: list = []

        await sensor_platform.async_setup_entry(hass, entry, added.extend)

        setpoint_circuits = sorted(
            s.circuit for s in added if isinstance(s, BuderusRoomSetpointSensor)
        )
        assert setpoint_circuits == sorted(ROOM_SETPOINT_CIRCUITS)
        temp_types = {
            getattr(s, "_sensor_type", None)
            for s in added
            if not isinstance(s, BuderusRoomSetpointSensor)
        }
        assert not any(str(t).startswith("setpoint_") for t in temp_types)


class TestBroadcastMap:
    def test_idx33_is_not_mapped_to_any_sensor(self):
        sensor_map = get_default_sensor_map()
        assert not [key for key in sensor_map if key[1] == 33]
        assert not [v for v in sensor_map.values() if v.startswith("setpoint_")]


class TestBroadcastLabels:
    """idx 33 must not be labelled as a setpoint anywhere (#19)."""

    def test_idx33_not_labelled_setpoint(self):
        from custom_components.buderus_wps.buderus_wps.broadcast_monitor import (
            KNOWN_BROADCASTS,
            PARAM_TO_BROADCAST,
        )

        for base in (0x0060, 0x0061, 0x0062, 0x0063):
            name, _fmt = KNOWN_BROADCASTS[(base, 33)]
            assert "SETPOINT" not in name
        assert not [
            n
            for n, key in PARAM_TO_BROADCAST.items()
            if key[1] == 33 and "SETPOINT" in n
        ]

    def test_module_idx107_labelled_active_setpoint(self):
        from custom_components.buderus_wps.buderus_wps.broadcast_monitor import (
            KNOWN_BROADCASTS,
        )

        for module_base in (0x0402, 0x0403):
            name, _fmt = KNOWN_BROADCASTS[(module_base, 107)]
            assert "ACTIVE_SETPOINT" in name
