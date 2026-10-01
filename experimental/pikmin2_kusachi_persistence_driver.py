"""Kusachi P2 persistence driver harness (#758).

Bounded root-level driver for the kusachi P1 residual P2 persistence
(save/reload/retry/re-entry). It consumes the integrated #708 persistence
wiring, #713 native hookup and #728 kusachi content wiring read-only (keys,
module, bindings) and drives the four sequences against the wired kusachi
stage, recording hashed per-gate evidence for downstream #533. It fails closed
on any unwired stage. No family/shared/native edits, no runtime run (driver +
tests only), no ADMIT. All six gates UNTESTED. Stdlib only.

The driver generates and validates the harness (commands, keys, markers,
evidence); it does not execute the engine. The downstream consumer
(`p2-challenge-ch_nari_01kusachi-p1`, #533) executes the harness to observe
persistence behavior.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = "p2-kusachi-persistence-driver-v1"
KUSACHI_KEY = "ch_NARI_01kusachi"
SEQUENCES = ("save", "reload", "retry", "re-entry")

# Persistence key shapes mirror integrated #708 (KEY_PREFIX/KEY_FIELDS) read-only;
# this module never re-derives the #708 table, it only shapes kusachi-bound keys.
KEY_PREFIX = "p2_challenge"
KEY_FIELDS = ("save", "load", "clear", "highscore", "unlock")

# Expected markers per sequence (the downstream probe counts these).
MARKERS = {
    "save": "P2_KUSACHI_SAVE key={key} staged=1",
    "reload": "P2_KUSACHI_RELOAD key={key} restored=1",
    "retry": "P2_KUSACHI_RETRY key={key} attempt={n}",
    "re-entry": "P2_KUSACHI_REENTRY key={key} restored=1",
}


class DriverRejected(ValueError):
    pass


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def stage_keys(cave_id):
    """Kusachi-bound persistence keys; raise DriverRejected unless wired."""
    if not isinstance(cave_id, str) or not cave_id:
        raise DriverRejected("Empty stage key")
    if cave_id != KUSACHI_KEY:
        raise DriverRejected("Unwired stage (only %r is bound): %r" % (KUSACHI_KEY, cave_id))
    return {field: "%s_%s_%s" % (KEY_PREFIX, cave_id.lower(), field) for field in KEY_FIELDS}


def check_wiring(wiring):
    """Validate the #728 wiring manifest read-only; return (ok, reasons)."""
    if not isinstance(wiring, dict):
        raise DriverRejected("Wiring manifest must be a mapping")
    reasons = []
    if wiring.get("stage") != KUSACHI_KEY:
        reasons.append("wiring stage is not kusachi")
    if not wiring.get("content_wired"):
        reasons.append("content_wired is not set")
    if not wiring.get("boot_marker"):
        reasons.append("boot marker missing")
    return (not reasons), reasons


def drive(stage_key, wiring, out_dir=None):
    """Generate the four-sequence harness with hashed per-gate evidence."""
    keys = stage_keys(stage_key)
    ok, reasons = check_wiring(wiring)
    if not ok:
        raise DriverRejected("Unwired stage: %s" % "; ".join(reasons))
    gates = {}
    for seq in SEQUENCES:
        marker = MARKERS[seq].format(key=keys["save"], n=1)
        blob = ("%s\n%s\n%s\n" % (SCHEMA, seq, marker)).encode()
        gates[seq] = {"marker": marker, "sha256": sha256_bytes(blob)}
    packet = {"schema": SCHEMA, "stage": stage_key, "keys": keys,
              "wiring_sha256": sha256_bytes(json.dumps(wiring, sort_keys=True).encode()),
              "gates": gates, "downstream_consumer": 533,
              "gates_claim": "all six runtime gates UNTESTED; harness only, not gameplay"}
    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "kusachi-persistence-packet.json"
        if path.exists():
            raise DriverRejected("Refusing to overwrite existing packet")
        path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        packet["packet_path"] = str(path)
    return packet


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--wiring", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    wiring = json.loads(args.wiring.read_text(encoding="utf-8"))
    packet = drive(args.stage, wiring, args.out)
    print(json.dumps({"packet": packet.get("packet_path"), "stage": args.stage}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())