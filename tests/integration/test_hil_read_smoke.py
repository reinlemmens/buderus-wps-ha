"""
Optional hardware-in-loop smoke test for USBtin/heat pump read path.

Run with HIL=1 to execute against actual hardware on /dev/ttyACM0.
Skipped by default.
"""

import os
import pytest

from buderus_wps import USBtinAdapter, HeatPumpClient
from buderus_wps.parameter_registry import ParameterRegistry


pytestmark = pytest.mark.skipif(os.getenv("HIL") != "1", reason="HIL not enabled")


def test_hil_read_access_level():
    adapter = USBtinAdapter("/dev/ttyACM0")
    registry = ParameterRegistry()
    client = HeatPumpClient(adapter, registry)
    with adapter:
        result = client.read_parameter("ACCESS_LEVEL", timeout=5.0)
        assert result["decoded"] is not None
