# Quickstart Guide: Terminal Menu UI

**Feature**: 008-terminal-menu-ui
**Date**: 2025-11-28

## Overview

The Buderus WPS Terminal Menu provides an interactive text-based interface to monitor and control your heat pump. It works over SSH connections, making it ideal for remote management from any terminal.

## Prerequisites

- Python 3.9 or later
- USB serial adapter connected to heat pump (e.g., USBtin)
- Terminal with minimum 80x24 characters
- ANSI color support (standard on Linux/macOS terminals)

## Installation

The terminal menu is included with the `buderus-wps` package:

```bash
pip install buderus-wps
```

Or from source:

```bash
cd buderus-wps-ha
pip install -e .
```

## Launching the Application

### Basic Usage

```bash
buderus-tui /dev/ttyACM0
```

Replace `/dev/ttyACM0` with your USB serial device path.

### Common Options

```bash
# Specify device path
buderus-tui /dev/ttyUSB0

# Read-only mode (no writing allowed)
buderus-tui --read-only /dev/ttyACM0

# Verbose logging
buderus-tui --verbose /dev/ttyACM0
```

### Finding Your Device

On Linux:
```bash
ls /dev/ttyACM* /dev/ttyUSB*
```

On macOS:
```bash
ls /dev/cu.usbserial* /dev/cu.usbmodem*
```

## Screen Layout

```
+------------------------------------------------------------------------------+
| BUDERUS WPS HEAT PUMP                                    [Connected] 14:30   |
+------------------------------------------------------------------------------+
| Home > Hot Water > Temperature                                               |
+------------------------------------------------------------------------------+
|                                                                              |
|   Current Status:                                                            |
|   ─────────────────────────────────────────────────────────────────────────  |
|   Outdoor Temperature:     8.5°C                                             |
|   Supply Temperature:     35.0°C                                             |
|   Hot Water Temperature:  52.0°C                                             |
|   Operating Mode:         HEATING                                            |
|   Compressor:             Running                                            |
|                                                                              |
|   Last update: 5s ago                                                        |
+------------------------------------------------------------------------------+
| ↑↓ Navigate  Enter Select  Esc Back  r Refresh  q Quit                       |
+------------------------------------------------------------------------------+
```

**Note**: Temperatures are read via CAN bus broadcast monitoring (3 seconds), which provides accurate sensor values. Press 'r' to manually refresh temperatures.

- **Header**: Shows application name, connection status, and time
- **Breadcrumb**: Shows your current location in the menu
- **Content Area**: Main display area for dashboard or menus
- **Help Bar**: Shows available keyboard shortcuts

## Keyboard Navigation

### General Navigation

| Key | Action |
|-----|--------|
| `↑` / `↓` | Move selection up/down |
| `Enter` | Select item or confirm |
| `Esc` | Go back / cancel |
| `r` | Refresh data from heat pump |
| `q` | Quit application |

### Menu Navigation

| Key | Action |
|-----|--------|
| `←` | Go to parent menu |
| `→` | Enter submenu |
| `Backspace` | Go to parent menu |

### Value Editing

| Key | Action |
|-----|--------|
| `Enter` | Start editing / confirm value |
| `Esc` | Cancel editing |
| `0-9` | Enter numeric value |
| `Backspace` | Delete character |

## Main Screens

### 1. Status Dashboard

The default screen shown on startup. Displays real-time status:

- **Temperatures**: Outdoor, supply, return, hot water, room
- **Operating Mode**: Off, Heating, Cooling, DHW, Auto
- **Compressor Status**: Running/Stopped, frequency (Hz), mode (DHW/Heating/Idle)
- **Heating Circuits**: Per-circuit room temperatures and setpoints (configured in buderus-wps.yaml)
- **Auxiliary Heater**: Active or inactive
- **Alarms**: Error indicator if alarms are active

Press `Enter` to access the main menu.

### 2. Main Menu

The top-level menu provides access to all features:

```
┌─────────────────────────────────────┐
│  > Status                           │
│    Hot Water                        │
│    Heating Circuit 1                │
│    Heating Circuit 2                │
│    Programs                         │
│    Energy                           │
│    Alarms                           │
│    Vacation                         │
└─────────────────────────────────────┘
```

### 3. Hot Water Settings

Control DHW (Domestic Hot Water) settings:

- **Temperature**: Set DHW setpoint (20-65°C)
- **Program Mode**: Always On, Program 1, 2, or 3, Always Off
- **Schedules**: Configure weekly heating times

### 4. Heating Circuit Settings

Control heating circuits (1-4):

- **Temperature**: View current temperature
- **Setpoint**: Set target temperature
- **Program Mode**: HP Optimized, Program 1-3, Always Reduced
- **Curve Settings**: Heating curve parameters
- **Summer Mode**: Automatic summer shutdown threshold

### 5. Weekly Schedules

View and edit weekly heating schedules:

```
┌─────────────────────────────────────┐
│  DHW Program 1                      │
│  ─────────────────────────────────  │
│  Monday      06:00 - 22:00          │
│  Tuesday     06:00 - 22:00          │
│  Wednesday   06:00 - 22:00          │
│  Thursday    06:00 - 22:00          │
│  Friday      06:00 - 22:00          │
│  Saturday    08:00 - 23:00          │
│  Sunday      08:00 - 23:00          │
└─────────────────────────────────────┘
```

**Note**: Schedule times must be on 30-minute boundaries (e.g., 06:00, 06:30, 07:00).

### 6. Energy Statistics

View energy consumption:

- **Heat Generated**: Total heat output in kWh
- **Auxiliary Heater**: Auxiliary heater consumption in kWh
- **Runtime Statistics**: Operating hours

### 7. Alarms

View and manage alarms:

- **Active Alarms**: Current fault conditions
- **Alarm History**: Past alarms with timestamps
- **Acknowledge**: Clear acknowledged alarms

## Common Tasks

### Check System Status

1. Launch the application
2. View the dashboard (shown automatically)
3. Press `r` to refresh values

### Adjust Hot Water Temperature

1. From dashboard, press `Enter` to open menu
2. Navigate to **Hot Water** → **Temperature**
3. Press `Enter` to edit
4. Type new value (e.g., `55`)
5. Press `Enter` to confirm

### View Weekly Schedule

1. Navigate to **Programs** → **DHW Program 1**
2. View schedule for all days
3. Use `↑`/`↓` to select a day
4. Press `Enter` to edit times

### Set Vacation Mode

1. Navigate to **Vacation**
2. Select circuit or DHW
3. Enter start and end dates
4. Press `Enter` to activate

## Troubleshooting

### "Connection failed"

- Check USB adapter is connected
- Verify device path: `ls /dev/ttyACM* /dev/ttyUSB*`
- Check permissions: `sudo chmod 666 /dev/ttyACM0`
- Add user to dialout group: `sudo usermod -a -G dialout $USER`

### "Communication timeout"

- Heat pump may be busy - wait and retry
- Check CAN bus connections
- Press `r` to retry

### Display looks corrupted

- Ensure terminal is at least 80x24 characters
- Try resizing terminal window
- Check terminal supports ANSI colors

### Cannot write values

- Check you're not in read-only mode
- Verify parameter is writable
- Ensure value is within valid range

## Remote Access via SSH

The terminal menu works perfectly over SSH:

```bash
# From another computer
ssh user@raspberrypi.local "buderus-tui /dev/ttyACM0"

# Or connect first, then run
ssh user@raspberrypi.local
buderus-tui /dev/ttyACM0
```

For persistent sessions, use `tmux` or `screen`:

```bash
# Start in tmux
tmux new -s heatpump "buderus-tui /dev/ttyACM0"

# Detach: Ctrl+b, then d
# Reattach later:
tmux attach -t heatpump
```

## Safety Notes

- **Read-only by default**: Use `--read-only` flag for monitoring-only access
- **Validation**: All values are validated before writing
- **Confirmation**: Important changes require confirmation
- **Graceful exit**: Always use `q` or `Ctrl+C` to exit cleanly
