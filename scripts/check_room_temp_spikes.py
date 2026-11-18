#!/usr/bin/env python3
"""Count room-temperature spikes (issue #17) in Home Assistant history.

Reads HASS_SERVER / HASS_TOKEN from the environment (source hass-env.sh).

    python3 scripts/check_room_temp_spikes.py --start 2026-11-18T06:55:00Z \
        [--end 2026-11-19T07:00:00Z] [--verbose]

A sample counts as a spike when it is
  * outside 10-35 degC (sentinels such as 0.0, 98.0, 998.5), or
  * part of a jump-and-return: a run of up to 5 samples >= 0.8 K away from
    the samples before and after it, which agree within 0.3 K.
Exit code 0 = no spikes, 1 = spikes found, 2 = not enough data.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

CIRCUITS = (1, 2, 3, 4)
ROOM = "sensor.heat_pump_room_temperature_c{}"
SETPOINT = "sensor.heat_pump_room_setpoint_c{}"


def fetch(start: str, end: str) -> dict[str, list[tuple[str, float | None]]]:
    server = os.environ["HASS_SERVER"].rstrip("/")
    token = os.environ["HASS_TOKEN"]
    ids = [ROOM.format(c) for c in CIRCUITS] + [SETPOINT.format(c) for c in CIRCUITS]
    query = urllib.parse.urlencode(
        {
            "filter_entity_id": ",".join(ids),
            "end_time": end,
            "minimal_response": "",
            "no_attributes": "",
        }
    )
    url = f"{server}/api/history/period/{urllib.parse.quote(start)}?{query}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)

    series: dict[str, list[tuple[str, float | None]]] = {}
    for entity_states in data:
        if not entity_states:
            continue
        entity_id = entity_states[0]["entity_id"]
        points = []
        for s in entity_states:
            try:
                value: float | None = float(s["state"])
            except (TypeError, ValueError):
                value = None
            points.append((s.get("last_changed", ""), value))
        series[entity_id] = points
    return series


def setpoint_at(setpoints: list[tuple[str, float | None]], ts: str) -> float | None:
    value = None
    for t, v in setpoints:
        if t > ts:
            break
        value = v
    return value


def _excursion_length(room: list[tuple[str, float]], i: int, max_run: int = 5) -> int:
    """Length of a run starting at i that jumps away and comes back, else 0.

    The samples before and after the run agree within 0.3 K, and every sample
    in the run is >= 0.8 K away from both.
    """
    if i == 0:
        return 0
    before = room[i - 1][1]
    for length in range(1, max_run + 1):
        if i + length >= len(room):
            return 0
        run = [v for _, v in room[i : i + length]]
        if any(abs(v - before) < 0.8 for v in run):
            return 0
        after = room[i + length][1]
        if abs(after - before) <= 0.3 and all(abs(v - after) >= 0.8 for v in run):
            return length
    return 0


def find_spikes(series, verbose: bool) -> tuple[int, int]:
    total = 0
    samples = 0
    for c in CIRCUITS:
        room = [(t, v) for t, v in series.get(ROOM.format(c), []) if v is not None]
        setpoints = series.get(SETPOINT.format(c), [])
        samples += len(room)
        spikes = []
        i = 0
        while i < len(room):
            t, v = room[i]
            if not 10.0 <= v <= 35.0:
                spikes.append((t, v, "out of range"))
                i += 1
                continue
            run = _excursion_length(room, i)
            if run:
                sp = setpoint_at(setpoints, t)
                kind = (
                    "equals setpoint"
                    if sp is not None and abs(sp - v) < 0.05
                    else "jump-and-return"
                )
                spikes.append((t, v, f"{kind} ({run} sample(s))"))
                i += run
                continue
            i += 1
        total += len(spikes)
        print(f"C{c}: {len(room)} changes, {len(spikes)} spikes")
        if verbose:
            for t, v, kind in spikes:
                print(f"    {t}  {v:7.1f}  {kind}")
    return total, samples


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--start", required=True, help="ISO time, e.g. 2026-11-18T06:55:00Z"
    )
    parser.add_argument("--end", default=None, help="ISO time (default: now)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    end = args.end or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    series = fetch(args.start, end)
    print(f"Window {args.start} -> {end}")
    total, samples = find_spikes(series, args.verbose)
    print(f"TOTAL spikes: {total}")
    if samples < 8:
        print("Not enough room-temperature data to judge.")
        return 2
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
