# Alarm pending sensor and new-alarm event

Date: 2026-11-25
Issue: reinlemmens/buderus-wps-ha#25
Size: small change

## Why

The heat pump shows alarms only on its own panel. The goal of #25 is to get
them into Home Assistant: a notification when a new alarm arrives, and a
moment in HA history to line up against other events.

The stored alarm log cannot be read over CAN. Every parameter index and every
service index was swept read-only, and a bus recording of six alarms being
confirmed on the panel showed no alarm text, time or per-alarm frame. What the
pump does expose is one status value that tells whether unconfirmed alarms
exist. This design builds on that value.

## What the pump gives us

Parameter `RTU800B_SYSTEM_STATUS` (idx 2182 on the reference pump, 2178 in the
built-in table; always look it up by name).

| Value | Meaning | Evidence |
|---|---|---|
| 4 | Unconfirmed alarm popups exist | Three scans and three bus recordings, with alarms of category H only and of H plus G |
| 3 | Short step while the last popup is confirmed | Seen twice, lasted 3.6 s and 51 s |
| 0 | Very short step right after 3 | Seen twice |
| 1 | No pending alarms | Two scans, two recordings |

Not yet observed: the change from 1 to 4 at the moment an alarm is raised, a
second alarm arriving while the value is already 4, and alarm categories other
than G and H. The design records the raw value so HA history answers these.

## Goals

- HA knows within one scan interval that an unconfirmed alarm exists.
- An automation can notify on a new alarm, also when the alarm was raised
  while HA or the integration was restarting. On the reference installation
  alarms have repeatedly appeared during integration start, so this case is
  the common one, not an edge case.
- HA keeps the time the last alarm was detected.
- The alarm code in the library that reads the wrong parameters is gone.

## Non-goals

- Alarm text, category or panel timestamp. Not available on the bus.
- One event per alarm. A further alarm while one is already pending is not
  visible.
- Confirming or resetting alarms from HA.
- Listening for the pump's status broadcast to the room units, or using the
  two weaker candidate signals (pump to mixing modules, idx 110 and 23).
- Changing how often the element list is downloaded (#24).

## Anti-goals

- A false "new alarm" on every HA restart while an alarm is still pending.
- Guessing: a status value never seen before must not be shown as "alarm" or
  as "no alarm".

## Approaches considered

- **A. Read the parameter every update cycle.** One extra read per scan
  interval through the existing read path. Reliable every cycle, works on
  other firmware through the name lookup. Detection delay up to one scan
  interval; the short value 3 can be missed. **Chosen**: cheapest and the
  accuracy is enough.
- **B. Listen for the broadcast to the room units.** No extra traffic, but the
  broadcast comes every 15 s and the listen window is 5 s, so most cycles see
  nothing without a much larger change to how the adapter is shared.
- **C. Both.** A few seconds faster on some transitions, at the cost of two
  sources that can disagree.

## Design

### Reading

- Each update cycle reads `RTU800B_SYSTEM_STATUS` by name with the plain read
  (the table lists its range as 0..0, so the range-validating read would
  reject real values). Short timeout, same as the other status flags.
- The raw integer goes into `BuderusData` as `system_status`.
- A failed read keeps the previous value. No value ever read gives `None`.
- The mapping from raw value to meaning lives in one place in the library:
  4 is pending; 0, 1 and 3 are not pending; anything else is unknown.

### Entities

| Entity | Type | State |
|---|---|---|
| Alarm pending | binary sensor, device class `problem` | on for 4, off for 0/1/3, unknown otherwise. Attribute `system_status` with the raw value. |
| Last alarm | sensor, device class `timestamp` | Time HA detected the last new alarm. Survives restarts. Unknown until the first one. |
| System status | sensor, diagnostic category | Raw value, so history shows values and transitions not yet understood. |

### New-alarm detection

A new alarm is the step from "not pending" to "pending".

- Normal case: previous reading was 0, 1 or 3 and the new reading is 4.
- After a restart: the first reading is 4 and the state remembered from before
  the restart was "not pending". Counts as a new alarm.
- First reading is 4 and the remembered state was "pending", or nothing is
  remembered (fresh install): not a new alarm.
- Unknown values and failed reads never start or end an alarm.

On a new alarm:

- "Last alarm" is set to the current time.
- Event `buderus_wps_alarm` is fired with `entry_id`, `status`,
  `previous_status` (may be null after a restart) and `after_restart`.
- One warning line in the log.

The detection must work when the user has disabled any of the three entities.

A status value outside 0, 1, 3 and 4 is logged once per value at warning
level.

### Cleanup in the library

Removed, because they read parameters that are not alarm log entries or do
not exist in the parameter table: `ALARM_PARAMS`, the `active_alarms`,
`alarm_log` and `info_log` properties, `acknowledge`, `clear`, the `Alarm`
data class, `AlarmNotClearableError`, the alarm entries in the menu structure,
and their tests. `AlarmCategory` goes too if nothing else uses it.

`MenuAPI.alarms` stays as a small read-only object with `system_status` and
`pending`. This is a breaking change to the library API and is listed as such
in the changelog.

The old specification files under `specs/007-heatpump-menu-api/` are history
and stay as they are.

### Documentation

- `docs/PROTOCOL.md`: section on the alarm status value, the confirm sequence
  and the finding that the log is not on the bus.
- `README.md`: the three entities, the event, an example notify automation,
  and the limits (no text, no per-alarm events).
- `CHANGELOG.md`.

### Tests

Unit tests in the style of `tests/unit/test_ha_binary_sensor.py`:

- value mapping, including an unknown value;
- 1 to 4 fires once; 4 to 4 does not; 4, 3, 0, 1 clears;
- restart with remembered "not pending" and first reading 4 fires;
- restart with remembered "pending", and fresh install, do not fire;
- failed read keeps state and fires nothing;
- event payload;
- "Last alarm" is restored after a restart.

Python 3.9 compatible, as the rest of the integration.

### Check on the real pump

After deployment the status should read 1 and "Alarm pending" should be off.
At the next real alarm, compare HA (sensor on, event, "Last alarm") with the
panel popup time, allowing for the panel clock running about two minutes
slow. This also confirms the 1 to 4 step that has not been observed directly.

## My calls (not discussed, correct them if wrong)

- Unknown status values show as unknown, not as alarm.
- Value 3 counts as "not pending".
- The diagnostic "System status" sensor is enabled by default.
- The cleanup lands on the same branch as a separate commit.
- `tests/fixtures/alarm_log_panel_photos.json` (panel photos transcribed, with
  alarm times from the house) is not part of this change and stays
  uncommitted.

## Left to the builder

- Where the new-alarm detection lives and how the remembered state is stored
  across restarts, as long as it does not depend on an entity being enabled.
- Entity keys and icons.
- Whether the coordinator reads through `MenuAPI.alarms` or the client
  directly.
