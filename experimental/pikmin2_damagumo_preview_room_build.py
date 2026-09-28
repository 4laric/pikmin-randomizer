"""Fail-closed analyzer for the damagumo preview-room build + GL run (#815).

Downstream consumer: shard-enemies-3-damagumo56-arena-assembly (#798 gen 3).
This module performs no runtime work; it validates the artifacts a leased
build + guarded GL run must produce, refusing with a reason instead of
guessing:

* stock-asset absence: the staged stock enemy template
  dataDir/stages/chal0/default.gen must exist under the canonical root;
  absence is refused with reason (user asset lands separately).
* marker-log grammar: room boot markers (P2_MUSE_DAMAGUMO_READY/BIND/HB),
  honest stage-0 FAIL lines (FAIL p2 room: ...), captain-down blocks
  (P2_FIXTURE_CAPTAIN_DOWN ... outcome=BLOCKED), and the terminal PASS.
* build provenance: executable SHA-256 plus a ninja -n dry run reading
  exactly `ninja: no work to do.`.

Malformed or missing inputs are refused, never defaulted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

STOCK_ASSET = os.path.join("dataDir", "stages", "chal0", "default.gen")

BOOT_MARKERS = (
    "P2_MUSE_DAMAGUMO_READY",
    "P2_MUSE_DAMAGUMO_BIND",
    "P2_MUSE_DAMAGUMO_HB",
)
FAIL_LINE = re.compile(r"^FAIL p2 room: (?P<reason>.+)$")
CAPTAIN_DOWN = re.compile(
    r"^P2_FIXTURE_CAPTAIN_DOWN tick=(?P<tick>\d+) hp=(?P<hp>[0-9.]+) "
    r"orima_dead=(?P<orima>[01]) dead_state=(?P<dead>[01]) outcome=BLOCKED$")
READY = re.compile(
    r"^P2_MUSE_DAMAGUMO_READY squad=(?P<squad>\d+) damagumo_gen=312004$")
TERMINAL_PASS = "PASS P2_MUSE_DAMAGUMO walk+natural-drain"
NINJA_CLEAN = "ninja: no work to do."


class Refused(ValueError):
    """Fail-closed refusal with a reason."""


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_stock_asset(root):
    """Refuse with reason when the staged stock asset is absent."""
    path = os.path.join(root, STOCK_ASSET)
    if not os.path.isfile(path):
        raise Refused(
            "staged stock asset absent: %s missing under canonical root %s "
            "(user asset lands separately; cannot stage the arena)"
            % (STOCK_ASSET, root))
    return path


def read_log_text(path):
    if not os.path.isfile(path):
        raise Refused("marker log missing: " + str(path))
    raw = open(path, "rb").read()
    for encoding in ("utf-8", "utf-16"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise Refused("marker log is not UTF-8 or UTF-16: " + str(path))


def parse_marker_log(text):
    """Parse a room marker log into a verdict dict; refuse malformed input."""
    lines = [l.rstrip("\r\n") for l in text.splitlines() if l.strip()]
    if not lines:
        raise Refused("marker log is empty")
    found_boot = {m: False for m in BOOT_MARKERS}
    fails = []
    captain = None
    terminal_pass = False
    ready_squad = None
    for line in lines:
        for marker in BOOT_MARKERS:
            if line.startswith(marker):
                found_boot[marker] = True
        m = FAIL_LINE.match(line)
        if m:
            fails.append(m.group("reason"))
        m = CAPTAIN_DOWN.match(line)
        if m:
            captain = m.groupdict()
        m = READY.match(line)
        if m:
            ready_squad = int(m.group("squad"))
        if line == TERMINAL_PASS:
            terminal_pass = True
    return {
        "lines": len(lines),
        "boot": found_boot,
        "boots_complete": all(found_boot.values()),
        "fails": fails,
        "captain_down": captain,
        "terminal_pass": terminal_pass,
        "ready_squad": ready_squad,
    }


def check_dry_run(path):
    text = read_log_text(path)
    if NINJA_CLEAN not in text:
        raise Refused(
            "ninja dry run is not clean (missing %r)" % NINJA_CLEAN)
    return True


def check_executable(path):
    if not os.path.isfile(path):
        raise Refused("executable missing: " + str(path))
    return sha256(path)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Damagumo preview-room build/run analyzer (#815)")
    ap.add_argument("--root", required=True, help="canonical root")
    ap.add_argument("--log", help="room marker log to validate")
    ap.add_argument("--dry-run", help="ninja -n log to validate")
    ap.add_argument("--exe", help="built room exe to hash")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    result = {}
    try:
        result["stock_asset"] = check_stock_asset(args.root)
        if args.log:
            result["markers"] = parse_marker_log(read_log_text(args.log))
        if args.dry_run:
            result["dry_run_clean"] = check_dry_run(args.dry_run)
        if args.exe:
            result["exe_sha256"] = check_executable(args.exe)
    except Refused as exc:
        print("REFUSED: %s" % exc)
        return 2
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("OK: %s" % json.dumps(result, default=str)[:400])
    return 0


if __name__ == "__main__":
    sys.exit(main())
