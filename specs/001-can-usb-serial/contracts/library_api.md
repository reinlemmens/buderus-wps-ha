# Library API Contract: CAN over USB Serial Connection

**Feature**: 001-can-usb-serial | **Version**: 1.0.0 | **Python**: 3.9+

## CANMessage

```python
@dataclass
class CANMessage:
    arbitration_id: int
    data: bytes
    is_extended_id: bool = False
    is_remote_frame: bool = False
    timestamp: Optional[float] = None
    
    @property
    def dlc(self) -> int: ...
    
    def to_usbtin_format(self) -> str: ...
    
    @classmethod
    def from_usbtin_format(cls, frame: str) -> 'CANMessage': ...
```

## USBtinAdapter

```python
class USBtinAdapter:
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 5.0): ...
    
    def connect(self) -> 'USBtinAdapter': ...
    def disconnect(self) -> None: ...
    
    @property
    def is_open(self) -> bool: ...
    
    def send_frame(self, message: CANMessage, timeout: Optional[float] = None) -> CANMessage: ...
    def receive_frame(self, timeout: Optional[float] = None) -> CANMessage: ...
    
    def __enter__(self) -> 'USBtinAdapter': ...
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool: ...
```

## ValueEncoder

```python
class ValueEncoder:
    @staticmethod
    def encode_temperature(temp_celsius: float, format_type: str = 'temp') -> bytes: ...
    
    @staticmethod
    def decode_temperature(data: bytes, format_type: str = 'temp') -> float: ...
    
    @staticmethod
    def encode_int(value: int, size_bytes: int = 4, signed: bool = True) -> bytes: ...
    
    @staticmethod
    def decode_int(data: bytes, signed: bool = True) -> int: ...
```

## Usage Example

```python
from buderus_wps.can_adapter import USBtinAdapter
from buderus_wps.can_message import CANMessage
from buderus_wps.value_encoder import ValueEncoder

with USBtinAdapter('/dev/ttyACM0') as adapter:
    request = CANMessage(arbitration_id=0x31D011E9, data=b'\x01', is_extended_id=True)
    response = adapter.send_frame(request)
    temp = ValueEncoder.decode_temperature(response.data, 'temp')
    print(f"Temperature: {temp}°C")
```

See full API documentation for detailed parameters, exceptions, and examples.
