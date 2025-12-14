"""MQTT Bridge for Home Assistant Discovery.

This module handles MQTT communication with Home Assistant, publishing
sensor values and control states via MQTT Discovery protocol.
"""

import json
import logging
from typing import Any, Callable

import paho.mqtt.client as mqtt

from .config import AddonConfig
from .entity_config import (
    EntityConfig,
    ALL_ENTITIES,
    TEMPERATURE_SENSORS,
    BINARY_SENSORS,
    get_entity_by_id,
    get_controllable_entities,
)

# Type for command handler callback
CommandHandler = Callable[[EntityConfig, str], None]

logger = logging.getLogger(__name__)

# MQTT Topics
DISCOVERY_PREFIX = "homeassistant"
STATE_PREFIX = "buderus_wps"
AVAILABILITY_TOPIC = f"{STATE_PREFIX}/status"
HA_STATUS_TOPIC = "homeassistant/status"

# Device info for Home Assistant
DEVICE_INFO = {
    "identifiers": ["buderus_wps_addon"],
    "name": "Buderus WPS Heat Pump",
    "manufacturer": "Buderus",
    "model": "WPS",
    "sw_version": "1.0.0",
}


class MQTTBridge:
    """Bridge between heat pump data and Home Assistant via MQTT."""

    def __init__(
        self,
        config: AddonConfig,
        command_handler: CommandHandler | None = None,
    ) -> None:
        """Initialize the MQTT bridge.

        Args:
            config: Add-on configuration
            command_handler: Optional callback for incoming commands
        """
        self.config = config
        self._command_handler = command_handler
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="buderus_wps_addon",
        )
        self._connected = False

        # Set up callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        # Set Last Will and Testament for offline status
        self._client.will_set(
            topic=AVAILABILITY_TOPIC,
            payload="offline",
            qos=1,
            retain=True,
        )

    def connect(self) -> None:
        """Connect to the MQTT broker."""
        logger.info(f"Connecting to MQTT broker: {self.config.mqtt_host}:{self.config.mqtt_port}")

        # Set authentication if provided
        if self.config.mqtt_username and self.config.mqtt_password:
            self._client.username_pw_set(
                self.config.mqtt_username,
                self.config.mqtt_password,
            )
            logger.debug("MQTT authentication configured")

        self._client.connect(
            self.config.mqtt_host,
            self.config.mqtt_port,
            keepalive=60,
        )
        self._client.loop_start()

    def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        logger.info("Disconnecting from MQTT broker")
        self.publish_availability(False)
        self._client.loop_stop()
        self._client.disconnect()

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: Any,
        rc: int | mqtt.ReasonCode,
        properties: Any = None,
    ) -> None:
        """Handle MQTT connection established.

        Args:
            client: MQTT client instance
            userdata: User data
            flags: Connection flags
            rc: Connection result code
            properties: MQTT 5.0 properties (optional)
        """
        if isinstance(rc, mqtt.ReasonCode):
            success = rc == mqtt.ReasonCode(0)
        else:
            success = rc == 0

        if success:
            logger.info("Connected to MQTT broker")
            self._connected = True

            # Subscribe to Home Assistant status for re-discovery
            client.subscribe(HA_STATUS_TOPIC)
            logger.debug(f"Subscribed to {HA_STATUS_TOPIC}")

            # Subscribe to command topics for controllable entities
            self._subscribe_to_command_topics(client)

            # Publish discovery and availability
            self.publish_discovery()
            self.publish_availability(True)
        else:
            logger.error(f"MQTT connection failed with code: {rc}")
            self._connected = False

    def _subscribe_to_command_topics(self, client: mqtt.Client) -> None:
        """Subscribe to command topics for all controllable entities.

        Args:
            client: MQTT client instance
        """
        controllable = get_controllable_entities()
        for entity in controllable:
            if entity.command_topic:
                client.subscribe(entity.command_topic)
                logger.debug(f"Subscribed to command topic: {entity.command_topic}")

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        rc: int | mqtt.ReasonCode | None = None,
        properties: Any = None,
    ) -> None:
        """Handle MQTT disconnection.

        Args:
            client: MQTT client instance
            userdata: User data
            rc: Disconnection reason code
            properties: MQTT 5.0 properties (optional)
        """
        logger.warning(f"Disconnected from MQTT broker: {rc}")
        self._connected = False

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        msg: mqtt.MQTTMessage,
    ) -> None:
        """Handle incoming MQTT messages.

        Args:
            client: MQTT client instance
            userdata: User data
            msg: MQTT message
        """
        topic = msg.topic
        payload = msg.payload.decode("utf-8")

        logger.debug(f"Received message on {topic}: {payload}")

        # Handle Home Assistant restart
        if topic == HA_STATUS_TOPIC and payload == "online":
            logger.info("Home Assistant came online, re-publishing discovery")
            self.publish_discovery()
            self.publish_availability(True)
            return

        # Handle command messages
        if topic.endswith("/set"):
            self._handle_command(topic, payload)

    def _handle_command(self, topic: str, payload: str) -> None:
        """Handle a command message from Home Assistant.

        Args:
            topic: The command topic (e.g., buderus_wps/switch/holiday_mode/set)
            payload: The command payload (e.g., "ON", "OFF", "Automatic")
        """
        # Parse entity_id from topic: buderus_wps/{type}/{entity_id}/set
        parts = topic.split("/")
        if len(parts) < 4:
            logger.warning(f"Invalid command topic format: {topic}")
            return

        entity_id = parts[2]  # e.g., "holiday_mode"

        # Find the entity
        entity = get_entity_by_id(entity_id)
        if not entity:
            logger.warning(f"Unknown entity in command: {entity_id}")
            return

        logger.info(f"Received command for {entity_id}: {payload}")

        # Call the command handler if registered
        if self._command_handler:
            try:
                self._command_handler(entity, payload)
            except Exception as e:
                logger.error(f"Command handler failed: {e}")
        else:
            logger.warning("No command handler registered")

    def set_command_handler(self, handler: CommandHandler) -> None:
        """Set the command handler callback.

        Args:
            handler: Callback function that receives (entity, value)
        """
        self._command_handler = handler

    def publish_discovery(self) -> None:
        """Publish MQTT Discovery messages for all entities."""
        logger.info("Publishing MQTT Discovery configurations")

        for entity in ALL_ENTITIES:
            self._publish_entity_discovery(entity)

    def _publish_entity_discovery(self, entity: EntityConfig) -> None:
        """Publish MQTT Discovery message for a single entity.

        Args:
            entity: Entity configuration
        """
        # Build discovery topic
        topic = f"{DISCOVERY_PREFIX}/{entity.entity_type}/{STATE_PREFIX}/{entity.entity_id}/config"

        # Build discovery payload
        payload = self._build_discovery_payload(entity)

        # Publish with retain
        self._client.publish(
            topic=topic,
            payload=json.dumps(payload),
            qos=1,
            retain=True,
        )
        logger.debug(f"Published discovery for {entity.entity_id}")

    def _build_discovery_payload(self, entity: EntityConfig) -> dict[str, Any]:
        """Build MQTT Discovery payload for an entity.

        Args:
            entity: Entity configuration

        Returns:
            Discovery payload dictionary
        """
        state_topic = f"{STATE_PREFIX}/{entity.entity_type}/{entity.entity_id}/state"

        payload: dict[str, Any] = {
            "name": entity.name,
            "unique_id": f"buderus_wps_{entity.entity_id}",
            "object_id": f"buderus_wps_{entity.entity_id}",
            "state_topic": state_topic,
            "availability_topic": AVAILABILITY_TOPIC,
            "device": DEVICE_INFO,
        }

        # Add entity-type-specific fields
        if entity.entity_type == "sensor":
            if entity.device_class:
                payload["device_class"] = entity.device_class
            if entity.unit:
                payload["unit_of_measurement"] = entity.unit
            if entity.state_class:
                payload["state_class"] = entity.state_class

        elif entity.entity_type == "binary_sensor":
            if entity.device_class:
                payload["device_class"] = entity.device_class
            payload["payload_on"] = "ON"
            payload["payload_off"] = "OFF"

        elif entity.entity_type == "select":
            if entity.options:
                payload["options"] = entity.options
            payload["command_topic"] = f"{STATE_PREFIX}/{entity.entity_type}/{entity.entity_id}/set"

        elif entity.entity_type == "switch":
            payload["command_topic"] = f"{STATE_PREFIX}/{entity.entity_type}/{entity.entity_id}/set"
            payload["payload_on"] = "ON"
            payload["payload_off"] = "OFF"

        elif entity.entity_type == "number":
            payload["command_topic"] = f"{STATE_PREFIX}/{entity.entity_type}/{entity.entity_id}/set"
            if entity.min_value is not None:
                payload["min"] = entity.min_value
            if entity.max_value is not None:
                payload["max"] = entity.max_value
            if entity.step is not None:
                payload["step"] = entity.step
            if entity.unit:
                payload["unit_of_measurement"] = entity.unit
            payload["mode"] = "slider"

        return payload

    def publish_state(self, entity_id: str, value: Any) -> None:
        """Publish a state value for an entity.

        Args:
            entity_id: Entity identifier
            value: State value to publish
        """
        entity = get_entity_by_id(entity_id)
        if not entity:
            logger.warning(f"Unknown entity: {entity_id}")
            return

        state_topic = f"{STATE_PREFIX}/{entity.entity_type}/{entity_id}/state"

        # Format value based on entity type
        if entity.entity_type == "binary_sensor":
            payload = "ON" if value else "OFF"
        elif entity.entity_type == "switch":
            payload = "ON" if value else "OFF"
        elif isinstance(value, float):
            payload = f"{value:.1f}"
        else:
            payload = str(value)

        self._client.publish(
            topic=state_topic,
            payload=payload,
            qos=0,
            retain=False,
        )
        logger.debug(f"Published state for {entity_id}: {payload}")

    def publish_availability(self, online: bool) -> None:
        """Publish availability status.

        Args:
            online: True if online, False if offline
        """
        payload = "online" if online else "offline"
        self._client.publish(
            topic=AVAILABILITY_TOPIC,
            payload=payload,
            qos=1,
            retain=True,
        )
        logger.info(f"Published availability: {payload}")

    @property
    def connected(self) -> bool:
        """Check if connected to MQTT broker."""
        return self._connected
