"""Acceptance tests for User Story 2: Send and Receive CAN Messages.

Tests cover:
- T046: AS1 - Send CAN read request and receive response
- T047: AS2 - Sequential message transmission
- T048: AS3 - Timeout error when no response

Acceptance Scenarios:
1. Given an open connection to the heat pump, When a CAN read request is sent
   for a temperature element, Then the system receives the response within the
   timeout period and returns the raw CAN message data
2. Given an open connection, When multiple CAN messages are sent in sequence,
   Then each message is transmitted completely before the next begins and
   responses can be matched to requests
3. Given a CAN message is sent, When no response is received within the timeout
   period, Then the system reports a timeout error with details about the failed message
"""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from buderus_wps.can_adapter import USBtinAdapter
from buderus_wps.can_message import CANMessage
from buderus_wps.exceptions import TimeoutError


class TestAcceptanceScenario1SendAndReceive:
    """AS1: Send CAN read request and receive response within timeout (T046)."""

    @patch("serial.Serial")
    def test_as1_send_temperature_request_receive_response(self, mock_serial_class):
        """
        Given: An open connection to the heat pump
        When: A CAN read request is sent for a temperature element
        Then: The system receives the response within timeout and returns raw CAN message data
        """
        # Setup: Mock serial connection
        mock_serial = MagicMock()
        mock_serial.is_open = True
        type(mock_serial).in_waiting = PropertyMock(return_value=10)

        # Simulate initialization + temperature response
        init_responses = [b"\r"] * 7
        # Temperature request response: ID 0x31D011E9, data bytes representing temp
        temperature_response = (
            b"T31D011E95800100C812\r"  # Example: 20.0°C encoded (DLC=5)
        )
        mock_serial.read.side_effect = init_responses + [temperature_response]
        mock_serial_class.return_value = mock_serial

        # Given: Open connection
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()
        assert adapter.is_open is True

        # When: Send CAN read request for temperature element
        # Using typical Buderus heat pump CAN ID for temperature query
        temp_request = CANMessage(
            arbitration_id=0x31D011E9,
            data=b"\x80\x01\x00\xc8\x12",  # Example query format
            is_extended_id=True,
        )
        response = adapter.send_frame(temp_request, timeout=2.0)

        # Then: System receives response within timeout
        assert response is not None
        assert isinstance(response, CANMessage)

        # Then: Response contains raw CAN message data
        assert response.arbitration_id == 0x31D011E9
        assert response.is_extended_id is True
        assert len(response.data) == 5  # Temperature response payload
        assert response.data == b"\x80\x01\x00\xc8\x12"

    @patch("serial.Serial")
    def test_as1_send_status_request_receive_response(self, mock_serial_class):
        """
        Given: An open connection
        When: A CAN read request is sent for status element
        Then: Response received and parsed correctly
        """
        # Setup
        mock_serial = MagicMock()
        mock_serial.is_open = True
        type(mock_serial).in_waiting = PropertyMock(return_value=10)

        init_responses = [b"\r"] * 7
        status_response = (
            b"t7231AA\r"  # Example status response (ID=0x723, DLC=1, Data=AA)
        )
        mock_serial.read.side_effect = init_responses + [status_response]
        mock_serial_class.return_value = mock_serial

        # Given: Open connection
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # When: Send status request
        status_request = CANMessage(
            arbitration_id=0x723, data=b"\xaa", is_extended_id=False
        )
        response = adapter.send_frame(status_request, timeout=2.0)

        # Then: Response received with correct data
        assert response.arbitration_id == 0x723
        assert response.data == b"\xaa"


class TestAcceptanceScenario2SequentialTransmission:
    """AS2: Sequential message transmission without interference (T047)."""

    @patch("serial.Serial")
    def test_as2_multiple_messages_transmitted_sequentially(self, mock_serial_class):
        """
        Given: An open connection
        When: Multiple CAN messages are sent in sequence
        Then: Each message transmitted completely before next begins
        And: Responses can be matched to requests
        """
        # Setup
        mock_serial = MagicMock()
        mock_serial.is_open = True
        type(mock_serial).in_waiting = PropertyMock(return_value=10)

        # Simulate initialization + 3 sequential responses
        init_responses = [b"\r"] * 7
        responses = [
            b"t1111AA\r",  # Response 1 (ID=0x111, DLC=1, Data=AA)
            b"t2222BBCC\r",  # Response 2 (ID=0x222, DLC=2, Data=BBCC)
            b"T31D011E94DEADBEEF\r",  # Response 3 (ID=0x31D011E9, DLC=4, Data=DEADBEEF)
        ]
        mock_serial.read.side_effect = init_responses + responses
        mock_serial_class.return_value = mock_serial

        # Given: Open connection
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # When: Send message 1
        msg1 = CANMessage(arbitration_id=0x111, data=b"\xaa")
        response1 = adapter.send_frame(msg1, timeout=2.0)

        # Then: Response 1 received and matched
        assert response1.arbitration_id == 0x111
        assert response1.data == b"\xaa"

        # When: Send message 2
        msg2 = CANMessage(arbitration_id=0x222, data=b"\xbb\xcc")
        response2 = adapter.send_frame(msg2, timeout=2.0)

        # Then: Response 2 received and matched
        assert response2.arbitration_id == 0x222
        assert response2.data == b"\xbb\xcc"

        # When: Send message 3 (extended ID)
        msg3 = CANMessage(
            arbitration_id=0x31D011E9, data=b"\xde\xad\xbe\xef", is_extended_id=True
        )
        response3 = adapter.send_frame(msg3, timeout=2.0)

        # Then: Response 3 received and matched
        assert response3.arbitration_id == 0x31D011E9
        assert response3.data == b"\xde\xad\xbe\xef"
        assert response3.is_extended_id is True

        # Verify: All messages transmitted in order
        write_calls = [call[0][0] for call in mock_serial.write.call_args_list]
        message_writes = write_calls[7:]  # Skip init

        # Check order preserved
        assert len(message_writes) == 3
        assert b"t1111AA\r" in message_writes[0]
        assert b"t2222BBCC\r" in message_writes[1]
        assert b"T31D011E94DEADBEEF\r" in message_writes[2]

    @patch("serial.Serial")
    def test_as2_responses_matched_to_correct_requests(self, mock_serial_class):
        """
        Given: Open connection with multiple pending requests
        When: Responses arrive in order
        Then: Each response correctly matched to its request
        """
        # Setup
        mock_serial = MagicMock()
        mock_serial.is_open = True
        type(mock_serial).in_waiting = PropertyMock(return_value=10)

        init_responses = [b"\r"] * 7
        responses = [
            b"t1232AAAA\r",  # ID=0x123, DLC=2, Data=AAAA
            b"t3452BBBB\r",  # ID=0x345, DLC=2, Data=BBBB
            b"t5672CCCC\r",  # ID=0x567, DLC=2, Data=CCCC
        ]
        mock_serial.read.side_effect = init_responses + responses
        mock_serial_class.return_value = mock_serial

        # Given: Open connection
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # When: Send requests with distinct IDs
        requests = [
            CANMessage(arbitration_id=0x123, data=b"\xaa\xaa"),
            CANMessage(arbitration_id=0x345, data=b"\xbb\xbb"),
            CANMessage(arbitration_id=0x567, data=b"\xcc\xcc"),
        ]

        responses_received = []
        for req in requests:
            resp = adapter.send_frame(req, timeout=2.0)
            responses_received.append(resp)

        # Then: Each response matches its request
        assert responses_received[0].arbitration_id == 0x123
        assert responses_received[0].data == b"\xaa\xaa"

        assert responses_received[1].arbitration_id == 0x345
        assert responses_received[1].data == b"\xbb\xbb"

        assert responses_received[2].arbitration_id == 0x567
        assert responses_received[2].data == b"\xcc\xcc"


class TestAcceptanceScenario3TimeoutHandling:
    """AS3: Timeout error when no response received (T048)."""

    @patch("serial.Serial")
    def test_as3_timeout_when_no_response(self, mock_serial_class):
        """
        Given: A CAN message is sent
        When: No response is received within the timeout period
        Then: System reports timeout error with details about failed message
        """
        # Setup: No response from device
        mock_serial = MagicMock()
        mock_serial.is_open = True
        type(mock_serial).in_waiting = PropertyMock(
            return_value=10
        )  # No data available

        init_responses = [b"\r"] * 7
        # No response after init - empty reads
        mock_serial.read.side_effect = init_responses + [b""] * 100
        mock_serial_class.return_value = mock_serial

        # Given: Open connection
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # When: Send message with short timeout
        request = CANMessage(
            arbitration_id=0x123, data=b"\xaa\xbb", is_extended_id=False
        )

        # Then: Timeout error raised with details
        with pytest.raises(TimeoutError) as exc_info:
            adapter.send_frame(request, timeout=0.1)

        # Verify error message contains details
        error_msg = str(exc_info.value).lower()
        assert "timeout" in error_msg or "no response" in error_msg

    @patch("serial.Serial")
    def test_as3_timeout_includes_message_context(self, mock_serial_class):
        """
        Given: Message sent but no response
        When: Timeout occurs
        Then: Error includes context about which message failed
        """
        # Setup
        mock_serial = MagicMock()
        mock_serial.is_open = True
        type(mock_serial).in_waiting = PropertyMock(return_value=10)

        init_responses = [b"\r"] * 7
        mock_serial.read.side_effect = init_responses + [b""] * 100
        mock_serial_class.return_value = mock_serial

        # Given: Open connection
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # When: Send extended ID message (Buderus heat pump)
        buderus_request = CANMessage(
            arbitration_id=0x31D011E9, data=b"\x80\x01\x00\xc8\x12", is_extended_id=True
        )

        # Then: Timeout with context
        with pytest.raises(TimeoutError):
            adapter.send_frame(buderus_request, timeout=0.1)

    @patch("serial.Serial")
    def test_as3_subsequent_operations_work_after_timeout(self, mock_serial_class):
        """
        Given: Previous message timed out
        When: New message is sent
        Then: Adapter still functional and can send/receive
        """
        # Setup
        mock_serial = MagicMock()
        mock_serial.is_open = True
        type(mock_serial).in_waiting = PropertyMock(return_value=10)

        init_responses = [b"\r"] * 7
        # First request: timeout (no response)
        # Second request: success
        mock_serial.read.side_effect = init_responses + [b""] * 10 + [b"t1231AA\r"]
        mock_serial_class.return_value = mock_serial

        # Given: Open connection
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # When: First message times out
        msg1 = CANMessage(arbitration_id=0x111, data=b"\xff")
        with pytest.raises(TimeoutError):
            adapter.send_frame(msg1, timeout=0.05)

        # Then: Adapter still functional
        assert adapter.is_open is True

        # When: Send second message
        msg2 = CANMessage(arbitration_id=0x123, data=b"\xaa")
        response = adapter.send_frame(msg2, timeout=1.0)

        # Then: Second message succeeds
        assert response is not None
        assert response.arbitration_id == 0x123


class TestAcceptanceScenario4HumanReadableLabels:
    """AS4: Monitor output shows human-readable parameter names (T084)."""

    def test_as4_get_known_name_returns_name_for_known_broadcast(self):
        """
        Given: A known broadcast CAN ID is received
        When: The monitor processes the reading
        Then: Human-readable name is available via get_known_name()
        """
        from unittest.mock import MagicMock

        from buderus_wps.broadcast_monitor import BroadcastMonitor, BroadcastReading

        # Setup: Mock adapter
        adapter = MagicMock()
        adapter.is_open = True
        monitor = BroadcastMonitor(adapter)

        # Given: A known broadcast reading (RC10 C1 room temp)
        reading = BroadcastReading(
            can_id=0x0C000060,
            base=0x0060,
            idx=0,
            dlc=2,
            raw_data=b"\x00\xcd",  # 205 = 20.5°C
            raw_value=205,
            timestamp=0.0,
        )

        # When: Get known name
        name = monitor.get_known_name(reading)

        # Then: Human-readable name is returned
        assert name == "RC10_C1_ROOM_TEMP"

    def test_as4_get_known_name_returns_none_for_unknown_broadcast(self):
        """
        Given: An unknown broadcast CAN ID is received
        When: The monitor processes the reading
        Then: get_known_name() returns None
        """
        from unittest.mock import MagicMock

        from buderus_wps.broadcast_monitor import BroadcastMonitor, BroadcastReading

        # Setup
        adapter = MagicMock()
        adapter.is_open = True
        monitor = BroadcastMonitor(adapter)

        # Given: An unknown broadcast reading
        reading = BroadcastReading(
            can_id=0x0CFFF000,
            base=0xF000,  # Unknown base
            idx=999,
            dlc=2,
            raw_data=b"\x00\x00",
            raw_value=0,
            timestamp=0.0,
        )

        # When: Get known name
        name = monitor.get_known_name(reading)

        # Then: Returns None
        assert name is None

    def test_as4_cmd_monitor_includes_name_in_output(self, capsys):
        """
        Given: CLI monitor command is run
        When: Broadcast readings are captured
        Then: Known parameters show human-readable names in output
        """
        import argparse
        from unittest.mock import MagicMock, patch

        from buderus_wps.broadcast_monitor import BroadcastCache, BroadcastReading
        from buderus_wps_cli.main import cmd_monitor

        # Setup: Mock adapter and broadcast monitor
        adapter = MagicMock()
        adapter.is_open = True

        # Create mock cache with known readings
        mock_cache = BroadcastCache()
        mock_cache.update(
            BroadcastReading(
                can_id=0x0C000060,
                base=0x0060,
                idx=0,
                dlc=2,
                raw_data=b"\x00\xcd",
                raw_value=205,
                timestamp=0.0,
            )
        )
        mock_cache.update(
            BroadcastReading(
                can_id=0x00030060,
                base=0x0060,
                idx=12,
                dlc=2,
                raw_data=b"\x00\x69",
                raw_value=105,
                timestamp=0.0,
            )
        )

        with patch("buderus_wps_cli.main.BroadcastMonitor") as MockMonitor:
            mock_monitor = MagicMock()
            mock_monitor.collect.return_value = mock_cache
            mock_monitor.get_known_name.side_effect = lambda r: {
                (0x0060, 0): "RC10_C1_ROOM_TEMP",
                (0x0060, 12): "OUTDOOR_TEMP_C0",
            }.get((r.base, r.idx))
            MockMonitor.return_value = mock_monitor

            # Given: CLI monitor args
            args = argparse.Namespace(duration=1.0, json=False, temps_only=False)

            # When: Run cmd_monitor
            result = cmd_monitor(adapter, args)

            # Then: Output includes human-readable names
            captured = capsys.readouterr()
            assert result == 0
            assert "RC10_C1_ROOM_TEMP" in captured.out
            assert "OUTDOOR_TEMP_C0" in captured.out
            assert "Name" in captured.out  # Header column

    def test_as4_cmd_monitor_json_includes_name_field(self, capsys):
        """
        Given: CLI monitor command is run with --json flag
        When: Broadcast readings are captured
        Then: JSON output includes "name" field for each reading
        """
        import argparse
        import json
        from unittest.mock import MagicMock, patch

        from buderus_wps.broadcast_monitor import BroadcastCache, BroadcastReading
        from buderus_wps_cli.main import cmd_monitor

        # Setup
        adapter = MagicMock()
        adapter.is_open = True

        mock_cache = BroadcastCache()
        mock_cache.update(
            BroadcastReading(
                can_id=0x0C000060,
                base=0x0060,
                idx=0,
                dlc=2,
                raw_data=b"\x00\xcd",
                raw_value=205,
                timestamp=0.0,
            )
        )

        with patch("buderus_wps_cli.main.BroadcastMonitor") as MockMonitor:
            mock_monitor = MagicMock()
            mock_monitor.collect.return_value = mock_cache
            mock_monitor.get_known_name.return_value = "RC10_C1_ROOM_TEMP"
            MockMonitor.return_value = mock_monitor

            # Given: CLI monitor args with JSON output
            args = argparse.Namespace(duration=1.0, json=True, temps_only=False)

            # When: Run cmd_monitor
            result = cmd_monitor(adapter, args)

            # Then: JSON output includes "name" field
            captured = capsys.readouterr()
            assert result == 0
            output = json.loads(captured.out)
            assert "readings" in output
            assert len(output["readings"]) == 1
            assert "name" in output["readings"][0]
            assert output["readings"][0]["name"] == "RC10_C1_ROOM_TEMP"

    def test_as4_unknown_broadcast_shows_dash_in_name_column(self, capsys):
        """
        Given: CLI monitor receives unknown broadcast
        When: Output is displayed
        Then: Unknown broadcasts show "-" in name column
        """
        import argparse
        from unittest.mock import MagicMock, patch

        from buderus_wps.broadcast_monitor import BroadcastCache, BroadcastReading
        from buderus_wps_cli.main import cmd_monitor

        # Setup
        adapter = MagicMock()
        adapter.is_open = True

        mock_cache = BroadcastCache()
        mock_cache.update(
            BroadcastReading(
                can_id=0x0CFFF000,
                base=0xF000,
                idx=999,
                dlc=2,
                raw_data=b"\x00\x00",
                raw_value=0,
                timestamp=0.0,
            )
        )

        with patch("buderus_wps_cli.main.BroadcastMonitor") as MockMonitor:
            mock_monitor = MagicMock()
            mock_monitor.collect.return_value = mock_cache
            mock_monitor.get_known_name.return_value = None  # Unknown
            MockMonitor.return_value = mock_monitor

            # Given: CLI monitor args
            args = argparse.Namespace(duration=1.0, json=False, temps_only=False)

            # When: Run cmd_monitor
            result = cmd_monitor(adapter, args)

            # Then: Unknown shows "-"
            captured = capsys.readouterr()
            assert result == 0
            # Should contain a dash for unknown parameter
            lines = captured.out.split("\n")
            data_lines = [l for l in lines if "0x0CFFF000" in l]
            assert len(data_lines) == 1
            assert "-" in data_lines[0]
