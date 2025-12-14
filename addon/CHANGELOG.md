# Changelog

All notable changes to the Buderus WPS Heat Pump Add-on will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - Unreleased

### Added

- Initial release
- Temperature sensor monitoring (outdoor, supply, return, DHW, buffer top/bottom)
- Compressor status binary sensor
- Heating Season Mode control (Winter, Automatic, Summer)
- DHW Program Mode control (Automatic, Always On, Always Off)
- Holiday Mode switch
- Extra Hot Water Duration and Target controls
- MQTT Discovery for automatic entity creation
- USB serial device configuration
- Automatic MQTT broker detection via Supervisor API
- Configurable logging verbosity
- Automatic reconnection on USB disconnect
- 60-second MQTT message buffering on broker disconnect
