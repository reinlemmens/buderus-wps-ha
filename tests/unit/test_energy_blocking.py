"""Unit tests for energy blocking control.

Tests for BlockingState, BlockingResult, BlockingStatus dataclasses
and EnergyBlockingControl methods.
"""

from unittest.mock import MagicMock

# Phase 2: Dataclass tests (T005-T007)


class TestBlockingState:
    """Tests for BlockingState dataclass - T005."""

    def test_blocking_state_creation(self) -> None:
        """BlockingState can be created with required fields."""
        from buderus_wps.energy_blocking import BlockingState

        state = BlockingState(
            component="compressor",
            blocked=True,
            source="user",
            timestamp=1733500800.0,
        )
        assert state.component == "compressor"
        assert state.blocked is True
        assert state.source == "user"
        assert state.timestamp == 1733500800.0

    def test_blocking_state_aux_heater(self) -> None:
        """BlockingState works for aux_heater component."""
        from buderus_wps.energy_blocking import BlockingState

        state = BlockingState(
            component="aux_heater",
            blocked=False,
            source="none",
            timestamp=1733500800.0,
        )
        assert state.component == "aux_heater"
        assert state.blocked is False
        assert state.source == "none"

    def test_blocking_state_sources(self) -> None:
        """BlockingState supports all source types."""
        from buderus_wps.energy_blocking import BlockingState

        for source in ["user", "external", "system", "none"]:
            state = BlockingState(
                component="compressor",
                blocked=True,
                source=source,
                timestamp=1733500800.0,
            )
            assert state.source == source


class TestBlockingResult:
    """Tests for BlockingResult dataclass - T006."""

    def test_blocking_result_success(self) -> None:
        """BlockingResult represents successful operation."""
        from buderus_wps.energy_blocking import BlockingResult

        result = BlockingResult(
            success=True,
            component="compressor",
            action="block",
            message="Compressor blocked successfully",
        )
        assert result.success is True
        assert result.component == "compressor"
        assert result.action == "block"
        assert result.message == "Compressor blocked successfully"
        assert result.error is None

    def test_blocking_result_failure(self) -> None:
        """BlockingResult represents failed operation with error."""
        from buderus_wps.energy_blocking import BlockingResult

        result = BlockingResult(
            success=False,
            component="aux_heater",
            action="unblock",
            message="Failed to unblock aux heater",
            error="Communication timeout after 5.0 seconds",
        )
        assert result.success is False
        assert result.error == "Communication timeout after 5.0 seconds"

    def test_blocking_result_actions(self) -> None:
        """BlockingResult supports all action types."""
        from buderus_wps.energy_blocking import BlockingResult

        for action in ["block", "unblock", "clear_all"]:
            result = BlockingResult(
                success=True,
                component="compressor",
                action=action,
                message=f"Action {action} completed",
            )
            assert result.action == action


class TestBlockingStatus:
    """Tests for BlockingStatus dataclass - T007."""

    def test_blocking_status_creation(self) -> None:
        """BlockingStatus contains both component states."""
        from buderus_wps.energy_blocking import BlockingState, BlockingStatus

        compressor = BlockingState(
            component="compressor",
            blocked=True,
            source="user",
            timestamp=1733500800.0,
        )
        aux_heater = BlockingState(
            component="aux_heater",
            blocked=False,
            source="none",
            timestamp=1733500800.0,
        )
        status = BlockingStatus(
            compressor=compressor,
            aux_heater=aux_heater,
            timestamp=1733500800.0,
        )
        assert status.compressor.blocked is True
        assert status.aux_heater.blocked is False
        assert status.timestamp == 1733500800.0

    def test_blocking_status_both_blocked(self) -> None:
        """BlockingStatus can represent both components blocked."""
        from buderus_wps.energy_blocking import BlockingState, BlockingStatus

        compressor = BlockingState(
            component="compressor",
            blocked=True,
            source="user",
            timestamp=1733500800.0,
        )
        aux_heater = BlockingState(
            component="aux_heater",
            blocked=True,
            source="user",
            timestamp=1733500800.0,
        )
        status = BlockingStatus(
            compressor=compressor,
            aux_heater=aux_heater,
            timestamp=1733500800.0,
        )
        assert status.compressor.blocked is True
        assert status.aux_heater.blocked is True


# Phase 3: User Story 1 tests (T016-T017)


class TestBlockCompressor:
    """Unit tests for block_compressor() method - T016."""

    def test_block_compressor_success(self) -> None:
        """block_compressor returns success result on successful write."""
        from buderus_wps.energy_blocking import BlockingResult, EnergyBlockingControl

        mock_client = MagicMock()
        # Mock write succeeds, read returns blocked status
        mock_client.read_parameter.return_value = {"decoded": 1}

        control = EnergyBlockingControl(mock_client)
        result = control.block_compressor()

        assert isinstance(result, BlockingResult)
        assert result.success is True
        assert result.component == "compressor"
        assert result.action == "block"

    def test_block_compressor_writes_correct_parameter(self) -> None:
        """block_compressor writes to COMPRESSOR_E21_EXTERN_BLOCK_BY_E21_EXT_1."""
        from buderus_wps.energy_blocking import (
            PARAM_COMPRESSOR_BLOCK,
            EnergyBlockingControl,
        )

        mock_client = MagicMock()
        mock_client.read_parameter.return_value = {"decoded": 1}

        control = EnergyBlockingControl(mock_client)
        control.block_compressor()

        # Verify write was called with correct parameter and value
        mock_client.write_value.assert_called_once_with(
            PARAM_COMPRESSOR_BLOCK, 1, timeout=5.0
        )

    def test_block_compressor_verifies_status(self) -> None:
        """block_compressor reads status to verify block was applied."""
        from buderus_wps.energy_blocking import (
            EnergyBlockingControl,
        )

        mock_client = MagicMock()
        mock_client.read_parameter.return_value = {"decoded": 1}

        control = EnergyBlockingControl(mock_client)
        control.block_compressor()

        # Verify read was called to check status
        mock_client.read_parameter.assert_called()


class TestUnblockCompressor:
    """Unit tests for unblock_compressor() method - T017."""

    def test_unblock_compressor_success(self) -> None:
        """unblock_compressor returns success result on successful write."""
        from buderus_wps.energy_blocking import BlockingResult, EnergyBlockingControl

        mock_client = MagicMock()
        mock_client.read_parameter.return_value = {"decoded": 0}

        control = EnergyBlockingControl(mock_client)
        result = control.unblock_compressor()

        assert isinstance(result, BlockingResult)
        assert result.success is True
        assert result.component == "compressor"
        assert result.action == "unblock"

    def test_unblock_compressor_writes_zero(self) -> None:
        """unblock_compressor writes 0 to unblock."""
        from buderus_wps.energy_blocking import (
            PARAM_COMPRESSOR_BLOCK,
            EnergyBlockingControl,
        )

        mock_client = MagicMock()
        mock_client.read_parameter.return_value = {"decoded": 0}

        control = EnergyBlockingControl(mock_client)
        control.unblock_compressor()

        mock_client.write_value.assert_called_once_with(
            PARAM_COMPRESSOR_BLOCK, 0, timeout=5.0
        )


# Phase 4: User Story 2 tests (T026-T027)


class TestBlockAuxHeater:
    """Unit tests for block_aux_heater() method - T026."""

    def test_block_aux_heater_success(self) -> None:
        """block_aux_heater returns success result on successful write."""
        from buderus_wps.energy_blocking import BlockingResult, EnergyBlockingControl

        mock_client = MagicMock()
        # Mock write succeeds, read returns blocked status
        mock_client.read_parameter.return_value = {"decoded": 1}

        control = EnergyBlockingControl(mock_client)
        result = control.block_aux_heater()

        assert isinstance(result, BlockingResult)
        assert result.success is True
        assert result.component == "aux_heater"
        assert result.action == "block"

    def test_block_aux_heater_writes_correct_parameter(self) -> None:
        """block_aux_heater writes to ADDITIONAL_USER_BLOCKED."""
        from buderus_wps.energy_blocking import (
            PARAM_AUX_HEATER_BLOCK,
            EnergyBlockingControl,
        )

        mock_client = MagicMock()
        mock_client.read_parameter.return_value = {"decoded": 1}

        control = EnergyBlockingControl(mock_client)
        control.block_aux_heater()

        # Verify write was called with correct parameter and value
        mock_client.write_value.assert_called_once_with(
            PARAM_AUX_HEATER_BLOCK, 1, timeout=5.0
        )

    def test_block_aux_heater_verifies_status(self) -> None:
        """block_aux_heater reads status to verify block was applied."""
        from buderus_wps.energy_blocking import (
            EnergyBlockingControl,
        )

        mock_client = MagicMock()
        mock_client.read_parameter.return_value = {"decoded": 1}

        control = EnergyBlockingControl(mock_client)
        control.block_aux_heater()

        # Verify read was called to check status
        mock_client.read_parameter.assert_called()


class TestUnblockAuxHeater:
    """Unit tests for unblock_aux_heater() method - T027."""

    def test_unblock_aux_heater_success(self) -> None:
        """unblock_aux_heater returns success result on successful write."""
        from buderus_wps.energy_blocking import BlockingResult, EnergyBlockingControl

        mock_client = MagicMock()
        mock_client.read_parameter.return_value = {"decoded": 0}

        control = EnergyBlockingControl(mock_client)
        result = control.unblock_aux_heater()

        assert isinstance(result, BlockingResult)
        assert result.success is True
        assert result.component == "aux_heater"
        assert result.action == "unblock"

    def test_unblock_aux_heater_writes_zero(self) -> None:
        """unblock_aux_heater writes 0 to unblock."""
        from buderus_wps.energy_blocking import (
            PARAM_AUX_HEATER_BLOCK,
            EnergyBlockingControl,
        )

        mock_client = MagicMock()
        mock_client.read_parameter.return_value = {"decoded": 0}

        control = EnergyBlockingControl(mock_client)
        control.unblock_aux_heater()

        mock_client.write_value.assert_called_once_with(
            PARAM_AUX_HEATER_BLOCK, 0, timeout=5.0
        )

    def test_unblock_aux_heater_verification_failure(self) -> None:
        """unblock_aux_heater returns failure when verification fails."""
        from buderus_wps.energy_blocking import EnergyBlockingControl

        mock_client = MagicMock()
        # Write succeeds but read shows still blocked
        mock_client.read_parameter.return_value = {"decoded": 1}

        control = EnergyBlockingControl(mock_client)
        result = control.unblock_aux_heater()

        assert result.success is False
        assert "verification failed" in result.message.lower()


# Phase 5: User Story 3 tests (T034-T036)


class TestGetStatus:
    """Unit tests for get_status() method - T034, T035, T036."""

    def test_get_status_returns_both_components(self) -> None:
        """get_status returns BlockingStatus with both compressor and aux_heater - T034."""
        from buderus_wps.energy_blocking import BlockingStatus, EnergyBlockingControl

        mock_client = MagicMock()
        mock_client.read_parameter.side_effect = [
            {"decoded": 1},  # Compressor blocked
            {"decoded": 0},  # Aux heater not blocked
        ]

        control = EnergyBlockingControl(mock_client)
        status = control.get_status()

        assert isinstance(status, BlockingStatus)
        assert status.compressor.component == "compressor"
        assert status.compressor.blocked is True
        assert status.aux_heater.component == "aux_heater"
        assert status.aux_heater.blocked is False

    def test_get_status_no_blocks_active(self) -> None:
        """get_status with no blocks active - T035."""
        from buderus_wps.energy_blocking import EnergyBlockingControl

        mock_client = MagicMock()
        mock_client.read_parameter.return_value = {"decoded": 0}

        control = EnergyBlockingControl(mock_client)
        status = control.get_status()

        assert status.compressor.blocked is False
        assert status.compressor.source == "none"
        assert status.aux_heater.blocked is False
        assert status.aux_heater.source == "none"

    def test_get_status_one_block_active(self) -> None:
        """get_status with one block active - T036."""
        from buderus_wps.energy_blocking import EnergyBlockingControl

        mock_client = MagicMock()
        mock_client.read_parameter.side_effect = [
            {"decoded": 0},  # Compressor not blocked
            {"decoded": 1},  # Aux heater blocked
        ]

        control = EnergyBlockingControl(mock_client)
        status = control.get_status()

        assert status.compressor.blocked is False
        assert status.aux_heater.blocked is True

    def test_get_status_includes_timestamp(self) -> None:
        """get_status includes timestamp."""
        from unittest.mock import patch

        from buderus_wps.energy_blocking import EnergyBlockingControl

        mock_client = MagicMock()
        mock_client.read_parameter.return_value = {"decoded": 0}

        control = EnergyBlockingControl(mock_client)

        with patch("time.time", return_value=1733500800.0):
            status = control.get_status()

        assert status.timestamp == 1733500800.0


# Phase 6: User Story 4 tests (T041-T042)


class TestClearAllBlocks:
    """Unit tests for clear_all_blocks() method - T041, T042."""

    def test_clear_all_blocks_clears_both_components(self) -> None:
        """clear_all_blocks clears both compressor and aux heater - T041."""
        from buderus_wps.energy_blocking import BlockingResult, EnergyBlockingControl

        mock_client = MagicMock()
        # Both unblock operations succeed
        mock_client.read_parameter.return_value = {"decoded": 0}

        control = EnergyBlockingControl(mock_client)
        result = control.clear_all_blocks()

        assert isinstance(result, BlockingResult)
        assert result.success is True
        assert result.action == "clear_all"
        assert mock_client.write_value.call_count == 2

    def test_clear_all_blocks_only_one_block_active(self) -> None:
        """clear_all_blocks when only one block active - T042."""
        from buderus_wps.energy_blocking import EnergyBlockingControl

        mock_client = MagicMock()
        mock_client.read_parameter.return_value = {"decoded": 0}

        control = EnergyBlockingControl(mock_client)
        result = control.clear_all_blocks()

        # Should still attempt to unblock both
        assert result.success is True
        assert mock_client.write_value.call_count == 2

    def test_clear_all_blocks_partial_failure(self) -> None:
        """clear_all_blocks reports failure if any unblock fails."""
        from buderus_wps.energy_blocking import EnergyBlockingControl

        mock_client = MagicMock()
        # First unblock succeeds, second fails verification
        mock_client.read_parameter.side_effect = [
            {"decoded": 0},  # Compressor unblock success
            {"decoded": 1},  # Aux heater still blocked
        ]

        control = EnergyBlockingControl(mock_client)
        result = control.clear_all_blocks()

        assert result.success is False
        assert (
            "aux_heater" in result.message.lower()
            or "partial" in result.message.lower()
        )


class TestBlockAll:
    """Unit tests for block_all() method."""

    def test_block_all_blocks_both_components(self) -> None:
        """block_all blocks both compressor and aux heater."""
        from buderus_wps.energy_blocking import BlockingResult, EnergyBlockingControl

        mock_client = MagicMock()
        # Both block operations succeed
        mock_client.read_parameter.return_value = {"decoded": 1}

        control = EnergyBlockingControl(mock_client)
        result = control.block_all()

        assert isinstance(result, BlockingResult)
        assert result.success is True
        assert result.action == "block_all"
        assert mock_client.write_value.call_count == 2

    def test_block_all_partial_failure(self) -> None:
        """block_all reports failure if any block fails."""
        from buderus_wps.energy_blocking import EnergyBlockingControl

        mock_client = MagicMock()
        # First block succeeds, second fails verification
        mock_client.read_parameter.side_effect = [
            {"decoded": 1},  # Compressor block success
            {"decoded": 0},  # Aux heater still unblocked
        ]

        control = EnergyBlockingControl(mock_client)
        result = control.block_all()

        assert result.success is False
        assert (
            "aux_heater" in result.message.lower()
            or "partial" in result.message.lower()
        )


# Phase 7: CLI tests (T046-T049)


class TestEnergyCLI:
    """Unit tests for energy CLI commands - T046, T047, T048, T049."""

    def test_energy_command_group_registered(self) -> None:
        """Energy command group is registered in CLI - T046."""
        from buderus_wps_cli.main import build_parser

        parser = build_parser()
        # Check that energy subcommand exists
        subparsers = parser._subparsers._group_actions[0].choices
        assert "energy" in subparsers

    def test_block_compressor_command_exists(self) -> None:
        """block-compressor command exists under energy - T047."""
        from buderus_wps_cli.main import build_parser

        parser = build_parser()
        # Parse valid command to verify it exists
        args = parser.parse_args(["energy", "block-compressor"])
        assert args.command == "energy"
        assert args.energy_cmd == "block-compressor"

    def test_status_command_text_output(self) -> None:
        """status command outputs text by default - T048."""
        from buderus_wps_cli.main import build_parser

        parser = build_parser()
        args = parser.parse_args(["energy", "status"])
        assert args.command == "energy"
        assert args.energy_cmd == "status"
        assert args.format == "text"  # Default format

    def test_status_command_json_output(self) -> None:
        """status command supports --format json - T049."""
        from buderus_wps_cli.main import build_parser

        parser = build_parser()
        args = parser.parse_args(["energy", "status", "--format", "json"])
        assert args.format == "json"

    def test_block_all_command_exists(self) -> None:
        """block-all command exists under energy."""
        from buderus_wps_cli.main import build_parser

        parser = build_parser()
        args = parser.parse_args(["energy", "block-all"])
        assert args.command == "energy"
        assert args.energy_cmd == "block-all"
