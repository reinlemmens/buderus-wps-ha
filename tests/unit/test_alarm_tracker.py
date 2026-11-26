"""Unit tests for new-alarm edge detection and restart memory (issue #25)."""

from datetime import datetime, timezone

import pytest

from custom_components.buderus_wps.alarm_tracker import AlarmTracker, NewAlarm

T0 = datetime(2026, 11, 26, 8, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 11, 26, 8, 1, tzinfo=timezone.utc)


def feed(tracker, statuses):
    return [tracker.update(s, T1) for s in statuses]


def test_one_to_four_fires_once():
    t = AlarmTracker()
    assert feed(t, [1, 4, 4]) == [None, NewAlarm(4, 1, False, T1), None]
    assert t.last_alarm == T1
    assert t.pending is True


def test_confirm_sequence_clears_without_event():
    t = AlarmTracker(remembered_pending=True, last_alarm=T0)
    assert feed(t, [4, 3, 0, 1]) == [None, None, None, None]
    assert t.pending is False
    assert t.last_alarm == T0


def test_three_then_four_is_a_new_alarm():
    t = AlarmTracker()
    assert feed(t, [3, 4])[1] == NewAlarm(4, 3, False, T1)


def test_restart_remembered_not_pending_fires():
    t = AlarmTracker(remembered_pending=False)
    assert t.update(4, T1) == NewAlarm(4, None, True, T1)


def test_restart_remembered_pending_does_not_fire():
    t = AlarmTracker(remembered_pending=True, last_alarm=T0)
    assert t.update(4, T1) is None
    assert t.last_alarm == T0


def test_fresh_install_does_not_fire():
    t = AlarmTracker()
    assert t.update(4, T1) is None
    assert t.pending is True
    assert t.last_alarm is None


@pytest.mark.parametrize("gap", [None, 2, 7])
def test_missing_or_unknown_reading_changes_nothing(gap):
    t = AlarmTracker()
    assert feed(t, [1, gap, 1, gap, 4, gap, 4]) == [
        None,
        None,
        None,
        None,
        NewAlarm(4, 1, False, T1),
        None,
        None,
    ]


def test_unknown_value_does_not_end_an_alarm():
    t = AlarmTracker(remembered_pending=True)
    feed(t, [4, 2])
    assert t.pending is True


def test_unknown_value_logged_once(caplog):
    t = AlarmTracker()
    with caplog.at_level("WARNING"):
        feed(t, [2, 2, 2, 7])
    assert sum("system status" in r.message.lower() for r in caplog.records) == 2


def test_round_trip_survives_restart():
    t = AlarmTracker()
    feed(t, [1, 4])
    restored = AlarmTracker.from_dict(t.as_dict())
    assert restored.pending is True
    assert restored.last_alarm == T1
    assert restored.update(4, T1) is None


def test_as_dict_is_json_plain():
    t = AlarmTracker()
    feed(t, [1, 4])
    assert t.as_dict() == {"pending": True, "last_alarm": T1.isoformat()}


@pytest.mark.parametrize(
    "data,pending,has_last",
    [
        (None, None, False),
        ("junk", None, False),
        ([], None, False),
        ({}, None, False),
        ({"pending": "yes", "last_alarm": "garbage"}, None, False),
        ({"pending": False, "last_alarm": 12345}, False, False),
        ({"pending": 1, "last_alarm": T0.isoformat()}, None, True),
    ],
)
def test_from_dict_tolerates_bad_data(data, pending, has_last):
    t = AlarmTracker.from_dict(data)
    assert t.pending is pending
    assert (t.last_alarm is not None) is has_last
