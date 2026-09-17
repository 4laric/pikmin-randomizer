"""Muse ch_MUKI_damagumo P1 runtime observer (#740).

Lane `p2-challenge-ch-muki-damagumo-p1`. P1 runtime acceptance for P2 Challenge
08 (1 floor, 150 s, decoded starting roster, spicy 1), reusing the done P0 import
base read-only and following the accepted #735 houdai shape. Gates 1/2/3 are P0
import facts; gates 4/5/6 (playable boot/combat/receipt/exit) require the
stage-boot path to resolve `ch_MUKI_damagumo`, which it currently does not (the
#705 table resolves only kusachi/02tile). This module therefore stages fail-closed
and validates honestly: no boot resolution means no runtime claim.

Source facts (P0, read-only):
* `ch_MUKI_damagumo`, P2 Challenge 08, 1 floor, ui_index 6, roster 7x3.
* Retail `user/Mukki/mapunits/caveinfo/ch_MUKI_damagumo.txt` (not redistributed).

This module stages a fresh arena via the P0 contract plus the #129 generator
owner, builds the private guarded fixture, runs it, and validates the native log
via `validate()` - a dependency-free run-log reader. `P2_MUSE_DAMAGUMO_INJECT` /
`P2_LIFECYCLE_INJECT` are never emitted; the reader rejects any run containing
them.
"""

import argparse
import json
import os
import re
from pathlib import Path

SOURCE_KEY = "ch_MUKI_damagumo"
GENERATOR = 0  # resolved at stage time; the boot table must name this key
FLOORS = 1
SECONDS = 150

READY_RE = re.compile(r"P2_MUSE_DAMAGUMO_READY squad=(\d+) stage=ch_MUKI_damagumo")
BIND_RE = re.compile(r"P2_DAMAGUMO_BIND generator=(\d+) source_id=ch_MUKI_damagumo")
BOOT_RE = re.compile(r"P2_CHALLENGE_BOOT stage=ch_MUKI_damagumo")
RECEIPT_RE = re.compile(r"P2_CHALLENGE_RECEIPT stage=ch_MUKI_damagumo")
EXIT_RE = re.compile(r"P2_CHALLENGE_EXIT stage=ch_MUKI_damagumo")
WINDOW_RE = re.compile(r"Experimental preview window set to 960x540 windowed and centered")
GUARD_DOWN_RE = re.compile(r"P2_FIXTURE_CAPTAIN_DOWN [^\n]*outcome=BLOCKED")
INJECT_RE = re.compile(r"P2_MUSE_DAMAGUMO_INJECT|P2_LIFECYCLE_INJECT")
STAGE_UNRESOLVED_RE = re.compile(r"SelectionError: unknown P2 challenge stage|BLOCKED stage_boot_unresolved")


def validate(text, code=0):
    """Validate a damagumo P1 run log. Returns passed/checks/gates."""
    if not isinstance(text, str):
        raise ValueError("Expected a native log string")
    ready = READY_RE.search(text)
    squad = int(ready.group(1)) if ready else 0
    binds = bool(BIND_RE.search(text))
    boot = bool(BOOT_RE.search(text))
    receipt = bool(RECEIPT_RE.search(text))
    exit_ok = bool(EXIT_RE.search(text))
    injected = bool(INJECT_RE.search(text))
    unresolved = bool(STAGE_UNRESOLVED_RE.search(text))
    captain_down = bool(GUARD_DOWN_RE.search(text))
    window = bool(WINDOW_RE.search(text))
    session = bool(re.search(r"P2_MUSE_DAMAGUMO_SESSION navi=1\b", text))
    completion = "PASS P2_MUSE_DAMAGUMO" in text
    checks = dict(
        binds=binds,
        window=window,
        live_squad=squad >= 1,
        boot=boot and not unresolved,
        receipt=receipt and not injected,
        exit_ok=exit_ok and not injected,
        session=session,
        no_inject=not injected,
        captain_safe=not captain_down,
        stage_resolved=not unresolved,
        completion=completion,
    )
    gates = dict(
        playable_boot=("pass" if (boot and not unresolved and not injected) else "fail"),
        combat_receipt=("pass" if (receipt and not injected) else "fail"),
        exit_cleanup=("pass" if (exit_ok and not injected) else "fail"),
    )
    return dict(passed=(code == 0 and all(checks.values())), checks=checks,
                gates=gates, squad=squad)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Muse damagumo P1 observer reader (#740)")
    sub = parser.add_subparsers(dest="command", required=True)
    reader = sub.add_parser("validate")
    reader.add_argument("--log", type=Path, required=True)
    reader.add_argument("--exit-code", type=int, default=0)
    reader.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    text = args.log.read_text(errors="replace")
    result = validate(text, args.exit_code)
    result["source"] = str(args.log)
    if args.out is not None:
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())