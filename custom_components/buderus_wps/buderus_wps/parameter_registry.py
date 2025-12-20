"""
Parameter registry backed by static defaults with optional device overrides.

Defaults are generated from fhem/26_KM273v018.pm via tools/generate_parameter_defaults.py
and stored in buderus_wps/parameter_defaults.py. When a live heat pump provides
an updated element list, the registry can be rebuilt with those entries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .parameter_defaults import PARAMETER_DEFAULTS


@dataclass(frozen=True)
class Parameter:
    idx: int
    extid: str
    min: int
    max: int
    format: str
    read: int
    text: str


class ParameterRegistry:
    """Manage parameter metadata with name/index lookup and overrides."""

    def __init__(self, parameters: Optional[List[dict]] = None) -> None:
        source = parameters if parameters is not None else PARAMETER_DEFAULTS
        self._parameters: List[Parameter] = [self._to_parameter(p) for p in source]
        self._by_name: Dict[str, Parameter] = {
            p.text.upper(): p for p in self._parameters
        }
        self._by_idx: Dict[int, Parameter] = {p.idx: p for p in self._parameters}

    @staticmethod
    def _to_parameter(entry: dict) -> Parameter:
        return Parameter(
            idx=int(entry["idx"]),
            extid=str(entry["extid"]),
            min=int(entry["min"]),
            max=int(entry["max"]),
            format=str(entry["format"]),
            read=int(entry["read"]),
            text=str(entry["text"]),
        )

    def get_by_name(self, name: str) -> Optional[Parameter]:
        if not name:
            return None
        return self._by_name.get(name.upper())

    def get_by_index(self, idx: int) -> Optional[Parameter]:
        return self._by_idx.get(idx)

    def override_with_device(self, entries: List[dict]) -> None:
        """Replace registry contents with device-provided entries."""
        self._parameters = [self._to_parameter(p) for p in entries]
        self._by_name = {p.text.upper(): p for p in self._parameters}
        self._by_idx = {p.idx: p for p in self._parameters}

    @property
    def parameters(self) -> List[Parameter]:
        return list(self._parameters)
