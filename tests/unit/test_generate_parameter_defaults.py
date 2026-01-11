import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import generate_parameter_defaults as gen


def test_diff_entries_detects_added_removed_modified(tmp_path):
    old = [
        {
            "idx": 1,
            "extid": "AA",
            "min": 0,
            "max": 1,
            "format": "int",
            "read": 0,
            "text": "FOO",
        },
        {
            "idx": 2,
            "extid": "BB",
            "min": 0,
            "max": 1,
            "format": "int",
            "read": 0,
            "text": "BAR",
        },
    ]
    new = [
        {
            "idx": 1,
            "extid": "AA",
            "min": 0,
            "max": 2,
            "format": "int",
            "read": 0,
            "text": "FOO",
        },  # modified max
        {
            "idx": 3,
            "extid": "CC",
            "min": 0,
            "max": 1,
            "format": "int",
            "read": 0,
            "text": "BAZ",
        },  # added
    ]
    added, removed, modified = gen.diff_entries(old, new)
    assert len(added) == 1 and added[0]["text"] == "BAZ"
    assert len(removed) == 1 and removed[0]["text"] == "BAR"
    assert len(modified) == 1 and modified[0][1]["max"] == 2


def test_validate_entries_rejects_duplicates():
    text = ""
    dup_entries = [
        {
            "idx": 1,
            "extid": "AA",
            "min": 0,
            "max": 1,
            "format": "int",
            "read": 0,
            "text": "FOO",
        },
        {
            "idx": 1,
            "extid": "BB",
            "min": 0,
            "max": 1,
            "format": "int",
            "read": 0,
            "text": "BAR",
        },
    ]
    try:
        gen.validate_entries(dup_entries, text)
        raise AssertionError("Expected validation to fail on duplicate idx")
    except SystemExit:
        pass


def test_metadata_written(tmp_path, monkeypatch):
    # Use a tiny custom target for isolation
    source = tmp_path / "dummy.pm"
    source.write_text(
        "{ 'idx' => 1 , 'extid' => 'AA' , 'max' => 1 , 'min' => 0 , 'format' => 'int' , 'read' => 0 , 'text' => 'FOO' },",
        encoding="utf-8",
    )
    target = tmp_path / "out.py"
    meta = tmp_path / "out.meta.json"

    monkeypatch.setattr(gen, "SOURCE", source)
    monkeypatch.setattr(gen, "TARGET", target)
    monkeypatch.setattr(gen, "META", meta)

    text = source.read_text(encoding="utf-8")
    entries = gen.extract_entries(text)
    gen.validate_entries(entries, text)
    gen.write_module(entries)

    assert target.exists()
    assert meta.exists()
    meta_data = json.loads(meta.read_text(encoding="utf-8"))
    assert meta_data["count"] == 1
