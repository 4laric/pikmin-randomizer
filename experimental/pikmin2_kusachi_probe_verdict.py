"""Kusachi probe-stream verdict analyzer (#809; consumer kusachi-gameplay-obs #780).

Reads the landed #793 extinction-window probe stream READ-ONLY and attempts to
settle the discriminating question: when the wired kusachi squad drops from
live to extinct, was it (a) a navi-drop cascade - the captain Navi died/lost
first and the following piki set was released - or (b) a direct manager-level
clear - pikiMgr live set zeroed while the captain stayed healthy?

Design contract (from issue #809 and the #787 diagnosis):

* This module NEVER fixes the extinction and NEVER claims #780 acceptance. It
  produces a settled verdict artifact plus a scoped fix contract.
* It is FAIL-CLOSED. A malformed stream, a stream with no live->extinct
  transition, or a stream whose discriminating fields cannot decide the
  question is refused with a reasoned VerdictRefused - never guessed.
* The verdict requires the extinction window to actually be present in the
  stream. The landed #793 probe run does NOT contain it (the squad holds
  alive=8 through tick 1254); the analyzer says so honestly rather than
  inferring a cause from healthy ticks.

Verdict vocabulary:

* CASCADE   - the captain Navi was lost at or before the collapse tick and the
              squad still had members alive at the moment of loss (i.e. the
              collapse followed the captain loss), so the squad was released by
              the captain-loss path rather than cleared while the captain lived.
* DIRECT    - the captain stayed healthy (navi_alive 1, orima_dead 0) for the
              entire run through the collapse tick: the manager live set was
              cleared with a live captain.
* UNRESOLVED- the stream contains the collapse but the discriminating values
              are absent/ambiguous, so no honest verdict exists.
"""
from __future__ import annotations

import argparse
import json
import sys

PROBE_PREFIX = "P2_KUSACHI_PROBE "
FORBIDDEN = (
    "P2_FIXTURE_CAPTAIN_DOWN",
    "FAIL KUSACHI_PROBE",
)

REQUIRED_FIELDS = (
    "tick", "navimgr", "navi", "navi_alive", "orima_dead", "alive", "reds",
    "slots",
)

CASCADE = "CASCADE"
DIRECT = "DIRECT"
UNRESOLVED = "UNRESOLVED"


class VerdictRefused(ValueError):
    """Raised when no honest verdict can be produced from the input."""


def read_log_text(path):
    """Decode a probe log regardless of UTF-8/UTF-16 console encoding."""
    raw = open(path, "rb").read()
    for encoding in ("utf-8", "utf-16"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise VerdictRefused("probe log is not UTF-8 or UTF-16: " + str(path))


def parse_probe_line(line):
    """Parse one P2_KUSACHI_PROBE line into a dict of typed values.

    Refuses malformed lines: missing fields, non-integer fields, non-binary
    slots, or a slots string disagreeing with the alive count.
    """
    if not line.startswith(PROBE_PREFIX):
        raise VerdictRefused("not a probe line: " + repr(line[:80]))
    fields = {}
    for token in line[len(PROBE_PREFIX):].strip().split():
        if "=" not in token:
            raise VerdictRefused("non key=value token in probe line: " + token)
        key, _, value = token.partition("=")
        fields[key] = value
    for key in REQUIRED_FIELDS:
        if key not in fields:
            raise VerdictRefused("probe line missing field: " + key)
    try:
        row = {
            "tick": int(fields["tick"]),
            "navimgr": int(fields["navimgr"]),
            "navi": int(fields["navi"]),
            "navi_alive": int(fields["navi_alive"]),
            "orima_dead": int(fields["orima_dead"]),
            "alive": int(fields["alive"]),
            "reds": int(fields["reds"]),
            "slots": fields["slots"],
        }
    except ValueError as exc:
        raise VerdictRefused("non-integer probe field: %s" % exc)
    if any(c not in "01" for c in row["slots"]):
        raise VerdictRefused("non-binary slots at tick %d" % row["tick"])
    if row["alive"] != row["slots"].count("1"):
        raise VerdictRefused(
            "slots disagree with alive count at tick %d" % row["tick"])
    for key in ("navimgr", "navi", "navi_alive", "orima_dead"):
        if row[key] not in (0, 1):
            raise VerdictRefused("flag %s out of range at tick %d"
                                 % (key, row["tick"]))
    return row


def parse_probe_stream(text):
    """Parse every probe line in a log; refuse a stream with zero lines."""
    rows = []
    for line in text.splitlines():
        if line.startswith(PROBE_PREFIX):
            rows.append(parse_probe_line(line))
    if not rows:
        raise VerdictRefused("no P2_KUSACHI_PROBE lines found")
    ticks = [r["tick"] for r in rows]
    if ticks != sorted(ticks) or len(set(ticks)) != len(ticks):
        raise VerdictRefused("probe ticks are not strictly increasing")
    return rows


def find_extinction_window(rows):
    """Locate the first live->extinct collapse. Returns (index, before, after).

    A collapse is a transition where the previous row had alive>0 and the
    current row has alive==0. Returns None when no collapse exists in the
    stream - the analyzer must then refuse rather than infer.
    """
    for i in range(1, len(rows)):
        prev, cur = rows[i - 1], rows[i]
        if prev["alive"] > 0 and cur["alive"] == 0:
            return i, prev, cur
    return None


def classify_window(rows, index):
    """Classify the collapse at `index` as CASCADE / DIRECT / UNRESOLVED.

    The captain flags (navi_alive / orima_dead) are only meaningful while
    naviMgr is present; `navimgr=0` ticks carry no captain information and are
    neither a loss nor a healthy confirmation. Uses run history up to and
    including the collapse tick so a captain loss that precedes the collapse
    (the defining cascade shape) is detected, not merely an adjacent-tick one.
    """
    collapse_tick = rows[index]["tick"]
    before = rows[index - 1]
    history = rows[:index + 1]

    informative = [r for r in history if r["navimgr"] == 1]

    # Direct clear: the captain was healthy (navi alive, orima not dead) on
    # every tick where naviMgr was present, through the collapse.
    if informative and all(r["navi_alive"] == 1 and r["orima_dead"] == 0
                           for r in informative):
        return DIRECT, (
            "squad collapsed at tick %d while the captain stayed healthy on "
            "all %d informative ticks (navi_alive held 1, orima_dead held 0)"
            % (collapse_tick, len(informative)))

    # Cascade: the captain was lost on some informative tick at or before the
    # collapse, and the squad was still live on the tick immediately before the
    # collapse (so the release, not a pre-existing empty set, emptied it).
    lost_row = None
    for r in informative:
        if r["navi_alive"] == 0 or r["orima_dead"] == 1:
            lost_row = r
            break
    if lost_row is not None and before["alive"] > 0:
        return CASCADE, (
            "captain lost at tick %d (navi_alive=%d orima_dead=%d); squad was "
            "live (%d) on the tick before the collapse at tick %d"
            % (lost_row["tick"], lost_row["navi_alive"],
               lost_row["orima_dead"], before["alive"], collapse_tick))

    # No informative captain state, or the squad was already empty before the
    # collapse: the stream cannot discriminate the two hypotheses.
    return UNRESOLVED, (
        "discriminating flags absent or ambiguous across the collapse at "
        "tick %d (informative ticks=%d, alive before=%d)"
        % (collapse_tick, len(informative), before["alive"]))


def analyze(path):
    """Full fail-closed analysis of a probe log. Returns a verdict dict."""
    text = read_log_text(path)
    for bad in FORBIDDEN:
        if bad in text:
            raise VerdictRefused("forbidden marker present: " + bad)
    rows = parse_probe_stream(text)
    window = find_extinction_window(rows)
    if window is None:
        raise VerdictRefused(
            "no live->extinct transition in %d probe ticks; the extinction "
            "window is absent so cascade-vs-clear cannot be settled from this "
            "stream" % len(rows))
    index, before, after = window
    verdict, reason = classify_window(rows, index)
    return {
        "verdict": verdict,
        "reason": reason,
        "before": before,
        "after": after,
        "ticks_observed": len(rows),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Kusachi probe-stream verdict analyzer (#809)")
    ap.add_argument("probe_log", help="path to the #793 probe.log")
    ap.add_argument("--json", action="store_true",
                    help="emit the verdict as JSON")
    args = ap.parse_args(argv)
    try:
        result = analyze(args.probe_log)
    except VerdictRefused as exc:
        print("REFUSED: %s" % exc)
        return 2
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("verdict: %s" % result["verdict"])
        print("reason: %s" % result["reason"])
        print("transition tick: %d -> %d"
              % (result["before"]["tick"], result["after"]["tick"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
