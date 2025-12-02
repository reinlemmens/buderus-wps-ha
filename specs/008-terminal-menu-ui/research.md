# Research: Terminal Menu UI

**Feature**: 008-terminal-menu-ui
**Date**: 2025-11-28

## Research Questions

### 1. Terminal UI Library Selection

**Question**: Which Python terminal UI library best fits the requirements?

**Options Evaluated**:

| Library | Pros | Cons |
|---------|------|------|
| curses (stdlib) | No dependencies, cross-platform, low-level control | Verbose, manual layout, no widgets |
| blessed | curses wrapper, easier API, positioning helpers | External dependency |
| textual | Modern, async, rich widgets | Heavy, complex for simple menus |
| prompt_toolkit | Great input handling | Better for prompts than full TUI |
| urwid | Widget-based, event-driven | Steeper learning curve |

**Decision**: `curses` (standard library)

**Rationale**:
- No external dependencies (constitution: minimal dependencies)
- Available on all target platforms (Linux, macOS, Windows via windows-curses)
- Sufficient for menu navigation and simple value editing
- Direct control over terminal rendering for SSH compatibility
- Team familiarity from similar projects

**Alternatives Rejected**:
- textual: Too heavy for simple hierarchical menu; would add complexity without benefit
- blessed: External dependency; curses is sufficient for our use case

---

### 2. Testing Strategy for Terminal UI

**Question**: How to test curses-based UI without a real terminal?

**Decision**: Use `unittest.mock` to mock curses and test logic separately

**Approach**:
1. **Unit tests**: Mock `curses.wrapper`, `stdscr`, and key input
2. **Integration tests**: Use `pyte` (terminal emulator) or record/replay
3. **Acceptance tests**: Use `pexpect` for end-to-end testing

**Key Patterns**:
```python
# Mock curses for unit tests
@patch('curses.wrapper')
@patch('curses.initscr')
def test_dashboard_render(mock_initscr, mock_wrapper):
    mock_stdscr = MagicMock()
    mock_stdscr.getmaxyx.return_value = (24, 80)
    # Test rendering logic
```

**Rationale**: Curses tests are notoriously difficult. Separating UI logic from rendering allows testing business logic independently. Full TUI tests use pexpect for realistic interaction.

---

### 3. Keyboard Input Handling

**Question**: How to handle arrow keys, escape sequences, and special keys?

**Decision**: Use curses keypad mode with a key mapping dictionary

**Implementation**:
```python
# Enable keypad mode for arrow keys
stdscr.keypad(True)

KEY_ACTIONS = {
    curses.KEY_UP: 'move_up',
    curses.KEY_DOWN: 'move_down',
    curses.KEY_LEFT: 'move_left',
    curses.KEY_RIGHT: 'move_right',
    curses.KEY_ENTER: 'select',
    10: 'select',  # Enter key
    13: 'select',  # Carriage return
    27: 'back',    # Escape
    ord('q'): 'quit',
    ord('r'): 'refresh',
}
```

**Rationale**: Curses handles terminal differences automatically when keypad mode is enabled. Mapping to actions decouples keys from behavior.

---

### 4. Screen Layout and Resize Handling

**Question**: How to handle different terminal sizes and resize events?

**Decision**: Minimum size requirement (80x24), dynamic reflow on resize

**Implementation**:
- Capture `curses.KEY_RESIZE` event
- Recalculate layout based on `stdscr.getmaxyx()`
- Display warning if terminal too small
- Center content in larger terminals

**Minimum Layout** (80x24):
```
+------------------------------------------------------------------------------+
| BUDERUS WPS HEAT PUMP                                    [Connected]         | <- Header (1 line)
+------------------------------------------------------------------------------+
| Home > Hot Water > Temperature                                               | <- Breadcrumb (1 line)
+------------------------------------------------------------------------------+
|                                                                              |
|   Outdoor Temperature:     8.5°C                                             |
|   Supply Temperature:     35.0°C                                             |
|   Hot Water Temperature:  52.0°C                                             |
|   Operating Mode:         HEATING                                            |
|   Compressor:             Running                                            |
|                                                                              |
|   [Menu Items...]                                                            |
|                                                                              |
+------------------------------------------------------------------------------+
| ↑↓ Navigate  Enter Select  Esc Back  r Refresh  q Quit                       | <- Help (1 line)
+------------------------------------------------------------------------------+
```

---

### 5. Connection State Management

**Question**: How to handle connection loss during operation?

**Decision**: Wrap all Menu API calls with error handling, display status in header

**States**:
1. **Connected**: Normal operation, green indicator
2. **Connecting**: Initial connection, show spinner
3. **Disconnected**: Error occurred, show message, offer retry
4. **Timeout**: Communication timeout, show warning

**Error Recovery**:
```python
try:
    value = api.status.outdoor_temperature
except TimeoutError:
    show_error("Communication timeout - press 'r' to retry")
except ConnectionError:
    show_error("Connection lost - press 'r' to reconnect")
```

---

### 6. Value Editing UX

**Question**: How should users edit numeric and enumeration values?

**Decision**: Inline editing with immediate validation

**Numeric Values** (e.g., temperature):
1. Press Enter to start editing
2. Current value shown with cursor
3. Type new value (numbers only)
4. Backspace to delete
5. Enter to confirm, Escape to cancel
6. Validation error shown if out of range

**Enumeration Values** (e.g., program mode):
1. Press Enter to see options
2. Up/Down to select
3. Enter to confirm
4. Escape to cancel

**Time Values** (schedules):
1. Show HH:MM format
2. Edit hours and minutes separately
3. Validate 30-minute boundaries

---

### 7. Menu API Integration

**Question**: How to integrate with existing Menu API from feature 007?

**Decision**: Use MenuAPI as the data source, MenuNavigator for navigation

**Integration Points**:

| TUI Component | Menu API Class | Usage |
|---------------|----------------|-------|
| Dashboard | StatusView | `api.status.read_all()` |
| Menu Navigation | MenuNavigator | `api.menu.navigate()`, `.items()`, `.up()` |
| Value Display | MenuNavigator | `api.menu.get_value()` |
| Value Editing | Various Controllers | `api.hot_water.temperature = x` |
| Schedules | HotWaterController, Circuit | `.get_schedule()`, `.set_schedule()` |
| Alarms | AlarmController | `.active_alarms`, `.acknowledge()` |

**Initialization**:
```python
from buderus_wps import USBtinAdapter, HeatPumpClient, ParameterRegistry, MenuAPI

def create_api(device_path: str) -> MenuAPI:
    adapter = USBtinAdapter(device_path)
    adapter.connect()
    registry = ParameterRegistry()
    client = HeatPumpClient(adapter, registry)
    return MenuAPI(client)
```

---

### 8. Broadcast Temperature Integration

**Question**: How to obtain reliable temperature readings for the dashboard?

**Decision**: Use CAN broadcast monitoring from feature 009

**Rationale**:
- RTR request/response returns unreliable 1-byte ACKs
- Broadcast monitoring captures actual sensor values from CAN traffic
- 3-second collection window provides all temperature data
- TEMP_BROADCAST_MAP defines sensor-to-name mappings

**Implementation**:
```python
from buderus_wps.config import get_default_sensor_map
from buderus_wps.broadcast import BroadcastMonitor

monitor = BroadcastMonitor(adapter, get_default_sensor_map())
readings = monitor.collect(duration=3.0)
temps = {r.sensor_name: r.temperature for r in readings}
```

---

### 9. Dynamic Circuit Configuration

**Question**: How to support configurable number of heating circuits (1-4)?

**Decision**: Load circuit configuration from buderus-wps.yaml at startup

**Rationale**:
- Different installations have different numbers of circuits
- Menu structure adapts based on configuration
- YAML already used for sensor mappings (feature 009)
- Graceful fallback if config missing

**Configuration Format**:
```yaml
circuits:
  - number: 1
    name: "Ground Floor"
    room_temp_sensor: "room_temp_c1"
  - number: 2
    name: "First Floor"
    room_temp_sensor: "room_temp_c2"
```

---

### 10. Compressor Status Display

**Question**: How to show compressor running state, frequency, and mode?

**Decision**: Use verified COMPRESSOR_REAL_FREQUENCY and request parameters

**Rationale** (verified 2024-12-02):
- `COMPRESSOR_REAL_FREQUENCY > 0` = compressor running
- `COMPRESSOR_DHW_REQUEST > 0` = DHW mode
- `COMPRESSOR_HEATING_REQUEST > 0` = Heating mode
- `COMPRESSOR_STATE` returns state code (not boolean), not reliable for running detection

**Dashboard Display**:
```
Compressor: Running at 45 Hz (DHW)
   - or -
Compressor: Stopped (Idle)
```

---

## Summary

All research questions resolved. Key decisions:

1. **curses** (stdlib) for terminal UI - no external dependencies
2. **Mock-based testing** with pexpect for acceptance tests
3. **Keypad mode** for cross-platform key handling
4. **80x24 minimum** with dynamic resize support
5. **Status indicator** in header for connection state
6. **Inline editing** with immediate validation
7. **Direct integration** with Menu API from feature 007
