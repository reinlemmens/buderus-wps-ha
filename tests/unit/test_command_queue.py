"""Unit tests for command queue functionality."""

import pytest
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from queue import Queue
from threading import Event

# Add addon to path for testing
addon_path = Path(__file__).parent.parent.parent / "addon"
sys.path.insert(0, str(addon_path))

from buderus_wps_addon.command_queue import (  # noqa: E402
    CommandQueue,
    Command,
    CommandResult,
    CommandStatus,
    MIN_COMMAND_DELAY,
    COMMAND_TIMEOUT,
)
from buderus_wps_addon.entity_config import EntityConfig


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock heat pump client."""
    client = MagicMock()
    client.write_parameter = MagicMock(return_value=True)
    client.read_parameter = MagicMock(return_value=1)
    return client


@pytest.fixture
def sample_select_entity() -> EntityConfig:
    """Create a sample select entity."""
    return EntityConfig(
        entity_id="heating_season_mode",
        entity_type="select",
        name="Heating Season Mode",
        options=["Winter", "Automatic", "Summer"],
        parameter_name="HEATING_SEASON_MODE",
    )


@pytest.fixture
def sample_switch_entity() -> EntityConfig:
    """Create a sample switch entity."""
    return EntityConfig(
        entity_id="holiday_mode",
        entity_type="switch",
        name="Holiday Mode",
        parameter_name="HOLIDAY_ACTIVE_GLOBAL",
    )


@pytest.fixture
def sample_number_entity() -> EntityConfig:
    """Create a sample number entity with range limits."""
    return EntityConfig(
        entity_id="extra_dhw_duration",
        entity_type="number",
        name="Extra Hot Water Duration",
        unit="h",
        min_value=0,
        max_value=48,
        step=1,
        use_menu_api=True,
    )


@pytest.fixture
def read_only_entity() -> EntityConfig:
    """Create a read-only sensor entity (no command_topic)."""
    entity = EntityConfig(
        entity_id="outdoor_temp",
        entity_type="sensor",
        name="Outdoor Temperature",
        device_class="temperature",
        unit="°C",
        state_class="measurement",
        broadcast_idx=12,
    )
    entity.command_topic = None  # Explicitly no command topic
    return entity


class TestCommand:
    """Test Command dataclass."""

    def test_create_command(self, sample_select_entity: EntityConfig) -> None:
        """Command should store entity and value."""
        cmd = Command(entity=sample_select_entity, value="Automatic")
        assert cmd.entity == sample_select_entity
        assert cmd.value == "Automatic"
        assert cmd.timestamp is not None

    def test_command_has_timestamp(self, sample_select_entity: EntityConfig) -> None:
        """Command should have creation timestamp."""
        before = time.time()
        cmd = Command(entity=sample_select_entity, value="Winter")
        after = time.time()
        assert before <= cmd.timestamp <= after


class TestCommandResult:
    """Test CommandResult dataclass."""

    def test_success_result(self) -> None:
        """CommandResult should indicate success."""
        result = CommandResult(
            entity_id="heating_season_mode",
            status=CommandStatus.SUCCESS,
            message="Command executed successfully",
        )
        assert result.status == CommandStatus.SUCCESS
        assert result.entity_id == "heating_season_mode"

    def test_failure_result(self) -> None:
        """CommandResult should indicate failure with message."""
        result = CommandResult(
            entity_id="holiday_mode",
            status=CommandStatus.FAILED,
            message="Parameter write failed",
        )
        assert result.status == CommandStatus.FAILED
        assert "write failed" in result.message


class TestCommandQueueInit:
    """Test CommandQueue initialization."""

    def test_init_creates_queue(self, mock_client: MagicMock) -> None:
        """CommandQueue should initialize with empty queue."""
        queue = CommandQueue(mock_client)
        assert queue.client == mock_client
        assert queue.pending_count() == 0

    def test_init_sets_client(self, mock_client: MagicMock) -> None:
        """CommandQueue should store heat pump client."""
        queue = CommandQueue(mock_client)
        assert queue.client is mock_client


class TestCommandValidation:
    """Test command validation."""

    def test_validate_select_valid_option(
        self, mock_client: MagicMock, sample_select_entity: EntityConfig
    ) -> None:
        """Valid select option should pass validation."""
        queue = CommandQueue(mock_client)
        is_valid, error = queue.validate_command(sample_select_entity, "Automatic")
        assert is_valid is True
        assert error is None

    def test_validate_select_invalid_option(
        self, mock_client: MagicMock, sample_select_entity: EntityConfig
    ) -> None:
        """Invalid select option should fail validation."""
        queue = CommandQueue(mock_client)
        is_valid, error = queue.validate_command(sample_select_entity, "InvalidOption")
        assert is_valid is False
        assert "Invalid option" in error

    def test_validate_switch_on(
        self, mock_client: MagicMock, sample_switch_entity: EntityConfig
    ) -> None:
        """Switch ON value should pass validation."""
        queue = CommandQueue(mock_client)
        is_valid, error = queue.validate_command(sample_switch_entity, "ON")
        assert is_valid is True

    def test_validate_switch_off(
        self, mock_client: MagicMock, sample_switch_entity: EntityConfig
    ) -> None:
        """Switch OFF value should pass validation."""
        queue = CommandQueue(mock_client)
        is_valid, error = queue.validate_command(sample_switch_entity, "OFF")
        assert is_valid is True

    def test_validate_switch_invalid(
        self, mock_client: MagicMock, sample_switch_entity: EntityConfig
    ) -> None:
        """Invalid switch value should fail validation."""
        queue = CommandQueue(mock_client)
        is_valid, error = queue.validate_command(sample_switch_entity, "MAYBE")
        assert is_valid is False
        assert "Invalid switch value" in error

    def test_validate_number_in_range(
        self, mock_client: MagicMock, sample_number_entity: EntityConfig
    ) -> None:
        """Number in valid range should pass validation."""
        queue = CommandQueue(mock_client)
        is_valid, error = queue.validate_command(sample_number_entity, "24")
        assert is_valid is True

    def test_validate_number_below_min(
        self, mock_client: MagicMock, sample_number_entity: EntityConfig
    ) -> None:
        """Number below min should fail validation."""
        queue = CommandQueue(mock_client)
        is_valid, error = queue.validate_command(sample_number_entity, "-1")
        assert is_valid is False
        assert "below minimum" in error

    def test_validate_number_above_max(
        self, mock_client: MagicMock, sample_number_entity: EntityConfig
    ) -> None:
        """Number above max should fail validation."""
        queue = CommandQueue(mock_client)
        is_valid, error = queue.validate_command(sample_number_entity, "100")
        assert is_valid is False
        assert "above maximum" in error

    def test_validate_number_not_numeric(
        self, mock_client: MagicMock, sample_number_entity: EntityConfig
    ) -> None:
        """Non-numeric value should fail validation for number entity."""
        queue = CommandQueue(mock_client)
        is_valid, error = queue.validate_command(sample_number_entity, "abc")
        assert is_valid is False
        assert "not a valid number" in error

    def test_validate_read_only_entity(
        self, mock_client: MagicMock, read_only_entity: EntityConfig
    ) -> None:
        """Read-only entity should fail validation."""
        queue = CommandQueue(mock_client)
        is_valid, error = queue.validate_command(read_only_entity, "15.5")
        assert is_valid is False
        assert "read-only" in error.lower() or "not controllable" in error.lower()


class TestCommandEnqueue:
    """Test command enqueueing."""

    def test_enqueue_valid_command(
        self, mock_client: MagicMock, sample_select_entity: EntityConfig
    ) -> None:
        """Valid command should be enqueued."""
        queue = CommandQueue(mock_client)
        result = queue.enqueue(sample_select_entity, "Automatic")
        assert result is True
        assert queue.pending_count() == 1

    def test_enqueue_invalid_command_rejected(
        self, mock_client: MagicMock, sample_select_entity: EntityConfig
    ) -> None:
        """Invalid command should be rejected."""
        queue = CommandQueue(mock_client)
        result = queue.enqueue(sample_select_entity, "InvalidOption")
        assert result is False
        assert queue.pending_count() == 0

    def test_enqueue_multiple_commands(
        self, mock_client: MagicMock, sample_select_entity: EntityConfig
    ) -> None:
        """Multiple commands should queue up."""
        queue = CommandQueue(mock_client)
        queue.enqueue(sample_select_entity, "Automatic")
        queue.enqueue(sample_select_entity, "Winter")
        assert queue.pending_count() == 2


class TestRateLimiting:
    """Test command rate limiting."""

    def test_min_delay_constant(self) -> None:
        """MIN_COMMAND_DELAY should be 500ms."""
        assert MIN_COMMAND_DELAY == 0.5

    @patch("buderus_wps_addon.command_queue.time.sleep")
    @patch("buderus_wps_addon.command_queue.time.time")
    def test_rate_limiting_applied(
        self,
        mock_time: MagicMock,
        mock_sleep: MagicMock,
        mock_client: MagicMock,
        sample_select_entity: EntityConfig,
    ) -> None:
        """Commands should be rate-limited with MIN_COMMAND_DELAY."""
        # Simulate time: first call at 0, second call at 0.1 (needs delay)
        mock_time.side_effect = [0, 0.1, 0.1, 0.6, 0.6]

        queue = CommandQueue(mock_client)
        queue._last_command_time = 0  # Simulate previous command at time 0

        # Execute a command (should wait)
        queue._execute_command(Command(entity=sample_select_entity, value="Automatic"))

        # Should have slept for the remaining time (0.5 - 0.1 = 0.4)
        mock_sleep.assert_called()
        sleep_time = mock_sleep.call_args[0][0]
        assert 0.3 <= sleep_time <= 0.5  # Allow some tolerance


class TestCommandExecution:
    """Test command execution."""

    def test_execute_select_command(
        self, mock_client: MagicMock, sample_select_entity: EntityConfig
    ) -> None:
        """Select command should call client.write_parameter."""
        queue = CommandQueue(mock_client)
        cmd = Command(entity=sample_select_entity, value="Automatic")
        result = queue._execute_command(cmd)

        assert result.status == CommandStatus.SUCCESS
        mock_client.write_parameter.assert_called_once()

    def test_execute_switch_on_command(
        self, mock_client: MagicMock, sample_switch_entity: EntityConfig
    ) -> None:
        """Switch ON command should write value 1."""
        queue = CommandQueue(mock_client)
        cmd = Command(entity=sample_switch_entity, value="ON")
        result = queue._execute_command(cmd)

        assert result.status == CommandStatus.SUCCESS
        mock_client.write_parameter.assert_called_with("HOLIDAY_ACTIVE_GLOBAL", 1)

    def test_execute_switch_off_command(
        self, mock_client: MagicMock, sample_switch_entity: EntityConfig
    ) -> None:
        """Switch OFF command should write value 0."""
        queue = CommandQueue(mock_client)
        cmd = Command(entity=sample_switch_entity, value="OFF")
        result = queue._execute_command(cmd)

        assert result.status == CommandStatus.SUCCESS
        mock_client.write_parameter.assert_called_with("HOLIDAY_ACTIVE_GLOBAL", 0)

    def test_execute_command_failure(
        self, mock_client: MagicMock, sample_select_entity: EntityConfig
    ) -> None:
        """Failed command should return FAILED status."""
        mock_client.write_parameter.side_effect = Exception("CAN timeout")

        queue = CommandQueue(mock_client)
        cmd = Command(entity=sample_select_entity, value="Automatic")
        result = queue._execute_command(cmd)

        assert result.status == CommandStatus.FAILED
        assert "CAN timeout" in result.message

    def test_execute_command_returns_false(
        self, mock_client: MagicMock, sample_select_entity: EntityConfig
    ) -> None:
        """Command returning False should be marked as failed."""
        mock_client.write_parameter.return_value = False

        queue = CommandQueue(mock_client)
        cmd = Command(entity=sample_select_entity, value="Automatic")
        result = queue._execute_command(cmd)

        assert result.status == CommandStatus.FAILED


class TestCommandTimeout:
    """Test command timeout handling."""

    def test_timeout_constant(self) -> None:
        """COMMAND_TIMEOUT should be 30 seconds."""
        assert COMMAND_TIMEOUT == 30.0

    def test_expired_command_skipped(
        self, mock_client: MagicMock, sample_select_entity: EntityConfig
    ) -> None:
        """Expired commands should be skipped."""
        queue = CommandQueue(mock_client)

        # Create a command with old timestamp
        cmd = Command(entity=sample_select_entity, value="Automatic")
        cmd.timestamp = time.time() - COMMAND_TIMEOUT - 1  # Expired

        result = queue._execute_command(cmd)

        assert result.status == CommandStatus.TIMEOUT
        mock_client.write_parameter.assert_not_called()


class TestMenuAPICommands:
    """Test commands that use MenuAPI instead of direct parameter writes."""

    def test_menu_api_entity_detected(
        self, mock_client: MagicMock, sample_number_entity: EntityConfig
    ) -> None:
        """Entities with use_menu_api should use MenuAPI."""
        assert sample_number_entity.use_menu_api is True

    @patch("buderus_wps_addon.command_queue.CommandQueue._execute_menu_api_command")
    def test_menu_api_command_routed(
        self,
        mock_menu_api: MagicMock,
        mock_client: MagicMock,
        sample_number_entity: EntityConfig,
    ) -> None:
        """MenuAPI commands should be routed to _execute_menu_api_command."""
        mock_menu_api.return_value = CommandResult(
            entity_id="extra_dhw_duration",
            status=CommandStatus.SUCCESS,
            message="OK",
        )

        queue = CommandQueue(mock_client)
        cmd = Command(entity=sample_number_entity, value="24")
        result = queue._execute_command(cmd)

        mock_menu_api.assert_called_once()


class TestCallbackIntegration:
    """Test callback integration for result notification."""

    def test_callback_on_success(
        self, mock_client: MagicMock, sample_select_entity: EntityConfig
    ) -> None:
        """Success callback should be called on successful execution."""
        callback = MagicMock()

        queue = CommandQueue(mock_client, result_callback=callback)
        queue.enqueue(sample_select_entity, "Automatic")
        queue.process_one()

        callback.assert_called_once()
        result = callback.call_args[0][0]
        assert result.status == CommandStatus.SUCCESS

    def test_callback_on_failure(
        self, mock_client: MagicMock, sample_select_entity: EntityConfig
    ) -> None:
        """Failure callback should be called on failed execution."""
        mock_client.write_parameter.side_effect = Exception("Error")
        callback = MagicMock()

        queue = CommandQueue(mock_client, result_callback=callback)
        queue.enqueue(sample_select_entity, "Automatic")
        queue.process_one()

        callback.assert_called_once()
        result = callback.call_args[0][0]
        assert result.status == CommandStatus.FAILED


class TestQueueOperations:
    """Test queue operations."""

    def test_clear_queue(
        self, mock_client: MagicMock, sample_select_entity: EntityConfig
    ) -> None:
        """Clear should empty the queue."""
        queue = CommandQueue(mock_client)
        queue.enqueue(sample_select_entity, "Automatic")
        queue.enqueue(sample_select_entity, "Winter")

        queue.clear()

        assert queue.pending_count() == 0

    def test_process_one_empty_queue(self, mock_client: MagicMock) -> None:
        """process_one on empty queue should return None."""
        queue = CommandQueue(mock_client)
        result = queue.process_one()
        assert result is None

    def test_process_one_returns_result(
        self, mock_client: MagicMock, sample_select_entity: EntityConfig
    ) -> None:
        """process_one should return the command result."""
        queue = CommandQueue(mock_client)
        queue.enqueue(sample_select_entity, "Automatic")

        result = queue.process_one()

        assert result is not None
        assert result.status == CommandStatus.SUCCESS
