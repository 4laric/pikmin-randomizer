"""Reader for the netplay session input log (PKNL v1, issue #1037).

Format: pc_port/netplay/pc_netplay_inlog.h. A header (magic, version, meta
text), then FRAME records (frame number, the two 16-byte inputs as deltas, this
peer's state-hash total, now and then the seven sub-hashes) and EVENT records
(the host's RESUME snapshot, notes, the end reason). A log cut anywhere (kill,
power loss) reads up to its last whole record.
"""

import struct
import sys
from pathlib import Path

MAGIC = b"PKNL"
INPUT_BYTES = 16
TAG_FRAME_MASK = 0x0F
TAG_EVENT = 0x40
EV_RESUME, EV_NOTE, EV_END = 1, 2, 3
SUB_NAMES = ("navi", "piki", "teki", "item", "world", "rng", "rand")


class Log:
    def __init__(self):
        self.meta = []        # [(key, value)]
        self.frames = []      # [{"frame", "in0", "in1", "total", "subs"}]
        self.events = []      # [{"frame", "kind", "data"}]
        self.truncated = 0    # bytes after the last whole record

    def get(self, key, default=""):
        for k, v in self.meta:
            if k == key:
                return v
        return default


def parse(data):
    if len(data) < 12 or data[:4] != MAGIC:
        raise ValueError("not a PKNL input log")
    version, _reserved, meta_len = struct.unpack_from("<HHI", data, 4)
    if version != 1:
        raise ValueError(f"unsupported PKNL version {version}")
    if 12 + meta_len > len(data):
        raise ValueError("bad meta length")
    log = Log()
    for line in data[12:12 + meta_len].decode("utf-8", errors="replace").splitlines():
        if not line:
            continue
        k, _, v = line.partition(" ")
        log.meta.append((k, v))
    prev = [bytes(INPUT_BYTES), bytes(INPUT_BYTES)]
    at = 12 + meta_len
    n = len(data)
    while at < n:
        start = at
        tag = data[at]
        at += 1
        if tag & ~TAG_FRAME_MASK == 0:
            need = 4 + (INPUT_BYTES if tag & 1 else 0) + (INPUT_BYTES if tag & 2 else 0) \
                + (8 if tag & 8 else 0) + (56 if tag & 4 else 0)
            if n - at < need:
                at = start
                break
            (frame,) = struct.unpack_from("<I", data, at)
            at += 4
            if tag & 1:
                prev[0] = data[at:at + INPUT_BYTES]
                at += INPUT_BYTES
            if tag & 2:
                prev[1] = data[at:at + INPUT_BYTES]
                at += INPUT_BYTES
            total = None
            subs = None
            if tag & 8:
                (total,) = struct.unpack_from("<Q", data, at)
                at += 8
            if tag & 4:
                subs = struct.unpack_from("<7Q", data, at)
                at += 56
            log.frames.append({"frame": frame, "in0": prev[0], "in1": prev[1], "total": total, "subs": subs})
        elif tag == TAG_EVENT:
            if n - at < 7:
                at = start
                break
            frame, kind, ln = struct.unpack_from("<IBH", data, at)
            at += 7
            if n - at < ln:
                at = start
                break
            log.events.append({"frame": frame, "kind": kind, "data": data[at:at + ln]})
            at += ln
        else:
            at = start
            break
    log.truncated = n - at
    return log


def load(path):
    return parse(Path(path).read_bytes())


def decode_input(raw):
    """The 16-byte netplay input (pc_netplay_gekko_input.h) as a dict."""
    buttons, sx, sy, cx, cy, tl, tr, yaw, flags, seq = struct.unpack_from("<HbbbbBBHBB", raw, 0)
    return {"buttons": buttons, "stickX": sx, "stickY": sy, "substickX": cx, "substickY": cy,
            "triggerL": tl, "triggerR": tr, "yaw": yaw, "flags": flags, "fragSeq": seq}


if __name__ == "__main__":
    lg = load(sys.argv[1])
    print(f"meta: {len(lg.meta)} keys; frames: {len(lg.frames)}; events: {len(lg.events)}; truncated bytes: {lg.truncated}")
    for k, v in lg.meta:
        print(f"  {k} {v[:100]}")
    if lg.frames:
        print(f"frames {lg.frames[0]['frame']}..{lg.frames[-1]['frame']}")
