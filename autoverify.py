#!/usr/bin/env python3
"""
Autonomous verification script for Buderus WPS Heat Pump integration.
Imitates the requested autonomous skill by directly interacting with the local library.
"""
import logging
import sys
import time

# Setup path to import local library
# Point to integration folder so we can import 'buderus_wps' (the inner library) directly
sys.path.append("/config/custom_components/buderus_wps")

# Mock homeassistant structure
import types
from unittest.mock import MagicMock

# Create homeassistant package
ha = types.ModuleType("homeassistant")
ha.__path__ = []
sys.modules["homeassistant"] = ha

# Mock submodules
sys.modules["homeassistant.config_entries"] = MagicMock()
sys.modules["homeassistant.const"] = MagicMock()
sys.modules["homeassistant.core"] = MagicMock()
sys.modules["homeassistant.exceptions"] = MagicMock()
sys.modules["homeassistant.helpers"] = MagicMock()
sys.modules["homeassistant.helpers.config_validation"] = MagicMock()
sys.modules["homeassistant.helpers.entity"] = MagicMock()
sys.modules["homeassistant.helpers.update_coordinator"] = MagicMock()
sys.modules["homeassistant.components"] = MagicMock()

# Mock exceptions
class HomeAssistantError(Exception): pass
sys.modules["homeassistant.exceptions"].HomeAssistantError = HomeAssistantError

# Mock external deps
sys.modules["voluptuous"] = MagicMock()

from buderus_wps.can_adapter import USBtinAdapter
from buderus_wps.energy_blocking import EnergyBlockingControl
from buderus_wps.heat_pump import HeatPump, HeatPumpClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
_LOGGER = logging.getLogger("autoverify")

PORT = "/dev/ttyACM0"  # Check your actual port

def verify_compressor_detection(client: HeatPumpClient):
    _LOGGER.info("--- Reading Sensors ---")

    # 1. Read COMPRESSOR_STATE (RTR)
    try:
        res = client.read_parameter("COMPRESSOR_STATE")
        _LOGGER.info(f"COMPRESSOR_STATE (RTR): {res}")
    except Exception as e:
        _LOGGER.error(f"Failed to read COMPRESSOR_STATE: {e}")

    # 2. Read HW_COMPRESSOR_CURRENT (Load Sensor) - bypass validation
    try:
        # Check by ID directly (945)
        res = client.read_parameter(945)
        val = res.get("decoded", 0)
        _LOGGER.info(f"HW_COMPRESSOR_CURRENT (Load): {val} (Raw response: {res})")
        return val # Return load value
    except Exception as e:
        _LOGGER.error(f"Failed to read HW_COMPRESSOR_CURRENT: {e}")
        return 0

def monitor_transition(client: HeatPumpClient, blocking: EnergyBlockingControl, condition_label: str, duration: int = 60, poll_interval: float = 2.0):
    """Monitor sensors for a duration or untill a condition is met (conceptually)."""
    _LOGGER.info(f"--- Monitoring for {duration}s: {condition_label} ---")
    end_time = time.time() + duration

    while time.time() < end_time:
        load = verify_compressor_detection(client)
        # We could add logic here to break early if condition met, but observing stability is good too.
        time.sleep(poll_interval)

def main():
    _LOGGER.info("Starting autonomous verification...")

    adapter = USBtinAdapter(PORT)
    try:
        adapter.connect()
        registry = HeatPump()
        client = HeatPumpClient(adapter, registry)
        blocking = EnergyBlockingControl(client)

        # 1. Initial State
        _LOGGER.info("=== STEP 1: Initial State ===")
        verify_compressor_detection(client)

        # 2. Trigger DHW Boost (Set Extra Duration to 1h)
        _LOGGER.info("=== STEP 2: Triggering DHW Boost (1h) ===")
        try:
             # writes to XDHW_TIME (idx varies, usually 2475 or discovered)
             # We use the name to let the client look it up in discovered registry
            client.write_value("XDHW_TIME", 1)
            _LOGGER.info("Set XDHW_TIME to 1h")
        except Exception as e:
            _LOGGER.error(f"Failed to set DHW boost: {e}")

        # 3. Monitor Start (Wait 30s for compressor to ramp up)
        _LOGGER.info("=== STEP 3: Waiting for Compressor Start (30s) ===")
        monitor_transition(client, blocking, "Compressor Start", duration=30)

        # 4. Block Compressor
        _LOGGER.info("=== STEP 4: Blocking Compressor ===")
        res = blocking.block_compressor()
        _LOGGER.info(f"Block result: {res}")

        # 5. Monitor Stop (Wait 30s for compressor to stop)
        _LOGGER.info("=== STEP 5: Waiting for Compressor Stop (30s) ===")
        monitor_transition(client, blocking, "Compressor Stop", duration=30)

        # 6. Unblock and Reset
        _LOGGER.info("=== STEP 6: Unblocking and Resetting ===")
        res = blocking.unblock_compressor()
        _LOGGER.info(f"Unblock result: {res}")

        try:
            client.write_value("XDHW_TIME", 0)
            _LOGGER.info("Reset XDHW_TIME to 0h")
        except Exception as e:
             _LOGGER.error(f"Failed to reset DHW boost: {e}")

        # Final Check
        verify_compressor_detection(client)

    except Exception as e:
        _LOGGER.exception(f"Fatal error: {e}")
    finally:
        if adapter.is_open:
            adapter.disconnect()
            _LOGGER.info("Disconnected.")

if __name__ == "__main__":
    main()
