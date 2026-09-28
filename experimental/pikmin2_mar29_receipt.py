"""Mar29 corpse receipt provider (#650, downstream #375).

Bounded runtime provider: the missing TEKI_Mar corpse receipt path. The native
adapter (native/pc_port/pc_p2_mar_receipt.{h,cpp}) binds the Mar actor and
resolves a delivered corpse view to its generator; the fixture
(native/tools/p2_muse_mar_receipt_fixture.cpp) observes NATURAL death/corpse,
credits exactly-once through the lane-06 receipt host (ordinary ledger identity
"enemy:29"), re-grants to prove Duplicate, observes natural haul, then exits
BEFORE Pod goal entry because the shared pc_p2_preview_deliver dispatch arm
for Mar is pending #186 owner review (delivering would hit the aborting
fallback). Exiting early is labelled (pod=deferred), never a fallback credit.

Gate 5 (transport_reward via Pod delivery) stays BLOCKED pending that #186
dispatch arm; gate 6 stays UNTESTED. No Transport, kill or credit is ever
injected: the fixture contains no suckMe call and no health/state writes.
"""

import argparse
import json
import os
import re
from pathlib import Path

MAR_GENERATOR = 375001
SOURCE_ID = 29

BIND_RE = re.compile(r"P2_MAR_RECEIPT_BIND generator=(\d+) source_id=29")
RESOLVE_RE = re.compile(
    r"P2_MAR_CORPSE_READY generator=(\d+) source_id=29 receipt=corpse:mar:(\d+)")
RECEIPT_RE = re.compile(
    r"P2_MAR29_RECEIPT seed=(\S+) id=enemy:29 slot=375001 encounter=corpse new=(\d+) dup=(\d+) count=(\d+)")
READY_RE = re.compile(
    r"P2_MAR29_READY squad=(\d+) mar_gen=375001 health=([\d.]+) reg=1 captain_parked=1")
DRAIN_RE = re.compile(
    r"P2_MAR29_DRAIN events=(\d+) min=([\d.]+) start=([\d.]+)")
DEATH_RE = re.compile(r"P2_MAR29_NATURAL_DEATH mar=1 health=0\.00 tick=(\d+)")
CORPSE_RE = re.compile(r"P2_MAR29_CORPSE pellet=1 generator=375001 tick=(\d+)")
CARRY_RE = re.compile(
    r"P2_MAR29_CARRY tick=(\d+) moved=([\d.]+) goal_dist=([\d.\-]+)")
HAUL_RE = re.compile(
    r"P2_MAR29_HAUL moved=([\d.]+) goal_dist=([\d.\-]+) tick=(\d+)")
PASS_RE = re.compile(r"PASS P2_MAR29_RECEIPT_RUN receipt=1 haul=1 pod=deferred")
BLOCKED_RE = re.compile(r"P2_FIXTURE_CAPTAIN_DOWN .* outcome=BLOCKED")
INJECTED_RES = (
    "P2_LL_INJECT", "P2_LIFECYCLE_INJECT", "injected_health",
    "P2_MAR29_FALLBACK", "direct transport assigned", "Transport(",
)


def parse_binds(text):
    return [int(m.group(1)) for m in BIND_RE.finditer(text)]


def check_bind_once(text):
    binds = parse_binds(text)
    if binds != [MAR_GENERATOR]:
        return dict(passed=False,
                    reason="expected single bind [375001], found %r" % (binds,),
                    binds=binds)
    return dict(passed=True, reason="bound once", binds=binds)


def check_resolution(text):
    found = [(int(m.group(1)), int(m.group(2)))
             for m in RESOLVE_RE.finditer(text)]
    good = [g for g in found if g == (MAR_GENERATOR, MAR_GENERATOR)]
    if not good:
        return dict(passed=False,
                    reason="no corpse:mar:375001 resolution", found=found)
    return dict(passed=True, reason="resolved 375001", found=found)


def check_exactly_once(text):
    ms = list(RECEIPT_RE.finditer(text))
    if len(ms) != 1:
        return dict(passed=False,
                    reason="expected 1 receipt line, found %d" % len(ms))
    m = ms[0]
    new, dup, count = int(m.group(2)), int(m.group(3)), int(m.group(4))
    if (new, dup, count) != (1, 0, 1):
        return dict(passed=False,
                    reason="expected new=1 dup=0 count=1, got %r" % (
                        (new, dup, count),))
    return dict(passed=True, reason="exactly-once ledger grant")


def check_natural_haul(text, min_moved=60.0):
    carries = [float(m.group(2)) for m in CARRY_RE.finditer(text)]
    haul = HAUL_RE.search(text)
    best = max(([float(haul.group(1))] if haul else []) + carries,
                default=0.0)
    passed = bool(PASS_RE.search(text))
    injected = [t for t in INJECTED_RES if t in text]
    if injected:
        return dict(passed=False, reason="injection markers present",
                    best=best)
    if not passed:
        return dict(passed=False, reason="no PASS run marker", best=best)
    if best < min_moved:
        return dict(passed=False,
                    reason="haul below threshold (best %.1f)" % best,
                    best=best)
    return dict(passed=True, reason="hauled %.1f, pod deferred" % best,
                best=best)


def check_no_captain_down(text):
    if BLOCKED_RE.search(text):
        return dict(passed=False, reason="captain-down interruption present")
    return dict(passed=True, reason="no captain-down marker")


def validate(text):
    """Validate one receipt-run native log (adapter scope, pod deferred)."""
    ready = READY_RE.search(text)
    return dict(
        bind=check_bind_once(text),
        resolution=check_resolution(text),
        exactly_once=check_exactly_once(text),
        haul=check_natural_haul(text),
        captain=check_no_captain_down(text),
        squad=int(ready.group(1)) if ready else 0,
    )


def splice_fixture(preview_path, fixture_path):
    """Insert the RoomApp fixture class into preview_p2_room.cpp ahead of main.

    Returns the patched text without writing; the caller stages it into the
    private build tree. Fails closed when the anchor is missing or the fixture
    is already present.
    """
    preview = Path(preview_path).read_text(encoding="utf-8")
    body = Path(fixture_path).read_text(encoding="utf-8")
    if "P2_MAR29_READY" in preview:
        raise ValueError("fixture already spliced")
    anchor = "\nint main("
    if anchor not in preview:
        raise ValueError("no main anchor in preview room")
    head, tail = preview.split(anchor, 1)
    return head + "\n" + body + anchor + tail


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", nargs="?",
                        help="native log file to validate")
    parser.add_argument("--splice", nargs=2, metavar=("PREVIEW", "FIXTURE"),
                        help="print spliced preview text to stdout")
    args = parser.parse_args(argv)
    if args.splice:
        print(splice_fixture(*args.splice))
        return 0
    if not args.log:
        parser.error("log file or --splice required")
    result = validate(Path(args.log).read_text(encoding="utf-8"))
    print(json.dumps(result, indent=1))
    ok = all(result[k]["passed"] for k in
             ("bind", "resolution", "exactly_once", "haul", "captain"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())