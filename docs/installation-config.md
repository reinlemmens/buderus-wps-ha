# Installation Configuration

This document captures the installation-specific configuration for the Buderus WPS heat pump system at the author's house.

## Heating Circuits

| Circuit | Type | Serves | Parameters Prefix |
|---------|------|--------|-------------------|
| 1 | Ventilo (fan coil) | App 0 | HK1_* |
| 2 | Floor heating | App 1 | HK2_* |
| 3 | Floor heating | App 0 | HK3_* |
| 4 | Floor heating | App 2 | HK4_* |

## DHW (Domestic Hot Water)

- Only serves **App 0**

## Summary by Apartment

| Apartment | Heating Systems | DHW |
|-----------|-----------------|-----|
| App 0 | Ventilo (HK1), Floor heating (HK3) | Yes |
| App 1 | Floor heating (HK2) | No |
| App 2 | Floor heating (HK4) | No |

## Notes

- Circuit 1 uses a ventilo (fan coil unit) which operates differently from floor heating
- Circuits 2, 3, and 4 are all floor heating systems
- DHW (warm water) is centrally produced but only distributed to App 0

## Configuration File

The configuration is stored at `~/.config/buderus-wps/config.yaml`.

### Example Configuration

```yaml
# Buderus WPS Heat Pump Configuration
version: "1.0"

# Heating circuit configuration
# type: "floor_heating" or "ventilo"
circuits:
  - number: 1
    type: ventilo
    apartment: "app0"
    label: "App 0 Ventilo"
  - number: 2
    type: floor_heating
    apartment: "app1"
    label: "App 1 Floor"
  - number: 3
    type: floor_heating
    apartment: "app0"
    label: "App 0 Floor"
  - number: 4
    type: floor_heating
    apartment: "app2"
    label: "App 2 Floor"

# Domestic hot water distribution
# List apartments with DHW access (omit for all apartments)
dhw:
  apartments:
    - "app0"

# Custom sensor display labels (optional)
labels:
  outdoor: "Outdoor Temperature"
  supply: "Supply Temperature"
  return_temp: "Return Temperature"
  dhw: "Hot Water Temperature"
  brine_in: "Brine Inlet"
```

### Configuration Locations

The system searches for configuration in this order:

1. `BUDERUS_WPS_CONFIG` environment variable
2. `./buderus-wps.yaml` (current directory)
3. `~/.config/buderus-wps/config.yaml` (XDG standard)

If no file is found, built-in defaults are used.
