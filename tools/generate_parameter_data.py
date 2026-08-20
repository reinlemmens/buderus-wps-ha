#!/usr/bin/env python3
"""Regenerate parameter_data.py from a FHEM element-list discovery capture.

The heat pump's element list (idx, extid, min, max, name) is the authoritative
source for CAN addressing: idx values differ between firmware versions and from
the static FHEM table (fhem/26_KM273v018.pm). Hand-patching individual idx
values created duplicate indices (see GitHub issue #11); this script rebuilds
the whole fallback table from a real device capture so it can never diverge
entry-by-entry again.

The capture is an strace of FHEM performing KM273_ReadElementList against the
device; every discovered element is logged as:

    KM273_ReadElementList done, idx=280 extid=e16a8a67f000ad max=60 min=0 element=COMPRESSOR_RESTART_TIME

format/read metadata is not part of the device element list, so it is merged
from parameter_defaults.py (pristine FHEM copy). Device day-program names
(e.g. DHW_PROGRAM_1_MON) map to FHEM's numbered variants (DHW_PROGRAM_1_1MON),
mirroring FHEM's own KM273_UpdateElements day-name handling.

Usage:
    python3 tools/generate_parameter_data.py [capture.hex]
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CAPTURE = REPO_ROOT / "fhem/fhem-capture/capture-20251224-174533.hex"
OUTPUT = REPO_ROOT / "custom_components/buderus_wps/buderus_wps/parameter_data.py"
DEFAULTS = REPO_ROOT / "custom_components/buderus_wps/buderus_wps/parameter_defaults.py"

ELEMENT_RE = re.compile(
    r"KM273_ReadElementList done, "
    r"idx=(\d+) extid=([0-9a-f]+) max=(-?\d+) min=(-?\d+) element=([A-Za-z0-9_]+)"
)

# Device names use plain day tokens (MON); FHEM's static table numbers them
# (1MON) for sort order. Same mapping FHEM applies in KM273_UpdateElements.
DAY_TOKENS = {
    "MON": "1MON",
    "TUE": "2TUE",
    "WED": "3WED",
    "THU": "4THU",
    "FRI": "5FRI",
    "SAT": "6SAT",
    "SUN": "7SUN",
}
DAY_RE = re.compile(r"_(MON|TUE|WED|THU|FRI|SAT|SUN)(?=_|$)")

HEADER = '''"""Parameter data discovered from the heat pump's element list.

# PROTOCOL: idx values are device-specific and MUST come from element discovery.
# This table was generated from a real device capture and serves as the fallback
# when live discovery is unavailable. Regenerate with:
#     python3 tools/generate_parameter_data.py
#
# Source capture: {capture}
# Elements: {count} (unique idx, unique extid, unique text)
# format/read metadata merged from parameter_defaults.py (FHEM static table).
#
# Each parameter is represented as a dictionary with the following keys:
#     idx: int - Device parameter index (used to build CAN IDs: 0x04003FE0 | idx << 14)
#     extid: str - External ID (14-character hex string, globally unique)
#     min: int - Minimum allowed value (can be negative)
#     max: int - Maximum allowed value
#     format: str - Data format type ("int", "tem", "sw1", "sw2", etc.)
#     read: int - FHEM cyclic-poll flag (1=include in polling list)
#     text: str - Human-readable parameter name (ALL_CAPS_WITH_UNDERSCORES)
"""

from __future__ import annotations

from typing import Optional, cast

PARAMETER_DATA = [
'''

FOOTER = ''']


# =========================================================================
# Helper Functions for Discovery Protocol
# These allow discovery.py to enrich discovered parameters with format/read
# metadata from the static fallback data.
# =========================================================================

# Build lookup dictionaries for fast access by name
_FORMAT_BY_NAME: dict[str, str] = {
    str(p["text"]).upper(): str(p["format"]) for p in PARAMETER_DATA
}
_READ_BY_NAME: dict[str, int] = {
    str(p["text"]).upper(): cast(int, p["read"]) for p in PARAMETER_DATA
}
_PARAM_BY_NAME = {str(p["text"]).upper(): p for p in PARAMETER_DATA}
_PARAM_BY_IDX = {p["idx"]: p for p in PARAMETER_DATA}


def get_format_for_name(name: str) -> Optional[str]:
    """Get the FHEM format type for a parameter by name.

    # PROTOCOL: Format lookup for discovery enrichment

    Args:
        name: Parameter name (case-insensitive)

    Returns:
        Format string ('tem', 'pw2', 'int', etc.) or None if not found

    Example:
        >>> get_format_for_name('OUTDOOR_TEMP')
        'tem'
        >>> get_format_for_name('ACCESS_LEVEL')
        'int'
    """
    return _FORMAT_BY_NAME.get(name.upper())


def get_read_flag_for_name(name: str) -> Optional[int]:
    """Get the read-only flag for a parameter by name.

    # PROTOCOL: Read flag lookup for discovery enrichment
    # In FHEM: read=0 means writable (not polled), read=1 means read-only (polled)

    Args:
        name: Parameter name (case-insensitive)

    Returns:
        Read flag (0=writable, 1=read-only) or None if not found

    Example:
        >>> get_read_flag_for_name('ACCESS_LEVEL')
        0
        >>> get_read_flag_for_name('STATUS')
        1
    """
    return _READ_BY_NAME.get(name.upper())


def get_parameter_by_name(name: str) -> Optional[dict]:
    """Get full parameter definition by name.

    Args:
        name: Parameter name (case-insensitive)

    Returns:
        Parameter dict with all fields, or None if not found

    Example:
        >>> p = get_parameter_by_name('ACCESS_LEVEL')
        >>> p['idx'], p['format']
        (1, 'int')
    """
    return _PARAM_BY_NAME.get(name.upper())


def get_parameter_by_idx(idx: int) -> Optional[dict]:
    """Get full parameter definition by index.

    Args:
        idx: Parameter index

    Returns:
        Parameter dict with all fields, or None if not found

    Example:
        >>> p = get_parameter_by_idx(1)
        >>> p['text']
        'ACCESS_LEVEL'
    """
    return _PARAM_BY_IDX.get(idx)
'''


def load_module_list(path: Path, varname: str) -> list[dict]:
    spec = importlib.util.spec_from_file_location("_gen_tmp", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, varname)


def fhem_day_name(device_name: str) -> str:
    """Map a device day-program name to FHEM's numbered variant."""
    return DAY_RE.sub(lambda m: "_" + DAY_TOKENS[m.group(1)], device_name)


def parse_capture(path: Path) -> list[dict]:
    elements = []
    with open(path, errors="replace") as fh:
        for line in fh:
            m = ELEMENT_RE.search(line)
            if m:
                elements.append(
                    {
                        "idx": int(m.group(1)),
                        "extid": m.group(2).upper(),
                        "max": int(m.group(3)),
                        "min": int(m.group(4)),
                        "text": m.group(5),
                    }
                )
    return elements


def main() -> int:
    capture = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CAPTURE
    elements = parse_capture(capture)
    if not elements:
        print(f"error: no elements found in {capture}", file=sys.stderr)
        return 1

    # Validate: the element list must be collision-free.
    for key in ("idx", "extid", "text"):
        values = [e[key] for e in elements]
        if len(values) != len(set(values)):
            dupes = sorted({v for v in values if values.count(v) > 1})
            print(f"error: duplicate {key} in capture: {dupes}", file=sys.stderr)
            return 1

    defaults = load_module_list(DEFAULTS, "PARAMETER_DEFAULTS")
    meta_by_name = {e["text"]: (e["format"], e["read"]) for e in defaults}
    meta_by_extid = {e["extid"].upper(): (e["format"], e["read"]) for e in defaults}

    unmatched = []
    for elem in elements:
        meta = (
            meta_by_name.get(elem["text"])
            or meta_by_name.get(fhem_day_name(elem["text"]))
            or meta_by_extid.get(elem["extid"])
        )
        if meta is None:
            unmatched.append(elem["text"])
            meta = ("int", 0)
        elem["format"], elem["read"] = meta

    if unmatched:
        print(
            f"note: {len(unmatched)} device elements without FHEM metadata "
            f"(defaulted to format='int'): {unmatched}"
        )

    elements.sort(key=lambda e: e["idx"])

    with open(OUTPUT, "w") as fh:
        fh.write(HEADER.format(capture=capture.name, count=len(elements)))
        for e in elements:
            fh.write(
                "    {\n"
                f'        "idx": {e["idx"]},\n'
                f'        "extid": "{e["extid"]}",\n'
                f'        "max": {e["max"]},\n'
                f'        "min": {e["min"]},\n'
                f'        "format": "{e["format"]}",\n'
                f'        "read": {e["read"]},\n'
                f'        "text": "{e["text"]}",\n'
                "    },\n"
            )
        fh.write(FOOTER)

    print(f"wrote {OUTPUT} with {len(elements)} parameters from {capture.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
