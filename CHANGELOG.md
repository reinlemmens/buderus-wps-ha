# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
