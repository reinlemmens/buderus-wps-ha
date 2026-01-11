"""CAN message dataclass with SLCAN format conversion.

This module implements the CANMessage dataclass representing a single CAN bus
protocol data unit. It provides validation, SLCAN format encoding/decoding,
and support for both standard (11-bit) and extended (29-bit) CAN frames.

Protocol References:
- CAN 2.0A: Standard 11-bit identifier frames
- CAN 2.0B: Extended 29-bit identifier frames
- SLCAN: Lawicel ASCII protocol for USB serial communication

CAN ID Structure for Broadcast Data (Hardware Verified 2025-12-05):
- Bits 31-24: Prefix (0x0C = data, 0x00 = status, 0x08 = counter)
- Bits 23-12: Parameter Index (identifies the parameter type)
- Bits 11-0:  Element Type (0x060-0x063 = E21/E22/E31/E32 units)
"""

from dataclasses import dataclass
from typing import Optional

# CAN ID Prefix Constants (Bits 31-24)
# PROTOCOL: Prefixes identify the type of CAN message
CAN_PREFIX_DATA = 0x0C  # Response/data frame prefix
CAN_PREFIX_STATUS = 0x00  # Status frame prefix
CAN_PREFIX_COUNTER = 0x08  # Counter/timer frame prefix

# Element Type Constants (Bits 11-0)
# PROTOCOL: Element types identify the heat pump unit or data category
ELEMENT_E21 = 0x060  # Unit E21 (primary)
ELEMENT_E22 = 0x061  # Unit E22 (secondary)
ELEMENT_E31 = 0x062  # Unit E31
ELEMENT_E32 = 0x063  # Unit E32
ELEMENT_COUNTER = 0x270  # Counter/timer values
ELEMENT_CONFIG = 0x403  # Configuration parameters


@dataclass
class CANMessage:
    """Immutable CAN message with validation and SLCAN conversion.

    Attributes:
        arbitration_id: CAN identifier (0x000-0x7FF for standard,
                       0x00000000-0x1FFFFFFF for extended)
        data: Message payload (0-8 bytes)
        is_extended_id: True for 29-bit extended frame, False for 11-bit standard
        is_remote_frame: True for Remote Transmission Request (RTR)
        timestamp: Unix timestamp of reception (None for outbound messages)
    """

    arbitration_id: int
    data: bytes
    is_extended_id: bool = False
    is_remote_frame: bool = False
    timestamp: Optional[float] = None
    _requested_dlc: Optional[int] = (
        None  # For remote frames, DLC may differ from len(data)
    )

    def __post_init__(self) -> None:
        """Validate message parameters after initialization.

        Raises:
            ValueError: Invalid arbitration ID range, data length, or remote frame with data
            TypeError: Data is not bytes type
        """
        # Validate arbitration ID range
        # Note: Using 32-bit range for extended IDs to support real Buderus heat pump IDs
        # which exceed the standard CAN 2.0B 29-bit limit
        if self.is_extended_id:
            if not (0 <= self.arbitration_id <= 0xFFFFFFFF):
                raise ValueError(
                    f"Extended frame arbitration_id must be in range 0x00000000-0xFFFFFFFF, "
                    f"got 0x{self.arbitration_id:08X}"
                )
        else:
            if not (0 <= self.arbitration_id <= 0x7FF):
                raise ValueError(
                    f"Standard frame arbitration_id must be in range 0x000-0x7FF, "
                    f"got 0x{self.arbitration_id:03X}"
                )

        # Validate data type
        if not isinstance(self.data, bytes):
            raise TypeError(f"Data must be bytes, got {type(self.data).__name__}")

        # Validate data length
        if not (0 <= len(self.data) <= 8):
            raise ValueError(
                f"Data length must be 0-8 bytes, got {len(self.data)} bytes"
            )

        # Validate remote frame constraint
        if self.is_remote_frame and len(self.data) > 0:
            raise ValueError(
                "Remote frames cannot contain data (data length must be 0)"
            )

    @property
    def dlc(self) -> int:
        """Data Length Code - number of bytes in payload.

        For remote frames, returns the requested DLC (which may be > 0 even with empty data).
        For data frames, returns the actual data length.

        Returns:
            Length of data field (0-8), or requested DLC for remote frames
        """
        if self.is_remote_frame and self._requested_dlc is not None:
            return self._requested_dlc
        return len(self.data)

    def to_usbtin_format(self) -> str:
        """Convert message to SLCAN (USBtin) format string.

        Format:
            Standard data frame:  t<III><L><DD...>\\r
            Extended data frame:  T<IIIIIIII><L><DD...>\\r
            Standard remote frame: r<III><L>\\r
            Extended remote frame: R<IIIIIIII><L>\\r

        Where:
            <III> = 3 hex digit ID (standard)
            <IIIIIIII> = 8 hex digit ID (extended)
            <L> = 1 hex digit data length (0-8)
            <DD...> = 2 hex digits per data byte

        Returns:
            SLCAN formatted string with \\r terminator

        Examples:
            >>> msg = CANMessage(0x123, b'\\x01\\x02', is_extended_id=False)
            >>> msg.to_usbtin_format()
            't1231220102\\r'
        """
        # Select command character
        if self.is_remote_frame:
            cmd = "R" if self.is_extended_id else "r"
        else:
            cmd = "T" if self.is_extended_id else "t"

        # Format arbitration ID
        if self.is_extended_id:
            id_str = f"{self.arbitration_id:08X}"
        else:
            id_str = f"{self.arbitration_id:03X}"

        # Format data length code
        dlc_str = f"{self.dlc:01X}"

        # Format data bytes
        data_str = self.data.hex().upper()

        return f"{cmd}{id_str}{dlc_str}{data_str}\r"

    @classmethod
    def from_usbtin_format(cls, frame: str) -> "CANMessage":
        """Parse SLCAN (USBtin) format string to CANMessage.

        Args:
            frame: SLCAN formatted string (with or without \\r terminator)

        Returns:
            Parsed CANMessage instance

        Raises:
            ValueError: Invalid frame format, bad hex characters, or length mismatch

        Examples:
            >>> msg = CANMessage.from_usbtin_format('t12341122\\r')
            >>> msg.arbitration_id
            0x123
            >>> msg.data
            b'\\x11\\x22'
        """
        # Remove trailing \r if present
        frame = frame.rstrip("\r")

        # Validate minimum length
        if len(frame) < 2:
            raise ValueError(
                f"Invalid SLCAN frame format: too short (min 2 chars, got {len(frame)})"
            )

        # Parse command character
        cmd = frame[0]
        if cmd not in ("t", "T", "r", "R"):
            raise ValueError(
                f"Invalid SLCAN frame format: unknown command '{cmd}' "
                "(expected 't', 'T', 'r', or 'R')"
            )

        is_extended = cmd in ("T", "R")
        is_remote = cmd in ("r", "R")

        # Determine ID field length
        id_len = 8 if is_extended else 3

        # Validate frame has enough characters for ID and DLC
        if len(frame) < 1 + id_len + 1:
            raise ValueError(
                f"Invalid SLCAN frame format: too short for {cmd} frame "
                f"(expected at least {1 + id_len + 1} chars, got {len(frame)})"
            )

        # Parse arbitration ID
        id_str = frame[1 : 1 + id_len]
        try:
            arbitration_id = int(id_str, 16)
        except ValueError:
            raise ValueError(f"Invalid hexadecimal in arbitration ID: '{id_str}'")

        # Parse DLC
        dlc_str = frame[1 + id_len : 1 + id_len + 1]
        try:
            dlc = int(dlc_str, 16)
        except ValueError:
            raise ValueError(f"Invalid hexadecimal in DLC: '{dlc_str}'")

        if not (0 <= dlc <= 8):
            raise ValueError(f"Invalid DLC value: {dlc} (must be 0-8)")

        # Parse data bytes (if not remote frame)
        if is_remote:
            data = b""
        else:
            data_str = frame[1 + id_len + 1 :]

            # Validate data length matches DLC
            expected_data_len = dlc * 2  # 2 hex chars per byte
            if len(data_str) != expected_data_len:
                raise ValueError(
                    f"Data length mismatch: DLC={dlc} expects {expected_data_len} "
                    f"hex chars, got {len(data_str)}"
                )

            # Parse data bytes
            try:
                data = bytes.fromhex(data_str)
            except ValueError:
                raise ValueError(f"Invalid hexadecimal in data: '{data_str}'")

        # Create message with requested DLC for remote frames
        msg = cls(
            arbitration_id=arbitration_id,
            data=data,
            is_extended_id=is_extended,
            is_remote_frame=is_remote,
        )

        # For remote frames, store the requested DLC
        if is_remote:
            object.__setattr__(msg, "_requested_dlc", dlc)

        return msg

    def decode_broadcast_id(self) -> tuple[int, int, int]:
        """Decode broadcast CAN ID into prefix, parameter index, and element type.

        The Buderus WPS heat pump broadcasts sensor data using a specific CAN ID
        structure. This method extracts the three components:

        CAN ID Structure (32-bit):
            Bits 31-24: Prefix (message type)
                - 0x0C: Data/response frame
                - 0x00: Status frame
                - 0x08: Counter/timer frame
            Bits 23-12: Parameter Index (identifies the parameter)
            Bits 11-0:  Element Type (identifies the unit/category)
                - 0x060-0x063: E21/E22/E31/E32 heat pump units
                - 0x270: Counter values
                - 0x403: Configuration parameters

        Returns:
            Tuple of (prefix, param_idx, element_type) as integers

        Examples:
            >>> msg = CANMessage(0x0C084060, b'\\x00\\xD6', is_extended_id=True)
            >>> msg.decode_broadcast_id()
            (12, 132, 96)  # (0x0C, 0x084, 0x060)

        Hardware Verified: 2025-12-05 against FHEM reference readings
        """
        # PROTOCOL: Extract components using bit masking
        prefix = (self.arbitration_id >> 24) & 0xFF  # Bits 31-24
        param_idx = (self.arbitration_id >> 12) & 0xFFF  # Bits 23-12
        element_type = self.arbitration_id & 0xFFF  # Bits 11-0

        return prefix, param_idx, element_type
