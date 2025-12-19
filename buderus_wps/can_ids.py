"""CAN ID constants for Buderus WPS heat pump protocol.

# PROTOCOL: CAN ID base values from fhem/26_KM273v018.pm:2229-2230
# These are the fundamental addressing constants for parameter access.
"""

# PROTOCOL: RTR request base for parameter read (line 2229)
# Usage: read_id = CAN_ID_READ_BASE | (param_idx << 14)
CAN_ID_READ_BASE = 0x04003FE0

# PROTOCOL: Response/write base for parameter access (line 2230)
# Usage: write_id = CAN_ID_WRITE_BASE | (param_idx << 14)
CAN_ID_WRITE_BASE = 0x0C003FE0
