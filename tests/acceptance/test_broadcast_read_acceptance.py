"""Acceptance tests for broadcast read feature (012-broadcast-read-fallback).

Tests cover user story acceptance scenarios:
- AS1.1: Basic broadcast read
- AS1.2: Broadcast read with custom duration
- AS1.3: Broadcast timeout error
- AS2.1: Auto fallback on invalid RTR
- AS2.2: No fallback for valid RTR
- AS2.3: Fallback failure with warning
- AS3.1: RTR source indication
- AS3.2: Broadcast source indication
- AS3.3: JSON source field
"""

from __future__ import annotations

import io
import json
import sys
from unittest.mock import MagicMock, patch


def create_mock_param(text: str, idx: int, fmt: str) -> MagicMock:
    """Create a mock Parameter object."""
    mock_param = MagicMock()
    mock_param.text = text
    mock_param.idx = idx
    mock_param.format = fmt
    return mock_param


class TestAS1BasicBroadcastRead:
    """AS1.1: Basic broadcast read acceptance tests."""

    def test_broadcast_read_returns_temperature_from_broadcast(self) -> None:
        """
        Given the CLI is connected to the heat pump via CAN bus,
        When user runs `read GT2_TEMP --broadcast`,
        Then the system collects broadcast traffic and returns the temperature value from broadcast data
        """
        from buderus_wps_cli import main as cli

        # Create mock args
        args = MagicMock()
        args.param = "GT2_TEMP"
        args.broadcast = True
        args.duration = 5.0
        args.no_fallback = False
        args.json = False
        args.timeout = 5.0

        # Create mock client with proper get() method
        mock_param = create_mock_param("GT2_TEMP", 10, "tem")
        mock_client = MagicMock()
        mock_client.get.return_value = mock_param

        # Create mock adapter
        mock_adapter = MagicMock()

        # Patch read_from_broadcast to return a temperature
        with patch.object(cli, "read_from_broadcast") as mock_read_broadcast:
            mock_read_broadcast.return_value = (10.5, bytes([0x00, 0x69]))

            # Capture stdout
            captured_output = io.StringIO()
            sys.stdout = captured_output

            try:
                result = cli.cmd_read(mock_client, args, mock_adapter)
            finally:
                sys.stdout = sys.__stdout__

            output = captured_output.getvalue()

            # Verify
            assert result == 0
            assert "GT2_TEMP" in output
            assert "10.5" in output
            assert "source=broadcast" in output
            mock_read_broadcast.assert_called_once_with(mock_adapter, "GT2_TEMP", 5.0)


class TestAS1BroadcastReadWithCustomDuration:
    """AS1.2: Broadcast read with custom duration acceptance tests."""

    def test_broadcast_read_with_custom_duration(self) -> None:
        """
        Given the CLI is connected and --broadcast flag is used,
        When user runs `read GT2_TEMP --broadcast --duration 10`,
        Then the system collects broadcast traffic for 10 seconds before returning the value
        """
        from buderus_wps_cli import main as cli

        args = MagicMock()
        args.param = "GT2_TEMP"
        args.broadcast = True
        args.duration = 10.0  # Custom duration
        args.no_fallback = False
        args.json = False
        args.timeout = 5.0

        mock_param = create_mock_param("GT2_TEMP", 10, "tem")
        mock_client = MagicMock()
        mock_client.get.return_value = mock_param

        mock_adapter = MagicMock()

        with patch.object(cli, "read_from_broadcast") as mock_read_broadcast:
            mock_read_broadcast.return_value = (10.5, bytes([0x00, 0x69]))

            captured_output = io.StringIO()
            sys.stdout = captured_output

            try:
                result = cli.cmd_read(mock_client, args, mock_adapter)
            finally:
                sys.stdout = sys.__stdout__

            # Verify custom duration was used
            assert result == 0
            mock_read_broadcast.assert_called_once_with(mock_adapter, "GT2_TEMP", 10.0)


class TestAS1BroadcastTimeoutError:
    """AS1.3: Broadcast timeout error acceptance tests."""

    def test_broadcast_timeout_shows_error(self) -> None:
        """
        Given the CLI is connected and --broadcast flag is used,
        When the requested parameter is not found in broadcast traffic within the duration,
        Then the system displays an appropriate error message indicating no broadcast data was captured
        """
        from buderus_wps_cli import main as cli

        args = MagicMock()
        args.param = "GT2_TEMP"
        args.broadcast = True
        args.duration = 5.0
        args.no_fallback = False
        args.json = False
        args.timeout = 5.0

        mock_param = create_mock_param("GT2_TEMP", 10, "tem")
        mock_client = MagicMock()
        mock_client.get.return_value = mock_param

        mock_adapter = MagicMock()

        with patch.object(cli, "read_from_broadcast") as mock_read_broadcast:
            mock_read_broadcast.return_value = None  # No data received

            captured_stderr = io.StringIO()
            sys.stderr = captured_stderr

            try:
                result = cli.cmd_read(mock_client, args, mock_adapter)
            finally:
                sys.stderr = sys.__stderr__

            error_output = captured_stderr.getvalue()

            # Verify error
            assert result == 1
            assert "ERROR" in error_output
            assert "GT2_TEMP" in error_output
            assert "not available via broadcast" in error_output


class TestAS2AutoFallbackOnInvalidRtr:
    """AS2.1: Auto fallback on invalid RTR acceptance tests."""

    def test_auto_fallback_on_invalid_rtr(self) -> None:
        """
        Given the CLI is connected and RTR read returns 0.1°C for a temperature parameter,
        When user runs `read GT2_TEMP`,
        Then the system automatically falls back to broadcast collection and returns the accurate value
        """
        from buderus_wps_cli import main as cli

        args = MagicMock()
        args.param = "GT2_TEMP"
        args.broadcast = False
        args.duration = 5.0
        args.no_fallback = False
        args.json = False
        args.timeout = 5.0

        mock_param = create_mock_param("GT2_TEMP", 10, "tem")
        mock_client = MagicMock()
        mock_client.get.return_value = mock_param
        # RTR returns 1-byte response (invalid)
        mock_client.read_value.return_value = bytes([0x01])
        mock_client._decode_value.return_value = 0.1

        mock_adapter = MagicMock()

        with patch.object(cli, "read_from_broadcast") as mock_read_broadcast:
            mock_read_broadcast.return_value = (10.5, bytes([0x00, 0x69]))

            captured_output = io.StringIO()
            captured_stderr = io.StringIO()
            sys.stdout = captured_output
            sys.stderr = captured_stderr

            try:
                result = cli.cmd_read(mock_client, args, mock_adapter)
            finally:
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__

            output = captured_output.getvalue()
            stderr = captured_stderr.getvalue()

            # Verify fallback was used
            assert result == 0
            assert "source=broadcast" in output
            assert "10.5" in output
            assert "WARNING" in stderr
            assert "broadcast fallback" in stderr


class TestAS2NoFallbackForValidRtr:
    """AS2.2: No fallback for valid RTR acceptance tests."""

    def test_no_fallback_when_rtr_valid(self) -> None:
        """
        Given the CLI is connected and RTR read returns a valid temperature value,
        When user runs `read GT2_TEMP`,
        Then the system returns the RTR value without attempting broadcast fallback
        """
        from buderus_wps_cli import main as cli

        args = MagicMock()
        args.param = "GT2_TEMP"
        args.broadcast = False
        args.duration = 5.0
        args.no_fallback = False
        args.json = False
        args.timeout = 5.0

        mock_param = create_mock_param("GT2_TEMP", 10, "tem")
        mock_client = MagicMock()
        mock_client.get.return_value = mock_param
        # RTR returns valid 2-byte response
        mock_client.read_value.return_value = bytes([0x00, 0x69])
        mock_client._decode_value.return_value = 10.5

        mock_adapter = MagicMock()

        with patch.object(cli, "read_from_broadcast") as mock_read_broadcast:
            captured_output = io.StringIO()
            sys.stdout = captured_output

            try:
                result = cli.cmd_read(mock_client, args, mock_adapter)
            finally:
                sys.stdout = sys.__stdout__

            output = captured_output.getvalue()

            # Verify no fallback was used
            assert result == 0
            assert "source=rtr" in output
            mock_read_broadcast.assert_not_called()


class TestAS2FallbackFailureWithWarning:
    """AS2.3: Fallback failure with warning acceptance tests."""

    def test_fallback_failure_shows_warning(self) -> None:
        """
        Given automatic fallback is triggered,
        When the broadcast fallback also fails to find the value,
        Then the system displays the original invalid RTR value with a warning that broadcast fallback was unsuccessful
        """
        from buderus_wps_cli import main as cli

        args = MagicMock()
        args.param = "GT2_TEMP"
        args.broadcast = False
        args.duration = 5.0
        args.no_fallback = False
        args.json = False
        args.timeout = 5.0

        mock_param = create_mock_param("GT2_TEMP", 10, "tem")
        mock_client = MagicMock()
        mock_client.get.return_value = mock_param
        # RTR returns 1-byte response (invalid)
        mock_client.read_value.return_value = bytes([0x01])
        mock_client._decode_value.return_value = 0.1

        mock_adapter = MagicMock()

        with patch.object(cli, "read_from_broadcast") as mock_read_broadcast:
            mock_read_broadcast.return_value = None  # Fallback also fails

            captured_output = io.StringIO()
            captured_stderr = io.StringIO()
            sys.stdout = captured_output
            sys.stderr = captured_stderr

            try:
                result = cli.cmd_read(mock_client, args, mock_adapter)
            finally:
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__

            output = captured_output.getvalue()
            stderr = captured_stderr.getvalue()

            # Verify warnings were shown
            assert result == 0  # Still returns, just with original data
            assert "source=rtr" in output  # Original RTR data used
            assert "WARNING" in stderr
            assert "fallback failed" in stderr


class TestAS3RtrSourceIndication:
    """AS3.1: RTR source indication acceptance tests."""

    def test_rtr_source_indicated_in_text_output(self) -> None:
        """
        Given a read is performed via RTR successfully,
        When the result is displayed,
        Then the output indicates the source was "RTR"
        """
        from buderus_wps_cli import main as cli

        args = MagicMock()
        args.param = "GT2_TEMP"
        args.broadcast = False
        args.duration = 5.0
        args.no_fallback = True  # Disable fallback to force RTR
        args.json = False
        args.timeout = 5.0

        mock_param = create_mock_param("GT2_TEMP", 10, "tem")
        mock_client = MagicMock()
        mock_client.get.return_value = mock_param
        mock_client.read_value.return_value = bytes([0x00, 0x69])
        mock_client._decode_value.return_value = 10.5

        mock_adapter = MagicMock()

        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            result = cli.cmd_read(mock_client, args, mock_adapter)
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue()

        assert result == 0
        assert "source=rtr" in output


class TestAS3BroadcastSourceIndication:
    """AS3.2: Broadcast source indication acceptance tests."""

    def test_broadcast_source_indicated_in_text_output(self) -> None:
        """
        Given a read is performed via broadcast (explicit or fallback),
        When the result is displayed,
        Then the output indicates the source was "broadcast"
        """
        from buderus_wps_cli import main as cli

        args = MagicMock()
        args.param = "GT2_TEMP"
        args.broadcast = True
        args.duration = 5.0
        args.no_fallback = False
        args.json = False
        args.timeout = 5.0

        mock_param = create_mock_param("GT2_TEMP", 10, "tem")
        mock_client = MagicMock()
        mock_client.get.return_value = mock_param

        mock_adapter = MagicMock()

        with patch.object(cli, "read_from_broadcast") as mock_read_broadcast:
            mock_read_broadcast.return_value = (10.5, bytes([0x00, 0x69]))

            captured_output = io.StringIO()
            sys.stdout = captured_output

            try:
                result = cli.cmd_read(mock_client, args, mock_adapter)
            finally:
                sys.stdout = sys.__stdout__

            output = captured_output.getvalue()

            assert result == 0
            assert "source=broadcast" in output


class TestAS3JsonSourceField:
    """AS3.3: JSON source field acceptance tests."""

    def test_json_output_includes_source_field_rtr(self) -> None:
        """
        Given JSON output mode is enabled,
        When a read is performed via RTR,
        Then the JSON includes a "source" field indicating "rtr"
        """
        from buderus_wps_cli import main as cli

        args = MagicMock()
        args.param = "GT2_TEMP"
        args.broadcast = False
        args.duration = 5.0
        args.no_fallback = True
        args.json = True
        args.timeout = 5.0

        mock_param = create_mock_param("GT2_TEMP", 10, "tem")
        mock_client = MagicMock()
        mock_client.get.return_value = mock_param
        mock_client.read_value.return_value = bytes([0x00, 0x69])
        mock_client._decode_value.return_value = 10.5

        mock_adapter = MagicMock()

        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            result = cli.cmd_read(mock_client, args, mock_adapter)
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        json_result = json.loads(output)

        assert result == 0
        assert "source" in json_result
        assert json_result["source"] == "rtr"

    def test_json_output_includes_source_field_broadcast(self) -> None:
        """
        Given JSON output mode is enabled,
        When a read is performed via broadcast,
        Then the JSON includes a "source" field indicating "broadcast"
        """
        from buderus_wps_cli import main as cli

        args = MagicMock()
        args.param = "GT2_TEMP"
        args.broadcast = True
        args.duration = 5.0
        args.no_fallback = False
        args.json = True
        args.timeout = 5.0

        mock_param = create_mock_param("GT2_TEMP", 10, "tem")
        mock_client = MagicMock()
        mock_client.get.return_value = mock_param

        mock_adapter = MagicMock()

        with patch.object(cli, "read_from_broadcast") as mock_read_broadcast:
            mock_read_broadcast.return_value = (10.5, bytes([0x00, 0x69]))

            captured_output = io.StringIO()
            sys.stdout = captured_output

            try:
                result = cli.cmd_read(mock_client, args, mock_adapter)
            finally:
                sys.stdout = sys.__stdout__

            output = captured_output.getvalue()
            json_result = json.loads(output)

            assert result == 0
            assert "source" in json_result
            assert json_result["source"] == "broadcast"
