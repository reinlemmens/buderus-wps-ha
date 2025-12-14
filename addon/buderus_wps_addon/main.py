"""Buderus WPS Add-on main entry point.

This module provides the main service loop for the Home Assistant add-on.
It connects to the heat pump via USB serial (USBtin CAN adapter) and
publishes sensor data to Home Assistant via MQTT Discovery.
"""

import logging
import signal
import sys
import time
from types import FrameType
from typing import Any

from buderus_wps import (
    USBtinAdapter,
    HeatPumpClient,
    BroadcastMonitor,
    MenuAPI,
    get_default_sensor_map,
)

from .config import AddonConfig, load_config
from .mqtt_bridge import MQTTBridge
from .entity_config import (
    EntityConfig,
    TEMPERATURE_SENSORS,
    BINARY_SENSORS,
    map_value_to_option,
)
from .command_queue import CommandQueue, CommandResult, CommandStatus

logger = logging.getLogger(__name__)

# Reconnection settings
INITIAL_RETRY_DELAY = 5.0  # seconds
MAX_RETRY_DELAY = 300.0  # 5 minutes
RETRY_BACKOFF_FACTOR = 2.0

# Broadcast index to entity ID mapping
BROADCAST_SENSOR_MAP: dict[int, str] = {
    12: "outdoor_temp",
    13: "supply_temp",
    14: "return_temp",
    15: "dhw_temp",
    16: "buffer_top_temp",
    17: "buffer_bottom_temp",
}


class BuderusService:
    """Main service class for the Buderus WPS add-on."""

    def __init__(self, config: AddonConfig, mqtt_bridge: MQTTBridge) -> None:
        """Initialize the service with configuration.

        Args:
            config: Add-on configuration from Supervisor
            mqtt_bridge: MQTT bridge for publishing to Home Assistant
        """
        self.config = config
        self.mqtt_bridge = mqtt_bridge
        self.adapter: USBtinAdapter | None = None
        self.client: HeatPumpClient | None = None
        self.broadcast_monitor: BroadcastMonitor | None = None
        self.menu_api: MenuAPI | None = None
        self.command_queue: CommandQueue | None = None
        self._running = False
        self._retry_delay = INITIAL_RETRY_DELAY

        # Register command handler with MQTT bridge
        self.mqtt_bridge.set_command_handler(self._handle_mqtt_command)

    def connect(self) -> bool:
        """Connect to the heat pump via USB serial.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to USB serial device: {self.config.serial_device}")
            self.adapter = USBtinAdapter(port=self.config.serial_device)
            self.adapter.open()
            self.client = HeatPumpClient(self.adapter)

            # Create broadcast monitor for temperature readings
            sensor_map = get_default_sensor_map()
            self.broadcast_monitor = BroadcastMonitor(self.adapter, sensor_map)

            # Create menu API for compressor status
            self.menu_api = MenuAPI(self.adapter)

            # Create command queue for control commands
            self.command_queue = CommandQueue(
                client=self.client,
                menu_api=self.menu_api,
                result_callback=self._on_command_result,
            )

            logger.info("Successfully connected to heat pump via USB serial")
            self._retry_delay = INITIAL_RETRY_DELAY  # Reset on success
            return True
        except FileNotFoundError:
            logger.error(f"Serial device not found: {self.config.serial_device}")
            return False
        except PermissionError:
            logger.error(
                f"Permission denied for serial device: {self.config.serial_device}. "
                "Ensure the device is mapped in add-on configuration."
            )
            return False
        except Exception as e:
            logger.error(f"Failed to connect to heat pump: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from the heat pump."""
        self.broadcast_monitor = None
        self.menu_api = None
        self.command_queue = None
        if self.adapter:
            try:
                self.adapter.close()
                logger.info("Disconnected from heat pump")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self.adapter = None
                self.client = None

    def is_connected(self) -> bool:
        """Check if currently connected to heat pump.

        Returns:
            True if connected, False otherwise
        """
        return self.adapter is not None and self.client is not None

    def reconnect_with_backoff(self) -> bool:
        """Attempt to reconnect with exponential backoff.

        Returns:
            True if reconnection successful, False otherwise
        """
        self.disconnect()

        logger.info(f"Attempting reconnection in {self._retry_delay:.1f} seconds...")
        time.sleep(self._retry_delay)

        if self.connect():
            return True

        # Increase delay for next attempt (exponential backoff)
        self._retry_delay = min(
            self._retry_delay * RETRY_BACKOFF_FACTOR, MAX_RETRY_DELAY
        )
        return False

    def check_connection(self) -> bool:
        """Check if connection is still alive.

        Returns:
            True if connection is healthy, False if disconnected
        """
        if not self.is_connected():
            return False

        try:
            # Try a simple operation to check connection
            # The adapter's serial port should be open
            if self.adapter and hasattr(self.adapter, "_serial"):
                return self.adapter._serial is not None and self.adapter._serial.is_open
        except Exception:
            pass

        return False

    def _handle_mqtt_command(self, entity: EntityConfig, value: str) -> None:
        """Handle a command received from MQTT.

        Args:
            entity: The entity to control
            value: The command value
        """
        if not self.command_queue:
            logger.warning("Command received but no command queue available")
            return

        if self.command_queue.enqueue(entity, value):
            logger.debug(f"Command queued: {entity.entity_id} = {value}")
        else:
            logger.warning(f"Failed to queue command: {entity.entity_id} = {value}")

    def _on_command_result(self, result: CommandResult) -> None:
        """Handle command execution result.

        Args:
            result: The result of command execution
        """
        if result.status == CommandStatus.SUCCESS:
            logger.info(f"Command succeeded: {result.entity_id} = {result.value}")
            # Publish updated state back to HA
            self._publish_control_state(result.entity_id, result.value)
        else:
            logger.warning(f"Command failed: {result.entity_id} - {result.message}")

    def _publish_control_state(self, entity_id: str, value: Any) -> None:
        """Publish control entity state after successful command.

        Args:
            entity_id: The entity ID
            value: The new value
        """
        # For select entities, map value back to option string
        if entity_id in ("heating_season_mode", "dhw_program_mode"):
            option = map_value_to_option(entity_id, int(value))
            if option:
                self.mqtt_bridge.publish_state(entity_id, option)
            return

        # For switch entities, publish ON/OFF
        if entity_id == "holiday_mode":
            self.mqtt_bridge.publish_state(entity_id, bool(value))
            return

        # For number entities, publish the numeric value
        self.mqtt_bridge.publish_state(entity_id, value)

    def poll_and_publish(self) -> None:
        """Poll sensor data and publish to MQTT."""
        if not self.is_connected():
            return

        # Process any pending commands first
        if self.command_queue:
            while self.command_queue.pending_count() > 0:
                self.command_queue.process_one()

        # Poll temperature sensors from broadcast monitor
        if self.broadcast_monitor:
            try:
                # Collect broadcast data for a short period
                readings = self.broadcast_monitor.collect(timeout=5.0)
                for reading in readings:
                    entity_id = BROADCAST_SENSOR_MAP.get(reading.index)
                    if entity_id:
                        self.mqtt_bridge.publish_state(entity_id, reading.value)
                        logger.debug(f"Published {entity_id}: {reading.value}")
            except Exception as e:
                logger.warning(f"Failed to read broadcast data: {e}")

        # Poll compressor status from MenuAPI
        if self.menu_api:
            try:
                status = self.menu_api.status.get_snapshot()
                if status and hasattr(status, "compressor_running"):
                    self.mqtt_bridge.publish_state("compressor", status.compressor_running)
                    logger.debug(f"Published compressor: {status.compressor_running}")
            except Exception as e:
                logger.debug(f"Failed to read compressor status: {e}")

    def run(self) -> None:
        """Run the main service loop."""
        self._running = True
        logger.info("Starting Buderus WPS service...")

        # Connect to MQTT broker
        try:
            self.mqtt_bridge.connect()
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return

        # Initial connection to heat pump
        if not self.connect():
            logger.warning("Initial connection failed, will retry...")
            self.mqtt_bridge.publish_availability(False)
        else:
            self.mqtt_bridge.publish_availability(True)

        while self._running:
            # Check connection and reconnect if needed
            if not self.check_connection():
                self.mqtt_bridge.publish_availability(False)
                if not self.reconnect_with_backoff():
                    continue  # Keep trying
                self.mqtt_bridge.publish_availability(True)

            # Poll sensors and publish to MQTT
            self.poll_and_publish()

            # Wait for next poll interval
            time.sleep(self.config.scan_interval)

    def stop(self) -> None:
        """Stop the service gracefully."""
        logger.info("Stopping Buderus WPS service...")
        self._running = False
        self.disconnect()
        self.mqtt_bridge.disconnect()


# Global service instance for signal handling
_service: BuderusService | None = None


def signal_handler(signum: int, frame: FrameType | None) -> None:
    """Handle shutdown signals gracefully."""
    signal_name = signal.Signals(signum).name
    logger.info(f"Received {signal_name}, initiating shutdown...")
    if _service:
        _service.stop()


def setup_logging(log_level: str) -> None:
    """Configure logging with the specified level.

    Args:
        log_level: Log level string (debug, info, warning, error)
    """
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
    }
    level = level_map.get(log_level.lower(), logging.INFO)

    # Use force=True to reconfigure even if already configured (Python 3.8+)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )


def main() -> int:
    """Main entry point for the add-on service.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    global _service

    # Load configuration
    config = load_config()
    setup_logging(config.log_level)

    logger.info("Buderus WPS Add-on starting...")
    logger.debug(f"Configuration: serial_device={config.serial_device}, "
                 f"mqtt_host={config.mqtt_host}, scan_interval={config.scan_interval}")

    # Validate configuration
    errors = config.validate()
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        return 1

    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Create MQTT bridge
    mqtt_bridge = MQTTBridge(config)

    # Create and run service
    _service = BuderusService(config, mqtt_bridge)

    try:
        _service.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1
    finally:
        if _service:
            _service.stop()

    logger.info("Buderus WPS Add-on stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
