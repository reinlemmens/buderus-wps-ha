#!/usr/bin/env python3
"""Simple test to read parameters and verify CAN communication.

This script:
1. Connects to USBtin
2. Reads XDHW_TIME using static idx (2475)
3. Reads XDHW_TIME using discovered idx (2480 from strace)
4. Compares results
"""

import sys
import time
import logging

sys.path.insert(0, '/home/rein/buderus-wps-ha')

from buderus_wps.can_adapter import USBtinAdapter
from buderus_wps.can_message import CANMessage

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

SERIAL_PORT = '/dev/ttyACM0'


def calculate_can_id(idx: int) -> int:
    """Calculate CAN ID from element idx.

    PROTOCOL: CAN ID = 0x04003FE0 | (idx << 14)
    """
    return 0x04003FE0 | (idx << 14)


def read_parameter(adapter: USBtinAdapter, idx: int, name: str) -> bytes:
    """Read a parameter by idx."""
    can_id = calculate_can_id(idx)
    logger.info(f"Reading {name}: idx={idx}, CAN ID=0x{can_id:08X}")

    # Create RTR frame to request parameter value
    request = CANMessage(
        arbitration_id=can_id,
        data=b'',
        is_extended_id=True,
        is_remote_frame=True
    )

    try:
        response = adapter.send_frame(request, timeout=5.0)
        if response:
            logger.info(f"  Response ID=0x{response.arbitration_id:08X}, data={response.data.hex()}")
            return response.data
        else:
            logger.warning(f"  No response")
            return None
    except Exception as e:
        logger.error(f"  Error: {e}")
        return None


def write_parameter(adapter: USBtinAdapter, idx: int, name: str, value: int) -> bool:
    """Write a parameter value."""
    can_id = calculate_can_id(idx)
    logger.info(f"Writing {name}: idx={idx}, CAN ID=0x{can_id:08X}, value={value}")

    # Create frame with value (2 bytes, big-endian)
    data = value.to_bytes(2, 'big')

    request = CANMessage(
        arbitration_id=can_id,
        data=data,
        is_extended_id=True
    )

    try:
        response = adapter.send_frame(request, timeout=5.0)
        if response:
            logger.info(f"  Response ID=0x{response.arbitration_id:08X}, data={response.data.hex()}")
            return True
        else:
            logger.warning(f"  No response")
            return False
    except Exception as e:
        logger.error(f"  Error: {e}")
        return False


def main():
    logger.info("=" * 60)
    logger.info("XDHW_TIME Read/Write Test")
    logger.info("=" * 60)

    # Two possible idx values for XDHW_TIME
    STATIC_IDX = 2475   # From our static parameter_defaults.py
    FHEM_IDX = 2480     # From strace of FHEM (CAN ID 0x066C3FE0)

    logger.info(f"Static idx: {STATIC_IDX} -> CAN ID: 0x{calculate_can_id(STATIC_IDX):08X}")
    logger.info(f"FHEM idx:   {FHEM_IDX} -> CAN ID: 0x{calculate_can_id(FHEM_IDX):08X}")
    logger.info("-" * 60)

    try:
        with USBtinAdapter(SERIAL_PORT) as adapter:
            logger.info(f"Connected: {adapter.status}")
            logger.info("-" * 60)

            # Test 1: Read using static idx
            logger.info("TEST 1: Read with static idx (2475)")
            static_value = read_parameter(adapter, STATIC_IDX, "XDHW_TIME (static)")

            time.sleep(0.5)

            # Test 2: Read using FHEM idx
            logger.info("\nTEST 2: Read with FHEM idx (2480)")
            fhem_value = read_parameter(adapter, FHEM_IDX, "XDHW_TIME (fhem)")

            time.sleep(0.5)

            # Test 3: Write using FHEM idx (set to 1)
            logger.info("\nTEST 3: Write value 1 using FHEM idx (2480)")
            write_result = write_parameter(adapter, FHEM_IDX, "XDHW_TIME", 1)

            time.sleep(0.5)

            # Test 4: Read back to verify
            logger.info("\nTEST 4: Read back to verify write")
            verify_value = read_parameter(adapter, FHEM_IDX, "XDHW_TIME (verify)")

            # Summary
            logger.info("-" * 60)
            logger.info("SUMMARY:")
            logger.info(f"  Static idx read:  {static_value.hex() if static_value else 'FAILED'}")
            logger.info(f"  FHEM idx read:    {fhem_value.hex() if fhem_value else 'FAILED'}")
            logger.info(f"  Write succeeded:  {write_result}")
            logger.info(f"  Verify read:      {verify_value.hex() if verify_value else 'FAILED'}")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
