"""Camera-control input scripts for the netplay M5c lane A lead camera (#887).

Writes PKNI v2 files (the gen_inputs.py format: 10-byte header, 56-byte
records, 4 pads of 14 bytes; the lockstep session reads pad 0 of each record
as the peer's local input, including its control yaw).

Two modes:

  heavy   A plausible field session (the gen_inputs.py pad-0 walk, A taps, B
          whistles, C-stick nudges) with dense camera controls on top: L-hold
          rotations with the main stick (analog L below the digital click),
          L clicks (attention), R clicks (zoom, sometimes with X held so they
          must not zoom), Z clicks (angle), and a fast-moving control yaw
          (drift, wobble and jumps). Start and Y are never pressed. This is
          the sim-neutrality workload: the lead camera replays these on every
          presented frame, so the hash logs must still equal the
          integration exe's on the same files.

  probe   Hands-off pad 0 except for camera events at known frames, for the
          responsiveness measurement: --turn-at F (L-hold rotation for
          --turn-len frames), --zoom-at F (R click), --angle-at F (Z click),
          --attention-at F (L click). Each option may repeat. The control yaw
          stays 0. Record i is the peer's i-th submitted input: it lands on
          GekkoNet frame i + delay, and the lead camera shows it on the
          frame it is submitted. Fix round 1: --start-at F (Start click; on
          the host it opens the pause menu) and --a-at F (A click; "Continue"
          in the pause menu) for the pause-cut evidence.
"""

import argparse
import math
import random
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_inputs  # noqa: E402  (same directory)

MAGIC = b"PKNI"
VERSION_V2 = 2
PAD_COUNT = 4
RECORD_SIZE_V2 = 56

TRIG_Z = gen_inputs.TRIG_Z
TRIG_R = gen_inputs.TRIG_R
TRIG_L = gen_inputs.TRIG_L
BTN_X = gen_inputs.BTN_X
BTN_A = gen_inputs.BTN_A
BTN_START = 0x1000  # PAD_BUTTON_START (Dolphin/pad.h)


def _pack(buttons, sx, sy, cx, cy, tl, tr, connected, yaw):
    return struct.pack("<HbbbbBBBBbHb", buttons, sx, sy, cx, cy, tl, tr, 0, 0, connected, yaw & 0xFFFF, 0)


def _write(path: Path, records):
    with open(path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<HHH", VERSION_V2, PAD_COUNT, RECORD_SIZE_V2))
        n = 0
        for (buttons, sx, sy, cx, cy, tl, tr, yaw) in records:
            f.write(_pack(buttons, sx, sy, cx, cy, tl, tr, 0, yaw))
            for _p in range(1, 4):
                f.write(_pack(0, 0, 0, 0, 0, 0, 0, -1, 0))
            n += 1
    return n


def _clamp8(v):
    return max(-127, min(127, int(v)))


def heavy(ticks: int, seed: int):
    rng = random.Random(seed)
    cam = random.Random(seed * 7919 + 0x43414D)
    walk = gen_inputs._PadScript(rng)
    yaw = cam.uniform(0.0, 1.0)
    yaw_rate = 0.0
    rot_left = 0
    rot_stick = 0
    rot_trig = 0
    clicks = {}  # bit -> ticks left held
    x_hold = 0
    next_cam = cam.randint(15, 60)
    for _t in range(ticks):
        buttons, sx, sy, cx, cy, tl, tr = walk.tick()
        # The walk script's own trigger squeezes are dropped: camera use is
        # scheduled here so the density is known.
        buttons &= ~(TRIG_L | TRIG_R | TRIG_Z)
        tl, tr = 0, 0
        next_cam -= 1
        if next_cam <= 0 and rot_left <= 0:
            r = cam.random()
            if r < 0.40:
                # L-hold rotation: analog L between the 17 rotate threshold
                # and the digital click, the main stick X steering it.
                rot_left = cam.randint(8, 45)
                rot_stick = cam.choice((-1, 1)) * cam.randint(30, 110)
                rot_trig = cam.randint(25, 115)
            elif r < 0.60:
                clicks[TRIG_R] = cam.randint(1, 3)          # zoom
                if cam.random() < 0.25:
                    x_hold = clicks[TRIG_R] + 2             # X held: no zoom
            elif r < 0.78:
                clicks[TRIG_Z] = cam.randint(1, 3)          # angle
            else:
                clicks[TRIG_L] = cam.randint(1, 3)          # attention
            next_cam = cam.randint(10, 70)
        if rot_left > 0:
            rot_left -= 1
            tl = rot_trig
            sx = _clamp8(rot_stick + cam.randint(-8, 8))
        for bit, left in list(clicks.items()):
            if left > 0:
                buttons |= bit
                if bit == TRIG_L:
                    tl = max(tl, 200)
                if bit == TRIG_R:
                    tr = max(tr, 200)
                clicks[bit] = left - 1
        if x_hold > 0:
            buttons |= BTN_X
            x_hold -= 1
        # Control yaw: drift with wobble, plus a jump now and then.
        yaw_rate += cam.uniform(-0.0008, 0.0008)
        yaw_rate = max(-0.01, min(0.01, yaw_rate))
        yaw += yaw_rate + 0.003 * math.sin(_t / 17.0)
        if cam.random() < 0.004:
            yaw += cam.uniform(-0.5, 0.5)
        yaw %= 1.0
        assert not buttons & 0x1800, "Start/Y must never be pressed"
        yield (buttons, sx, sy, cx, cy, tl, tr, int(yaw * 65536.0 + 0.5))


def probe(ticks: int, turns, turn_len: int, turn_stick: int, turn_trigger: int, zooms, angles, attentions,
          starts=(), a_presses=()):
    events = {}
    for f in turns:
        for i in range(turn_len):
            events.setdefault(f + i, []).append("turn")
    for f in zooms:
        events.setdefault(f, []).append("zoom")
        events.setdefault(f + 1, []).append("zoom")
    for f in angles:
        events.setdefault(f, []).append("angle")
        events.setdefault(f + 1, []).append("angle")
    for f in attentions:
        events.setdefault(f, []).append("attention")
        events.setdefault(f + 1, []).append("attention")
    # Fix round 1 (evidence review E1): Start opens the pause menu (host
    # pad only: newPikiGame reads P1's Kontroller), A on its first item,
    # "Continue", closes it.
    for f in starts:
        events.setdefault(f, []).append("start")
        events.setdefault(f + 1, []).append("start")
    for f in a_presses:
        events.setdefault(f, []).append("a")
        events.setdefault(f + 1, []).append("a")
    for t in range(ticks):
        buttons, sx, tl, tr = 0, 0, 0, 0
        for ev in events.get(t, ()):
            if ev == "turn":
                tl = max(tl, turn_trigger)
                sx = turn_stick
            elif ev == "zoom":
                buttons |= TRIG_R
                tr = 200
            elif ev == "angle":
                buttons |= TRIG_Z
            elif ev == "attention":
                buttons |= TRIG_L
                tl = 200
            elif ev == "start":
                buttons |= BTN_START
            elif ev == "a":
                buttons |= BTN_A
        yield (buttons, sx, 0, 0, 0, tl, tr, 0)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=("heavy", "probe"))
    p.add_argument("--ticks", type=int, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seed", type=int, default=1, help="heavy: script seed")
    p.add_argument("--turn-at", type=int, action="append", default=[])
    p.add_argument("--turn-len", type=int, default=20)
    p.add_argument("--turn-stick", type=int, default=100)
    p.add_argument("--turn-trigger", type=int, default=90,
                   help="analog L during a turn (rotation needs >= 17; the digital click is not pressed)")
    p.add_argument("--zoom-at", type=int, action="append", default=[])
    p.add_argument("--angle-at", type=int, action="append", default=[])
    p.add_argument("--attention-at", type=int, action="append", default=[])
    p.add_argument("--start-at", type=int, action="append", default=[],
                   help="probe: Start click (2 records) at this record; opens the pause menu on the host")
    p.add_argument("--a-at", type=int, action="append", default=[],
                   help="probe: A click (2 records) at this record; picks 'Continue' in the pause menu")
    a = p.parse_args(argv)
    if a.ticks <= 0:
        print("gen_camera_inputs: --ticks must be positive", file=sys.stderr)
        return 2
    if a.mode == "heavy":
        n = _write(a.out, heavy(a.ticks, a.seed))
    else:
        n = _write(a.out, probe(a.ticks, a.turn_at, a.turn_len, _clamp8(a.turn_stick), max(0, min(255, a.turn_trigger)),
                                a.zoom_at, a.angle_at, a.attention_at, a.start_at, a.a_at))
    print(f"gen_camera_inputs: wrote {n} {a.mode} records to {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
