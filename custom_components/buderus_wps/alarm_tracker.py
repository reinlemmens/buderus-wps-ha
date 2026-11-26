"""New-alarm detection for the heat pump's alarm-pending status (issue #25).

The pump only tells whether unconfirmed alarms exist (see
buderus_wps/alarm_status.py). A new alarm is therefore the step from
"not pending" to "pending". This module turns a sequence of status readings
into those steps and keeps the little state that has to survive a restart of
Home Assistant, so an alarm raised while HA was down is still reported once
and an alarm that was already pending is not reported again.

No Home Assistant imports: the coordinator owns an AlarmTracker, persists
as_dict() and fires the event.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .buderus_wps.alarm_status import alarm_pending

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class NewAlarm:
    """A detected step from "not pending" to "pending"."""

    status: int
    # Last status read before the step. None when the "not pending" state is
    # only remembered from before a restart.
    previous_status: int | None
    after_restart: bool
    detected_at: datetime


class AlarmTracker:
    """Track the alarm-pending state across readings and restarts."""

    def __init__(
        self,
        remembered_pending: bool | None = None,
        last_alarm: datetime | None = None,
    ) -> None:
        self._pending = remembered_pending
        self._last_alarm = last_alarm
        # Last status with a known meaning read by this instance.
        self._last_status: int | None = None
        self._warned_values: set[int] = set()

    @property
    def pending(self) -> bool | None:
        """Last known pending state, from a reading or remembered."""
        return self._pending

    @property
    def last_alarm(self) -> datetime | None:
        """When the last new alarm was detected."""
        return self._last_alarm

    def update(self, status: int | None, now: datetime) -> NewAlarm | None:
        """Process one status reading; return a NewAlarm on a rising edge.

        A missing reading or a value of unknown meaning changes nothing: it
        neither starts nor ends an alarm.
        """
        if status is None:
            return None

        pending = alarm_pending(status)
        if pending is None:
            if status not in self._warned_values:
                self._warned_values.add(status)
                _LOGGER.warning(
                    "Unknown heat pump system status %s (known: 0, 1, 3, 4); "
                    "alarm state left unchanged",
                    status,
                )
            return None

        new_alarm: NewAlarm | None = None
        if pending and self._pending is False:
            new_alarm = NewAlarm(
                status=status,
                previous_status=self._last_status,
                after_restart=self._last_status is None,
                detected_at=now,
            )
            self._last_alarm = now

        self._pending = pending
        self._last_status = status
        return new_alarm

    def as_dict(self) -> dict[str, Any]:
        """State to persist, JSON-serialisable."""
        return {
            "pending": self._pending,
            "last_alarm": (
                self._last_alarm.isoformat() if self._last_alarm is not None else None
            ),
        }

    @classmethod
    def from_dict(cls, data: Any) -> AlarmTracker:
        """Rebuild from persisted state; bad or missing fields are dropped."""
        if not isinstance(data, dict):
            return cls()

        pending = data.get("pending")
        if not isinstance(pending, bool):
            pending = None

        last_alarm: datetime | None = None
        raw = data.get("last_alarm")
        if isinstance(raw, str):
            try:
                last_alarm = datetime.fromisoformat(raw)
            except ValueError:
                last_alarm = None
            else:
                if last_alarm.tzinfo is None:
                    last_alarm = last_alarm.replace(tzinfo=timezone.utc)

        return cls(remembered_pending=pending, last_alarm=last_alarm)
