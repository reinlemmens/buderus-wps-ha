"""
Parameter registry backed by static data with optional device overrides.

Defaults come from buderus_wps/parameter_data.py, the device-derived table that
HeatPump also falls back to. Do NOT use parameter_defaults.py (FHEM numbering):
its idx values are offset by up to 5 for most parameters (#15). When a live
heat pump provides an updated element list, the registry can be rebuilt with
those entries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .parameter_data import PARAMETER_DATA


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

    def __init__(self, parameters: Optional[list[dict]] = None) -> None:
        source = parameters if parameters is not None else PARAMETER_DATA
        self._parameters: list[Parameter] = [self._to_parameter(p) for p in source]
        self._by_name: dict[str, Parameter] = {
            p.text.upper(): p for p in self._parameters
        }
        self._by_idx: dict[int, Parameter] = {p.idx: p for p in self._parameters}

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

    def get_parameter(self, name_or_idx: str | int) -> Optional[Parameter]:
        """Look up parameter by name or index.

        Args:
            name_or_idx: Parameter name (str) or index (int)

        Returns:
            Parameter if found, None otherwise
        """
        if isinstance(name_or_idx, int):
            return self.get_by_index(name_or_idx)
        return self.get_by_name(str(name_or_idx))

    def override_with_device(self, entries: list[dict]) -> None:
        """Replace registry contents with device-provided entries."""
        self._parameters = [self._to_parameter(p) for p in entries]
        self._by_name = {p.text.upper(): p for p in self._parameters}
        self._by_idx = {p.idx: p for p in self._parameters}

    @property
    def parameters(self) -> list[Parameter]:
        return list(self._parameters)
