# Exception Hierarchy

**Feature**: 001-can-usb-serial | **Version**: 1.0.0

## Exception Tree

```
BuderusCANException (base)
├── ConnectionError
│   ├── DeviceNotFoundError
│   ├── DevicePermissionError
│   ├── DeviceDisconnectedError
│   └── DeviceInitializationError
├── TimeoutError
│   ├── ReadTimeoutError
│   └── WriteTimeoutError
├── CANError
│   ├── CANBusOffError
│   ├── CANBitrateError
│   └── CANFrameError
└── ConcurrencyError
```

## Key Exceptions

### ConnectionError
Raised when serial port cannot be opened or device disconnects.

### TimeoutError  
Raised when no response received within timeout period (default: 5s).

### CANError
Raised for CAN bus protocol errors (bus-off, bitrate mismatch, malformed frames).

### ConcurrencyError
Raised when concurrent operations attempted (library is NOT thread-safe).

## Python Built-ins

- **ValueError**: Invalid parameter values (ID out of range, data length > 8 bytes, etc.)
- **TypeError**: Incorrect parameter types (data not bytes, etc.)

See full exceptions documentation for detailed error messages and troubleshooting.
