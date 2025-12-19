"""Hardware-in-loop cross-validation tests.

These tests compare CAN bus readings with independent Home Assistant sensors
to validate data accuracy.

Requirements:
- Physical heat pump connected via USBtin at /dev/ttyACM0
- Home Assistant running with independent sensors configured
- HA long-lived access token in HA_TOKEN environment variable

Usage:
    HA_TOKEN=<your_token> pytest tests/hil/test_cross_validation.py -v
"""

import json
import os
import subprocess
import pytest
import requests
from typing import Optional, Tuple


# Skip all tests if not on HA hardware
pytestmark = pytest.mark.skipif(
    not os.path.exists("/dev/ttyACM0"),
    reason="Requires physical heat pump connection"
)


HA_URL = os.environ.get("HA_URL", "http://localhost:8123")
HA_TOKEN = os.environ.get("HA_TOKEN", "")


def get_ha_sensor_value(entity_id: str) -> Optional[float]:
    """Fetch sensor value from Home Assistant REST API.

    Args:
        entity_id: Full entity ID (e.g., sensor.boiler_temp_hot_water_boiler_temp)

    Returns:
        Sensor value as float, or None if unavailable
    """
    if not HA_TOKEN:
        pytest.skip("HA_TOKEN environment variable not set")

    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(
            f"{HA_URL}/api/states/{entity_id}",
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            state = data.get("state")
            if state and state not in ("unavailable", "unknown"):
                return float(state)
    except Exception as e:
        pytest.skip(f"Failed to fetch HA sensor: {e}")

    return None


def get_can_broadcast_temp(param_name: str, duration: float = 8.0) -> Optional[Tuple[float, str]]:
    """Read temperature from CAN bus broadcast.

    Args:
        param_name: Parameter name to look for (e.g., GT8_TEMP)
        duration: How long to monitor broadcast traffic

    Returns:
        Tuple of (temperature, raw_hex) or None if not found
    """
    result = subprocess.run(
        [
            "python", "buderus_wps_cli/main.py",
            "--timeout", "10",
            "monitor",
            "--duration", str(duration),
            "--temps-only",
            "--json"
        ],
        capture_output=True,
        text=True,
        cwd="/workspaces/buderus-wps-ha" if os.path.exists("/workspaces") else ".",
        env={**os.environ, "PYTHONPATH": "."}
    )

    if result.returncode != 0:
        return None

    # Parse JSON output (skip "Monitoring..." line)
    for line in result.stdout.split("\n"):
        if line.startswith("{"):
            data = json.loads(line)
            for reading in data.get("readings", []):
                if reading.get("name") == param_name:
                    return (reading["temperature"], reading["raw_hex"])

    return None


class TestHotWaterTemperatureCrossValidation:
    """Cross-validate hot water temperature between CAN and HA sensor."""

    # Tolerance in degrees Celsius for validation
    TEMP_TOLERANCE = 5.0  # Allow 5°C difference due to sensor placement

    def test_dhw_temp_matches_ha_sensor(self):
        """Compare DHW temperature from CAN bus with HA independent sensor.

        GT9_TEMP is the hot water (DHW) tank temperature sensor broadcast.
        sensor.boiler_temp_hot_water_boiler_temp is an independent HA sensor.

        Due to different sensor placements, a tolerance of ±5°C is allowed.
        """
        # Try GT9_TEMP first (more commonly broadcast), then GT8_TEMP
        can_result = get_can_broadcast_temp("GT9_TEMP", duration=15.0)

        if can_result is None:
            can_result = get_can_broadcast_temp("GT8_TEMP", duration=10.0)

        if can_result is None:
            pytest.skip("GT9_TEMP/GT8_TEMP not found in broadcast traffic")

        can_temp, raw_hex = can_result
        print(f"\nCAN DHW Temp: {can_temp}°C (raw: 0x{raw_hex})")

        # Get HA sensor reading
        ha_temp = get_ha_sensor_value("sensor.boiler_temp_hot_water_boiler_temp")

        if ha_temp is None:
            pytest.skip("HA sensor unavailable")

        print(f"HA sensor: {ha_temp}°C")

        # Compare values
        diff = abs(can_temp - ha_temp)
        print(f"Difference: {diff}°C (tolerance: ±{self.TEMP_TOLERANCE}°C)")

        assert diff <= self.TEMP_TOLERANCE, (
            f"Temperature mismatch: CAN={can_temp}°C, HA={ha_temp}°C, "
            f"diff={diff}°C exceeds tolerance of {self.TEMP_TOLERANCE}°C"
        )

        print(f"✓ Cross-validation PASSED: CAN {can_temp}°C ≈ HA {ha_temp}°C")


class TestOutdoorTemperatureCrossValidation:
    """Cross-validate outdoor temperature if HA sensor available."""

    TEMP_TOLERANCE = 3.0  # Outdoor sensors should be closer

    def test_outdoor_temp_matches_ha_sensor(self):
        """Compare OUTDOOR_TEMP from CAN with HA outdoor sensor."""
        can_result = get_can_broadcast_temp("OUTDOOR_TEMP_C1", duration=10.0)

        if can_result is None:
            # Try alternative names
            can_result = get_can_broadcast_temp("OUTDOOR_TEMP_C3", duration=5.0)

        if can_result is None:
            pytest.skip("Outdoor temp not found in broadcast")

        can_temp, raw_hex = can_result
        print(f"\nCAN Outdoor: {can_temp}°C (raw: 0x{raw_hex})")

        # Try common HA outdoor sensor entity IDs
        ha_temp = None
        for entity_id in [
            "sensor.outdoor_temperature",
            "sensor.outside_temperature",
            "weather.home",  # Weather entity has temperature attribute
        ]:
            ha_temp = get_ha_sensor_value(entity_id)
            if ha_temp is not None:
                break

        if ha_temp is None:
            pytest.skip("No HA outdoor sensor configured")

        print(f"HA outdoor: {ha_temp}°C")

        diff = abs(can_temp - ha_temp)
        print(f"Difference: {diff}°C")

        assert diff <= self.TEMP_TOLERANCE, (
            f"Outdoor temp mismatch: CAN={can_temp}°C, HA={ha_temp}°C"
        )


class TestBroadcastDataIntegrity:
    """Test that broadcast data is internally consistent."""

    def test_temperature_readings_are_plausible(self):
        """Verify all temperature readings are within plausible ranges."""
        result = subprocess.run(
            [
                "python", "buderus_wps_cli/main.py",
                "--timeout", "10",
                "monitor",
                "--duration", "5",
                "--temps-only",
                "--json"
            ],
            capture_output=True,
            text=True,
            cwd="/workspaces/buderus-wps-ha" if os.path.exists("/workspaces") else ".",
            env={**os.environ, "PYTHONPATH": "."}
        )

        assert result.returncode == 0, f"Monitor failed: {result.stderr}"

        # Parse readings
        for line in result.stdout.split("\n"):
            if line.startswith("{"):
                data = json.loads(line)
                readings = data.get("readings", [])

                assert len(readings) > 0, "No broadcast readings captured"

                for reading in readings:
                    temp = reading["temperature"]
                    name = reading.get("name") or f"idx={reading['idx']}"

                    # All temperatures should be within -50°C to +120°C
                    assert -50 <= temp <= 120, (
                        f"Implausible temperature for {name}: {temp}°C"
                    )

                print(f"✓ All {len(readings)} temperature readings are plausible")
                return

        pytest.fail("No JSON output from monitor command")
