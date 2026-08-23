# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.0-beta.3] - 2026-08-23

### Added
- **DHW stop temperature control in "Always On" mode (#13).** In
  `DHW_PROGRAM_MODE=1` the controller terminates a charge on
  `DHW_GT8_STOP_TEMP` (idx 444) and ignores the Comfort/Economy profile
  registers, so the existing profile entities are inert in that mode.
  Confirmed on hardware: idx 444 read 61.0 °C — matching every observed
  charge termination — while the Comfort register read 54.0 and was ignored.
  Idx 444 carries no write range in the FHEM protocol reference and is not
  writable, so it is exposed read-only as
  `sensor.heat_pump_dhw_stop_temperature_active`, alongside a new writable
  `number.heat_pump_dhw_stop_temperature_limit` for `DHW_GT8_STOP_MAX_TEMP`
  (idx 440, 20.0-64.0 °C). Writes to idx 440 reach the device and read back
  correctly, but whether it governs charge termination is **not yet
  confirmed**: on an idle pump idx 444 did not follow a write to 440. The
  read-only sensor is what makes the relationship observable across a
  charge.
- **`number.heat_pump_dhw_start_temperature_active`** for
  `DHW_USER_SET_START_TEMP` (idx 498, 20.0-79.0 °C), the active start
  temperature paired with the stop registers above.

### Fixed
- **Coordinator could wedge silently with no recovery (#10).** The update
  path acquired the coordinator lock and ran serial I/O with no timeout, so
  a hung read blocked `_async_update_data` forever: no logs, no reconnect,
  entities unavailable until a config-entry reload. Every update cycle is
  now bounded by a 60 s timeout; repeated timeouts (or a stall watchdog
  detecting no successful update for 5 scan intervals) force-close the
  serial port, replace the coordinator lock outright so a stuck holder
  cannot leak into the new session, and re-enter the existing
  reconnect-with-backoff loop.
- **Orphaned `number.heat_pump_dhw_stop_temperature` registry row (#9).**
  The `dhw_stop_temp` -> `xdhw_stop_temp` entity-key rename in v1.5.x left a
  permanently-unavailable registry entry behind. Setup now removes registry
  rows for a curated list of renamed entity keys (`STALE_ENTITY_KEYS`);
  future renames must add their old key to that list.

### Changed
- **README documents Energy Block vs Compressor Block semantics (#8).**
  `switch.heat_pump_energy_block` is a mode-level control (rewrites heating
  and DHW program modes), while `switch.heat_pump_compressor_block` blocks
  the compressor directly with pumps still running. The peak-rate example
  automation now uses the compressor block, the safer actuator for capacity
  shedding.

## [1.6.0-beta.2] - 2026-08-20

### Fixed
- **Duplicate parameter indices (#11).** Four `idx` values were shared by two
  parameters each: 279 (`COMPRESSOR_REAL_FREQUENCY` / `COMPRESSOR_RESTART_TIME`),
  296 (`COMPRESSOR_STATE_2` / `COMPRESSOR_TYPE`), 2478 (`XDHW_STOP_TEMP` /
  `XDHW_WEEKPROGRAM_FAILED`) and 2480 (`XDHW_TIME` / `XDHW_WEEKPROGRAM_HOUR`).
  Since `idx` maps 1:1 to CAN IDs (`0x04003FE0 | idx << 14`), each pair shared a
  CAN ID and shadowed the other in index lookups. The visible symptom was
  `XDHW_STOP_TEMP` reading a bogus 3.8 °C.
- **`update_from_discovery()` could corrupt the registry.** It mutated
  `_params_by_idx` per element with an unguarded `del`, so swapped or shared
  indices could delete another parameter's mapping or raise `KeyError` mid-merge
  — swallowed by the coordinator's broad `except`, leaving the registry
  half-updated. The index map is now rebuilt atomically after the merge;
  discovered parameters win collisions and losers stay reachable by name.

### Changed
- **`parameter_data.py` regenerated from the device element list** — 1792
  entries (was 1788), zero duplicate idx/extid/text. The previous table came
  from FHEM's static list, which differs from this device in whole regions:
  1556 of 1788 entries carried a wrong idx and were corrected by runtime
  discovery on every startup. Startup now reports `0 indices updated`.
  Format and read metadata are merged from `parameter_defaults.py`, with
  day-program name mapping so `sw1`/`sw2` schedule formats survive.
- Release archives no longer contain `__pycache__/*.pyc` files, which earlier
  releases shipped by mistake (246 KB vs 884 KB).

### Added
- `tools/generate_parameter_data.py` regenerates `parameter_data.py` from a
  device capture. `parameter_data.py` must never be hand-patched again — seven
  hand-patched entries are what caused #11.
- Regression tests for index collisions (swap, chain-shift, stale collision).
  `test_no_duplicate_indices` now forbids duplicates; it previously *asserted*
  them.

### Verified on hardware
`XDHW_STOP_TEMP` reads 60.0 °C at idx 2478 (CAN `0x066BBFE0`), `XDHW_TIME` at
idx 2480; write round-trips confirmed. Startup log: `Loaded 1792 parameters`,
`Element discovery: 1792 elements, 0 indices updated`, no duplicate warnings,
no errors.

## [1.6.0-beta.1] - 2026-05-28

### Added
- **DHW Comfort/Economy mode control.** Per Buderus advice, running DHW in
  "Comfort" mode at all times maximises consumption; "Eco" or a time program
  is preferred. The integration now exposes the underlying parameters so the
  mode can be selected and the setpoint pairs tuned from Home Assistant.
  - New `select.heat_pump_dhw_time_program` entity wrapping `DHW_TIMEPROGRAM`
    (idx 494, dp1). Options: `Always On (Comfort)`, `Program 1`, `Program 2`.
  - New `number` entities for the four start/stop setpoint pairs that the
    Comfort/Economy schedules switch between:
    - `number.heat_pump_dhw_start_temperature_comfort` — `DHW_GT3_START_TEMP_COMFORT`
      (20.0–56.0 °C)
    - `number.heat_pump_dhw_start_temperature_economy` — `DHW_GT3_START_TEMP_ECONOMY`
      (20.0–56.0 °C)
    - `number.heat_pump_dhw_stop_temperature_comfort` — `DHW_GT8_STOP_TEMP_COMFORT`
      (21.0–64.0 °C)
    - `number.heat_pump_dhw_stop_temperature_economy` — `DHW_GT8_STOP_TEMP_ECONOMY`
      (21.0–64.0 °C)

### Notes
- `DHW_TIMEPROGRAM` writes were flagged as ignored in one earlier
  hardware test (see `specs/002-buderus-wps-python-class/protocol-broadcast-mapping.md`).
  FHEM exposes it as writable; behaviour should be verified on device after
  upgrade. The read path always yields a valid sensor value regardless.

## [1.5.3] - 2026-01-XX
- Test: import `HomeAssistantError` from `switch` module for stable identity.
- CI: fix code-quality workflow and apply lint/format.

## [1.5.2]
- Fix: syntax error in `parameter_data.py`.

## [1.5.1]
- Fix: add timeouts to coordinator lock and executor jobs.

## [1.5.0] - Element Discovery & DHW Setpoint Control
- Element discovery with fail-fast behavior; persistent cache in `/config/`.
- New `number.heat_pump_dhw_setpoint` entity (40–70 °C).
- Fixed GT10/GT11 brine temperature readings.
- GT3_TEMP now read via RTR instead of broadcast.
