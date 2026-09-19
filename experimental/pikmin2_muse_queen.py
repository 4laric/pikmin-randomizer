"""Independent Queen30 (Empress Bulblax) gate-5 transport review (muse-queen, #496).

Verifies the already-produced lane24 Queen gate-5 candidate WITHOUT reusing
lane24's validator code and WITHOUT editing any Queen/King/shared native
module. The check re-derives the full natural chain from the raw cited
``native.log``:

READY (health=5000.0) -> HOST_AI_SUPPRESSED -> BASELINE/ARMED -> blows-driven
FLICKs -> CORPSE (health=0.0) -> DEATH_SEEN (receiver=engine) ->
CORPSE_PELLET (found=1) -> CARRY (transport>0) ->
POD_RECEIPT (id=corpse:queen:<gen>) with no staging markers.

Source anchors (read-only):
- Queen HP 5000.0: ``native/pikmin2-research`` Queen ``setParameters`` uses
  ``C_GENERALPARMS.mHealth`` (general fp00); mirrored as
  ``p2queen::HealthDefault`` in the candidate's ``pc_p2_queen_policy.h``.
- Queen ``onKill`` runs the standard ``EnemyBase::onKill`` corpse path and
  Queen.cpp creates no custom Pellet (hence the candidate's generated-host
  carcass recipe); the Empress drops no pellets in source so the sidecar
  zeroes the copied host pellet-appear chance.
- Receipt value is Pod-package configured (``corpseValue`` from the
  ``P2_POD_1`` config line in ``pc_p2_preview.cpp``), NOT source-derived, and
  the hauled carcass is the bound TEKI_Chappy host's (observed carry=3),
  NOT a source-Queen 20-30-carrier corpse. Both are reported as caveats;
  neither fails the transport-mechanism gate.

Staging markers that force FAIL (exact tokens; the benign ``no_injection=1``
substring inside the ARMED line is NOT matched):
``P2_QUEEN_TEKI_FORCED_TRANSPORT``, ``P2_QUEEN_TEKI_TRANSPORT_INJECT``,
``P2_QUEEN_NATURAL_REPIN``, ``P2_QUEEN_NATURAL_NAVI_HEAL``, ``NAVI_HEAL``,
``P2_POD_CAPTAIN_RETURN``, ``TransportMode``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Exact staging tokens. Deliberately NOT a bare "INJECT" substring: the benign
# ARMED line carries "no_injection=1" and must not trip the detector.
STAGING_MARKERS = (
    "P2_QUEEN_TEKI_FORCED_TRANSPORT",
    "P2_QUEEN_TEKI_TRANSPORT_INJECT",
    "P2_QUEEN_NATURAL_REPIN",
    "P2_QUEEN_NATURAL_NAVI_HEAL",
    "NAVI_HEAL",
    "P2_POD_CAPTAIN_RETURN",
    "TransportMode",
)

READY_RE = re.compile(
    r"P2_QUEEN_TEKI_READY generator=(\d+) type=(\d+) binding=creature_host health=([\d.]+)"
)
FLICK_RE = re.compile(
    r"P2_QUEEN_TEKI_FLICK generator=(\d+) shaken=(\d+) blown_threshold=(\d+) stuck_threshold=(\d+)"
)
CARRY_RE = re.compile(
    r"P2_QUEEN_CREATURE_CARRY carcass_state=(\d+) carry=(\d+) transport=(\d+)"
)
RECEIPT_RE = re.compile(
    r"\[Pikipelago\] P2_POD_RECEIPT id=corpse:queen:(\d+) value=(\d+) new=(\d+) pokos=(\d+)"
)

SOURCE_QUEEN_HP = 5000.0
# Source shake ladder mirrored by the candidate sidecar (blows 30/35/45/50).
SOURCE_FLICK_LADDER = (30, 35, 45, 50)


@dataclass
class QueenGate5Verdict:
    ok: bool = False
    generator: str = ""
    host_type: str = ""
    ready_line: int = 0
    receipt_line: int = 0
    receipt_value: int = 0
    flick_count: int = 0
    flick_ladder_seen: tuple = ()
    max_transport: int = 0
    carry_at_latch: int = 0
    staging_hits: list = field(default_factory=list)
    failures: list = field(default_factory=list)
    caveats: list = field(default_factory=list)


def review_queen_gate5_log(path: str | Path, expect_generator: str = "") -> QueenGate5Verdict:
    """Independently re-derive the Queen gate-5 chain from a raw native.log."""
    v = QueenGate5Verdict()
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        v.failures.append(f"unreadable log: {exc}")
        return v
    lines = text.splitlines()

    order: dict[str, int] = {}
    ladder: list[int] = []
    flick_spots: list[tuple[int, int]] = []
    for i, line in enumerate(lines, start=1):
        for marker in STAGING_MARKERS:
            if marker in line:
                v.staging_hits.append(f"{i}:{marker}")
        m = READY_RE.search(line)
        if m and "ready" not in order:
            order["ready"] = i
            v.generator, v.host_type = m.group(1), m.group(2)
            v.ready_line = i
            try:
                hp = float(m.group(3))
            except ValueError:
                hp = -1.0
            if hp != SOURCE_QUEEN_HP:
                v.failures.append(f"READY health {m.group(3)} != source Queen {SOURCE_QUEEN_HP}")
        if "P2_QUEEN_TEKI_HOST_AI_SUPPRESSED" in line and "suppressed" not in order:
            order["suppressed"] = i
        if "P2_QUEEN_CREATURE_BASELINE" in line and "baseline" not in order:
            order["baseline"] = i
        if "P2_QUEEN_CREATURE_ARMED" in line and "armed" not in order:
            order["armed"] = i
            if "no_injection=1" not in line or "deploy_once=1" not in line:
                v.failures.append(f"ARMED line {i} lacks no_injection/deploy_once flags")
        fm = FLICK_RE.search(line)
        if fm:
            if "flick" not in order:
                order["flick"] = i
            v.flick_count += 1
            ladder.append(int(fm.group(3)))
            flick_spots.append((int(fm.group(3)), i))
        if "P2_QUEEN_TEKI_CORPSE" in line and "health=0.0" in line and "corpse" not in order:
            order["corpse"] = i
        if "P2_QUEEN_CREATURE_DEATH_SEEN receiver=engine" in line and "death_seen" not in order:
            order["death_seen"] = i
        if "P2_QUEEN_CREATURE_CORPSE_PELLET found=1" in line and "pellet" not in order:
            order["pellet"] = i
        cm = CARRY_RE.search(line)
        if cm:
            if "carry" not in order:
                order["carry"] = i
            transport = int(cm.group(3))
            if transport > v.max_transport:
                v.max_transport = transport
                v.carry_at_latch = int(cm.group(2))
        rm = RECEIPT_RE.search(line)
        if rm and "receipt" not in order:
            order["receipt"] = i
            v.receipt_line = i
            v.receipt_value = int(rm.group(2))
            if rm.group(1) != v.generator:
                v.failures.append(
                    f"receipt generator {rm.group(1)} != READY generator {v.generator}"
                )

    v.flick_ladder_seen = tuple(sorted(set(ladder)))
    if expect_generator and v.generator and v.generator != expect_generator:
        v.failures.append(f"generator {v.generator} != expected {expect_generator}")

    # Strict order applies to the lifecycle backbone. FLICKs are exempt from
    # first-occurrence ordering: the candidate harness prints ARMED after the
    # deploy while blows-driven FLICKs already fire (candidate log: first
    # FLICK :777 before ARMED :787). FLICKs must instead fall inside the
    # (READY, RECEIPT) window.
    sequence = ["ready", "suppressed", "baseline", "armed",
                "corpse", "death_seen", "pellet", "carry", "receipt"]
    missing = [step for step in sequence if step not in order]
    if missing:
        v.failures.append(f"missing chain steps: {','.join(missing)}")
    else:
        positions = [order[s] for s in sequence]
        if positions != sorted(positions):
            v.failures.append("chain steps out of order")
    flick_lines = [n for _, n in flick_spots]
    if flick_lines and "ready" in order and "receipt" in order:
        if not any(order["ready"] < n < order["receipt"] for n in flick_lines):
            v.failures.append("no FLICK inside the READY..RECEIPT window")
    if v.staging_hits:
        v.failures.append(f"staging markers present: {';'.join(v.staging_hits[:8])}")
    if v.flick_count < 3:
        v.failures.append(f"only {v.flick_count} FLICK lines (need >=3 blows-driven)")
    if v.max_transport <= 0 and "carry" in order:
        v.failures.append("CARRY observed but transport never >0 (no carrier latch)")
    if not any(t in v.flick_ladder_seen for t in SOURCE_FLICK_LADDER):
        v.failures.append(f"no source-ladder threshold {SOURCE_FLICK_LADDER} in FLICKs")

    # Honest, always-reported caveats: proxy host + package-configured reward.
    v.caveats.append(
        f"proxy identity: type={v.host_type or '?'} TEKI_Chappy host with Queen visual; "
        "gate-1 identity stays proxy (held at spawn), only the transport chain is adjudicated here"
    )
    v.caveats.append(
        f"host-derived carry: observed carry={v.carry_at_latch} transport peak={v.max_transport}; "
        "this is the Chappy host carcass, not a source-Queen 20-30-carrier corpse"
    )
    v.caveats.append(
        f"package-configured reward: receipt value={v.receipt_value} comes from the Pod "
        "package corpseValue (P2_POD_1 config), not source-Queen reward semantics (lane 06 owns rewards)"
    )

    v.ok = not v.failures
    return v


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Independent Queen30 gate-5 log review")
    ap.add_argument("--log", required=True, help="native.log path to review")
    ap.add_argument("--expect-generator", default="", help="expected generator id")
    ap.add_argument("--json", default="", help="optional path to write the verdict JSON")
    args = ap.parse_args(argv)
    v = review_queen_gate5_log(args.log, args.expect_generator)
    print(f"generator={v.generator} host_type={v.host_type} ready_line={v.ready_line} "
          f"receipt_line={v.receipt_line} value={v.receipt_value} flicks={v.flick_count} "
          f"max_transport={v.max_transport}")
    for c in v.caveats:
        print(f"CAVEAT {c}")
    if v.ok:
        print("VERDICT PASS Queen gate5 natural transport chain (with caveats above)")
    else:
        for f in v.failures:
            print(f"FAIL {f}")
        print("VERDICT FAIL Queen gate5 chain")
    if args.json:
        Path(args.json).write_text(json.dumps(v.__dict__, indent=1), encoding="utf-8")
    return 0 if v.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
