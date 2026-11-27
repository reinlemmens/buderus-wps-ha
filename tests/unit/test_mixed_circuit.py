"""Mixed circuit room sensor acknowledgement and diagnostics (#22).

MV_T5_ACKNOWLEDGED_BITMASK (idx 1826) mirrors the installer menu setting
"Cn room -> Acknowledge room sensor" at bit circuit-1. While a circuit's bit
is clear the pump ignores its room thermostat (MV_T5_ATTENUATED_n sticks at
20.0), so room influence and the room setpoint control have no effect.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.buderus_wps import sensor as sensor_platform
from custom_components.buderus_wps import switch as switch_platform
from custom_components.buderus_wps.buderus_wps.heat_pump import HeatPumpClient
from custom_components.buderus_wps.buderus_wps.mixed_circuit import (
    MIXED_CIRCUITS,
    ROOM_SENSOR_ACK_PARAM,
    VALUE_ROOM_SENSOR,
    VALUE_ROOM_TEMP_USED,
    VALUE_SUPPLY_TARGET,
    decode_bitmask,
    decode_temperature,
    is_acknowledged,
    with_acknowledged,
)
from custom_components.buderus_wps.buderus_wps.parameter_registry import (
    ParameterRegistry,
)
from custom_components.buderus_wps.buderus_wps.room_thermostat import (
    WriteRateLimiter,
)
from custom_components.buderus_wps.const import DOMAIN, MIXED_CIRCUIT_CONTEXT
from custom_components.buderus_wps.sensor import BuderusMixedCircuitSensor
from custom_components.buderus_wps.switch import BuderusRoomSensorAcknowledgedSwitch


class TestParameterMapping:
    """Slot n = mixed circuit n+1, at the idx values read from the device."""

    def test_circuits_and_slots(self):
        assert {c: mc.slot for c, mc in MIXED_CIRCUITS.items()} == {2: 1, 3: 2, 4: 3}

    @pytest.mark.parametrize(
        "circuit,expected",
        [
            (
                2,
                {
                    VALUE_ROOM_TEMP_USED: 1862,
                    VALUE_ROOM_SENSOR: 1828,
                    VALUE_SUPPLY_TARGET: 1806,
                },
            ),
            (
                3,
                {
                    VALUE_ROOM_TEMP_USED: 1864,
                    VALUE_ROOM_SENSOR: 1832,
                    VALUE_SUPPLY_TARGET: 1808,
                },
            ),
            (
                4,
                {
                    VALUE_ROOM_TEMP_USED: 1866,
                    VALUE_ROOM_SENSOR: 1836,
                    VALUE_SUPPLY_TARGET: 1810,
                },
            ),
        ],
    )
    def test_param_indices_match_device(self, circuit, expected):
        registry = ParameterRegistry()
        params = MIXED_CIRCUITS[circuit].params
        assert {
            key: registry.get_by_name(name).idx for key, name in params.items()
        } == expected

    def test_ack_bitmask_index(self):
        assert ParameterRegistry().get_by_name(ROOM_SENSOR_ACK_PARAM).idx == 1826


class TestBitmask:
    def test_bits_match_observed_masks(self):
        # Observed: C2+C3 acknowledged = 0x0006; C4 added = 0x000E.
        assert [is_acknowledged(0x0006, c) for c in (2, 3, 4)] == [True, True, False]
        assert [is_acknowledged(0x000E, c) for c in (2, 3, 4)] == [True, True, True]

    def test_none_mask_is_unknown(self):
        assert is_acknowledged(None, 4) is None

    def test_set_and_clear_touch_only_own_bit(self):
        assert with_acknowledged(0x0006, 4, True) == 0x000E
        assert with_acknowledged(0x000E, 4, False) == 0x0006
        assert with_acknowledged(0x00F6, 3, False) == 0x00F2
        assert with_acknowledged(0x000E, 4, True) == 0x000E

    @pytest.mark.parametrize(
        "raw,expected",
        [(6, 6), (14, 14), (None, None), (True, None), ("x", None), (-1, None)],
    )
    def test_decode_bitmask(self, raw, expected):
        assert decode_bitmask(raw) == expected


class TestDecodeTemperature:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            (241, 24.1),
            (200, 20.0),
            (163, 16.3),
            (None, None),
            (True, None),
            (65526, None),
        ],
    )
    def test_decode(self, raw, expected):
        assert decode_temperature(raw) == expected


class TestRawWrite:
    def _client(self):
        adapter = MagicMock()
        adapter.timeout = 2.0
        return HeatPumpClient(adapter, ParameterRegistry()), adapter

    def test_generic_write_refuses_bitmask(self):
        client, _ = self._client()
        with pytest.raises(PermissionError):
            client.write_value(ROOM_SENSOR_ACK_PARAM, 14)

    def test_raw_write_frame(self):
        client, adapter = self._client()
        client.write_raw_value(ROOM_SENSOR_ACK_PARAM, 0x000E)
        msg = adapter.send_frame.call_args[0][0]
        assert msg.arbitration_id == 0x04003FE0 | (1826 << 14)
        assert msg.data == bytes.fromhex("000e")
        assert msg.is_extended_id is True

    @pytest.mark.parametrize("raw", [-1, 0x10000, 1.5, True])
    def test_raw_write_rejects_bad_values(self, raw):
        client, adapter = self._client()
        with pytest.raises(ValueError):
            client.write_raw_value(ROOM_SENSOR_ACK_PARAM, raw)
        adapter.send_frame.assert_not_called()


class TestCoordinator:
    @pytest.fixture
    def coordinator(self, mock_hass):
        from custom_components.buderus_wps.coordinator import BuderusCoordinator

        coord = BuderusCoordinator(mock_hass, "/dev/ttyACM0", 60)
        coord.hass = mock_hass
        coord._adapter = MagicMock()
        coord._connected = True
        coord._client = MagicMock()
        coord._last_known_good_data = None
        coord.data = None
        coord.async_set_updated_data = MagicMock()
        return coord

    @pytest.fixture(autouse=True)
    def _no_sleep(self, monkeypatch):
        from custom_components.buderus_wps import coordinator as coord_mod

        monkeypatch.setattr(coord_mod, "ROOM_SENSOR_ACK_VERIFY_DELAY", 0)

    def _fake_pump(self, coordinator, mask, accept=True):
        state = {"mask": mask}

        def read(name, *a, **k):
            assert name == ROOM_SENSOR_ACK_PARAM
            return {"decoded": state["mask"]}

        def write(name, raw, *a, **k):
            assert name == ROOM_SENSOR_ACK_PARAM
            if accept:
                state["mask"] = raw

        coordinator._client.read_parameter.side_effect = read
        coordinator._client.write_raw_value.side_effect = write
        return state

    @pytest.mark.asyncio
    async def test_acknowledge_sets_only_circuit_bit(self, coordinator):
        state = self._fake_pump(coordinator, 0x0006)
        await coordinator.async_set_room_sensor_acknowledged(4, True)
        coordinator._client.write_raw_value.assert_called_once_with(
            ROOM_SENSOR_ACK_PARAM, 0x000E
        )
        assert state["mask"] == 0x000E
        coordinator._client.write_value.assert_not_called()

    @pytest.mark.asyncio
    async def test_unacknowledge_clears_only_circuit_bit(self, coordinator):
        self._fake_pump(coordinator, 0x000E)
        await coordinator.async_set_room_sensor_acknowledged(4, False)
        coordinator._client.write_raw_value.assert_called_once_with(
            ROOM_SENSOR_ACK_PARAM, 0x0006
        )

    @pytest.mark.asyncio
    async def test_no_write_when_already_in_state(self, coordinator):
        self._fake_pump(coordinator, 0x000E)
        await coordinator.async_set_room_sensor_acknowledged(3, True)
        coordinator._client.write_raw_value.assert_not_called()

    @pytest.mark.asyncio
    async def test_rejected_write_raises(self, coordinator):
        from custom_components.buderus_wps.coordinator import HomeAssistantError

        self._fake_pump(coordinator, 0x0006, accept=False)
        with pytest.raises(HomeAssistantError, match="did not apply"):
            await coordinator.async_set_room_sensor_acknowledged(4, True)

    @pytest.mark.asyncio
    async def test_updates_data_optimistically(self, coordinator):
        self._fake_pump(coordinator, 0x0006)
        data = MagicMock()
        data.room_sensor_acknowledged = {2: True, 3: True, 4: False}
        coordinator.data = data
        await coordinator.async_set_room_sensor_acknowledged(4, True)
        assert data.room_sensor_acknowledged[4] is True
        coordinator.async_set_updated_data.assert_called_once_with(data)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("circuit", [0, 1, 5])
    async def test_rejects_non_mixed_circuit(self, coordinator, circuit):
        with pytest.raises(ValueError, match="not supported"):
            await coordinator.async_set_room_sensor_acknowledged(circuit, True)
        coordinator._client.write_raw_value.assert_not_called()

    @pytest.mark.asyncio
    async def test_not_connected_raises(self, coordinator):
        from custom_components.buderus_wps.coordinator import HomeAssistantError

        coordinator._connected = False
        with pytest.raises(HomeAssistantError, match="Not connected"):
            await coordinator.async_set_room_sensor_acknowledged(4, True)

    @pytest.mark.asyncio
    async def test_rate_limited(self, coordinator):
        from custom_components.buderus_wps.coordinator import HomeAssistantError

        self._fake_pump(coordinator, 0x0006)
        coordinator._room_sensor_ack_limiter = WriteRateLimiter(
            max_writes=1, window_s=3600
        )
        await coordinator.async_set_room_sensor_acknowledged(4, True)
        with pytest.raises(HomeAssistantError, match="too often"):
            await coordinator.async_set_room_sensor_acknowledged(4, False)

    def test_read_ack_only_when_no_diagnostics_wanted(self, coordinator):
        coordinator._client.read_parameter.side_effect = lambda n: {"decoded": 6}
        ack, values = coordinator._sync_read_mixed_circuits()
        assert ack == {2: True, 3: True, 4: False}
        assert values == {}
        coordinator._client.read_parameter.assert_called_once_with(
            ROOM_SENSOR_ACK_PARAM
        )

    def test_reads_wanted_diagnostics(self, coordinator):
        reads = {
            ROOM_SENSOR_ACK_PARAM: 6,
            "MV_T5_ATTENUATED_3": 200,
            "MV_T5_ACTUAL_3": None,  # 0xDEAD decodes to None
            "MV_T1_SETPOINT_3": 313,
        }
        coordinator._client.read_parameter.side_effect = lambda n: {"decoded": reads[n]}
        coordinator._wanted_mixed_values = {
            (4, VALUE_ROOM_TEMP_USED),
            (4, VALUE_ROOM_SENSOR),
            (4, VALUE_SUPPLY_TARGET),
        }
        _ack, values = coordinator._sync_read_mixed_circuits()
        assert values == {
            4: {
                VALUE_ROOM_TEMP_USED: 20.0,
                VALUE_ROOM_SENSOR: None,
                VALUE_SUPPLY_TARGET: 31.3,
            }
        }

    def test_read_failure_keeps_last_known_values(self, coordinator):
        prev = MagicMock()
        prev.room_sensor_acknowledged = {2: True, 3: True, 4: True}
        prev.mixed_circuit_values = {4: {VALUE_ROOM_TEMP_USED: 24.1}}
        coordinator._last_known_good_data = prev
        coordinator._wanted_mixed_values = {(4, VALUE_ROOM_TEMP_USED)}
        coordinator._client.read_parameter.side_effect = TimeoutError("no answer")
        ack, values = coordinator._sync_read_mixed_circuits()
        assert ack == {2: True, 3: True, 4: True}
        assert values == {4: {VALUE_ROOM_TEMP_USED: 24.1}}

    def test_wanted_values_from_listener_contexts(self, coordinator):
        coordinator.async_contexts = lambda: iter(
            [None, (MIXED_CIRCUIT_CONTEXT, 4, VALUE_ROOM_TEMP_USED), ("other", 1, 2)]
        )
        assert coordinator._collect_wanted_mixed_values() == {(4, VALUE_ROOM_TEMP_USED)}


class TestSwitch:
    def test_state_from_bitmask(self, mock_coordinator):
        assert BuderusRoomSensorAcknowledgedSwitch(mock_coordinator, 3).is_on is True
        assert BuderusRoomSensorAcknowledgedSwitch(mock_coordinator, 4).is_on is False

    def test_unknown_when_disconnected(self, mock_coordinator_disconnected):
        switch = BuderusRoomSensorAcknowledgedSwitch(mock_coordinator_disconnected, 4)
        assert switch.is_on is None

    def test_identity(self, mock_coordinator):
        switch = BuderusRoomSensorAcknowledgedSwitch(mock_coordinator, 4)
        assert switch._attr_unique_id.endswith("_room_sensor_acknowledged_c4")
        assert switch._attr_name == "Room Sensor Acknowledged C4"

    @pytest.mark.asyncio
    async def test_turn_on_off(self, mock_coordinator):
        switch = BuderusRoomSensorAcknowledgedSwitch(mock_coordinator, 4)
        await switch.async_turn_on()
        await switch.async_turn_off()
        calls = mock_coordinator.async_set_room_sensor_acknowledged.call_args_list
        assert [c.args for c in calls] == [(4, True), (4, False)]

    @pytest.mark.asyncio
    async def test_setup_adds_switch_per_mixed_circuit(self, mock_coordinator):
        entry = MagicMock()
        entry.entry_id = "e1"
        hass = MagicMock()
        hass.data = {DOMAIN: {"e1": {"coordinator": mock_coordinator}}}
        added: list = []
        await switch_platform.async_setup_entry(hass, entry, added.extend)
        circuits = sorted(
            s.circuit
            for s in added
            if isinstance(s, BuderusRoomSensorAcknowledgedSwitch)
        )
        assert circuits == [2, 3, 4]


class TestDiagnosticSensors:
    def test_values(self, mock_coordinator):
        mock_coordinator.data.mixed_circuit_values = {
            4: {VALUE_ROOM_TEMP_USED: 20.0, VALUE_SUPPLY_TARGET: 31.3}
        }
        used = BuderusMixedCircuitSensor(mock_coordinator, 4, VALUE_ROOM_TEMP_USED)
        target = BuderusMixedCircuitSensor(mock_coordinator, 4, VALUE_SUPPLY_TARGET)
        assert used.native_value == 20.0
        assert target.native_value == 31.3

    def test_dead_room_sensor_is_unavailable(self, mock_coordinator):
        mock_coordinator.data.mixed_circuit_values = {4: {VALUE_ROOM_SENSOR: None}}
        sensor = BuderusMixedCircuitSensor(mock_coordinator, 4, VALUE_ROOM_SENSOR)
        assert sensor.available is False

    def test_room_sensor_available_with_value(self, mock_coordinator):
        mock_coordinator.data.mixed_circuit_values = {3: {VALUE_ROOM_SENSOR: 21.8}}
        sensor = BuderusMixedCircuitSensor(mock_coordinator, 3, VALUE_ROOM_SENSOR)
        assert sensor.available is True
        assert sensor.native_value == 21.8

    def test_not_yet_read_is_available_but_unknown(self, mock_coordinator):
        sensor = BuderusMixedCircuitSensor(mock_coordinator, 2, VALUE_ROOM_SENSOR)
        assert sensor.available is True
        assert sensor.native_value is None

    def test_disabled_by_default_and_registers_context(self, mock_coordinator):
        sensor = BuderusMixedCircuitSensor(mock_coordinator, 4, VALUE_ROOM_TEMP_USED)
        assert sensor._attr_entity_registry_enabled_default is False
        assert sensor._attr_unique_id.endswith("_room_temp_used_c4")
        assert sensor._attr_name == "Room Temperature Used By Pump C4"

    @pytest.mark.asyncio
    async def test_setup_adds_three_per_mixed_circuit(self, mock_coordinator):
        mock_coordinator.parameter_allowlist = []
        entry = MagicMock()
        entry.entry_id = "e1"
        hass = MagicMock()
        hass.data = {DOMAIN: {"e1": {"coordinator": mock_coordinator}}}
        added: list = []
        await sensor_platform.async_setup_entry(hass, entry, added.extend)
        keys = sorted(
            (s.circuit, s.value_key)
            for s in added
            if isinstance(s, BuderusMixedCircuitSensor)
        )
        assert len(keys) == 9
        assert {c for c, _ in keys} == {2, 3, 4}
