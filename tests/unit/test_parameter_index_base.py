"""All parameter lookups share one index base: parameter_data.py (#15).

parameter_defaults.py is the FHEM-derived table. Its idx values differ from the
device-derived parameter_data.py for ~1560 of ~1750 shared parameters (offset
0..+5, drifting with idx). Any registry falling back to it addresses a
neighbouring register. parameter_defaults.py is kept only as generator input
for format/read metadata; nothing at runtime may resolve an idx from it.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from buderus_wps.parameter import HeatPump
from buderus_wps.parameter_data import PARAMETER_DATA
from buderus_wps.parameter_registry import ParameterRegistry
from buderus_wps.runtime_registry import RuntimeParameterRegistry

PKG_DIR = Path(__file__).resolve().parents[2] / "custom_components" / "buderus_wps"
DATA_IDX = {p["text"].upper(): p["idx"] for p in PARAMETER_DATA}

# Known divergent examples from the issue (data idx, FHEM idx).
DIVERGENT = {
    "GT3_TEMP": 682,  # FHEM 681
    "COMPRESSOR_BLOCKED": 248,  # FHEM 247
    "XDHW_TIME": 2480,  # FHEM 2475
    "DHW_GT8_STOP_TEMP": 444,  # FHEM 443
    "MV_T5_SETPOINT_ACTUAL_3": 1900,  # FHEM 1898
}


@pytest.mark.parametrize(("name", "idx"), sorted(DIVERGENT.items()))
def test_runtime_registry_fallback_uses_device_index(name, idx):
    element = RuntimeParameterRegistry(use_static_fallback=True).get_by_name(name)
    assert element is not None
    assert element.idx == idx


@pytest.mark.parametrize(("name", "idx"), sorted(DIVERGENT.items()))
def test_parameter_registry_default_uses_device_index(name, idx):
    param = ParameterRegistry().get_by_name(name)
    assert param is not None
    assert param.idx == idx


def test_all_lookup_paths_agree_on_every_parameter():
    runtime = RuntimeParameterRegistry(use_static_fallback=True)
    registry = ParameterRegistry()
    heat_pump = HeatPump()  # no cache path -> parameter_data.py fallback

    mismatches = []
    for name, idx in DATA_IDX.items():
        got = (
            runtime.get_by_name(name).idx,
            registry.get_by_name(name).idx,
            heat_pump.get_parameter(name).idx,
        )
        if got != (idx, idx, idx):
            mismatches.append((name, idx, got))
    assert not mismatches, mismatches[:10]


def test_no_runtime_module_imports_parameter_defaults():
    offenders = []
    for path in PKG_DIR.rglob("*.py"):
        if path.name == "parameter_defaults.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [a.name for a in node.names]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            if any(n.split(".")[-1] == "parameter_defaults" for n in names):
                offenders.append(str(path.relative_to(PKG_DIR)))
    assert not offenders, offenders


def test_no_parameter_access_by_hardcoded_idx():
    """idx values are device-specific; code must look parameters up by name.

    coordinator.py read ``_get_binary(247)`` as COMPRESSOR_BLOCKED, but 247 is
    the FHEM index: on the device 247 is COMPRESSOR_ALARM_2 and
    COMPRESSOR_BLOCKED is 248 (#15).
    """
    offenders = []
    for path in PKG_DIR.rglob("*.py"):
        if path.name.startswith("parameter_d") or path.name.startswith("diagnose"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and node.args):
                continue
            first = node.args[0]
            if not (
                isinstance(first, ast.Constant)
                and type(first.value) is int  # noqa: E721 - exclude bool
            ):
                continue
            func = node.func
            name = getattr(func, "attr", getattr(func, "id", "")).lower()
            if any(k in name for k in ("read", "write", "get_binary", "get_parameter")):
                offenders.append(f"{path.relative_to(PKG_DIR)}:{node.lineno} {name}")
    assert not offenders, offenders
