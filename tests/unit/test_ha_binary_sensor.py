"""Unit tests for Home Assistant binary sensor entities."""

from __future__ import annotations

import pytest

# conftest.py sets up HA mocks before we import
from custom_components.buderus_wps.binary_sensor import BuderusCompressorSensor


class TestCompressorBinarySensor:
    """Test compressor binary sensor entity."""

    def test_compressor_sensor_has_running_device_class(self, mock_coordinator):
        """Compressor sensor must have RUNNING device class."""
        sensor = BuderusCompressorSensor(mock_coordinator)
        assert sensor._attr_device_class == "running"

    def test_compressor_sensor_has_correct_name(self, mock_coordinator):
        """Compressor sensor must be named 'Compressor'."""
        sensor = BuderusCompressorSensor(mock_coordinator)
        assert sensor._attr_name == "Compressor"

    def test_compressor_sensor_returns_true_when_running(self, mock_coordinator):
        """Sensor returns True when compressor is running."""
        mock_coordinator.data.compressor_running = True
        sensor = BuderusCompressorSensor(mock_coordinator)
        assert sensor.is_on is True

    def test_compressor_sensor_returns_false_when_stopped(self, mock_coordinator):
        """Sensor returns False when compressor is stopped."""
        mock_coordinator.data.compressor_running = False
        sensor = BuderusCompressorSensor(mock_coordinator)
        assert sensor.is_on is False

    def test_compressor_sensor_returns_none_when_disconnected(
        self, mock_coordinator_disconnected
    ):
        """Sensor returns None when coordinator has no data."""
        sensor = BuderusCompressorSensor(mock_coordinator_disconnected)
        assert sensor.is_on is None

    def test_compressor_sensor_entity_key(self, mock_coordinator):
        """Sensor must use correct entity key for unique ID."""
        sensor = BuderusCompressorSensor(mock_coordinator)
        assert sensor.entity_key == "compressor_running"
