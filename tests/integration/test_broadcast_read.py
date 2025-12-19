"""Integration tests for broadcast read functionality.

Tests cover:
- T012: Broadcast read with mock adapter
- T023: Automatic fallback behavior
- T024: --no-fallback disabling fallback
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, MagicMock, patch


class TestBroadcastReadWithMockAdapter:
    """Integration tests for read_from_broadcast() with mock adapter."""

    def test_broadcast_read_returns_temperature(self) -> None:
        """Test broadcast read returns valid temperature value."""
        from buderus_wps_cli.main import read_from_broadcast

        # Create mock adapter that returns broadcast data
        mock_adapter = MagicMock()

        # Mock BroadcastMonitor.collect() to return cached readings
        # Patch at the source module where it's imported from
        with patch('buderus_wps.broadcast_monitor.BroadcastMonitor') as mock_monitor_class:
            mock_cache = MagicMock()
            mock_reading = MagicMock()
            mock_reading.is_temperature = True
            mock_reading.temperature = 10.5
            mock_reading.raw_data = bytes([0x00, 0x69])  # 10.5°C in tenths
            mock_cache.get_by_idx_and_base.return_value = mock_reading

            mock_monitor = MagicMock()
            mock_monitor.collect.return_value = mock_cache
            mock_monitor_class.return_value = mock_monitor

            result = read_from_broadcast(mock_adapter, "GT2_TEMP", duration=1.0)

            assert result is not None
            temp, raw = result
            assert temp == 10.5
            assert raw == bytes([0x00, 0x69])

    def test_broadcast_read_parameter_not_in_mapping(self) -> None:
        """Test broadcast read returns None for unmapped parameter."""
        from buderus_wps_cli.main import read_from_broadcast

        mock_adapter = MagicMock()
        result = read_from_broadcast(mock_adapter, "UNKNOWN_PARAM", duration=1.0)

        assert result is None

    def test_broadcast_read_no_data_received(self) -> None:
        """Test broadcast read returns None when no data is received."""
        from buderus_wps_cli.main import read_from_broadcast

        mock_adapter = MagicMock()

        with patch('buderus_wps.broadcast_monitor.BroadcastMonitor') as mock_monitor_class:
            mock_cache = MagicMock()
            mock_cache.get_by_idx_and_base.return_value = None  # No data

            mock_monitor = MagicMock()
            mock_monitor.collect.return_value = mock_cache
            mock_monitor_class.return_value = mock_monitor

            result = read_from_broadcast(mock_adapter, "GT2_TEMP", duration=1.0)

            assert result is None

    def test_broadcast_read_uses_correct_duration(self) -> None:
        """Test broadcast read passes duration to BroadcastMonitor."""
        from buderus_wps_cli.main import read_from_broadcast

        mock_adapter = MagicMock()

        with patch('buderus_wps.broadcast_monitor.BroadcastMonitor') as mock_monitor_class:
            mock_cache = MagicMock()
            mock_cache.get_by_idx_and_base.return_value = None

            mock_monitor = MagicMock()
            mock_monitor.collect.return_value = mock_cache
            mock_monitor_class.return_value = mock_monitor

            read_from_broadcast(mock_adapter, "GT2_TEMP", duration=15.0)

            mock_monitor.collect.assert_called_once_with(duration=15.0)


class TestIsInvalidRtrResponse:
    """Integration tests for is_invalid_rtr_response()."""

    def test_invalid_rtr_response_single_byte_temp(self) -> None:
        """1-byte response for temperature parameter is invalid."""
        from buderus_wps_cli.main import is_invalid_rtr_response

        # Single byte response (0x01 = 0.1°C) is invalid for temperatures
        assert is_invalid_rtr_response(bytes([0x01]), "tem") is True

    def test_valid_rtr_response_two_bytes_temp(self) -> None:
        """2-byte response for temperature parameter is valid."""
        from buderus_wps_cli.main import is_invalid_rtr_response

        # Two bytes (e.g., 0x0069 = 10.5°C) is valid
        assert is_invalid_rtr_response(bytes([0x00, 0x69]), "tem") is False

    def test_single_byte_non_temp_is_valid(self) -> None:
        """1-byte response for non-temperature parameter is valid."""
        from buderus_wps_cli.main import is_invalid_rtr_response

        # Single byte for non-temperature (e.g., status) is valid
        assert is_invalid_rtr_response(bytes([0x01]), "dec") is False


class TestAutomaticFallbackBehavior:
    """Integration tests for automatic fallback when RTR returns invalid data."""

    def test_fallback_triggered_on_invalid_rtr(self) -> None:
        """Automatic fallback is triggered when RTR returns 1-byte response."""
        # This tests cmd_read() behavior - will need the full implementation
        # For now, mark as expected to fail until T027-T028 are implemented
        pytest.skip("Requires cmd_read() fallback implementation (T027-T028)")

    def test_no_fallback_when_rtr_valid(self) -> None:
        """No fallback when RTR returns valid 2-byte response."""
        pytest.skip("Requires cmd_read() fallback implementation (T027-T028)")

    def test_no_fallback_flag_disables_fallback(self) -> None:
        """--no-fallback flag prevents automatic fallback."""
        pytest.skip("Requires cmd_read() fallback implementation (T027-T028)")
