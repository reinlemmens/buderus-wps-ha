"""Energy blocking control for Buderus WPS heat pump.

This module provides control for blocking energy consumption on
high-power components: the compressor and auxiliary (electric) heater.

Use cases:
- Demand response during peak electricity pricing
- Manual load shedding during high grid demand
- Integration with smart grid or home energy management systems

PROTOCOL: CAN Parameters
- COMPRESSOR_E21_EXTERN_BLOCK_BY_E21_EXT_1 (idx 263) - write compressor block
- COMPRESSOR_BLOCKED (idx 247) - read compressor status
- ADDITIONAL_USER_BLOCKED (idx 155) - write aux heater block
- ADDITIONAL_BLOCKED (idx 9) - read aux heater status

Reference: FHEM 26_KM273v018.pm lines 332, 415, 247
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .heat_pump import HeatPumpClient


# PROTOCOL: CAN Parameter indices
# Reference: FHEM 26_KM273v018.pm
PARAM_COMPRESSOR_BLOCK = "COMPRESSOR_E21_EXTERN_BLOCK_BY_E21_EXT_1"  # idx 263
PARAM_COMPRESSOR_STATUS = "COMPRESSOR_BLOCKED"  # idx 247
PARAM_AUX_HEATER_BLOCK = "ADDITIONAL_USER_BLOCKED"  # idx 155
PARAM_AUX_HEATER_STATUS = "ADDITIONAL_BLOCKED"  # idx 9


@dataclass
class BlockingState:
    """Status of a single component's blocking state.

    Attributes:
        component: Component identifier ("compressor" or "aux_heater")
        blocked: True if component is currently blocked
        source: Source of block ("user", "external", "system", "none")
        timestamp: Unix timestamp when status was read
    """

    component: str
    blocked: bool
    source: str
    timestamp: float


@dataclass
class BlockingResult:
    """Result of a blocking operation.

    Attributes:
        success: True if operation completed successfully
        component: Component that was targeted
        action: Action that was attempted ("block", "unblock", "clear_all")
        message: Human-readable result message
        error: Error details if success is False
    """

    success: bool
    component: str
    action: str
    message: str
    error: Optional[str] = None


@dataclass
class BlockingStatus:
    """Aggregate blocking status for all components.

    Attributes:
        compressor: Compressor blocking status
        aux_heater: Auxiliary heater blocking status
        timestamp: Unix timestamp of status read
    """

    compressor: BlockingState
    aux_heater: BlockingState
    timestamp: float


class EnergyBlockingControl:
    """Control energy blocking for heat pump components.

    Provides methods to block/unblock the compressor and auxiliary heater,
    preventing energy consumption during peak demand periods.

    PROTOCOL: Uses the following CAN parameters:
    - COMPRESSOR_E21_EXTERN_BLOCK_BY_E21_EXT_1 (idx 263) - write compressor block
    - COMPRESSOR_BLOCKED (idx 247) - read compressor status
    - ADDITIONAL_USER_BLOCKED (idx 155) - write aux heater block
    - ADDITIONAL_BLOCKED (idx 9) - read aux heater status
    """

    # Default timeout for blocking operations
    DEFAULT_TIMEOUT = 5.0

    def __init__(self, client: HeatPumpClient) -> None:
        """Initialize with an existing HeatPumpClient connection.

        Args:
            client: Connected HeatPumpClient instance
        """
        self._client = client

    def _write_compressor_block(self, blocked: bool, timeout: float) -> None:
        """Write compressor block state.

        PROTOCOL: Writes to COMPRESSOR_E21_EXTERN_BLOCK_BY_E21_EXT_1 (idx 263)
        """
        value = 1 if blocked else 0
        self._client.write_value(PARAM_COMPRESSOR_BLOCK, value, timeout=timeout)

    def _read_compressor_status(self, timeout: float) -> bool:
        """Read compressor blocked status.

        PROTOCOL: Reads COMPRESSOR_BLOCKED (idx 247)
        Returns True if compressor is blocked.
        """
        result = self._client.read_parameter(PARAM_COMPRESSOR_STATUS, timeout=timeout)
        decoded = result.get("decoded", 0)
        return bool(decoded != 0)

    def block_compressor(self, timeout: float = DEFAULT_TIMEOUT) -> BlockingResult:
        """Block the compressor from running.

        Writes to COMPRESSOR_E21_EXTERN_BLOCK_BY_E21_EXT_1 and verifies
        by reading COMPRESSOR_BLOCKED status.

        Args:
            timeout: Operation timeout in seconds

        Returns:
            BlockingResult with success status and message
        """
        try:
            self._write_compressor_block(True, timeout)

            # Verify block was applied
            is_blocked = self._read_compressor_status(timeout)
            if is_blocked:
                return BlockingResult(
                    success=True,
                    component="compressor",
                    action="block",
                    message="Compressor blocked successfully",
                )
            else:
                return BlockingResult(
                    success=False,
                    component="compressor",
                    action="block",
                    message="Block command sent but verification failed",
                    error="Status shows compressor still unblocked after write",
                )
        except Exception as e:
            return BlockingResult(
                success=False,
                component="compressor",
                action="block",
                message="Failed to block compressor",
                error=str(e),
            )

    def unblock_compressor(self, timeout: float = DEFAULT_TIMEOUT) -> BlockingResult:
        """Unblock the compressor, restoring normal operation.

        Writes to COMPRESSOR_E21_EXTERN_BLOCK_BY_E21_EXT_1 and verifies
        by reading COMPRESSOR_BLOCKED status.

        Args:
            timeout: Operation timeout in seconds

        Returns:
            BlockingResult with success status and message
        """
        try:
            self._write_compressor_block(False, timeout)

            # Verify unblock was applied
            is_blocked = self._read_compressor_status(timeout)
            if not is_blocked:
                return BlockingResult(
                    success=True,
                    component="compressor",
                    action="unblock",
                    message="Compressor unblocked successfully",
                )
            else:
                return BlockingResult(
                    success=False,
                    component="compressor",
                    action="unblock",
                    message="Unblock command sent but verification failed",
                    error="Status shows compressor still blocked after write",
                )
        except Exception as e:
            return BlockingResult(
                success=False,
                component="compressor",
                action="unblock",
                message="Failed to unblock compressor",
                error=str(e),
            )

    def _write_aux_heater_block(self, blocked: bool, timeout: float) -> None:
        """Write aux heater block state.

        PROTOCOL: Writes to ADDITIONAL_USER_BLOCKED (idx 155)
        """
        value = 1 if blocked else 0
        self._client.write_value(PARAM_AUX_HEATER_BLOCK, value, timeout=timeout)

    def _read_aux_heater_status(self, timeout: float) -> bool:
        """Read aux heater blocked status.

        PROTOCOL: Reads ADDITIONAL_BLOCKED (idx 9)
        Returns True if aux heater is blocked.
        """
        result = self._client.read_parameter(PARAM_AUX_HEATER_STATUS, timeout=timeout)
        decoded = result.get("decoded", 0)
        return bool(decoded != 0)

    def block_aux_heater(self, timeout: float = DEFAULT_TIMEOUT) -> BlockingResult:
        """Block the auxiliary (electric backup) heater from running.

        Writes to ADDITIONAL_USER_BLOCKED and verifies
        by reading ADDITIONAL_BLOCKED status.

        Args:
            timeout: Operation timeout in seconds

        Returns:
            BlockingResult with success status and message
        """
        try:
            self._write_aux_heater_block(True, timeout)

            # Verify block was applied
            is_blocked = self._read_aux_heater_status(timeout)
            if is_blocked:
                return BlockingResult(
                    success=True,
                    component="aux_heater",
                    action="block",
                    message="Auxiliary heater blocked successfully",
                )
            else:
                return BlockingResult(
                    success=False,
                    component="aux_heater",
                    action="block",
                    message="Block command sent but verification failed",
                    error="Status shows aux heater still unblocked after write",
                )
        except Exception as e:
            return BlockingResult(
                success=False,
                component="aux_heater",
                action="block",
                message="Failed to block auxiliary heater",
                error=str(e),
            )

    def unblock_aux_heater(self, timeout: float = DEFAULT_TIMEOUT) -> BlockingResult:
        """Unblock the auxiliary heater, restoring normal operation.

        Writes to ADDITIONAL_USER_BLOCKED and verifies
        by reading ADDITIONAL_BLOCKED status.

        Args:
            timeout: Operation timeout in seconds

        Returns:
            BlockingResult with success status and message
        """
        try:
            self._write_aux_heater_block(False, timeout)

            # Verify unblock was applied
            is_blocked = self._read_aux_heater_status(timeout)
            if not is_blocked:
                return BlockingResult(
                    success=True,
                    component="aux_heater",
                    action="unblock",
                    message="Auxiliary heater unblocked successfully",
                )
            else:
                return BlockingResult(
                    success=False,
                    component="aux_heater",
                    action="unblock",
                    message="Unblock command sent but verification failed",
                    error="Status shows aux heater still blocked after write",
                )
        except Exception as e:
            return BlockingResult(
                success=False,
                component="aux_heater",
                action="unblock",
                message="Failed to unblock auxiliary heater",
                error=str(e),
            )

    def get_status(self, timeout: float = DEFAULT_TIMEOUT) -> BlockingStatus:
        """Get the current blocking status of all components.

        Reads COMPRESSOR_BLOCKED and ADDITIONAL_BLOCKED to determine
        current blocking state.

        Args:
            timeout: Operation timeout in seconds

        Returns:
            BlockingStatus with current state of both components
        """
        current_time = time.time()

        # Read compressor status
        compressor_blocked = self._read_compressor_status(timeout)
        compressor_state = BlockingState(
            component="compressor",
            blocked=compressor_blocked,
            source="user" if compressor_blocked else "none",
            timestamp=current_time,
        )

        # Read aux heater status
        aux_heater_blocked = self._read_aux_heater_status(timeout)
        aux_heater_state = BlockingState(
            component="aux_heater",
            blocked=aux_heater_blocked,
            source="user" if aux_heater_blocked else "none",
            timestamp=current_time,
        )

        return BlockingStatus(
            compressor=compressor_state,
            aux_heater=aux_heater_state,
            timestamp=current_time,
        )

    def clear_all_blocks(self, timeout: float = DEFAULT_TIMEOUT) -> BlockingResult:
        """Clear all energy blocking restrictions.

        Unblocks both the compressor and auxiliary heater with a single call.

        Args:
            timeout: Operation timeout in seconds

        Returns:
            BlockingResult with combined success status
        """
        # Attempt to unblock compressor
        compressor_result = self.unblock_compressor(timeout)

        # Attempt to unblock aux heater
        aux_heater_result = self.unblock_aux_heater(timeout)

        # Check combined success
        if compressor_result.success and aux_heater_result.success:
            return BlockingResult(
                success=True,
                component="all",
                action="clear_all",
                message="All energy blocks cleared successfully",
            )
        else:
            # Report which one(s) failed
            failures = []
            if not compressor_result.success:
                failures.append("compressor")
            if not aux_heater_result.success:
                failures.append("aux_heater")

            return BlockingResult(
                success=False,
                component="all",
                action="clear_all",
                message=f"Partial failure clearing blocks: {', '.join(failures)} failed",
                error=f"compressor: {compressor_result.error}, aux_heater: {aux_heater_result.error}",
            )

    def block_all(self, timeout: float = DEFAULT_TIMEOUT) -> BlockingResult:
        """Block all energy-consuming components.

        Blocks both the compressor and auxiliary heater with a single call.
        Useful for demand response or load shedding scenarios.

        Args:
            timeout: Operation timeout in seconds

        Returns:
            BlockingResult with combined success status
        """
        # Attempt to block compressor
        compressor_result = self.block_compressor(timeout)

        # Attempt to block aux heater
        aux_heater_result = self.block_aux_heater(timeout)

        # Check combined success
        if compressor_result.success and aux_heater_result.success:
            return BlockingResult(
                success=True,
                component="all",
                action="block_all",
                message="All energy consumers blocked successfully",
            )
        else:
            # Report which one(s) failed
            failures = []
            if not compressor_result.success:
                failures.append("compressor")
            if not aux_heater_result.success:
                failures.append("aux_heater")

            return BlockingResult(
                success=False,
                component="all",
                action="block_all",
                message=f"Partial failure blocking: {', '.join(failures)} failed",
                error=f"compressor: {compressor_result.error}, aux_heater: {aux_heater_result.error}",
            )
