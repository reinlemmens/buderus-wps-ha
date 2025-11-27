import pytest
from unittest.mock import Mock

from buderus_wps.heat_pump import HeatPumpClient
from buderus_wps.parameter_registry import ParameterRegistry
from buderus_wps.can_message import CANMessage


class FakeAdapter:
    def __init__(self):
        self.is_open = True
        self.sent = []
        self.recv_queue = []
        self.last_timeout = None

    def connect(self):
        self.is_open = True

    def flush_input_buffer(self):
        pass

    def send_frame(self, message: CANMessage, timeout: float = 1.0):
        self.sent.append(message)
        if self.recv_queue:
            return self.recv_queue.pop(0)
        return None

    def receive_frame(self, timeout: float = 1.0):
        if self.recv_queue:
            return self.recv_queue.pop(0)
        raise TimeoutError("no frame")


def test_read_value_builds_ids_and_validates_response_id():
    reg = ParameterRegistry([{"idx": 1, "extid": "ABCD", "min": 0, "max": 10, "format": "int", "read": 0, "text": "FOO"}])
    adapter = FakeAdapter()
    client = HeatPumpClient(adapter, reg)

    response_id = 0x0C003FE0 | (1 << 14)
    adapter.recv_queue.append(CANMessage(arbitration_id=response_id, data=b"\x01", is_extended_id=True))

    data = client.read_value("foo", timeout=0.1)
    assert data == b"\x01"

    req = adapter.sent[0]
    assert req.is_remote_frame is True


def test_read_value_ignores_unrelated_frames():
    reg = ParameterRegistry([{"idx": 1, "extid": "ABCD", "min": 0, "max": 10, "format": "int", "read": 1, "text": "FOO"}])

    class Adapter(FakeAdapter):
        def __init__(self):
            super().__init__()
            self.timeout = 1.0
            self.receive_calls = 0

        def send_frame(self, message: CANMessage, timeout: float = 1.0):
            # First response is unrelated
            return CANMessage(arbitration_id=0x123, data=b"\x00", is_extended_id=True)

        def receive_frame(self, timeout: float = 1.0):
            self.receive_calls += 1
            if self.receive_calls == 1:
                return CANMessage(arbitration_id=0x0C003FE0 | (1 << 14), data=b"\x02", is_extended_id=True)
            raise TimeoutError("no frame")

    adapter = Adapter()
    client = HeatPumpClient(adapter, reg)
    data = client.read_value("foo", timeout=0.5)
    assert data == b"\x02"
    assert adapter.receive_calls == 1


def test_write_value_encodes_and_sends():
    reg = ParameterRegistry([{"idx": 1, "extid": "00000001", "min": 0, "max": 100, "format": "int", "read": 0, "text": "BAR"}])
    adapter = FakeAdapter()
    client = HeatPumpClient(adapter, reg)

    client.write_value("bar", 5)
    sent = adapter.sent[-1]
    assert sent.arbitration_id == 1
    assert sent.data == b"\x05"


def test_write_value_out_of_range_raises():
    reg = ParameterRegistry([{"idx": 1, "extid": "00000001", "min": 0, "max": 10, "format": "int", "read": 0, "text": "BAR"}])
    adapter = FakeAdapter()
    client = HeatPumpClient(adapter, reg)

    with pytest.raises(ValueError):
        client.write_value("bar", 1000)
