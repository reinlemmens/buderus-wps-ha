import logging
import sys
import time
import types
from unittest.mock import MagicMock

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
_LOGGER = logging.getLogger(__name__)

# Setup path to import local library
# Point to integration folder so we can import 'buderus_wps' (the inner library) directly
sys.path.append("/config/custom_components/buderus_wps")

# Mock homeassistant structure
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

try:
    from buderus_wps.can_adapter import USBtinAdapter
    from buderus_wps.heat_pump import HeatPump, HeatPumpClient
except ImportError as e:
    _LOGGER.error(f"Failed to import buderus_wps modules: {e}")
    _LOGGER.error("Ensure sys.path is correct and pyserial is installed.")
    sys.exit(1)

MONITORED_PARAMS = [
    "EVU_1_ACTIVE",
    "EVU_2_ACTIVE",
    "EVU_3_ACTIVE",
    "HEATING_EXTERN_BLOCKED",
    "ADDITIONAL_TIMER_EVU_ECONOMY_MODE",
    "EVU_1_ACTIVATED_BY_E21_EXT_1",
    "EVU_1_ACTIVATED_BY_E22_EXT_1",
]

def main():
    _LOGGER.info("Starting EVU Sniffer...")

    # 1. Initialize Adapter
    adapter = USBtinAdapter("/dev/ttyACM0")

    try:
        adapter.connect()
        _LOGGER.info("Connected to CAN adapter on /dev/ttyACM0")
    except Exception as e:
        _LOGGER.error(f"Fatal error: {e}")
        return

    client = HeatPumpClient(adapter)

    previous_values = {}

    _LOGGER.info(f"Monitoring parameters: {', '.join(MONITORED_PARAMS)}")
    _LOGGER.info("Keep running... Toggle the EVU contact now!")
    _LOGGER.info("Press Ctrl+C to stop (if interactive) or wait for timeout.")

    start_time = time.time()
    # Run for 120 seconds
    DURATION = 120

    try:
        while time.time() - start_time < DURATION:
            changed = False
            for param_name in MONITORED_PARAMS:
                try:
                    # Try to read
                    res = client.read_parameter(param_name)
                    val = res.get("decoded")

                    # Check for change
                    if param_name not in previous_values:
                        previous_values[param_name] = val
                        _LOGGER.info(f"Initial {param_name}: {val}")
                    elif previous_values[param_name] != val:
                        _LOGGER.info(f"CHANGE DETECTED! {param_name}: {previous_values[param_name]} -> {val}")
                        previous_values[param_name] = val
                        changed = True

                except Exception:
                    # Don't spam logs with read errors per parameter, maybe just debug
                    # _LOGGER.debug(f"Failed to read {param_name}: {e}")
                    pass

            if changed:
                _LOGGER.info("-" * 20)

            time.sleep(1.0)

    except KeyboardInterrupt:
        _LOGGER.info("Stopping...")
    finally:
        adapter.disconnect()
        _LOGGER.info("Disconnected.")

if __name__ == "__main__":
    main()
