"""Command queue for rate-limited heat pump control.

This module provides a queue-based command execution system that ensures
commands are sent to the heat pump with proper rate limiting (500ms minimum
between commands) to prevent CAN bus congestion.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue, Empty
from typing import Any, Callable

from .entity_config import (
    EntityConfig,
    map_option_to_value,
)

logger = logging.getLogger(__name__)

# Rate limiting constants
MIN_COMMAND_DELAY = 0.5  # 500ms minimum between commands
COMMAND_TIMEOUT = 30.0  # Commands expire after 30 seconds


class CommandStatus(Enum):
    """Status of a command execution."""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    INVALID = "invalid"


@dataclass
class Command:
    """A command to be executed on the heat pump."""

    entity: EntityConfig
    value: Any
    timestamp: float = field(default_factory=time.time)


@dataclass
class CommandResult:
    """Result of a command execution."""

    entity_id: str
    status: CommandStatus
    message: str = ""
    value: Any = None


class CommandQueue:
    """Queue for rate-limited command execution.

    Ensures commands are sent to the heat pump with proper spacing
    to prevent CAN bus congestion.
    """

    def __init__(
        self,
        client: Any,
        menu_api: Any = None,
        result_callback: Callable[[CommandResult], None] | None = None,
    ) -> None:
        """Initialize the command queue.

        Args:
            client: HeatPumpClient for parameter read/write
            menu_api: Optional MenuAPI for extra DHW controls
            result_callback: Optional callback for command results
        """
        self.client = client
        self.menu_api = menu_api
        self.result_callback = result_callback
        self._queue: Queue[Command] = Queue()
        self._last_command_time: float = 0

    def pending_count(self) -> int:
        """Return the number of pending commands."""
        return self._queue.qsize()

    def validate_command(
        self, entity: EntityConfig, value: Any
    ) -> tuple[bool, str | None]:
        """Validate a command before enqueueing.

        Args:
            entity: The entity to control
            value: The value to set

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if entity is controllable
        if entity.command_topic is None:
            return False, f"Entity '{entity.entity_id}' is not controllable (read-only)"

        # Validate based on entity type
        if entity.entity_type == "select":
            return self._validate_select(entity, value)
        elif entity.entity_type == "switch":
            return self._validate_switch(entity, value)
        elif entity.entity_type == "number":
            return self._validate_number(entity, value)

        return True, None

    def _validate_select(
        self, entity: EntityConfig, value: Any
    ) -> tuple[bool, str | None]:
        """Validate a select entity command."""
        if entity.options and str(value) not in entity.options:
            return False, f"Invalid option '{value}'. Valid options: {entity.options}"
        return True, None

    def _validate_switch(
        self, entity: EntityConfig, value: Any
    ) -> tuple[bool, str | None]:
        """Validate a switch entity command."""
        if str(value).upper() not in ("ON", "OFF"):
            return False, f"Invalid switch value '{value}'. Must be 'ON' or 'OFF'"
        return True, None

    def _validate_number(
        self, entity: EntityConfig, value: Any
    ) -> tuple[bool, str | None]:
        """Validate a number entity command."""
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            return False, f"Value '{value}' is not a valid number"

        if entity.min_value is not None and num_value < entity.min_value:
            return False, f"Value {num_value} is below minimum {entity.min_value}"

        if entity.max_value is not None and num_value > entity.max_value:
            return False, f"Value {num_value} is above maximum {entity.max_value}"

        return True, None

    def enqueue(self, entity: EntityConfig, value: Any) -> bool:
        """Add a command to the queue.

        Args:
            entity: The entity to control
            value: The value to set

        Returns:
            True if command was enqueued, False if validation failed
        """
        is_valid, error = self.validate_command(entity, value)
        if not is_valid:
            logger.warning(f"Command validation failed: {error}")
            return False

        cmd = Command(entity=entity, value=value)
        self._queue.put(cmd)
        logger.debug(f"Enqueued command: {entity.entity_id} = {value}")
        return True

    def process_one(self) -> CommandResult | None:
        """Process one command from the queue.

        Returns:
            CommandResult if a command was processed, None if queue was empty
        """
        try:
            cmd = self._queue.get_nowait()
        except Empty:
            return None

        result = self._execute_command(cmd)

        if self.result_callback:
            self.result_callback(result)

        return result

    def _execute_command(self, cmd: Command) -> CommandResult:
        """Execute a single command with rate limiting.

        Args:
            cmd: The command to execute

        Returns:
            CommandResult indicating success or failure
        """
        # Check if command has expired
        if time.time() - cmd.timestamp > COMMAND_TIMEOUT:
            logger.warning(f"Command for {cmd.entity.entity_id} expired")
            return CommandResult(
                entity_id=cmd.entity.entity_id,
                status=CommandStatus.TIMEOUT,
                message="Command expired before execution",
            )

        # Apply rate limiting
        self._apply_rate_limit()

        # Route to appropriate handler
        if cmd.entity.use_menu_api:
            return self._execute_menu_api_command(cmd)
        else:
            return self._execute_parameter_command(cmd)

    def _apply_rate_limit(self) -> None:
        """Apply rate limiting between commands."""
        elapsed = time.time() - self._last_command_time
        if elapsed < MIN_COMMAND_DELAY:
            wait_time = MIN_COMMAND_DELAY - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.3f}s")
            time.sleep(wait_time)
        self._last_command_time = time.time()

    def _execute_parameter_command(self, cmd: Command) -> CommandResult:
        """Execute a command via direct parameter write.

        Args:
            cmd: The command to execute

        Returns:
            CommandResult indicating success or failure
        """
        entity = cmd.entity
        value = cmd.value

        try:
            # Convert value based on entity type
            write_value = self._convert_value(entity, value)

            if entity.parameter_name is None:
                return CommandResult(
                    entity_id=entity.entity_id,
                    status=CommandStatus.FAILED,
                    message="No parameter name configured",
                )

            logger.info(
                f"Executing command: {entity.parameter_name} = {write_value}"
            )
            result = self.client.write_parameter(entity.parameter_name, write_value)

            if result:
                return CommandResult(
                    entity_id=entity.entity_id,
                    status=CommandStatus.SUCCESS,
                    message="Command executed successfully",
                    value=write_value,
                )
            else:
                return CommandResult(
                    entity_id=entity.entity_id,
                    status=CommandStatus.FAILED,
                    message="Parameter write returned False",
                )

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return CommandResult(
                entity_id=entity.entity_id,
                status=CommandStatus.FAILED,
                message=str(e),
            )

    def _execute_menu_api_command(self, cmd: Command) -> CommandResult:
        """Execute a command via MenuAPI.

        Args:
            cmd: The command to execute

        Returns:
            CommandResult indicating success or failure
        """
        entity = cmd.entity
        value = cmd.value

        if self.menu_api is None:
            return CommandResult(
                entity_id=entity.entity_id,
                status=CommandStatus.FAILED,
                message="MenuAPI not available",
            )

        try:
            # Handle extra DHW commands
            if entity.entity_id == "extra_dhw_duration":
                duration = int(float(value))
                logger.info(f"Setting extra DHW duration: {duration}h")
                self.menu_api.dhw.set_extra_hot_water(duration=duration)
                return CommandResult(
                    entity_id=entity.entity_id,
                    status=CommandStatus.SUCCESS,
                    message=f"Extra DHW duration set to {duration}h",
                    value=duration,
                )

            elif entity.entity_id == "extra_dhw_target":
                target = float(value)
                logger.info(f"Setting extra DHW target: {target}°C")
                self.menu_api.dhw.set_extra_hot_water(target_temp=target)
                return CommandResult(
                    entity_id=entity.entity_id,
                    status=CommandStatus.SUCCESS,
                    message=f"Extra DHW target set to {target}°C",
                    value=target,
                )

            else:
                return CommandResult(
                    entity_id=entity.entity_id,
                    status=CommandStatus.FAILED,
                    message=f"Unknown MenuAPI entity: {entity.entity_id}",
                )

        except Exception as e:
            logger.error(f"MenuAPI command execution failed: {e}")
            return CommandResult(
                entity_id=entity.entity_id,
                status=CommandStatus.FAILED,
                message=str(e),
            )

    def _convert_value(self, entity: EntityConfig, value: Any) -> int | float:
        """Convert HA value to parameter value.

        Args:
            entity: The entity configuration
            value: The HA value to convert

        Returns:
            The converted value for parameter write
        """
        if entity.entity_type == "switch":
            return 1 if str(value).upper() == "ON" else 0

        if entity.entity_type == "select":
            mapped = map_option_to_value(entity.entity_id, str(value))
            if mapped is not None:
                return mapped
            return int(value)

        if entity.entity_type == "number":
            return float(value)

        return value

    def clear(self) -> None:
        """Clear all pending commands."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except Empty:
                break
        logger.info("Command queue cleared")
