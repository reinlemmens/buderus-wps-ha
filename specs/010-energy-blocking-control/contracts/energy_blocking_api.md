# API Contract: Energy Blocking Control

**Feature**: 010-energy-blocking-control
**Date**: 2025-12-06
**Type**: Python Library API

## Library API: EnergyBlockingControl

### Class Definition

```python
class EnergyBlockingControl:
    """Control energy blocking for heat pump components.

    Provides methods to block/unblock the compressor and auxiliary heater,
    preventing energy consumption during peak demand periods.
    """

    def __init__(self, client: HeatPumpClient) -> None:
        """Initialize with an existing HeatPumpClient connection.

        Args:
            client: Connected HeatPumpClient instance
        """
        ...

    def block_compressor(self, timeout: float = 5.0) -> BlockingResult:
        """Block the compressor from running.

        Args:
            timeout: Operation timeout in seconds

        Returns:
            BlockingResult with success status and message
        """
        ...

    def unblock_compressor(self, timeout: float = 5.0) -> BlockingResult:
        """Unblock the compressor, restoring normal operation.

        Args:
            timeout: Operation timeout in seconds

        Returns:
            BlockingResult with success status and message
        """
        ...

    def block_aux_heater(self, timeout: float = 5.0) -> BlockingResult:
        """Block the auxiliary (electric backup) heater.

        Args:
            timeout: Operation timeout in seconds

        Returns:
            BlockingResult with success status and message
        """
        ...

    def unblock_aux_heater(self, timeout: float = 5.0) -> BlockingResult:
        """Unblock the auxiliary heater, restoring normal operation.

        Args:
            timeout: Operation timeout in seconds

        Returns:
            BlockingResult with success status and message
        """
        ...

    def get_status(self, timeout: float = 3.0) -> BlockingStatus:
        """Read current blocking status for all components.

        Args:
            timeout: Operation timeout in seconds

        Returns:
            BlockingStatus with compressor and aux_heater states
        """
        ...

    def clear_all_blocks(self, timeout: float = 5.0) -> BlockingResult:
        """Clear all blocking restrictions, restoring normal operation.

        Args:
            timeout: Operation timeout in seconds

        Returns:
            BlockingResult with success status and message
        """
        ...
```

### Data Classes

```python
@dataclass
class BlockingState:
    """Status of a single component's blocking state."""
    component: str  # "compressor" or "aux_heater"
    blocked: bool   # True if blocked
    source: str     # "user", "external", "system", "none"
    timestamp: float

@dataclass
class BlockingResult:
    """Result of a blocking operation."""
    success: bool
    component: str
    action: str  # "block", "unblock", "clear_all"
    message: str
    error: Optional[str] = None

@dataclass
class BlockingStatus:
    """Aggregate blocking status."""
    compressor: BlockingState
    aux_heater: BlockingState
    timestamp: float
```

## CLI API

### Commands

```bash
# Block compressor
buderus-wps energy block-compressor [--timeout SECONDS]

# Unblock compressor
buderus-wps energy unblock-compressor [--timeout SECONDS]

# Block auxiliary heater
buderus-wps energy block-aux-heater [--timeout SECONDS]

# Unblock auxiliary heater
buderus-wps energy unblock-aux-heater [--timeout SECONDS]

# View status
buderus-wps energy status [--format json|text]

# Clear all blocks
buderus-wps energy clear-all [--timeout SECONDS]
```

### Output Formats

#### Text Output (default)

```
Energy Blocking Status:
  Compressor:     BLOCKED (user)
  Aux Heater:     Normal
```

#### JSON Output (--format json)

```json
{
  "compressor": {
    "component": "compressor",
    "blocked": true,
    "source": "user",
    "timestamp": 1733500800.0
  },
  "aux_heater": {
    "component": "aux_heater",
    "blocked": false,
    "source": "none",
    "timestamp": 1733500800.0
  }
}
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Command failed (communication error, etc.) |
| 2 | Invalid arguments |

## TUI Integration (Optional)

If TUI is available, add menu item under Settings or main menu:

```
Energy Control
├── Block Compressor      [ON/OFF toggle]
├── Block Aux Heater      [ON/OFF toggle]
└── Clear All Blocks      [action]
```

## Error Responses

### Communication Timeout

```python
BlockingResult(
    success=False,
    component="compressor",
    action="block",
    message="Failed to block compressor",
    error="Communication timeout after 5.0 seconds"
)
```

### Verification Failure

```python
BlockingResult(
    success=False,
    component="aux_heater",
    action="block",
    message="Block command sent but verification failed",
    error="Status shows aux_heater still unblocked after write"
)
```
