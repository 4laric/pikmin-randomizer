"""#186 decision packet for the tutorial Font::setTexture guard (#785).

Bounded packet producer for prerequisite recovery request 5aac47ab... (issue
#785; downstream tutorial P1). It packages the EXACT source pins, shared guard
scope, consumer check, requested #186 decision and integrator landing
disposition for the blocked `tutorial-p1-font-settexture-crash-fix` (#750)
slice, consuming that lane read-only without duplicating its scope or touching
shared files. Fail-closed: unknown pins, missing inputs or grammar drift raise
before any packet is emitted. Stdlib only. No engine edits, no builds, no
runtime runs, no ADMIT. All six gates UNTESTED.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = "p2-tutorial-crash-fix-186-packet-v1"
PRODUCER_LANE = "tutorial-p1-font-settexture-crash-fix"
PRODUCER_ISSUE = 750
DOWNSTREAM_ISSUES = (148,)

# Exact source pins, read-only refs (from the blocked lane record + brief).
PRODUCER_ROOT = "69b74c1ed5ebd096be1c5c9eb8fcd0a9d4023490"
PRODUCER_NATIVE = "0940c1e4c2d47519df3b8f0a44f2e921796b722f"

# Shared guard scope under #186 review (read-only refs; landing needs approval).
GUARD_CALLSITE = {"file": "native/src/sysCommon/graphics.cpp", "symbol": "Font::setTexture"}
BUILD_MEMBERSHIP = ["native/CMakeLists.txt"]

# Consumer check: the staged tutorial P1 boot re-run that must observe the fix.
CONSUMER = {
    "lane": "p2-overworld-tutorial-p1-staged-rerun",
    "command": "Rebuild the tutorial fixture under lease and re-run the staged boot from the staged run dir with the guarded fixture",
    "expected": "No 0xC0000005 at Font::setTexture; boot proceeds past splash or an exact new blocker is recorded; no invented acceptance",
}

_FULL_SHA_RE = __import__("re").compile(r"[0-9a-f]{40}\Z")


class PacketRejected(ValueError):
    pass


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def check_pin(value, name):
    if not isinstance(value, str) or not _FULL_SHA_RE.match(value):
        raise PacketRejected("Pin %s must be a full 40-hex commit: %r" % (name, value))
    return value


def build_packet(root_pin, native_pin, out_dir=None):
    """Validate pins and emit the #186 decision packet (dict; optionally written)."""
    check_pin(root_pin, "producer root")
    check_pin(native_pin, "producer native")
    if root_pin != PRODUCER_ROOT or native_pin != PRODUCER_NATIVE:
        raise PacketRejected("Pins do not match the blocked producer record")
    packet = {
        "schema": SCHEMA,
        "producer": {"lane": PRODUCER_LANE, "issue": PRODUCER_ISSUE,
                     "root": root_pin, "native": native_pin},
        "guard": {"callsite": GUARD_CALLSITE, "build_membership": BUILD_MEMBERSHIP,
                  "note": "Shared-engine scope; landing requires explicit #186 approval. No approval granted here."},
        "consumer": dict(CONSUMER, downstream_issues=list(DOWNSTREAM_ISSUES)),
        "requested_decision": "#186 approve/amend/decline the Font::setTexture guard with reasons",
        "landing": "Single-writer integrator lands on approval, rebuilds under lease, re-runs the staged boot.",
        "gates": "all six runtime gates UNTESTED; no runtime run, no ADMIT",
    }
    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "tutorial-crash-fix-186-packet.json"
        if path.exists():
            raise PacketRejected("Refusing to overwrite existing packet")
        blob = (json.dumps(packet, indent=2, sort_keys=True) + "\n").encode()
        path.write_bytes(blob)
        packet["packet_path"] = str(path)
        packet["packet_sha256"] = sha256_bytes(blob)
    return packet


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-pin", default=PRODUCER_ROOT)
    parser.add_argument("--native-pin", default=PRODUCER_NATIVE)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    packet = build_packet(args.root_pin, args.native_pin, args.out)
    print(json.dumps({"packet": packet.get("packet_path")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())