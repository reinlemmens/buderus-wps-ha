"""Unit tests for alarm parsing and management."""

from unittest.mock import MagicMock

from buderus_wps.menu_api import AlarmCategory, AlarmController


class TestAlarmController:
    """Test AlarmController functionality."""

    def test_active_alarms_parsing(self):
        """Test parsing of active alarms from ADDITIONAL_ALARM parameters."""
        mock_client = MagicMock()

        # Mock responses for alarm_log_1 (ADDITIONAL_ALARM) through alarm_log_5
        # Index 1 (ADDITIONAL_ALARM) returns error code 5283
        # Index 2 returns 0 (no alarm)
        # Others return 0
        def read_param_side_effect(param_name):
            if param_name == "ADDITIONAL_ALARM":
                return {"decoded": 5283}
            return {"decoded": 0}

        mock_client.read_parameter.side_effect = read_param_side_effect

        msg_controller = AlarmController(mock_client)
        active = msg_controller.active_alarms

        assert len(active) == 1
        alarm = active[0]
        assert alarm.code == 5283
        assert "Error 5283" in alarm.description
        assert alarm.category == AlarmCategory.ALARM

        # Verify correct parameter was read
        # Note: ALARM_PARAMS["alarm_log_1"] maps to "ADDITIONAL_ALARM" now
        mock_client.read_parameter.assert_any_call("ADDITIONAL_ALARM")

    def test_no_active_alarms(self):
        """Test when no alarms are active."""
        mock_client = MagicMock()
        mock_client.read_parameter.return_value = {"decoded": 0}

        msg_controller = AlarmController(mock_client)
        active = msg_controller.active_alarms

        assert len(active) == 0

    def test_parse_alarm_handles_none(self):
        """Test _parse_alarm handles None/empty decoder results."""
        mock_client = MagicMock()
        controller = AlarmController(mock_client)

        # Result with no decoded value
        assert controller._parse_alarm({}, 1) is None

        # Result with None decoded
        assert controller._parse_alarm({"decoded": None}, 1) is None

        # Result with 0 decoded
        assert controller._parse_alarm({"decoded": 0}, 1) is None
