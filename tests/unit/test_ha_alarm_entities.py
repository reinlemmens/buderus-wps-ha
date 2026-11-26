"""Entities of the alarm-pending feature (issue #25)."""

from datetime import datetime, timezone

import pytest

from custom_components.buderus_wps.binary_sensor import BuderusAlarmPendingSensor
from custom_components.buderus_wps.sensor import (
    BuderusLastAlarmSensor,
    BuderusSystemStatusSensor,
)


class TestAlarmPending:
    @pytest.mark.parametrize(
        "status,expected", [(4, True), (0, False), (1, False), (3, False), (2, None), (None, None)]
    )
    def test_state(self, mock_coordinator, status, expected):
        mock_coordinator.data.system_status = status
        assert BuderusAlarmPendingSensor(mock_coordinator).is_on is expected

    def test_unknown_when_disconnected(self, mock_coordinator_disconnected):
        assert BuderusAlarmPendingSensor(mock_coordinator_disconnected).is_on is None

    def test_identity(self, mock_coordinator):
        s = BuderusAlarmPendingSensor(mock_coordinator)
        assert s._attr_device_class == "problem"
        assert s._attr_name == "Alarm Pending"
        assert s._attr_unique_id.endswith("_alarm_pending")

    def test_raw_value_attribute(self, mock_coordinator):
        mock_coordinator.data.system_status = 3
        mock_coordinator.get_data_age_seconds.return_value = None
        mock_coordinator._last_successful_update = None
        attrs = BuderusAlarmPendingSensor(mock_coordinator).extra_state_attributes
        assert attrs["system_status"] == 3


class TestLastAlarm:
    def test_value_is_coordinator_last_alarm(self, mock_coordinator):
        when = datetime(2026, 11, 25, 2, 42, tzinfo=timezone.utc)
        mock_coordinator.last_alarm = when
        s = BuderusLastAlarmSensor(mock_coordinator)
        assert s.native_value == when
        assert s._attr_device_class == "timestamp"
        assert s._attr_unique_id.endswith("_last_alarm")

    def test_unknown_until_first_alarm(self, mock_coordinator):
        mock_coordinator.last_alarm = None
        assert BuderusLastAlarmSensor(mock_coordinator).native_value is None

    def test_kept_while_disconnected(self, mock_coordinator_disconnected):
        when = datetime(2026, 11, 25, 2, 42, tzinfo=timezone.utc)
        mock_coordinator_disconnected.last_alarm = when
        assert BuderusLastAlarmSensor(mock_coordinator_disconnected).native_value == when


class TestSystemStatus:
    def test_raw_value(self, mock_coordinator):
        mock_coordinator.data.system_status = 4
        s = BuderusSystemStatusSensor(mock_coordinator)
        assert s.native_value == 4
        assert s._attr_entity_category == "diagnostic"
        assert s._attr_unique_id.endswith("_system_status")

    def test_none_when_disconnected(self, mock_coordinator_disconnected):
        assert BuderusSystemStatusSensor(mock_coordinator_disconnected).native_value is None


async def test_platforms_add_the_entities(mock_hass, mock_coordinator):
    from unittest.mock import MagicMock

    from custom_components.buderus_wps import binary_sensor, sensor
    from custom_components.buderus_wps.const import DOMAIN

    entry = MagicMock(entry_id="entry1")
    mock_coordinator.parameter_allowlist = []
    mock_hass.data = {DOMAIN: {"entry1": {"coordinator": mock_coordinator}}}
    added = []
    await binary_sensor.async_setup_entry(mock_hass, entry, added.extend)
    await sensor.async_setup_entry(mock_hass, entry, added.extend)
    kinds = {type(e) for e in added}
    assert {BuderusAlarmPendingSensor, BuderusLastAlarmSensor, BuderusSystemStatusSensor} <= kinds


async def test_legacy_yaml_platforms_stay_as_they_were(mock_hass, mock_coordinator):
    """Legacy YAML setup keeps its fixed entity set; alarm entities need a config entry."""
    from custom_components.buderus_wps import binary_sensor, sensor
    from custom_components.buderus_wps.const import DOMAIN

    mock_coordinator.parameter_allowlist = []
    mock_hass.data = {DOMAIN: {"coordinator": mock_coordinator}}
    added = []
    info = {"platform": "buderus_wps"}
    await binary_sensor.async_setup_platform(mock_hass, {}, added.extend, info)
    await sensor.async_setup_platform(mock_hass, {}, added.extend, info)
    alarm_kinds = (
        BuderusAlarmPendingSensor,
        BuderusLastAlarmSensor,
        BuderusSystemStatusSensor,
    )
    assert not [e for e in added if isinstance(e, alarm_kinds)]
