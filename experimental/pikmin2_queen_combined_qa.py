"""Combined-candidate Queen30 transport QA checker (#529).

Independent re-derivation of the lane24 Queen gate5 chain on the PRIVATE
combined species pin. Written from the marker contract only; shares no code
with lane24's validators.

Required natural chain (all in one GL log, exit code 0):
  READY (generator 230010, source Queen HP 5000.0) -> host-AI suppression ->
  attached Pikmin + blows-driven FLICKs -> natural death health=0.0 ->
  corpse pellet found -> autonomous carrier latch (transport>0) ->
  real Pod receipt id=corpse:queen:230010 value=2 new=1 -> PASS line.

Explicit non-parity caveats (reported, never relabelled):
  carry counts and transport peaks are Chappy-host-derived, not source-Queen
  20-30-carrier semantics; receipt value=2 is Pod-package-configured
  (P2_POD_1), owned by lane 06. Gate-1 identity stays the authored carrier
  binding; only the transport chain is adjudicated here.

Any staging/injection marker fails the run outright.
"""

import argparse
import json
import re
from pathlib import Path

HOST_GENERATOR = 230010
SOURCE_HP = 5000.0

READY = re.compile(
    r"P2_QUEEN_TEKI_READY generator=(\d+) type=(\d+).*health=([\d.]+)")
SUPPRESSED = re.compile(r"P2_QUEEN_TEKI_HOST_AI_SUPPRESSED generator=(\d+)")
ATTACHED = re.compile(
    r"P2_QUEEN_TEKI_ATTACHED generator=(\d+) attached=(\d+)")
FLICK = re.compile(r"P2_QUEEN_TEKI_FLICK generator=(\d+)")
DEAD = re.compile(
    r"P2_QUEEN_TEKI_CORPSE generator=(\d+) health=([\d.]+)")
CORPSE_PELLET = re.compile(
    r"P2_QUEEN_CREATURE_CORPSE_PELLET found=(\d+)")
CARRY = re.compile(
    r"P2_QUEEN_CREATURE_CARRY .*carry=(\d+) transport=(\d+)")
RECEIPT = re.compile(
    r"P2_POD_RECEIPT id=corpse:queen:(\d+) value=(\d+) new=(\d+)")
PASS_LINE = "PASS P2_QUEEN_CREATURE_RUNTIME"
WINDOW_LINE = "Experimental preview window set to 960x540 windowed and centered"
BASELINE = re.compile(r"P2_QUEEN_CREATURE_BASELINE red=(\d+)")

STAGING_MARKERS = (
    "NAVI_HEAL",
    "REPIN",
    "NAVI_SUSTAIN",
    "GUARD_PIKMIN",
    "P2_QUEEN_INJECT",
    "P2_KING_INJECT",
    "P2_QUEEN_TEKI_FORCED_TRANSPORT",
    "P2_QUEEN_TEKI_TRANSPORT_INJECT",
    "P2_KING_TEKI_FORCED_TRANSPORT",
    "P2_POD_CAPTAIN_RETURN",
    "TransportMode writes",
    "FORCED_TRANSPORT",
)


def find_staging(text):
    """Return sorted staging markers present in the log."""
    return sorted(m for m in STAGING_MARKERS if m in text)


def qa_validate(text, code):
    """Validate a combined-candidate Queen creature log. No runtime here."""
    if not isinstance(text, str):
        raise ValueError("Expected a native log string")
    ready = READY.search(text)
    ready_ok = (ready is not None
                and int(ready.group(1)) == HOST_GENERATOR
                and abs(float(ready.group(3)) - SOURCE_HP) < 1e-6)
    attached_peak = max([int(m.group(1)) for m in
                         re.finditer(r"P2_QUEEN_TEKI_ATTACHED generator=%d attached=(\d+)" % HOST_GENERATOR,
                                     text)] or [0])
    flicks = len(re.findall(r"P2_QUEEN_TEKI_FLICK generator=%d" % HOST_GENERATOR,
                            text))
    dead = DEAD.search(text)
    dead_ok = (dead is not None
               and int(dead.group(1)) == HOST_GENERATOR
               and abs(float(dead.group(2))) < 1e-6)
    pellet = CORPSE_PELLET.search(text)
    carries = [(int(m.group(1)), int(m.group(2)))
               for m in CARRY.finditer(text)]
    latched = any(t > 0 for _, t in carries)
    carry_peak = max([c for c, _ in carries] or [0])
    transport_peak = max([t for _, t in carries] or [0])
    receipts = [(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                for m in RECEIPT.finditer(text)]
    granted = [r for r in receipts if r[2] == 1]
    receipt_ok = (len(granted) == 1 and granted[0][0] == HOST_GENERATOR
                  and granted[0][1] == 2)
    staging = find_staging(text)
    baseline = BASELINE.search(text)
    checks = dict(
        completion=code == 0 and PASS_LINE in text,
        ready_hp=ready_ok,
        host_ai_suppressed=bool(SUPPRESSED.search(text)),
        attached=attached_peak >= 1,
        flick=flicks >= 1,
        natural_death=dead_ok,
        corpse_pellet=pellet is not None and int(pellet.group(1)) == 1,
        carrier_latch=latched,
        pod_receipt=receipt_ok,
        no_staging=not staging,
        window_960x540=WINDOW_LINE in text,
        squad_baseline=baseline is not None and int(baseline.group(1)) >= 1,
    )
    failed = sorted(name for name, ok in checks.items() if not ok)
    return dict(
        passed=not failed,
        failed=failed,
        checks=checks,
        ready_line=(text[:ready.start()].count("\n") + 1) if ready else None,
        flick_count=flicks,
        attached_peak=attached_peak,
        carry_peak=carry_peak,
        transport_peak=transport_peak,
        receipts=["queen:%d value=%d new=%d" % r for r in receipts],
        staging_hits=staging,
        exit_code=code,
        caveats=[
            "host-derived carry: carry peak %d / transport peak %d from the "
            "Chappy host carcass, not source-Queen 20-30-carrier semantics"
            % (carry_peak, transport_peak),
            "package-configured reward: receipt value=2 from the P2_POD_1 "
            "package corpseValue, not source-Queen reward semantics "
            "(lane 06 owns rewards)",
            "proxy identity: gate-1 identity stays the authored carrier "
            "binding; only the transport chain is adjudicated here",
        ],
        scope="Combined-pin Empress Bulblax (30) bound to generated host "
              "230010, killed by free Pikmin with Pod corpse receipt; no "
              "staging or injection channels present",
    )


def main(argv=None):
    """CLI: check a GL log file and write hashed QA evidence."""
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("--log", type=Path, required=True)
    check.add_argument("--code", type=int, default=0)
    check.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    text = args.log.read_text(encoding="utf-8", errors="replace")
    result = qa_validate(text, args.code)
    result["log"] = str(args.log)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("queen-combined-qa", result["passed"], "failed=%s" % result["failed"],
          flush=True)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
