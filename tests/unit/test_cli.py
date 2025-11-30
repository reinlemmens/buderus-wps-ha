import argparse
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from buderus_wps_cli import main as cli


def test_build_parser_has_commands():
    parser = cli.build_parser()
    args = parser.parse_args(["read", "ACCESS_LEVEL"])
    assert args.command == "read"
    args = parser.parse_args(["list"])
    assert args.command == "list"
    args = parser.parse_args(["write", "ACCESS_LEVEL", "2"])
    assert args.command == "write"
    args = parser.parse_args(["dump"])
    assert args.command == "dump"


class DummyClient:
    def __init__(self, parameters=None, fail_on=None):
        params = parameters if parameters is not None else [
            type("P", (), {"text": "X", "idx": 1, "extid": "AA", "min": 0, "max": 1, "format": "int", "read": 0})
        ]
        self.registry = type("R", (), {"parameters": params})
        self._adapter = type("A", (), {"read_only": False})()
        self.read_value_arg = None
        self.write_value_args = None
        self.fail_on = set(fail_on or [])

    def get(self, x):
        # Return a dummy param
        return type("P", (), {"text": "X", "idx": 1, "extid": "AA", "min": 0, "max": 1, "format": "int", "read": 0})

    def read_value(self, name, timeout=5.0):
        self.read_value_arg = name
        return b"\x00"

    def write_value(self, name, value, timeout=5.0):
        self.write_value_args = (name, value)

    def _decode_value(self, param, raw):
        return 0

    def read_parameter(self, name, timeout=5.0):
        if name in self.fail_on:
            raise RuntimeError("boom")
        return {
            "name": name,
            "idx": 1,
            "extid": "AA",
            "format": "int",
            "min": 0,
            "max": 1,
            "read": 0,
            "raw": b"\x00",
            "decoded": 0,
        }


def test_cmd_read_success(monkeypatch, capsys):
    client = DummyClient()
    args = argparse.Namespace(param="X", json=False, timeout=5.0)
    rc = cli.cmd_read(client, args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "X =" in out  # Format: "X = <value>  (raw=0x<hex>, idx=<n>)"


def test_cmd_write_blocks_read_only(monkeypatch):
    client = DummyClient()
    client._adapter.read_only = True
    args = argparse.Namespace(param="X", value="1", timeout=5.0)
    rc = cli.cmd_write(client, args)
    assert rc == 1


def test_cmd_write_blocks_dry_run(monkeypatch):
    client = DummyClient()
    args = argparse.Namespace(param="X", value="1", dry_run=True, timeout=5.0)
    rc = cli.cmd_write(client, args)
    assert rc == 1


def test_cmd_dump_success_human(capsys):
    params = [
        type("P", (), {"text": "FOO", "idx": 1, "extid": "01", "min": 0, "max": 10, "format": "int", "read": 0}),
        type("P", (), {"text": "BAR", "idx": 2, "extid": "02", "min": 0, "max": 10, "format": "int", "read": 0}),
    ]
    client = DummyClient(parameters=params)
    args = argparse.Namespace(json=False, timeout=5.0)
    rc = cli.cmd_dump(client, args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "FOO" in out and "BAR" in out


def test_cmd_dump_json_with_error(capsys):
    params = [
        type("P", (), {"text": "GOOD", "idx": 1, "extid": "01", "min": 0, "max": 10, "format": "int", "read": 0}),
        type("P", (), {"text": "BAD", "idx": 2, "extid": "02", "min": 0, "max": 10, "format": "int", "read": 0}),
    ]
    client = DummyClient(parameters=params, fail_on={"BAD"})
    args = argparse.Namespace(json=True, timeout=5.0)
    rc = cli.cmd_dump(client, args)
    assert rc == 1
    out = capsys.readouterr().out
    assert '"GOOD"' in out
    assert '"errors"' in out


def test_main_list_connects(monkeypatch):
    connect_called = {"value": False}
    disconnect_called = {"value": False}

    class DummyAdapter:
        def __init__(self, port, baudrate=0, timeout=0, read_only=False):
            self.port = port
            self.timeout = timeout
            self.read_only = read_only

        def connect(self):
            connect_called["value"] = True

        def disconnect(self):
            disconnect_called["value"] = True

        @property
        def is_open(self):
            return connect_called["value"]

    monkeypatch.setattr(cli, "USBtinAdapter", DummyAdapter)

    rc = cli.main(["list"])
    assert rc == 0
    assert connect_called["value"] is True
    assert disconnect_called["value"] is True
