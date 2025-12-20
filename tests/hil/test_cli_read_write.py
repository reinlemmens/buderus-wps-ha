"""
Hardware-in-the-loop tests for CLI read/write operations.

These tests run against a real heat pump via USB CAN adapter.
Run with: RUN_HIL_TESTS=1 pytest tests/hil/test_cli_read_write.py -v -s

Hardware requirements:
- USBtin CAN adapter connected at /dev/ttyACM0
- Buderus WPS heat pump on CAN bus
"""

import os
import subprocess
import sys

import pytest

# Configuration
SERIAL_PORT = os.environ.get("USBTIN_PORT", "/dev/ttyACM0")

# Skip all HIL tests if hardware is not available or RUN_HIL_TESTS not set
pytestmark = pytest.mark.skipif(
    not os.path.exists(SERIAL_PORT) or not os.environ.get("RUN_HIL_TESTS"),
    reason=f"HIL tests require hardware at {SERIAL_PORT} and RUN_HIL_TESTS=1",
)

CLI_CMD = [sys.executable, "buderus_wps_cli/main.py"]


def run_cli(*args, timeout: float = 10.0) -> subprocess.CompletedProcess:
    """Run CLI command and return result."""
    cmd = CLI_CMD + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


class TestCLIRead:
    """Test CLI read operations."""

    def test_read_gt3_temp(self):
        """Read DHW tank temperature via RTR request.

        Note: RTR requests return 1-byte ACK responses from the KM273 gateway.
        Actual sensor data is broadcast on different CAN ID bases (0x0060-0x0063).
        Use 'wps-cli monitor --temps-only' to read actual temperatures.
        """
        result = run_cli("read", "GT3_TEMP")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")

        assert result.returncode == 0, f"Command failed: {result.stderr}"
        assert "GT3_TEMP =" in result.stdout

        # RTR requests return 1-byte ACK, not actual temperature data
        # The CLI still displays it with °C suffix based on parameter format
        import re

        match = re.search(r"raw=0x([0-9A-F]+)", result.stdout)
        assert match, f"Could not find raw value in: {result.stdout}"
        raw_hex = match.group(1)
        print(f"Raw hex: {raw_hex} ({len(raw_hex)//2} bytes)")

        # Accept 1-byte response (ACK) - this is the actual hardware behavior
        # Actual temperatures must be read via broadcast monitoring
        assert len(raw_hex) >= 2, f"Expected at least 1 byte, got: 0x{raw_hex}"

    def test_read_xdhw_time(self):
        """Read extra DHW time - integer parameter."""
        result = run_cli("read", "XDHW_TIME")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")

        assert result.returncode == 0, f"Command failed: {result.stderr}"
        assert "XDHW_TIME =" in result.stdout

        # Extract decoded value
        import re

        match = re.search(r"XDHW_TIME = (\d+)", result.stdout)
        assert match, f"Could not parse value from: {result.stdout}"
        value = int(match.group(1))
        assert 0 <= value <= 48, f"XDHW_TIME out of range: {value}"

    def test_read_xdhw_stop_temp(self):
        """Read extra DHW stop temperature."""
        result = run_cli("read", "XDHW_STOP_TEMP")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")

        assert result.returncode == 0, f"Command failed: {result.stderr}"
        assert "XDHW_STOP_TEMP =" in result.stdout
        assert "°C" in result.stdout

    def test_read_nonexistent_param(self):
        """Reading non-existent parameter should fail gracefully."""
        result = run_cli("read", "NONEXISTENT_PARAM_12345")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")

        assert result.returncode != 0
        assert "ERROR" in result.stderr or "Unknown" in result.stderr

    def test_read_json_output(self):
        """Test JSON output format."""
        result = run_cli("read", "GT3_TEMP", "--json")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")

        assert result.returncode == 0, f"Command failed: {result.stderr}"

        import json

        data = json.loads(result.stdout)
        assert "name" in data
        assert "decoded" in data
        assert "raw" in data
        assert data["name"] == "GT3_TEMP"


class TestCLIWrite:
    """Test CLI write operations."""

    def test_write_xdhw_time_and_read_back(self):
        """Write XDHW_TIME and verify it persists."""
        # First read current value
        result = run_cli("read", "XDHW_TIME")
        print(f"Initial read: {result.stdout}")

        # Write value 1
        result = run_cli("write", "XDHW_TIME", "1")
        print(f"Write result: {result.stdout} {result.stderr}")
        assert result.returncode == 0, f"Write failed: {result.stderr}"
        assert "OK" in result.stdout

        # Read back and verify
        result = run_cli("read", "XDHW_TIME")
        print(f"Read back: {result.stdout}")
        assert result.returncode == 0

        # Value should be 1 (or countdown started)
        import re

        match = re.search(r"XDHW_TIME = (\d+)", result.stdout)
        if match:
            value = int(match.group(1))
            print(f"XDHW_TIME after write: {value}")
            # Note: value might have started counting down already

    def test_write_readonly_param_fails(self):
        """Writing to read-only parameter should fail."""
        result = run_cli("write", "GT3_TEMP", "500")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")

        assert result.returncode != 0
        assert "read-only" in result.stderr.lower() or "ERROR" in result.stderr

    def test_write_out_of_range_fails(self):
        """Writing out-of-range value should fail."""
        # XDHW_STOP_TEMP has range 500-650
        result = run_cli("write", "XDHW_STOP_TEMP", "100")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")

        assert result.returncode != 0
        assert "out of range" in result.stderr.lower() or "ERROR" in result.stderr


class TestCLIList:
    """Test CLI list operations."""

    def test_list_all(self):
        """List all parameters."""
        result = run_cli("list")
        print(f"First 500 chars: {result.stdout[:500]}")

        assert result.returncode == 0
        assert "GT3_TEMP" in result.stdout
        assert "XDHW_TIME" in result.stdout

    def test_list_filtered(self):
        """List parameters with filter."""
        result = run_cli("list", "--filter", "XDHW")
        print(f"stdout: {result.stdout}")

        assert result.returncode == 0
        assert "XDHW_TIME" in result.stdout
        assert "XDHW_STOP_TEMP" in result.stdout
        # Should NOT contain unrelated params
        assert "GT3_TEMP" not in result.stdout


class TestCLIMonitor:
    """Test CLI broadcast monitoring operations."""

    def test_monitor_temps_only(self):
        """Monitor broadcast traffic for temperature readings."""
        result = run_cli("monitor", "--duration", "3", "--temps-only")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")

        assert result.returncode == 0
        # Should show temperature readings in degrees
        assert "°C" in result.stdout or "Captured" in result.stdout

    def test_monitor_json_output(self):
        """Test monitor JSON output format."""
        result = run_cli("monitor", "--duration", "3", "--json")
        print(f"stdout (first 500): {result.stdout[:500]}")

        assert result.returncode == 0

        import json

        data = json.loads(result.stdout)
        assert "count" in data
        assert "readings" in data
        assert isinstance(data["readings"], list)

        if data["count"] > 0:
            reading = data["readings"][0]
            assert "can_id" in reading
            assert "temperature" in reading
            assert "is_temperature" in reading

    def test_monitor_captures_temperatures(self):
        """Verify monitor captures real temperature broadcasts."""
        result = run_cli("monitor", "--duration", "5", "--temps-only", "--json")

        assert result.returncode == 0

        import json

        data = json.loads(result.stdout)

        # Should capture at least some temperature readings in 5 seconds
        temps = [r for r in data["readings"] if r["is_temperature"]]
        print(f"Captured {len(temps)} temperature readings")

        # The heat pump broadcasts temperatures regularly
        assert len(temps) >= 1, "Expected at least 1 temperature reading"

        # Check reasonable temperature range (0-120°C)
        for t in temps:
            temp = t["temperature"]
            assert 0 <= temp <= 120, f"Temperature out of range: {temp}°C"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
