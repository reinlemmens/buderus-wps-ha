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


class DummyClient:
    def __init__(self):
        self.registry = type("R", (), {"parameters": []})
        self._adapter = type("A", (), {"read_only": False})()
        self.read_value_arg = None
        self.write_value_args = None

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


def test_cmd_read_success(monkeypatch, capsys):
    client = DummyClient()
    args = argparse.Namespace(param="X", json=False)
    rc = cli.cmd_read(client, args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "X:" in out


def test_cmd_write_blocks_read_only(monkeypatch):
    client = DummyClient()
    client._adapter.read_only = True
    args = argparse.Namespace(param="X", value="1")
    rc = cli.cmd_write(client, args)
    assert rc == 1


def test_cmd_write_blocks_dry_run(monkeypatch):
    client = DummyClient()
    args = argparse.Namespace(param="X", value="1", dry_run=True)
    rc = cli.cmd_write(client, args)
    assert rc == 1
