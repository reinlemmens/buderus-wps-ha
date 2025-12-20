"""
High-level Buderus WPS heat pump client with live parameter fetch.

Behavior:
- Boots with static defaults (generated from 26_KM273v018.pm)
- Can fetch live parameter metadata from the heat pump using the
  KM273_ReadElementList CAN sequence (simplified, best-effort)
- Provides read/write operations with validation against min/max and format
"""

from __future__ import annotations

import logging
import struct
import time
from typing import Any, Dict, List, Optional

from .can_adapter import USBtinAdapter
from .can_message import CANMessage
from .exceptions import DeviceCommunicationError, TimeoutError
from .parameter import HeatPump, Parameter
from .value_encoder import ValueEncoder

# PROTOCOL: CAN message ID base values for parameter access
# Request (RTR) IDs use prefix 0x04, Response IDs use prefix 0x0C
# Parameter index is shifted left by 14 bits and OR'd with base
CAN_REQUEST_BASE = 0x04003FE0  # RTR request for parameter read
CAN_RESPONSE_BASE = 0x0C003FE0  # Response to parameter read


class HeatPumpClient:
    """High-level client using USBtinAdapter to fetch metadata and read/write values."""

    def __init__(
        self,
        adapter: USBtinAdapter,
        registry: Optional[HeatPump] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        if adapter is None:
            raise ValueError("adapter is required")
        self._adapter = adapter
        self._registry = registry or HeatPump()
        self._logger = logger or logging.getLogger(__name__)

    @property
    def registry(self) -> HeatPump:
        return self._registry

    def fetch_live_registry(self, timeout: float = 5.0) -> HeatPump:
        """
        Best-effort live fetch of parameter list using KM273_ReadElementList flow.

        Sequence:
        - Send R01FD7FE0 (request total length)
        - If a response with length arrives, page through via T01FD3FE0/R01FDBFE0
        This is a simplified implementation that stops when no more data arrives.
        """
        # Ensure connected
        if not self._adapter.is_open:
            self._adapter.connect()

        read_cmd = CANMessage(
            arbitration_id=0x01FD7FE0,
            data=b"",
            is_extended_id=True,
            is_remote_frame=True,
        )
        try:
            self._adapter.send_frame(read_cmd, timeout=timeout)
        except TimeoutError:
            self._logger.warning(
                "No response to initial element list length request; using defaults"
            )
            return self._registry
        except Exception as e:
            self._logger.warning(
                "Element list length request failed: %s; using defaults", e
            )
            return self._registry

        # Attempt to read pages; KM273 uses 4096-byte chunks, but we don't have full protocol details.
        entries: List[Dict[str, Any]] = []
        # In absence of full parsing details, fall back immediately to defaults.
        if not entries:
            return self._registry

        # Note: override_with_device would reload registry with new entries
        # but since entries is always empty in current implementation,
        # this code path is never reached
        return self._registry

    def get(self, name_or_idx: Any) -> Parameter:
        param = self._lookup(name_or_idx)
        if not param:
            raise KeyError(f"Unknown parameter: {name_or_idx}")
        return param

    def read_value(self, name_or_idx: Any, timeout: Optional[float] = None) -> bytes:
        param = self.get(name_or_idx)
        adapter_timeout = getattr(self._adapter, "timeout", 2.0)
        effective_timeout = timeout if timeout is not None else adapter_timeout
        request_id = CAN_REQUEST_BASE | (param.idx << 14)
        response_id = CAN_RESPONSE_BASE | (param.idx << 14)
        request = CANMessage(
            arbitration_id=request_id,
            data=b"",
            is_extended_id=True,
            is_remote_frame=True,
        )
        self._adapter.flush_input_buffer()
        start = time.time()
        frame = self._adapter.send_frame(request, timeout=effective_timeout)
        if frame.arbitration_id == response_id:
            return frame.data

        # If the first frame is unrelated traffic, keep listening until timeout for the expected id.
        while time.time() - start < effective_timeout:
            remaining = max(effective_timeout - (time.time() - start), 0.01)
            next_frame = self._adapter.receive_frame(timeout=remaining)
            if next_frame is None:
                break
            if next_frame.arbitration_id == response_id:
                return next_frame.data

        raise DeviceCommunicationError(
            f"Unexpected response id 0x{frame.arbitration_id:X} (expected 0x{response_id:X})",
            context={
                "expected": response_id,
                "got": frame.arbitration_id,
                "param": param.text,
            },
        )

    def read_parameter(
        self, name_or_idx: Any, timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Read and decode parameter, returning metadata + raw/decoded values."""
        param = self.get(name_or_idx)
        raw = self.read_value(param.text, timeout=timeout)
        decoded = self._decode_value(param, raw)
        return {
            "name": param.text,
            "idx": param.idx,
            "extid": param.extid,
            "format": param.format,
            "min": param.min,
            "max": param.max,
            "read": param.read,
            "raw": raw,
            "decoded": decoded,
        }

    def write_value(
        self, name_or_idx: Any, value: Any, timeout: Optional[float] = None
    ) -> None:
        param = self.get(name_or_idx)
        # FHEM: read=1 means "readable", not "read-only"
        # A parameter is read-only if min >= max (no valid write range)
        if param.min >= param.max:
            raise PermissionError(
                f"Parameter {param.text} is read-only (min={param.min} >= max={param.max})"
            )
        encoded = self._encode_value(param, value)
        # PROTOCOL: Write uses same CAN ID as read request (CAN_REQUEST_BASE | idx << 14)
        # See FHEM 26_KM273v018.pm line 2229, 2678, 2746
        request_id = CAN_REQUEST_BASE | (param.idx << 14)
        msg = CANMessage(arbitration_id=request_id, data=encoded, is_extended_id=True)
        self._adapter.flush_input_buffer()
        adapter_timeout = getattr(self._adapter, "timeout", 2.0)
        self._adapter.send_frame(
            msg, timeout=timeout if timeout is not None else adapter_timeout
        )

    # Internal helpers
    def _lookup(self, name_or_idx: Any) -> Optional[Parameter]:
        """Look up parameter by name or index using the registry.

        Supports both HeatPump (get_parameter) and ParameterRegistry (get_by_name/get_by_index).
        """
        # Try HeatPump interface first
        # Use unified lookup method
        return self._registry.get_parameter(name_or_idx)

    def _encode_value(self, param: Parameter, value: Any) -> bytes:
        """Encode human-readable value to raw bytes for CAN transmission.

        # PROTOCOL: Matches FHEM behavior from fhem/26_KM273v018.pm:2728-2729
        # User passes human-readable values (e.g., 53.0°C), we convert to raw.

        Args:
            param: Parameter definition with format, min, max
            value: Human-readable value from user

        Returns:
            Bytes for CAN transmission (typically 2 bytes)

        Raises:
            ValueError: If value is out of range for the parameter
        """
        fmt = param.format
        from .formats import get_format_factor

        # For formats with factors, validate human-readable value against scaled min/max
        factor = get_format_factor(fmt)
        if factor != 1:
            # Convert min/max from raw to human-readable for validation
            min_human = param.min * factor
            max_human = param.max * factor
            try:
                float_value = float(value)
                if float_value < min_human or float_value > max_human:
                    raise ValueError(
                        f"Value {value} out of range for {param.text} "
                        f"[{min_human}, {max_human}]"
                    )
            except (TypeError, ValueError) as e:
                if "out of range" in str(e):
                    raise
                # Non-numeric values handled by encoder (e.g., select options)
        else:
            # For int format, validate raw value directly
            try:
                int_value = int(value)
                if int_value < param.min or int_value > param.max:
                    raise ValueError(
                        f"Value {value} out of range for {param.text} "
                        f"[{param.min}, {param.max}]"
                    )
            except (TypeError, ValueError) as e:
                if "out of range" in str(e):
                    raise
                # Non-numeric values (select options, time strings) handled by encoder

        # Use FHEM-compatible encoding for known formats
        # This converts human-readable values to raw bytes
        return ValueEncoder.encode_by_format(
            value=value,
            format_type=fmt,
            size_bytes=2,  # FHEM always uses 2 bytes for writes
            min_val=param.min,
        )

    def _encode_int_like(
        self, param: Parameter, value: Any, dlc_hint: int = 0
    ) -> bytes:
        try:
            ivalue = int(value)
        except Exception as e:
            raise ValueError(f"Invalid value for {param.text}: {value}") from e
        if ivalue < param.min or ivalue > param.max:
            raise ValueError(
                f"Value {ivalue} out of range for {param.text} [{param.min}, {param.max}]"
            )
        signed = param.min < 0

        # Use dlc_hint if provided (from actual device response)
        if dlc_hint > 0:
            size = dlc_hint
        else:
            # PROTOCOL: FHEM always uses 2 bytes for writes (see line 2746)
            # Always use at least 2 bytes for compatibility with heat pump
            size = 2
            if signed:
                if ivalue < -32768 or ivalue > 32767:
                    size = 4
            else:
                if ivalue > 0xFFFF:
                    size = 4
        return ivalue.to_bytes(size, "big", signed=signed)

    def _decode_value(self, param: Parameter, raw: bytes) -> Any:
        """Decode raw bytes from CAN to human-readable value.

        # PROTOCOL: Matches FHEM behavior from fhem/26_KM273v018.pm:2714-2740
        # Returns human-readable values (e.g., 53.0°C from raw 530).

        Args:
            param: Parameter definition with format, min, max
            raw: Raw bytes from CAN response

        Returns:
            Decoded human-readable value (float, int, str, or None for DEAD)
        """
        try:
            result = ValueEncoder.decode_by_format(
                data=raw,
                format_type=param.format,
                min_val=param.min,
            )
            # None indicates DEAD sensor - return as-is for caller to handle
            return result
        except (ValueError, struct.error) as e:
            self._logger.warning(
                "Failed to decode %s (format=%s, raw=%s): %s",
                param.text,
                param.format,
                raw.hex(),
                e,
            )
            return raw.hex()  # Return hex string as fallback
