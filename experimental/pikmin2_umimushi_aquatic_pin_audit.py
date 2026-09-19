"""Read-only pin-discovery audit for the UmiMushi71 blocked receiver gate (#648).

Inventories UmiMushi 71 (+100/+101) source anchors with file:line citations and
records the exact missing prerequisite contract (or precise blocker) consumable by
`shard-enemies-6-umimushi71-observer` (#374). Planning-only: no runtime, no family
edits, all six gates UNTESTED, no ADMIT.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ISSUE = 648
DOWNSTREAM_LANE = "shard-enemies-6-umimushi71-observer"
DOWNSTREAM_ISSUE = 374
BACKLOG = 167

# Decomp revision the citations below were verified against (read-only).
DECOMP_REV = "632af93787b9c95b63f0c13be32b161375ce3a96"
DECOMP_ROOT = "native/pikmin2-research"

IDENTITIES = (
    {"id": 71, "name": "UmiMushi", "title": "Ranging Bloyster",
     "spawnable": True, "mgr": "UmiMushi::Mgr"},
    {"id": 100, "name": "UmiMushiBase", "title": "Bloyster base (crashes)",
     "spawnable": False, "mgr": "UmiMushi::Mgr",
     "note": "EFlag_UseOwnID without EFlag_CanBeSpawned; direct generation excluded"},
    {"id": 101, "name": "UmiMushiBlind", "title": "Toady Bloyster",
     "spawnable": True, "mgr": "UmiMushi::Mgr"},
)

# Every anchor below was spot-checked against the decomp checkout this turn.
# Cleanup/re-entry has NO anchor in the reviewed functions; that absence is
# recorded explicitly, not filled in.
ANCHORS = (
    {"area": "identity", "file": "include/Game/enemyInfo.h",
     "lines": "76-86,122-123,130,159-160", "note": "ID declarations incl. 71/100/101"},
    {"area": "identity", "file": "src/plugProjectYamashitaU/generalEnemyMgr.cpp",
     "lines": "450", "note": "registers only EnemyID_UmiMushiBase"},
    {"area": "identity", "file": "src/plugProjectYamashitaU/genEnemy.cpp",
     "lines": "495-573,591", "note": "generator dispatch incl. both Bloysters; base case separate"},
    {"area": "identity", "file": "src/plugProjectYamashitaU/enemyInfo.cpp",
     "lines": "102-104", "note": "71 and 101 spawnable; 100 excluded from direct generation"},
    {"area": "birth", "file": "src/plugProjectMorimuraU/umiMushiMgr.cpp",
     "lines": "86", "note": "Mgr::createObj tags UmiMushi then Blind by per-ID counts"},
    {"area": "birth", "file": "src/plugProjectMorimuraU/umiMushi.cpp",
     "lines": "94", "note": "Obj::onInit starts shared FSM in Walk; Blind gets scale/health/joints"},
    {"area": "attack", "file": "src/plugProjectMorimuraU/umiMushiState.cpp",
     "lines": "510", "note": "StateAttack::exec: tongue key 3, eatPikmin, Navi key 5 if mCanEatNavis, flick key 6"},
    {"area": "attack", "file": "src/plugProjectMorimuraU/umiMushiState.cpp",
     "lines": "606", "note": "StateEat::exec swallows at animation end"},
    {"area": "receiver", "file": "src/plugProjectMorimuraU/umiMushi.cpp",
     "lines": "467", "note": "damageCallBack: bitter passes; Piki stick/coll-part or sub-body-height routing; no tail-ID rule proven"},
    {"area": "receiver", "file": "src/plugProjectMorimuraU/umiMushi.cpp",
     "lines": "493,512,531", "note": "press/hipdrop/earthquake Purple scaling"},
    {"area": "receiver", "file": "src/plugProjectMorimuraU/umiMushi.cpp",
     "lines": "552", "note": "initMouthSlots: seven slots, radius 30 (25 Blind)"},
    {"area": "receiver", "file": "src/plugProjectMorimuraU/umiMushi.cpp",
     "lines": "843", "note": "isChangeNavi: Blind false; nearest/live Navi retarget branches"},
    {"area": "death", "file": "src/plugProjectMorimuraU/umiMushiState.cpp",
     "lines": "634,649", "note": "StateDead: deathProcedure then kill at animation end; no loot/drop or reset established"},
    {"area": "cleanup", "file": None, "lines": None,
     "note": "ABSENT: no generator-rebirth, day-end reset or persistence anchor in the reviewed functions"},
)

# Blocked-lane evidence this verdict consumes (read-only).
BLOCKED_EVIDENCE = {
    "lane": "shard-enemies-6-umimushi71-observer",
    "state": "blocked", "generation": 4, "issue": 374,
    "death_run": "death-run1/pass1: 102 throws, hp 1500.0->1485.0, 12 swallows; "
                 "captain dragged ~270u, dead tick 1273, P2_FIXTURE_CAPTAIN_DOWN exit 86",
    "runtime_evidence": "natural_death=false, corpse_recorded=false, resolution=false, passed=false",
    "port": "pc_port/pc_p2_umimushi.cpp(.h) + tools/p2_muse_umimushi_fixture.cpp "
            "(UMI_DEAD=8 dead/dead1 clips; forget/reset hooks present, re-entry unobserved)",
}


def inventory():
    """Return the anchor rows (dicts); cleanup absence stays explicit."""
    return [dict(row) for row in ANCHORS]


def verdict():
    """Exact missing-input contract consumable by #374 (no invented values)."""
    return {
        "downstream": {"lane": DOWNSTREAM_LANE, "issue": DOWNSTREAM_ISSUE},
        "missing_inputs": [
            {"input": "captain-alive natural death + corpse/disappearance run",
             "why": "only death run killed the captain (guard 86), tainting every "
                    "observation; runtime-evidence natural_death=false, corpse_recorded=false",
             "producer": "shard-enemies-6-umimushi71-observer (owns module+fixture+arena)",
             "prescription": "park captain out of tongue/attack reach, thrown-Pikmin latch, "
                             "extended window; no new lane needed"},
            {"input": "cleanup/re-entry run incl. generator rebirth",
             "why": "no source anchor in reviewed functions; forget/reset hooks exist in "
                    "port but re-entry unobserved (tadpole stage-reset precedent applies)",
             "producer": "shard-enemies-6-umimushi71-observer (owns fixture)",
             "prescription": "stage-boundary reset + rebirth with stale/fresh proof; no new lane needed"},
            {"input": "family receiver review (latch-vs-routing for 71/101)",
             "why": "open per gen-4 reassessment and still family-owned; no live review lane exists",
             "producer": "NONE live; recommend a new bounded receiver-review lane modeled on "
                         "#641 (Catfish26, done kind=tooling), owned outside this audit",
             "prescription": "do not duplicate any live scope; review latch/stick routing, "
                             "tail-ID rule and collision-part weakpoints against umiMushi.cpp:467+"},
        ],
        "wake_167": {"satisfied": False,
                     "reason": "#167 checklist unchecked; no integrated UmiMushi receiver review; "
                               "#641 covers Catfish26 (different family/scope)"},
        "gates": "all six UNTESTED by this audit",
    }


def missing_prerequisite():
    return ("UmiMushi 71/100/101 aquatic receiver prerequisite: no live producer. "
            "Death/corpse + re-entry belong to the blocked lane itself (#374, prescription "
            "recorded); the family receiver review needs a new bounded lane modeled on #641. "
            "#167 wake NOT satisfied.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    payload = json.dumps({"issue": ISSUE, "identities": list(IDENTITIES),
                          "anchors": inventory(), "blocked": BLOCKED_EVIDENCE,
                          "verdict": verdict()}, indent=2, sort_keys=True) + "\n"
    if args.out is None:
        print(payload, end="")
    else:
        args.out.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())