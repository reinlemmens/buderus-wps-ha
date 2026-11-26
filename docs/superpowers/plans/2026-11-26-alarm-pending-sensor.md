# Alarm Pending Sensor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show in Home Assistant whether the heat pump has unconfirmed alarms, remember when the last new alarm was detected, and fire an event on each new alarm, including one raised while HA was restarting.

**Architecture:** The coordinator reads `RTU800B_SYSTEM_STATUS` once per update cycle. A small HA-free `AlarmTracker` turns the sequence of readings into "new alarm" edges; the coordinator owns it, persists its state with HA's `Store`, and fires the event. Three thin entities read from the coordinator. The wrong alarm code in the bundled library is replaced by a two-property read-only controller.

**Tech Stack:** Python 3.9+, Home Assistant custom integration (`DataUpdateCoordinator`, `helpers.storage.Store`), pytest with the mocked-HA fixtures in `tests/conftest.py`.

**Spec:** `docs/superpowers/specs/2026-11-25-alarm-pending-sensor-design.md`

## Global Constraints

- Python 3.9 compatible. Library files under `custom_components/buderus_wps/buderus_wps/` are type-checked by mypy on 3.9: use `Optional[X]`, not `X | None`, there. Integration files already use `from __future__ import annotations`.
- Parameter is always addressed by name `RTU800B_SYSTEM_STATUS` (idx differs per firmware: 2178 in the built-in table, 2182 on the reference pump). Never hard-code the index.
- Use the plain `read_parameter`, never `read_parameter_with_validation`: the table lists the range as 0..0 and validation would reject real values.
- Status mapping, exact: `4` = pending; `0`, `1`, `3` = not pending; anything else = unknown.
- Event name, exact: `buderus_wps_alarm`. Payload keys, exact: `entry_id`, `status`, `previous_status`, `after_restart`.
- No bus writes. This feature only adds one read per cycle.
- New-alarm detection must not depend on any entity being enabled.
- `hass.bus.async_fire` and `Store` calls happen in the event loop, never in the executor thread (`_sync_*` methods run in the executor).
- Tests run with `~/dev/buderus-wps-ha/venv/bin/python -m pytest <path> --no-cov -q` from the worktree root. Baseline before this plan: 1162 passed, 4 skipped.
- Lint: `~/dev/buderus-wps-ha/venv/bin/python -m ruff check --config pyproject.toml custom_components/buderus_wps/ tests/` (called "ruff" below).
- Commit messages end with `Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>`. Do not push.
- `tests/fixtures/alarm_log_panel_photos.json` is not part of this change: never `git add` it (no `git add -A`).
- `specs/007-heatpump-menu-api/` is history: leave untouched.

## Review Focus

Conditions the spec implies but does not spell out. Each has a test in the task named.

1. Stored alarm state is unreadable or not a dict at startup: setup still succeeds and behaves like a fresh install, no event. (Task 3)
2. Stored state has the right keys but wrong types (`pending: "yes"`, `last_alarm: "garbage"`): bad fields are dropped, good ones kept, no exception. (Task 2)
3. The pump answers with something that is not a whole number (`None`, `4.0`, `"4"`, `True`): `4.0` counts as 4, everything else as "no reading"; the update cycle continues. (Task 1)
4. Saving the state fails (disk full, store error): the update cycle still returns data and the event still fires. (Task 3)
5. YAML setup without a config entry: storage key and event payload work with `entry_id` absent. (Task 3)

## File Structure

| File | Responsibility |
|---|---|
| `custom_components/buderus_wps/buderus_wps/alarm_status.py` (new) | Parameter name, status values, raw value to meaning. HA-free. |
| `custom_components/buderus_wps/alarm_tracker.py` (new) | Edge detection and the state that survives restarts. HA-free. |
| `custom_components/buderus_wps/coordinator.py` | Read per cycle, own the tracker, persist, fire event. |
| `custom_components/buderus_wps/const.py` | Event name, storage constants. |
| `custom_components/buderus_wps/__init__.py` | Pass `entry_id` to the coordinator. |
| `custom_components/buderus_wps/binary_sensor.py`, `sensor.py` | Three entities. |
| `custom_components/buderus_wps/buderus_wps/menu_api.py`, `menu_structure.py`, `enums.py`, `exceptions.py`, `__init__.py` | Cleanup of the wrong alarm code. |
| `tests/conftest.py` | HA mocks for `Store`, `TIMESTAMP`, `PROBLEM`, `EntityCategory`; `system_status` on `MockBuderusData`. |

---

### Task 1: Status mapping in the library

**Files:**
- Create: `custom_components/buderus_wps/buderus_wps/alarm_status.py`
- Modify: `custom_components/buderus_wps/buderus_wps/__init__.py` (export the four names below)
- Modify: `docs/PROTOCOL.md` (new section before "## Implementation Notes")
- Test: `tests/unit/test_alarm_status.py`

**Interfaces:**
- Produces:
  - `SYSTEM_STATUS_PARAM: str = "RTU800B_SYSTEM_STATUS"`
  - `STATUS_ALARM_PENDING: int = 4`
  - `alarm_pending(status: Optional[int]) -> Optional[bool]`
  - `parse_system_status(decoded: Any) -> Optional[int]`

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from buderus_wps.alarm_status import (
    STATUS_ALARM_PENDING,
    SYSTEM_STATUS_PARAM,
    alarm_pending,
    parse_system_status,
)


def test_constants():
    assert SYSTEM_STATUS_PARAM == "RTU800B_SYSTEM_STATUS"
    assert STATUS_ALARM_PENDING == 4


@pytest.mark.parametrize(
    "status,expected",
    [(4, True), (0, False), (1, False), (3, False), (2, None), (5, None), (255, None), (None, None)],
)
def test_alarm_pending(status, expected):
    assert alarm_pending(status) is expected


@pytest.mark.parametrize(
    "decoded,expected",
    [(4, 4), (0, 0), (4.0, 4), (None, None), (4.5, None), ("4", None), (True, None), (b"\x04", None)],
)
def test_parse_system_status(decoded, expected):
    assert parse_system_status(decoded) == expected


def test_exported_from_package():
    import buderus_wps

    assert buderus_wps.alarm_pending(4) is True
    assert buderus_wps.SYSTEM_STATUS_PARAM == "RTU800B_SYSTEM_STATUS"
```

- [ ] **Step 2: Run to verify failure**

Run: `~/dev/buderus-wps-ha/venv/bin/python -m pytest tests/unit/test_alarm_status.py --no-cov -q`
Expected: collection error, `No module named 'buderus_wps.alarm_status'`

- [ ] **Step 3: Implement `alarm_status.py` and the exports**

`parse_system_status`: `bool` is rejected even though it is an `int` subclass. The module docstring states the evidence table from the spec ("What the pump gives us") in four lines.

- [ ] **Step 4: Add the "Alarm Status" section to `docs/PROTOCOL.md`**

Content, taken from the spec: the parameter name and the by-name rule; the value table (4, 3, 0, 1); the confirm sequence (4 → 3 → 0 → 1, with a full node re-poll by the pump between 3 and 0); the same value is broadcast by the pump to the room units about every 15 s (type 0, idx 2, e.g. `0x00008060`..`0x00008063` on the reference installation); and the negative result: the stored alarm log, alarm texts and single OK presses do not appear on the bus, the whole parameter and service index space was swept read-only.

- [ ] **Step 5: Run tests and lint**

Run: `~/dev/buderus-wps-ha/venv/bin/python -m pytest tests/unit/test_alarm_status.py --no-cov -q` → all pass
Run: ruff (command in Global Constraints) → clean

- [ ] **Step 6: Commit**

```bash
git add custom_components/buderus_wps/buderus_wps/alarm_status.py custom_components/buderus_wps/buderus_wps/__init__.py docs/PROTOCOL.md tests/unit/test_alarm_status.py
git commit -m "feat: decode the alarm-pending system status value (#25)"
```

---

### Task 2: AlarmTracker (edge detection, restart memory)

**Files:**
- Create: `custom_components/buderus_wps/alarm_tracker.py`
- Test: `tests/unit/test_alarm_tracker.py`

**Interfaces:**
- Consumes: `alarm_pending` from Task 1 (`from .buderus_wps.alarm_status import alarm_pending`).
- Produces:

```python
@dataclass(frozen=True)
class NewAlarm:
    status: int
    previous_status: int | None   # None when the predecessor is only remembered
    after_restart: bool
    detected_at: datetime          # timezone-aware UTC


class AlarmTracker:
    def __init__(self, remembered_pending: bool | None = None, last_alarm: datetime | None = None) -> None: ...
    @property
    def pending(self) -> bool | None: ...      # last known, from readings or memory
    @property
    def last_alarm(self) -> datetime | None: ...
    def update(self, status: int | None, now: datetime) -> NewAlarm | None: ...
    def as_dict(self) -> dict[str, Any]: ...    # {"pending": bool|None, "last_alarm": ISO str|None}
    @classmethod
    def from_dict(cls, data: Any) -> AlarmTracker: ...
```

Rules for `update` (the spec's "New-alarm detection"):
- `status` is `None` or maps to unknown: return `None`, change nothing. An unknown value is logged once per distinct value at warning level.
- Known status: a new alarm is "new reading pending, tracked `pending` is `False`". `previous_status` is the last known status seen by this instance, `after_restart` is true when this instance has not seen a known status before. Then `pending` and the last known status are updated; on a new alarm `last_alarm = now`.
- Tracked `pending` of `None` (fresh install) followed by 4 is not a new alarm.

- [ ] **Step 1: Write the failing tests**

```python
from datetime import datetime, timezone

import pytest

from custom_components.buderus_wps.alarm_tracker import AlarmTracker, NewAlarm

T0 = datetime(2026, 11, 26, 8, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 11, 26, 8, 1, tzinfo=timezone.utc)


def feed(tracker, statuses):
    return [tracker.update(s, T1) for s in statuses]


def test_one_to_four_fires_once():
    t = AlarmTracker()
    assert feed(t, [1, 4, 4]) == [None, NewAlarm(4, 1, False, T1), None]
    assert t.last_alarm == T1
    assert t.pending is True


def test_confirm_sequence_clears_without_event():
    t = AlarmTracker(remembered_pending=True, last_alarm=T0)
    assert feed(t, [4, 3, 0, 1]) == [None, None, None, None]
    assert t.pending is False
    assert t.last_alarm == T0


def test_three_then_four_is_a_new_alarm():
    t = AlarmTracker()
    assert feed(t, [3, 4])[1] == NewAlarm(4, 3, False, T1)


def test_restart_remembered_not_pending_fires():
    t = AlarmTracker(remembered_pending=False)
    assert t.update(4, T1) == NewAlarm(4, None, True, T1)


def test_restart_remembered_pending_does_not_fire():
    t = AlarmTracker(remembered_pending=True, last_alarm=T0)
    assert t.update(4, T1) is None
    assert t.last_alarm == T0


def test_fresh_install_does_not_fire():
    t = AlarmTracker()
    assert t.update(4, T1) is None
    assert t.pending is True
    assert t.last_alarm is None


@pytest.mark.parametrize("gap", [None, 2, 7])
def test_missing_or_unknown_reading_changes_nothing(gap):
    t = AlarmTracker()
    assert feed(t, [1, gap, 1, gap, 4, gap, 4]) == [
        None, None, None, None, NewAlarm(4, 1, False, T1), None, None,
    ]


def test_unknown_value_does_not_end_an_alarm():
    t = AlarmTracker(remembered_pending=True)
    feed(t, [4, 2])
    assert t.pending is True


def test_unknown_value_logged_once(caplog):
    t = AlarmTracker()
    with caplog.at_level("WARNING"):
        feed(t, [2, 2, 2, 7])
    assert sum("system status" in r.message.lower() for r in caplog.records) == 2


def test_round_trip_survives_restart():
    t = AlarmTracker()
    feed(t, [1, 4])
    restored = AlarmTracker.from_dict(t.as_dict())
    assert restored.pending is True
    assert restored.last_alarm == T1
    assert restored.update(4, T1) is None


def test_as_dict_is_json_plain():
    t = AlarmTracker()
    feed(t, [1, 4])
    assert t.as_dict() == {"pending": True, "last_alarm": T1.isoformat()}


@pytest.mark.parametrize(
    "data,pending,has_last",
    [
        (None, None, False),
        ("junk", None, False),
        ([], None, False),
        ({}, None, False),
        ({"pending": "yes", "last_alarm": "garbage"}, None, False),
        ({"pending": False, "last_alarm": 12345}, False, False),
        ({"pending": 1, "last_alarm": T0.isoformat()}, None, True),
    ],
)
def test_from_dict_tolerates_bad_data(data, pending, has_last):
    t = AlarmTracker.from_dict(data)
    assert t.pending is pending
    assert (t.last_alarm is not None) is has_last
```

- [ ] **Step 2: Run to verify failure**

Run: `~/dev/buderus-wps-ha/venv/bin/python -m pytest tests/unit/test_alarm_tracker.py --no-cov -q`
Expected: `No module named 'custom_components.buderus_wps.alarm_tracker'`

- [ ] **Step 3: Implement `alarm_tracker.py`**

No Home Assistant imports. `from_dict` accepts only a real `bool` for `pending` and only an ISO string that `datetime.fromisoformat` parses for `last_alarm`; a parsed value without tzinfo is taken as UTC.

- [ ] **Step 4: Run tests and lint** (same commands as Task 1, with this test file) → all pass, clean

- [ ] **Step 5: Commit**

```bash
git add custom_components/buderus_wps/alarm_tracker.py tests/unit/test_alarm_tracker.py
git commit -m "feat: track new-alarm edges across restarts (#25)"
```

---

### Task 3: Coordinator reads, detects, persists, fires

**Files:**
- Modify: `custom_components/buderus_wps/const.py`
- Modify: `custom_components/buderus_wps/coordinator.py` (`BuderusData`, `__init__`, `async_setup`, `_async_update_data_inner` success branch, `_sync_fetch_data`)
- Modify: `custom_components/buderus_wps/__init__.py:193` (config-entry path only)
- Modify: `tests/conftest.py`
- Test: `tests/unit/test_alarm_coordinator.py`

**Interfaces:**
- Consumes: `SYSTEM_STATUS_PARAM`, `parse_system_status` (Task 1); `AlarmTracker`, `NewAlarm` (Task 2).
- Produces:
  - `const.py`: `EVENT_ALARM: Final = "buderus_wps_alarm"`, `ALARM_STORAGE_VERSION: Final = 1`, `ALARM_STORAGE_KEY_PREFIX: Final = "buderus_wps.alarm_state"`
  - `BuderusData.system_status: int | None = None`
  - `BuderusCoordinator(hass, port, scan_interval, parameter_allowlist=None, entry_id: str | None = None)`; attribute `entry_id`
  - Attributes `BuderusCoordinator._alarm_store` (the `Store`) and `BuderusCoordinator._alarm_tracker` (the `AlarmTracker`), both created in `__init__`
  - `BuderusCoordinator.last_alarm -> datetime | None` (property, from the tracker)
  - `BuderusCoordinator._sync_read_system_status() -> int | None`
  - `BuderusCoordinator._async_load_alarm_state() -> None`
  - `BuderusCoordinator._handle_system_status(status: int | None) -> None`
  - Storage key: `f"{ALARM_STORAGE_KEY_PREFIX}.{entry_id or 'yaml'}"`

Behaviour:
- `_sync_read_system_status`: `read_parameter(SYSTEM_STATUS_PARAM, timeout=0.5)`, result through `parse_system_status`. Any exception or a `None` result falls back to `self._last_known_good_data.system_status` when cached data exists, else `None`. Same shape as `_sync_read_room_setpoints`. Called from `_sync_fetch_data`; result goes into `BuderusData(system_status=...)`.
- `_async_load_alarm_state`: awaited first thing in `async_setup`. Loads the store, builds the tracker with `AlarmTracker.from_dict`. Never raises: any failure is logged at warning level and leaves a fresh tracker.
- `_handle_system_status`: called in `_async_update_data_inner` right after `self._last_known_good_data = fresh_data` (fresh data only, not on the stale-data returns). Calls `tracker.update(status, datetime.now(timezone.utc))`. On a `NewAlarm`: fire `EVENT_ALARM` on `self.hass.bus` with the four payload keys, and log one warning line. When `tracker.as_dict()` differs from before the update: `self._alarm_store.async_delay_save(self._alarm_tracker.as_dict, 1.0)`. A failing save is logged and swallowed. This method never raises.

- [ ] **Step 1: Extend `tests/conftest.py`**

In `setup_ha_mocks`: register `sys.modules["homeassistant.helpers.storage"]` with a `Store` class below; set `sensor_mock.SensorDeviceClass.TIMESTAMP = "timestamp"`, `binary_sensor_mock.BinarySensorDeviceClass.PROBLEM = "problem"`, `const_mock.EntityCategory.DIAGNOSTIC = "diagnostic"`. Add `system_status: Optional[int] = None` to `MockBuderusData`.

```python
class MockStore:
    """Stand-in for homeassistant.helpers.storage.Store."""

    def __init__(self, hass, version, key, *args, **kwargs):
        self.version = version
        self.key = key
        self.data = None          # what async_load returns
        self.saved = None         # last data handed to a save
        self.load_error = None
        self.save_error = None

    async def async_load(self):
        if self.load_error:
            raise self.load_error
        return self.data

    def async_delay_save(self, data_func, delay=0):
        if self.save_error:
            raise self.save_error
        self.saved = data_func()
```

- [ ] **Step 2: Write the failing tests**

```python
from unittest.mock import MagicMock

import pytest

from custom_components.buderus_wps.const import EVENT_ALARM
from custom_components.buderus_wps.coordinator import BuderusCoordinator


def make(mock_hass, entry_id="entry1"):
    c = BuderusCoordinator(mock_hass, "/dev/ttyACM0", 60, entry_id=entry_id)
    c.hass = mock_hass  # mocked parent does not set this
    c._client = MagicMock()
    return c


class TestRead:
    def test_reads_by_name_without_validation(self, mock_hass):
        c = make(mock_hass)
        c._client.read_parameter.return_value = {"decoded": 4}
        assert c._sync_read_system_status() == 4
        c._client.read_parameter.assert_called_once_with("RTU800B_SYSTEM_STATUS", timeout=0.5)
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


class TestDetection:
    def test_new_alarm_fires_event_and_saves(self, mock_hass):
        c = make(mock_hass)
        c._handle_system_status(1)
        c._handle_system_status(4)
        mock_hass.bus.async_fire.assert_called_once_with(
            EVENT_ALARM,
            {"entry_id": "entry1", "status": 4, "previous_status": 1, "after_restart": False},
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
            {"entry_id": "entry1", "status": 4, "previous_status": None, "after_restart": True},
        )

    async def test_alarm_already_pending_before_restart_is_silent(self, mock_hass):
        c = make(mock_hass)
        c._alarm_store.data = {"pending": True, "last_alarm": "2026-11-25T02:42:00+00:00"}
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
```

- [ ] **Step 3: Run to verify failure**

Run: `~/dev/buderus-wps-ha/venv/bin/python -m pytest tests/unit/test_alarm_coordinator.py --no-cov -q`
Expected: FAIL, `unexpected keyword argument 'entry_id'`

- [ ] **Step 4: Implement** per the Interfaces and Behaviour blocks above. In `__init__.py` the config-entry path becomes `BuderusCoordinator(hass, port, scan_interval, allowlist, entry_id=entry.entry_id)`; the YAML path stays as is.

- [ ] **Step 5: Run the new tests, then the whole suite**

Run: `~/dev/buderus-wps-ha/venv/bin/python -m pytest tests/unit/test_alarm_coordinator.py --no-cov -q` → all pass
Run: `~/dev/buderus-wps-ha/venv/bin/python -m pytest tests/unit tests/integration tests/acceptance tests/contract --no-cov -q` → no failures (existing coordinator tests construct the coordinator positionally and call `async_setup`; they must still pass)
Run: ruff as in Task 1 → clean

- [ ] **Step 6: Commit**

```bash
git add custom_components/buderus_wps/const.py custom_components/buderus_wps/coordinator.py custom_components/buderus_wps/__init__.py tests/conftest.py tests/unit/test_alarm_coordinator.py
git commit -m "feat: read system status each cycle and fire buderus_wps_alarm (#25)"
```

---

### Task 4: Entities and user documentation

**Files:**
- Modify: `custom_components/buderus_wps/binary_sensor.py`
- Modify: `custom_components/buderus_wps/sensor.py`
- Modify: `README.md`, `CHANGELOG.md`
- Test: `tests/unit/test_ha_alarm_entities.py`

**Interfaces:**
- Consumes: `BuderusData.system_status`, `BuderusCoordinator.last_alarm` (Task 3); `alarm_pending` (Task 1).
- Produces:

| Class | File | Entity key | `_attr_name` | Notes |
|---|---|---|---|---|
| `BuderusAlarmPendingSensor(coordinator, entry=None)` | `binary_sensor.py` | `alarm_pending` | `Alarm Pending` | device class `PROBLEM`; `is_on` = `alarm_pending(data.system_status)`; attribute `system_status` added to the base attributes |
| `BuderusLastAlarmSensor(coordinator, entry=None)` | `sensor.py` | `last_alarm` | `Last Alarm` | device class `TIMESTAMP`; `native_value` = `coordinator.last_alarm`, also when `coordinator.data` is `None` |
| `BuderusSystemStatusSensor(coordinator, entry=None)` | `sensor.py` | `system_status` | `System Status` | `_attr_entity_category = EntityCategory.DIAGNOSTIC`; `native_value` = `data.system_status`; no unit, no state class |

All three are added in both `async_setup_entry` and `async_setup_platform` of their file.

- [ ] **Step 1: Write the failing tests**

```python
from datetime import datetime, timezone

import pytest

from custom_components.buderus_wps.binary_sensor import BuderusAlarmPendingSensor
from custom_components.buderus_wps.sensor import (
    BuderusLastAlarmSensor,
    BuderusSystemStatusSensor,
)


class TestAlarmPending:
    @pytest.mark.parametrize(
        "status,expected", [(4, True), (0, False), (1, False), (3, False), (2, None), (None, None)]
    )
    def test_state(self, mock_coordinator, status, expected):
        mock_coordinator.data.system_status = status
        assert BuderusAlarmPendingSensor(mock_coordinator).is_on is expected

    def test_unknown_when_disconnected(self, mock_coordinator_disconnected):
        assert BuderusAlarmPendingSensor(mock_coordinator_disconnected).is_on is None

    def test_identity(self, mock_coordinator):
        s = BuderusAlarmPendingSensor(mock_coordinator)
        assert s._attr_device_class == "problem"
        assert s._attr_name == "Alarm Pending"
        assert s._attr_unique_id.endswith("_alarm_pending")

    def test_raw_value_attribute(self, mock_coordinator):
        mock_coordinator.data.system_status = 3
        mock_coordinator.get_data_age_seconds.return_value = None
        mock_coordinator._last_successful_update = None
        attrs = BuderusAlarmPendingSensor(mock_coordinator).extra_state_attributes
        assert attrs["system_status"] == 3


class TestLastAlarm:
    def test_value_is_coordinator_last_alarm(self, mock_coordinator):
        when = datetime(2026, 11, 25, 2, 42, tzinfo=timezone.utc)
        mock_coordinator.last_alarm = when
        s = BuderusLastAlarmSensor(mock_coordinator)
        assert s.native_value == when
        assert s._attr_device_class == "timestamp"
        assert s._attr_unique_id.endswith("_last_alarm")

    def test_unknown_until_first_alarm(self, mock_coordinator):
        mock_coordinator.last_alarm = None
        assert BuderusLastAlarmSensor(mock_coordinator).native_value is None

    def test_kept_while_disconnected(self, mock_coordinator_disconnected):
        when = datetime(2026, 11, 25, 2, 42, tzinfo=timezone.utc)
        mock_coordinator_disconnected.last_alarm = when
        assert BuderusLastAlarmSensor(mock_coordinator_disconnected).native_value == when


class TestSystemStatus:
    def test_raw_value(self, mock_coordinator):
        mock_coordinator.data.system_status = 4
        s = BuderusSystemStatusSensor(mock_coordinator)
        assert s.native_value == 4
        assert s._attr_entity_category == "diagnostic"
        assert s._attr_unique_id.endswith("_system_status")

    def test_none_when_disconnected(self, mock_coordinator_disconnected):
        assert BuderusSystemStatusSensor(mock_coordinator_disconnected).native_value is None


async def test_platforms_add_the_entities(mock_hass, mock_coordinator):
    from unittest.mock import MagicMock

    from custom_components.buderus_wps import binary_sensor, sensor
    from custom_components.buderus_wps.const import DOMAIN

    entry = MagicMock(entry_id="entry1")
    mock_coordinator.parameter_allowlist = []
    mock_hass.data = {DOMAIN: {"entry1": {"coordinator": mock_coordinator}}}
    added = []
    await binary_sensor.async_setup_entry(mock_hass, entry, added.extend)
    await sensor.async_setup_entry(mock_hass, entry, added.extend)
    kinds = {type(e) for e in added}
    assert {BuderusAlarmPendingSensor, BuderusLastAlarmSensor, BuderusSystemStatusSensor} <= kinds
```

- [ ] **Step 2: Run to verify failure**

Run: `~/dev/buderus-wps-ha/venv/bin/python -m pytest tests/unit/test_ha_alarm_entities.py --no-cov -q`
Expected: `ImportError: cannot import name 'BuderusAlarmPendingSensor'`

- [ ] **Step 3: Implement the three entity classes and register them**

- [ ] **Step 4: Update `README.md`**

New subsection "### Alarms" after "### Controls": a table with `binary_sensor.heat_pump_alarm_pending`, `sensor.heat_pump_last_alarm`, `sensor.heat_pump_system_status`; the event `buderus_wps_alarm` with its four payload fields; the limits from the spec's Non-goals in plain words (no alarm text or category, a further alarm while one is pending gives no new event, detection up to one scan interval late, alarms cannot be confirmed from HA). Under "## Example Automations" add "### Notify on a new heat pump alarm":

```yaml
automation:
  - alias: "Heat pump alarm"
    trigger:
      - platform: event
        event_type: buderus_wps_alarm
    action:
      - service: notify.notify
        data:
          title: "Heat pump alarm"
          message: >-
            The heat pump reports a new alarm. Check the panel for the text.
            {% if trigger.event.data.after_restart %}(Raised while Home Assistant was restarting.){% endif %}
```

- [ ] **Step 5: Update `CHANGELOG.md`**

New top section `## [Unreleased]` with `### Added`: one entry covering the three entities, the event, the restart behaviour and the limits, referencing #25.

- [ ] **Step 6: Run the whole suite and lint** (commands from Task 3 Step 5) → no failures, clean

- [ ] **Step 7: Commit**

```bash
git add custom_components/buderus_wps/binary_sensor.py custom_components/buderus_wps/sensor.py README.md CHANGELOG.md tests/unit/test_ha_alarm_entities.py
git commit -m "feat: alarm pending, last alarm and system status entities (#25)"
```

---

### Task 5: Remove the wrong alarm code from the library

Separate commit. Reason, for the commit body: `ADDITIONAL_ALARM*` are auxiliary-heater flags and not log entries; `INFO_LOG_*`, `ALARM_ACKNOWLEDGE` and `ALARM_CLEAR` do not exist in the parameter table, so `acknowledge()` and `clear()` could only fail; the alarm log is not readable over CAN.

**Files:**
- Modify: `custom_components/buderus_wps/buderus_wps/menu_api.py` (`Alarm` dataclass at :146, `AlarmController` at :610-689, imports at :66-80)
- Modify: `custom_components/buderus_wps/buderus_wps/menu_structure.py` (`ALARM_PARAMS` at :135-149, "Alarms" menu at :349-362, docstring line :15)
- Modify: `custom_components/buderus_wps/buderus_wps/enums.py` (`AlarmCategory` at :48)
- Modify: `custom_components/buderus_wps/buderus_wps/exceptions.py` (`AlarmNotClearableError` at :230)
- Modify: `custom_components/buderus_wps/buderus_wps/__init__.py` (exports)
- Delete: `tests/unit/test_alarms.py`
- Modify: `tests/unit/test_menu_api.py` (imports, `TestAlarmController` at :470-568)
- Modify: `tests/unit/test_menu_structure.py:143`
- Modify: `tests/integration/test_menu_api_integration.py` (`TestAlarmIntegration` at :340)
- Modify: `tests/acceptance/test_user_stories.py` (`TestUS7Alarms` at :453-499, lines :601-603, import :12)
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: `SYSTEM_STATUS_PARAM`, `parse_system_status`, `alarm_pending` (Task 1).
- Produces: `AlarmController(client)` with exactly two public members:
  - `system_status -> Optional[int]`: `parse_system_status` of the decoded plain read of `SYSTEM_STATUS_PARAM`; read errors propagate, as in the other controllers.
  - `pending -> Optional[bool]`: `alarm_pending(self.system_status)`.
  `MenuAPI.alarms` keeps returning it.
- Removed names: `ALARM_PARAMS`, `Alarm`, `AlarmCategory`, `AlarmNotClearableError`, `AlarmController.active_alarms`, `.alarm_log`, `.info_log`, `.acknowledge`, `.clear`.
- Menu tree: the "Alarms" item stays, with description `"Alarm status (the alarm log is not readable over CAN)"` and one child `MenuItem(name="Alarm Pending Status", description="4 = unconfirmed alarm pending, 1 = none", parameter=SYSTEM_STATUS_PARAM)`.

- [ ] **Step 1: Replace `TestAlarmController` in `tests/unit/test_menu_api.py`** and drop the now-unused imports

```python
class TestAlarmController:
    """AlarmController exposes only what the pump really reports."""

    @pytest.mark.parametrize("decoded,status,pending", [(4, 4, True), (1, 1, False), (2, 2, None), (None, None, None)])
    def test_status_and_pending(self, mock_client, decoded, status, pending):
        mock_client.read_parameter.return_value = {"decoded": decoded}
        ctrl = AlarmController(mock_client)
        assert ctrl.system_status == status
        assert ctrl.pending is pending

    def test_reads_system_status_by_name(self, mock_client):
        mock_client.read_parameter.return_value = {"decoded": 1}
        AlarmController(mock_client).system_status
        mock_client.read_parameter.assert_called_once_with("RTU800B_SYSTEM_STATUS")

    def test_no_log_or_write_api(self, mock_client):
        ctrl = AlarmController(mock_client)
        for gone in ("active_alarms", "alarm_log", "info_log", "acknowledge", "clear"):
            assert not hasattr(ctrl, gone)
        mock_client.write_value.assert_not_called()
```

- [ ] **Step 2: Rewrite the other alarm tests to the new interface**

- `tests/integration/test_menu_api_integration.py` `TestAlarmIntegration.test_alarm_workflow`: with `read_parameter` returning `{"decoded": 1}` then `{"decoded": 4}`, `api.alarms.pending` is `False` then `True`.
- `tests/acceptance/test_user_stories.py` `TestUS7Alarms`: story text becomes "see whether an alarm is waiting on the panel"; AC1 `api.alarms.pending is True` for decoded 4; AC2 `is False` for decoded 1; AC3 removed (acknowledging from HA is out of scope). Lines :601-603 become `assert api.alarms.pending in (True, False, None)`.
- `tests/unit/test_menu_structure.py`: keep `test_has_alarms_menu`; add `test_alarms_menu_reads_system_status` asserting the "Alarms" item has exactly one child whose `parameter == "RTU800B_SYSTEM_STATUS"`; add `test_alarm_params_removed` asserting `not hasattr(buderus_wps.menu_structure, "ALARM_PARAMS")`.
- Delete `tests/unit/test_alarms.py`.

- [ ] **Step 3: Run to verify failure**

Run: `~/dev/buderus-wps-ha/venv/bin/python -m pytest tests/unit/test_menu_api.py tests/unit/test_menu_structure.py tests/integration/test_menu_api_integration.py tests/acceptance/test_user_stories.py --no-cov -q`
Expected: failures in the rewritten alarm tests (`AttributeError: ... 'system_status'`, `ALARM_PARAMS` still present)

- [ ] **Step 4: Make the library changes** listed under Files and Interfaces

- [ ] **Step 5: Check nothing still refers to the removed names**

Run: `grep -rnE "ALARM_PARAMS|AlarmCategory|AlarmNotClearableError|active_alarms|alarm_log\b|info_log|menu_api import.*\bAlarm\b" custom_components buderus_wps_cli tests --include='*.py'`
Expected: no output

- [ ] **Step 6: Add to `CHANGELOG.md` under `## [Unreleased]`**

`### Changed` entry marked **Breaking (library API)**: the names removed, the two properties that remain, and the reason in one sentence.

- [ ] **Step 7: Run the whole suite, lint, and mypy**

Run: whole suite and ruff as in Task 3 Step 5 → no failures, clean
Run: `MYPYPATH=custom_components/buderus_wps ~/dev/buderus-wps-ha/venv/bin/python -m mypy --explicit-package-bases -p buderus_wps --config-file pyproject.toml` (the CI command) → no new errors compared with the same command on the commit before this task

- [ ] **Step 8: Commit**

```bash
git add -u custom_components/buderus_wps/buderus_wps tests CHANGELOG.md
git commit -m "refactor!: drop alarm log API that read the wrong parameters (#25)"
```

(`git add -u` stages tracked files only, including the deletion; it leaves `tests/fixtures/` alone.)

---

## After the last task

Not part of any task; for whoever deploys:

- Deploy as described in `CLAUDE.md`. Expected right after: `sensor.heat_pump_system_status` = 1, `binary_sensor.heat_pump_alarm_pending` off, `sensor.heat_pump_last_alarm` unknown.
- At the next real alarm, compare HA (sensor on, event under Developer Tools → Events, "Last alarm") with the panel popup time; the panel clock runs about two minutes slow. This is the first direct observation of the 1 → 4 step. If the status shows a value other than 0, 1, 3, 4, the warning line in the log and the history of the diagnostic sensor are the evidence to bring back to #25.
