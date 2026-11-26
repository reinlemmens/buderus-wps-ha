"""Coordinator side of the alarm-pending feature (issue #25): read, detect, persist, fire."""

from unittest.mock import MagicMock

import pytest

from custom_components.buderus_wps.const import EVENT_ALARM
from custom_components.buderus_wps.coordinator import BuderusCoordinator


def make(mock_hass, entry_id="entry1"):
    c = BuderusCoordinator(mock_hass, "/dev/ttyACM0", 60, entry_id=entry_id)
    c.hass = mock_hass  # mocked parent does not set this
    c._client = MagicMock()
    c._registry = MagicMock()  # is_discovered() is truthy unless a test says otherwise
    return c


class TestRead:
    def test_reads_by_name_without_validation(self, mock_hass):
        c = make(mock_hass)
        c._client.read_parameter.return_value = {"decoded": 4}
        assert c._sync_read_system_status() == 4
        c._client.read_parameter.assert_called_once_with(
            "RTU800B_SYSTEM_STATUS", timeout=0.5
        )
        c._client.read_parameter_with_validation.assert_not_called()

    def test_failed_read_keeps_previous_value(self, mock_hass):
        c = make(mock_hass)
        c._last_known_good_data = MagicMock(system_status=1)
        c._client.read_parameter.side_effect = TimeoutError("no answer")
        assert c._sync_read_system_status() == 1

    def test_failed_read_without_cache_is_none(self, mock_hass):
        c = make(mock_hass)
        c._client.read_parameter.side_effect = TimeoutError("no answer")
        assert c._sync_read_system_status() is None

    @pytest.mark.parametrize("decoded", [None, "4", 4.5, True])
    def test_unusable_answer_is_no_reading(self, mock_hass, decoded):
        c = make(mock_hass)
        c._client.read_parameter.return_value = {"decoded": decoded}
        assert c._sync_read_system_status() is None


class TestReadGuards:
    """The read must not guess and must not fail silently forever."""

    def test_parameter_this_pump_did_not_report_is_never_read(self, mock_hass):
        c = make(mock_hass)
        c._registry.is_discovered.return_value = False
        c._last_known_good_data = MagicMock(system_status=4)
        assert c._sync_read_system_status() is None
        c._registry.is_discovered.assert_called_with("RTU800B_SYSTEM_STATUS")
        c._client.read_parameter.assert_not_called()

    def test_no_registry_is_no_reading(self, mock_hass):
        c = make(mock_hass)
        c._registry = None
        assert c._sync_read_system_status() is None
        c._client.read_parameter.assert_not_called()

    @staticmethod
    def _warnings(caplog):
        return [
            r
            for r in caplog.records
            if r.levelname == "WARNING" and "RTU800B_SYSTEM_STATUS" in r.getMessage()
        ]

    def test_persistent_read_failure_warns_once(self, mock_hass, caplog):
        c = make(mock_hass)
        c._last_known_good_data = MagicMock(system_status=1)
        c._client.read_parameter.side_effect = TimeoutError("no answer")
        with caplog.at_level("WARNING"):
            for _ in range(9):
                assert c._sync_read_system_status() == 1
            assert self._warnings(caplog) == []
            for _ in range(16):
                assert c._sync_read_system_status() == 1
        assert len(self._warnings(caplog)) == 1

    def test_failure_warning_comes_again_after_a_recovery(self, mock_hass, caplog):
        c = make(mock_hass)
        c._last_known_good_data = MagicMock(system_status=1)
        answers = [TimeoutError("no answer")] * 10 + [{"decoded": 1}]
        c._client.read_parameter.side_effect = answers + answers[:10]
        with caplog.at_level("WARNING"):
            for _ in range(21):
                assert c._sync_read_system_status() == 1
        assert len(self._warnings(caplog)) == 2


class TestHomeAssistantStillStarting:
    """Automations attach their triggers only once HA is running."""

    async def test_alarm_raised_during_restart_waits_for_ha_start(self, mock_hass):
        c = make(mock_hass)
        c._alarm_store.data = {"pending": False, "last_alarm": None}
        await c._async_load_alarm_state()

        mock_hass.state = "NOT_RUNNING"
        c._handle_system_status(4)
        mock_hass.bus.async_fire.assert_not_called()
        assert c._alarm_tracker.pending is False
        assert c.last_alarm is None
        assert c._alarm_store.saved is None

        mock_hass.state = "RUNNING"
        c._handle_system_status(4)
        mock_hass.bus.async_fire.assert_called_once_with(
            EVENT_ALARM,
            {
                "entry_id": "entry1",
                "status": 4,
                "previous_status": None,
                "after_restart": True,
            },
        )

    def test_alarm_seen_while_ha_is_stopping_is_kept_for_next_start(self, mock_hass):
        c = make(mock_hass)
        c._handle_system_status(1)
        mock_hass.state = "STOPPING"
        c._handle_system_status(4)
        mock_hass.bus.async_fire.assert_not_called()
        assert c._alarm_store.saved == {"pending": False, "last_alarm": None}


class TestDetection:
    def test_new_alarm_fires_event_and_saves(self, mock_hass):
        c = make(mock_hass)
        c._handle_system_status(1)
        c._handle_system_status(4)
        mock_hass.bus.async_fire.assert_called_once_with(
            EVENT_ALARM,
            {
                "entry_id": "entry1",
                "status": 4,
                "previous_status": 1,
                "after_restart": False,
            },
        )
        assert c._alarm_store.saved["pending"] is True
        assert c.last_alarm is not None and c.last_alarm.tzinfo is not None

    def test_still_pending_does_not_fire_again(self, mock_hass):
        c = make(mock_hass)
        for s in (1, 4, 4, 4):
            c._handle_system_status(s)
        assert mock_hass.bus.async_fire.call_count == 1

    def test_no_reading_fires_nothing(self, mock_hass):
        c = make(mock_hass)
        c._handle_system_status(None)
        mock_hass.bus.async_fire.assert_not_called()
        assert c._alarm_store.saved is None

    def test_save_failure_does_not_block_event_or_raise(self, mock_hass):
        c = make(mock_hass)
        c._handle_system_status(1)
        c._alarm_store.save_error = OSError("disk full")
        c._handle_system_status(4)
        assert mock_hass.bus.async_fire.call_count == 1

    def test_yaml_setup_without_entry_id(self, mock_hass):
        c = make(mock_hass, entry_id=None)
        assert c._alarm_store.key == "buderus_wps.alarm_state.yaml"
        c._handle_system_status(1)
        c._handle_system_status(4)
        assert mock_hass.bus.async_fire.call_args[0][1]["entry_id"] is None

    def test_storage_key_per_entry(self, mock_hass):
        assert make(mock_hass)._alarm_store.key == "buderus_wps.alarm_state.entry1"


class TestRestart:
    async def test_alarm_raised_during_restart_fires(self, mock_hass):
        c = make(mock_hass)
        c._alarm_store.data = {"pending": False, "last_alarm": None}
        await c._async_load_alarm_state()
        c._handle_system_status(4)
        mock_hass.bus.async_fire.assert_called_once_with(
            EVENT_ALARM,
            {
                "entry_id": "entry1",
                "status": 4,
                "previous_status": None,
                "after_restart": True,
            },
        )

    async def test_alarm_already_pending_before_restart_is_silent(self, mock_hass):
        c = make(mock_hass)
        c._alarm_store.data = {
            "pending": True,
            "last_alarm": "2026-11-25T02:42:00+00:00",
        }
        await c._async_load_alarm_state()
        c._handle_system_status(4)
        mock_hass.bus.async_fire.assert_not_called()
        assert c.last_alarm.isoformat() == "2026-11-25T02:42:00+00:00"

    @pytest.mark.parametrize("data", [None, "junk", {"pending": "yes"}])
    async def test_missing_or_bad_store_is_a_fresh_install(self, mock_hass, data):
        c = make(mock_hass)
        c._alarm_store.data = data
        await c._async_load_alarm_state()
        c._handle_system_status(4)
        mock_hass.bus.async_fire.assert_not_called()

    async def test_unreadable_store_does_not_break_setup(self, mock_hass):
        c = make(mock_hass)
        c._alarm_store.load_error = OSError("corrupt")
        await c._async_load_alarm_state()  # must not raise
        c._handle_system_status(4)
        mock_hass.bus.async_fire.assert_not_called()


class TestWiring:
    """The pieces above are actually called by setup and by the update cycle."""

    async def test_update_cycle_runs_detection_on_fresh_data(self, mock_hass):
        c = make(mock_hass)
        c._connected = True
        c._sync_fetch_data = MagicMock(
            side_effect=[MagicMock(system_status=1), MagicMock(system_status=4)]
        )
        await c._async_update_data_inner()
        mock_hass.bus.async_fire.assert_not_called()
        await c._async_update_data_inner()
        assert mock_hass.bus.async_fire.call_count == 1
        assert mock_hass.bus.async_fire.call_args[0][0] == EVENT_ALARM

    async def test_stale_data_cycle_does_not_run_detection(self, mock_hass):
        c = make(mock_hass)
        c._handle_system_status(1)
        c._connected = False
        c._last_known_good_data = MagicMock(system_status=4)
        assert await c._async_update_data_inner() is c._last_known_good_data
        mock_hass.bus.async_fire.assert_not_called()

    async def test_setup_restores_alarm_state(self, mock_hass):
        c = make(mock_hass)
        c._sync_connect = MagicMock()
        c._start_watchdog = MagicMock()
        c._alarm_store.data = {"pending": False, "last_alarm": None}
        assert await c.async_setup() is True
        c._handle_system_status(4)
        assert mock_hass.bus.async_fire.call_args[0][1]["after_restart"] is True

    def test_fetch_puts_status_into_data(self, mock_hass):
        c = make(mock_hass)
        c._monitor = MagicMock()
        c.energy_blocking = MagicMock()

        def read(name, **kwargs):
            return {"decoded": 4 if name == "RTU800B_SYSTEM_STATUS" else 0}

        c._client.read_parameter.side_effect = read
        c._client.read_parameter_with_validation.return_value = {"decoded": 0}
        assert c._sync_fetch_data().system_status == 4
