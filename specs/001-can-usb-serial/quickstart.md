# Quickstart Guide: CAN over USB Serial Connection

Get up and running with the Buderus WPS heat pump CAN communication library in minutes.

## Prerequisites

### Hardware
- USBtin CAN adapter (or compatible SLCAN adapter)
- Buderus WPS heat pump with CAN bus connection
- USB cable

### Software
- Python 3.9 or higher
- Serial port drivers (usually automatic)

### Permissions (Linux/macOS)
```bash
sudo usermod -a -G dialout $USER
# Log out and back in
```

## Installation

```bash
pip install buderus-wps
```

## Quick Example

```python
from buderus_wps.can_adapter import USBtinAdapter
from buderus_wps.can_message import CANMessage
from buderus_wps.value_encoder import ValueEncoder

# Connect and read temperature
with USBtinAdapter('/dev/ttyACM0') as adapter:
    request = CANMessage(
        arbitration_id=0x31D011E9,
        data=b'\x00',
        is_extended_id=True
    )
    
    response = adapter.send_frame(request)
    temp_celsius = ValueEncoder.decode_temperature(response.data, 'temp')
    print(f"Outdoor Temperature: {temp_celsius}°C")
```

## Finding Serial Port

**Linux/macOS:**
```bash
ls /dev/tty*
# Look for /dev/ttyACM0 or /dev/tty.usbmodem*
```

**Windows:**
```python
import serial.tools.list_ports
for port in serial.tools.list_ports.comports():
    print(f"{port.device}: {port.description}")
```

## Error Handling

```python
try:
    with USBtinAdapter('/dev/ttyACM0') as adapter:
        response = adapter.send_frame(request)
except FileNotFoundError:
    print("Serial port not found")
except TimeoutError:
    print("No response from heat pump")
except ConnectionError as e:
    print(f"Connection error: {e}")
```

## Troubleshooting

### Port Access Denied
```bash
sudo usermod -a -G dialout $USER
```

### Port Not Found
- Verify USB adapter is connected: `ls /dev/tty*`
- Check driver installation
- Try different USB port

### No Response / Timeout
- Check CAN bus connection to heat pump
- Verify heat pump is powered on
- Check CAN bus termination (120Ω resistors)

## Next Steps

- **API Reference**: Detailed class documentation
- **Parameter Guide**: Complete list of Buderus parameters
- **Examples**: Temperature monitoring, web dashboard, Home Assistant integration

---

Ready to start? Copy the Quick Example and modify for your parameters!
