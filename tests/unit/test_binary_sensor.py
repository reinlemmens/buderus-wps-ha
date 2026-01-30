"""Unit tests for binary sensors."""

from unittest.mock import MagicMock

from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from custom_components.buderus_wps.binary_sensor import (
    BuderusCompressorSensor,
    BuderusDHWActiveSensor,
    BuderusHeatingActiveSensor,
)


class TestCompressorSensor:
    """Test compressor sensor."""

    def test_sensor_properties(self, mock_coordinator: MagicMock) -> None:
        """Test compressor sensor properties."""
        mock_entry = MagicMock()
        sensor = BuderusCompressorSensor(mock_coordinator, mock_entry)

        assert sensor._attr_device_class is BinarySensorDeviceClass.RUNNING
        assert sensor._attr_name == "Compressor"
        assert sensor.entity_key == "compressor_running"

    def test_state(self, mock_coordinator: MagicMock) -> None:
        """Test is_on reflects data."""
        mock_entry = MagicMock()
        mock_coordinator.data = MagicMock()
        mock_coordinator.data.compressor_running = True

        sensor = BuderusCompressorSensor(mock_coordinator, mock_entry)
        assert sensor.is_on is True


class TestActiveSensors:
    """Test active sensors (DHW and Heating)."""

    def test_dhw_active_properties(self, mock_coordinator: MagicMock) -> None:
        """Test DHW active sensor properties."""
        mock_entry = MagicMock()
        sensor = BuderusDHWActiveSensor(mock_coordinator, mock_entry)

        assert sensor._attr_device_class is BinarySensorDeviceClass.RUNNING
        assert sensor._attr_name == "DHW Active"
        assert sensor._attr_icon == "mdi:water-boiler"
        assert sensor.entity_key == "dhw_active"

    def test_dhw_active_state(self, mock_coordinator: MagicMock) -> None:
        """Test is_on reflects dhw_active."""
        mock_entry = MagicMock()
        mock_coordinator.data = MagicMock()
        mock_coordinator.data.dhw_active = True

        sensor = BuderusDHWActiveSensor(mock_coordinator, mock_entry)
        assert sensor.is_on is True

        mock_coordinator.data.dhw_active = False
        assert sensor.is_on is False

    def test_heating_active_properties(self, mock_coordinator: MagicMock) -> None:
        """Test heating active sensor properties."""
        mock_entry = MagicMock()
        sensor = BuderusHeatingActiveSensor(mock_coordinator, mock_entry)

        assert sensor._attr_device_class is BinarySensorDeviceClass.RUNNING
        assert sensor._attr_name == "Heating Active"
        assert sensor._attr_icon == "mdi:radiator"
        assert sensor.entity_key == "heating_active"

    def test_heating_active_state(self, mock_coordinator: MagicMock) -> None:
        """Test is_on reflects g1_active."""
        mock_entry = MagicMock()
        mock_coordinator.data = MagicMock()
        mock_coordinator.data.g1_active = True

        sensor = BuderusHeatingActiveSensor(mock_coordinator, mock_entry)
        assert sensor.is_on is True

        mock_coordinator.data.g1_active = False
        assert sensor.is_on is False
