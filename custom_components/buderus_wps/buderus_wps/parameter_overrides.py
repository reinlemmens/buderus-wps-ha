"""Curated write-bounds overrides for parameters the tables mark unwritable."""

# PROTOCOL: the generated parameter tables (parameter_data.py /
# parameter_defaults.py) and element discovery both report min=0, max=0 for
# some parameters that are in fact writable on the device. write_value()
# treats min >= max as read-only and its range validation would reject every
# value against [0, 0], so such a parameter cannot be written at all.
#
# This module carries hand-curated bounds for those parameters, keyed by name
# (idx values drift between firmware versions; names are stable). An override
# is applied ONLY when the table's own bounds are unusable (min >= max), so a
# future regenerated table or discovery result that carries real bounds wins.
#
# Do NOT patch the generated tables instead: they are marked auto-generated
# and a regeneration would silently drop the edit, and update_from_discovery()
# re-applies the device-reported (empty) bounds on every connect.

from dataclasses import replace
from typing import Any

# name -> (min, max) in RAW units (same scale as the tables; 'tem' format
# raw values are tenths of a degree Celsius).
WRITE_BOUNDS_OVERRIDES: dict[str, tuple[int, int]] = {
    # Active DHW stop temperature (GT8), the register the controller charges
    # against in DHW_PROGRAM_MODE=1 "Always On" (issue #13). The table has
    # min=0/max=0; use the range of its Comfort/Economy siblings (idx 448/452:
    # 210-640 raw = 21.0-64.0 degrees C).
    "DHW_GT8_STOP_TEMP": (210, 640),
}


def apply_bounds_override(param: Any) -> Any:
    """Return param with curated bounds when its own bounds are unusable.

    Leaves the parameter untouched when the table already carries a valid
    write range (min < max) or when no override is registered.
    """
    override = WRITE_BOUNDS_OVERRIDES.get(param.text)
    if override is not None and param.min >= param.max:
        return replace(param, min=override[0], max=override[1])
    return param
