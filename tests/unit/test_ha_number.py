"""Unit tests for Home Assistant number entities."""

from __future__ import annotations

import pytest
from homeassistant.components.number import NumberMode

# conftest.py sets up HA mocks before we import
from custom_components.buderus_wps.number import BuderusDHWExtraDurationNumber


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
        """DHW extra duration max value must be 24."""
        number = BuderusDHWExtraDurationNumber(mock_coordinator)
        assert number._attr_native_max_value == 24

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

    def test_number_returns_none_when_disconnected(
        self, mock_coordinator_disconnected
    ):
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
