#!/usr/bin/env python3
"""Probe room setpoint / room influence parameters on the heat pump.

Workflow (run on the HA host, after switching off switch.heat_pump_usb_connection):

    probe_room_params.py snap baseline          # raw-read candidate indices -> baseline.json
    # ... change one value on the heat pump menu ...
    probe_room_params.py snap after_c3_setpoint
    probe_room_params.py diff baseline after_c3_setpoint

    probe_room_params.py sniff 90               # capture bus while you change a menu value

Reads are done by raw index (CAN id 0x04003FE0 | idx << 14), so unnamed
indices (gaps in the element list) are probed too.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

LIB = os.environ.get("WPS_LIB", "/config/custom_components/buderus_wps")
# append, not insert: the integration dir holds select.py etc. that would shadow stdlib
sys.path.append(LIB)

from buderus_wps import USBtinAdapter  # noqa: E402
from buderus_wps.can_message import CANMessage  # noqa: E402
from buderus_wps.parameter import HeatPump  # noqa: E402

PORT = os.environ.get("WPS_PORT", "/dev/ttyACM0")
OUT = Path(os.environ.get("WPS_OUT", str(Path.home() / "room_probe")))

REQ = 0x04003FE0
RESP = 0x0C003FE0

RANGES = [
    (1160, 1173),  # HW_ROOM_*
    (1590, 1600),  # MV_E12_EEPROM_INCREASE_ROOM_SETPOINT area
    (1638, 1646),  # MV_E12_EEPROM_ROOMSENSOR_INFLUENCE_FACTOR area
    (1700, 1712),  # MV_E12_ROOMSENSOR_INFLUENCE / ROOM_SETPOINT_TEMP_ACTIVE
    (2060, 2160),  # ROOM_* block incl. unnamed gap indices
]


def indices() -> list[int]:
    if os.environ.get("WPS_ALL"):
        # every index 0..max known element idx (+ trailing slot)
        top = max(p.idx for p in HeatPump().parameters)
        return list(range(0, top + 2))
    out: list[int] = []
    for a, b in RANGES:
        out.extend(range(a, b + 1))
    return out


def names() -> dict[int, str]:
    hp = HeatPump()
    res = {}
    for i in indices():
        p = hp.get_parameter(i)
        if p:
            res[i] = f"{p.text} [{p.format} {p.min}..{p.max}]"
    return res


def idx_of(can_id: int) -> tuple[str, int] | None:
    for base, kind in ((REQ, "REQ/WRITE"), (RESP, "RESP")):
        if (can_id & ~(0xFFF << 14)) == base:
            return kind, (can_id >> 14) & 0xFFF
    return None


def raw_read(ad: USBtinAdapter, idx: int, timeout: float = 0.6) -> str | None:
    want = RESP | (idx << 14)
    ad.flush_input_buffer()
    msg = CANMessage(
        arbitration_id=REQ | (idx << 14),
        data=b"",
        is_extended_id=True,
        is_remote_frame=True,
    )
    t0 = time.time()
    try:
        f = ad.send_frame(msg, timeout=timeout)
    except Exception:
        return None
    while True:
        if f is not None and f.arbitration_id == want:
            return f.data.hex()
        left = timeout - (time.time() - t0)
        if left <= 0:
            return None
        try:
            f = ad.receive_frame(timeout=max(left, 0.05))
        except Exception:
            return None


def decode(hexdata: str | None) -> str:
    if not hexdata:
        return "-"
    b = bytes.fromhex(hexdata)
    v = int.from_bytes(b, "big", signed=True)
    return f"{v} ({v / 10:.1f})"


def cmd_snap(label: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    nm = names()
    ad = USBtinAdapter(PORT, timeout=1.0)
    ad.connect()
    data: dict[str, str | None] = {}
    try:
        for i in indices():
            data[str(i)] = raw_read(ad, i)
    finally:
        ad.disconnect()
    (OUT / f"{label}.json").write_text(
        json.dumps({"ts": time.time(), "data": data}, indent=1)
    )
    for i in indices():
        h = data[str(i)]
        if h is None and i not in nm:
            continue
        print(f"{i:5d} {h or '-':>10} {decode(h):>16}  {nm.get(i, '<unnamed>')}")
    n_ok = sum(1 for v in data.values() if v)
    print(f"\n{n_ok}/{len(data)} indices answered -> {OUT / (label + '.json')}")


def cmd_diff(a: str, b: str) -> None:
    da = json.loads((OUT / f"{a}.json").read_text())["data"]
    db = json.loads((OUT / f"{b}.json").read_text())["data"]
    nm = names()
    changed = [k for k in da if da.get(k) != db.get(k)]
    if not changed:
        print("no differences")
    for k in changed:
        i = int(k)
        print(
            f"{i:5d} {da[k] or '-':>10} -> {db.get(k) or '-':<10} "
            f"{decode(da[k])} -> {decode(db.get(k))}  {nm.get(i, '<unnamed>')}"
        )


def cmd_sniff(seconds: float) -> None:
    hp = HeatPump()
    ad = USBtinAdapter(PORT, timeout=1.0)
    ad.connect()
    last: dict[int, bytes] = {}
    end = time.time() + seconds
    print(f"sniffing {seconds:.0f}s — change the menu value now")
    try:
        while time.time() < end:
            try:
                f = ad.receive_frame(timeout=0.5)
            except Exception:
                continue
            if f is None:
                continue
            cid = f.arbitration_id
            hit = idx_of(cid)
            ts = time.strftime("%H:%M:%S")
            if hit and hit[0] == "REQ/WRITE" and f.data:
                p = hp.get_parameter(hit[1])
                print(
                    f"{ts} WRITE idx={hit[1]} data={f.data.hex()} "
                    f"{decode(f.data.hex())} {p.text if p else '<unnamed>'}"
                )
            elif cid in last and last[cid] != f.data:
                print(
                    f"{ts} CHANGE id=0x{cid:08X} {last[cid].hex()} -> {f.data.hex()}"
                    + (f" idx={hit[1]}" if hit else "")
                )
            last[cid] = f.data
    finally:
        ad.disconnect()
    print(f"done, {len(last)} distinct ids seen")


# idx -> (min_raw, max_raw); only these may be written by this probe tool
WRITABLE = {
    2137: (100, 350),  # ROOM_SETPOINT_BASE_TEMP (C1)
    1882: (100, 350),  # MV_T5_SETPOINT_1 (C2)
    1884: (100, 350),  # MV_T5_SETPOINT_2 (C3)
    1886: (100, 350),  # MV_T5_SETPOINT_3 (C4)
}


def cmd_write(idx: int, raw: int, verify: list[int]) -> None:
    import struct

    lo, hi = WRITABLE.get(idx, (None, None))
    if lo is None or not lo <= raw <= hi:
        sys.exit(f"refused: idx {idx} raw {raw} not in allowlist {WRITABLE}")
    ad = USBtinAdapter(PORT, timeout=1.0)
    ad.connect()
    try:
        print(f"before idx {idx}: {decode(raw_read(ad, idx))}")
        msg = CANMessage(
            arbitration_id=REQ | (idx << 14),
            data=struct.pack(">h", raw),
            is_extended_id=True,
        )
        ad.send_frame_nowait(msg)
        print(f"sent idx {idx} <- {raw} ({raw / 10:.1f})")
        for delay in (1, 5, 15):
            time.sleep(delay)
            vals = ", ".join(f"{i}={decode(raw_read(ad, i))}" for i in [idx, *verify])
            print(f"+{delay}s: {vals}")
    finally:
        ad.disconnect()


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "snap":
        cmd_snap(sys.argv[2])
    elif cmd == "diff":
        cmd_diff(sys.argv[2], sys.argv[3])
    elif cmd == "write":
        cmd_write(int(sys.argv[2]), int(sys.argv[3]), [int(x) for x in sys.argv[4:]])
    elif cmd == "sniff":
        cmd_sniff(float(sys.argv[2]) if len(sys.argv) > 2 else 60)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
