"""Unit tests for Home Assistant number entities."""

from __future__ import annotations

import pytest
from homeassistant.components.number import NumberMode

# conftest.py sets up HA mocks before we import
from custom_components.buderus_wps.number import (
    BuderusDHWExtraDurationNumber,
    BuderusDHWSetpointNumber,
)


class TestDHWExtraDurationNumber:
    """Test DHW extra duration number entity."""

    def test_number_has_correct_name(self, mock_coordinator):
        """DHW extra duration must be named 'DHW Extra Duration'."""
        number = BuderusDHWExtraDurationNumber(mock_coordinator)
        assert number._attr_name == "DHW Extra Duration"

    def test_number_has_correct_icon(self, mock_coordinator):
        """DHW extra duration must have water-boiler icon."""
        number = BuderusDHWExtraDurationNumber(mock_coordinator)
        assert number._attr_icon == "mdi:water-boiler"

    def test_number_has_correct_min_value(self, mock_coordinator):
        """DHW extra duration min value must be 0."""
        number = BuderusDHWExtraDurationNumber(mock_coordinator)
        assert number._attr_native_min_value == 0

    def test_number_has_correct_max_value(self, mock_coordinator):
        """DHW extra duration max value must be 48."""
        number = BuderusDHWExtraDurationNumber(mock_coordinator)
        assert number._attr_native_max_value == 48

    def test_number_has_correct_step(self, mock_coordinator):
        """DHW extra duration step must be 1."""
        number = BuderusDHWExtraDurationNumber(mock_coordinator)
        assert number._attr_native_step == 1

    def test_number_has_correct_unit(self, mock_coordinator):
        """DHW extra duration must use hours unit."""
        number = BuderusDHWExtraDurationNumber(mock_coordinator)
        assert number._attr_native_unit_of_measurement == "h"

    def test_number_has_box_mode(self, mock_coordinator):
        """DHW extra duration must use box mode for direct value input."""
        number = BuderusDHWExtraDurationNumber(mock_coordinator)
        assert number._attr_mode == NumberMode.BOX

    def test_number_returns_current_duration(self, mock_coordinator):
        """Number returns current DHW extra duration from coordinator."""
        mock_coordinator.data.dhw_extra_duration = 5
        number = BuderusDHWExtraDurationNumber(mock_coordinator)
        assert number.native_value == 5

    def test_number_returns_zero_when_not_active(self, mock_coordinator):
        """Number returns 0 when DHW extra is not active."""
        mock_coordinator.data.dhw_extra_duration = 0
        number = BuderusDHWExtraDurationNumber(mock_coordinator)
        assert number.native_value == 0

    def test_number_returns_none_when_disconnected(self, mock_coordinator_disconnected):
        """Number returns None when coordinator has no data."""
        number = BuderusDHWExtraDurationNumber(mock_coordinator_disconnected)
        assert number.native_value is None

    def test_number_entity_key(self, mock_coordinator):
        """Number must use correct entity key for unique ID."""
        number = BuderusDHWExtraDurationNumber(mock_coordinator)
        assert number.entity_key == "dhw_extra_duration"

    @pytest.mark.asyncio
    async def test_set_value_calls_coordinator(self, mock_coordinator):
        """Setting value should call coordinator.async_set_dhw_extra_duration."""
        number = BuderusDHWExtraDurationNumber(mock_coordinator)
        await number.async_set_native_value(8)

        mock_coordinator.async_set_dhw_extra_duration.assert_called_once_with(8)
        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_zero_stops_production(self, mock_coordinator):
        """Setting 0 should call coordinator to stop production."""
        number = BuderusDHWExtraDurationNumber(mock_coordinator)
        await number.async_set_native_value(0)

        mock_coordinator.async_set_dhw_extra_duration.assert_called_once_with(0)


class TestDHWSetpointNumber:
    """Test DHW setpoint temperature number entity."""

    def test_number_has_correct_name(self, mock_coordinator):
        """DHW setpoint must be named 'DHW Setpoint Temperature'."""
        number = BuderusDHWSetpointNumber(mock_coordinator)
        assert number._attr_name == "DHW Setpoint Temperature"

    def test_number_has_correct_icon(self, mock_coordinator):
        """DHW setpoint must have water-thermometer icon."""
        number = BuderusDHWSetpointNumber(mock_coordinator)
        assert number._attr_icon == "mdi:water-thermometer"

    def test_number_has_correct_min_value(self, mock_coordinator):
        """DHW setpoint min value must be 40.0°C."""
        number = BuderusDHWSetpointNumber(mock_coordinator)
        assert number._attr_native_min_value == 40.0

    def test_number_has_correct_max_value(self, mock_coordinator):
        """DHW setpoint max value must be 70.0°C."""
        number = BuderusDHWSetpointNumber(mock_coordinator)
        assert number._attr_native_max_value == 70.0

    def test_number_has_correct_step(self, mock_coordinator):
        """DHW setpoint step must be 0.5°C."""
        number = BuderusDHWSetpointNumber(mock_coordinator)
        assert number._attr_native_step == 0.5

    def test_number_has_correct_unit(self, mock_coordinator):
        """DHW setpoint must use Celsius unit."""
        from homeassistant.const import UnitOfTemperature

        number = BuderusDHWSetpointNumber(mock_coordinator)
        assert number._attr_native_unit_of_measurement == UnitOfTemperature.CELSIUS

    def test_number_has_box_mode(self, mock_coordinator):
        """DHW setpoint must use box mode for direct value input."""
        number = BuderusDHWSetpointNumber(mock_coordinator)
        assert number._attr_mode == NumberMode.BOX

    def test_number_returns_current_setpoint(self, mock_coordinator):
        """Number returns current DHW setpoint from coordinator."""
        mock_coordinator.data.dhw_setpoint = 55.0
        number = BuderusDHWSetpointNumber(mock_coordinator)
        assert number.native_value == 55.0

    def test_number_returns_none_when_disconnected(self, mock_coordinator_disconnected):
        """Number returns None when coordinator has no data."""
        number = BuderusDHWSetpointNumber(mock_coordinator_disconnected)
        assert number.native_value is None

    def test_number_entity_key(self, mock_coordinator):
        """Number must use correct entity key for unique ID."""
        number = BuderusDHWSetpointNumber(mock_coordinator)
        assert number.entity_key == "dhw_setpoint"

    @pytest.mark.asyncio
    async def test_set_value_calls_coordinator(self, mock_coordinator):
        """Setting value should call coordinator.async_set_dhw_setpoint."""
        number = BuderusDHWSetpointNumber(mock_coordinator)
        await number.async_set_native_value(55.0)

        mock_coordinator.async_set_dhw_setpoint.assert_called_once_with(55.0)
        # Uses optimistic update instead of refresh (consistent with BuderusDHWStopTempNumber)
        mock_coordinator.async_set_updated_data.assert_called_once()


class TestDHWStopMaxTempNumber:
    """Test the writable DHW stop temperature ceiling (idx 440, issue #13)."""

    def test_number_attributes(self, mock_coordinator):
        """Ceiling uses the parameter table's own range (200/640 raw)."""
        from custom_components.buderus_wps.number import (
            BuderusDHWStopMaxTempNumber,
        )

        number = BuderusDHWStopMaxTempNumber(mock_coordinator)
        assert number._attr_name == "DHW Stop Temperature Limit"
        assert number._attr_native_min_value == 20.0
        assert number._attr_native_max_value == 64.0
        assert number._attr_native_step == 0.5
        assert number.entity_key == "dhw_gt8_stop_max_temp"

    def test_number_returns_current_value(self, mock_coordinator):
        """Number returns the ceiling from coordinator data."""
        from custom_components.buderus_wps.number import (
            BuderusDHWStopMaxTempNumber,
        )

        mock_coordinator.data.dhw_gt8_stop_max_temp = 61.0
        number = BuderusDHWStopMaxTempNumber(mock_coordinator)
        assert number.native_value == 61.0

    def test_number_returns_none_when_disconnected(self, mock_coordinator_disconnected):
        """Number returns None when coordinator has no data."""
        from custom_components.buderus_wps.number import (
            BuderusDHWStopMaxTempNumber,
        )

        number = BuderusDHWStopMaxTempNumber(mock_coordinator_disconnected)
        assert number.native_value is None

    @pytest.mark.asyncio
    async def test_set_value_calls_coordinator(self, mock_coordinator):
        """Setting value calls the coordinator setter with optimistic update."""
        from custom_components.buderus_wps.number import (
            BuderusDHWStopMaxTempNumber,
        )

        number = BuderusDHWStopMaxTempNumber(mock_coordinator)
        await number.async_set_native_value(54.0)

        mock_coordinator.async_set_dhw_gt8_stop_max_temp.assert_called_once_with(54.0)
        mock_coordinator.async_set_updated_data.assert_called_once()

    def test_active_stop_temp_has_no_number_entity(self, mock_coordinator):
        """idx 444 is read-only; it must not be exposed as a writable number."""
        from custom_components.buderus_wps import number as number_module

        assert not hasattr(number_module, "BuderusDHWStopTempActiveNumber")


class TestDHWStartTempActiveNumber:
    """Test the active DHW start temperature entity (idx 498, issue #13)."""

    def test_number_attributes(self, mock_coordinator):
        """Active start temp uses the parameter table range (20.0-79.0)."""
        from custom_components.buderus_wps.number import (
            BuderusDHWStartTempActiveNumber,
        )

        number = BuderusDHWStartTempActiveNumber(mock_coordinator)
        assert number._attr_name == "DHW Start Temperature (Active)"
        assert number._attr_native_min_value == 20.0
        assert number._attr_native_max_value == 79.0
        assert number.entity_key == "dhw_user_start_temp"

    def test_number_returns_current_value(self, mock_coordinator):
        """Number returns the active start temperature from coordinator data."""
        from custom_components.buderus_wps.number import (
            BuderusDHWStartTempActiveNumber,
        )

        mock_coordinator.data.dhw_user_start_temp = 45.0
        number = BuderusDHWStartTempActiveNumber(mock_coordinator)
        assert number.native_value == 45.0

    @pytest.mark.asyncio
    async def test_set_value_calls_coordinator(self, mock_coordinator):
        """Setting value calls the coordinator setter with optimistic update."""
        from custom_components.buderus_wps.number import (
            BuderusDHWStartTempActiveNumber,
        )

        number = BuderusDHWStartTempActiveNumber(mock_coordinator)
        await number.async_set_native_value(40.0)

        mock_coordinator.async_set_dhw_user_start_temp.assert_called_once_with(40.0)
        mock_coordinator.async_set_updated_data.assert_called_once()
