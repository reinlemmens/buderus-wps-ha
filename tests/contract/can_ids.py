"""
CAN ID constants and construction formulas.

This module centralizes CAN ID definitions and the formulas used to
construct dynamic parameter access IDs.

# PROTOCOL: CAN ID construction formulas from fhem/26_KM273v018.pm:2229-2230
# Read:  rtr = 0x04003FE0 | (idx << 14)
# Write: txd = 0x0C003FE0 | (idx << 14)
"""

# Base CAN IDs for parameter read/write operations
CAN_ID_READ_BASE = 0x04003FE0
CAN_ID_WRITE_BASE = 0x0C003FE0

# Fixed CAN IDs for the discovery protocol
DISCOVERY_ELEMENT_COUNT_SEND = 0x01FD7FE0
DISCOVERY_ELEMENT_COUNT_RECV = 0x09FD7FE0
DISCOVERY_ELEMENT_DATA_SEND = 0x01FD3FE0
DISCOVERY_ELEMENT_DATA_RECV = 0x09FDBFE0
DISCOVERY_ELEMENT_BUFFER_READ = 0x01FDBFE0
