"""Integration tests for energy blocking control with mocked CAN adapter.

Tests the full flow of blocking/unblocking operations using mocked
hardware communication.
"""

import pytest
from unittest.mock import MagicMock, patch


# Phase 3: User Story 1 integration tests (T018)


class TestCompressorBlockingIntegration:
    """Integration tests for compressor blocking - T018."""

    def test_block_compressor_full_flow(self) -> None:
        """Full flow: block compressor, verify blocked, unblock, verify unblocked."""
        from buderus_wps.energy_blocking import EnergyBlockingControl

        mock_client = MagicMock()
        # Simulate: first read returns blocked, second returns unblocked
        mock_client.read_parameter.side_effect = [
            {"decoded": 1},  # After block
            {"decoded": 0},  # After unblock
        ]

        control = EnergyBlockingControl(mock_client)

        # Block compressor
        result = control.block_compressor()
        assert result.success is True
        assert result.component == "compressor"
        assert result.action == "block"

        # Unblock compressor
        result = control.unblock_compressor()
        assert result.success is True
        assert result.component == "compressor"
        assert result.action == "unblock"

        # Verify write calls
        assert mock_client.write_value.call_count == 2

    def test_block_compressor_with_adapter_mock(self) -> None:
        """Test with mocked adapter simulating real CAN communication."""
        from buderus_wps.energy_blocking import EnergyBlockingControl

        mock_client = MagicMock()
        mock_client.read_parameter.return_value = {"decoded": 1}

        control = EnergyBlockingControl(mock_client)
        result = control.block_compressor()

        assert result.success is True
        mock_client.write_value.assert_called_once()
        mock_client.read_parameter.assert_called_once()

    def test_compressor_block_verification_failure(self) -> None:
        """Test when block command succeeds but verification fails."""
        from buderus_wps.energy_blocking import EnergyBlockingControl

        mock_client = MagicMock()
        # Write succeeds but read shows still unblocked
        mock_client.read_parameter.return_value = {"decoded": 0}

        control = EnergyBlockingControl(mock_client)
        result = control.block_compressor()

        assert result.success is False
        assert "verification failed" in result.message.lower()
        assert result.error is not None


# Phase 4: User Story 2 integration tests (T028)


class TestAuxHeaterBlockingIntegration:
    """Integration tests for aux heater blocking - T028."""

    def test_block_aux_heater_full_flow(self) -> None:
        """Full flow: block aux heater, verify blocked, unblock, verify unblocked."""
        from buderus_wps.energy_blocking import EnergyBlockingControl

        mock_client = MagicMock()
        # Simulate: first read returns blocked, second returns unblocked
        mock_client.read_parameter.side_effect = [
            {"decoded": 1},  # After block
            {"decoded": 0},  # After unblock
        ]

        control = EnergyBlockingControl(mock_client)

        # Block aux heater
        result = control.block_aux_heater()
        assert result.success is True
        assert result.component == "aux_heater"
        assert result.action == "block"

        # Unblock aux heater
        result = control.unblock_aux_heater()
        assert result.success is True
        assert result.component == "aux_heater"
        assert result.action == "unblock"

        # Verify write calls
        assert mock_client.write_value.call_count == 2

    def test_aux_heater_block_verification_failure(self) -> None:
        """Test when block command succeeds but verification fails."""
        from buderus_wps.energy_blocking import EnergyBlockingControl

        mock_client = MagicMock()
        # Write succeeds but read shows still unblocked
        mock_client.read_parameter.return_value = {"decoded": 0}

        control = EnergyBlockingControl(mock_client)
        result = control.block_aux_heater()

        assert result.success is False
        assert "verification failed" in result.message.lower()
        assert result.error is not None


# Phase 5: User Story 3 integration tests (T037)


class TestGetStatusIntegration:
    """Integration tests for get_status() - T037."""

    def test_get_status_full_flow(self) -> None:
        """get_status returns current blocking state from hardware."""
        from buderus_wps.energy_blocking import EnergyBlockingControl

        mock_client = MagicMock()
        mock_client.read_parameter.side_effect = [
            {"decoded": 1},  # Compressor blocked
            {"decoded": 1},  # Aux heater blocked
        ]

        control = EnergyBlockingControl(mock_client)
        status = control.get_status()

        assert status.compressor.blocked is True
        assert status.aux_heater.blocked is True
        assert mock_client.read_parameter.call_count == 2


# Phase 6: User Story 4 integration tests (T043)


class TestClearAllBlocksIntegration:
    """Integration tests for clear_all_blocks() - T043."""

    def test_clear_all_blocks_full_flow(self) -> None:
        """Full flow: set both blocks, then clear all."""
        from buderus_wps.energy_blocking import EnergyBlockingControl

        mock_client = MagicMock()
        # Block operations succeed
        mock_client.read_parameter.side_effect = [
            {"decoded": 1},  # Compressor block verify
            {"decoded": 1},  # Aux heater block verify
            {"decoded": 0},  # Clear compressor verify
            {"decoded": 0},  # Clear aux heater verify
        ]

        control = EnergyBlockingControl(mock_client)

        # Block both
        result1 = control.block_compressor()
        result2 = control.block_aux_heater()
        assert result1.success is True
        assert result2.success is True

        # Clear all
        result = control.clear_all_blocks()
        assert result.success is True
        assert result.action == "clear_all"


# Phase 8: Edge case tests (T058-T061)


class TestEnergyBlockingEdgeCases:
    """Edge case tests for energy blocking - T058, T059, T060, T061."""

    def test_communication_timeout_error_handling(self) -> None:
        """Test error handling on communication timeout - T058."""
        from buderus_wps.energy_blocking import EnergyBlockingControl

        mock_client = MagicMock()
        mock_client.write_value.side_effect = TimeoutError("Operation timed out")

        control = EnergyBlockingControl(mock_client)
        result = control.block_compressor()

        assert result.success is False
        assert result.error is not None
        assert "timed out" in result.error.lower()

    def test_verification_failure_error_handling(self) -> None:
        """Test error handling on verification failure - T059."""
        from buderus_wps.energy_blocking import EnergyBlockingControl

        mock_client = MagicMock()
        # Write succeeds but verification shows wrong state
        mock_client.read_parameter.return_value = {"decoded": 0}

        control = EnergyBlockingControl(mock_client)
        result = control.block_compressor()

        assert result.success is False
        assert "verification failed" in result.message.lower()

    def test_rapid_command_succession(self) -> None:
        """Test rapid command succession handling - T060."""
        from buderus_wps.energy_blocking import EnergyBlockingControl

        mock_client = MagicMock()
        # All operations succeed
        mock_client.read_parameter.side_effect = [
            {"decoded": 1},  # Block 1
            {"decoded": 0},  # Unblock 1
            {"decoded": 1},  # Block 2
            {"decoded": 0},  # Unblock 2
        ]

        control = EnergyBlockingControl(mock_client)

        # Rapid succession of commands
        r1 = control.block_compressor()
        r2 = control.unblock_compressor()
        r3 = control.block_compressor()
        r4 = control.unblock_compressor()

        # All should succeed
        assert r1.success is True
        assert r2.success is True
        assert r3.success is True
        assert r4.success is True

    def test_error_when_component_already_running(self) -> None:
        """Test error handling when component already running - T061."""
        from buderus_wps.energy_blocking import EnergyBlockingControl

        mock_client = MagicMock()
        # Block command fails because compressor is currently running
        mock_client.write_value.side_effect = Exception("Component is currently active")

        control = EnergyBlockingControl(mock_client)
        result = control.block_compressor()

        assert result.success is False
        assert result.error is not None
