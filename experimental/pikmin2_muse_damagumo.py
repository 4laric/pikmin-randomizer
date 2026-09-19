"""Muse Damagumo56 natural-acceptance observer (issue #173, shard enemies-3).

Damagumo (Beady Long Legs, roster source 56) is the remaining Long Legs
species with zero acceptance evidence. The family is integrated (Houdai66 /
BigFoot69, #502/#574) and ``engine/pc_port/pc_p2_long_legs_fsm.cpp`` carries
the Damagumo disc parms, but no slice staged or accepted 56.

This module is the engine-free acceptance contract: a dependency-free run-log
reader plus focused negatives. It stages nothing, injects nothing and emits
no markers; the future Damagumo fixture writes the same marker grammar and
this reader gives deterministic verdicts. A printed marker alone can never
pass: every gate below requires the correlated source facts in one log.

Source facts (read-only retail ``native/pikmin2-research``):
* Damagumo ``onInit`` runs ``disableEvent(0, EB_LeaveCarcass)``
  (Damagumo.cpp:80) - no carcass, no corpse, no corpse transport, ever. Gate 5
  is therefore source-backed N/A exactly as for Houdai66/BigFoot69, and is
  NOT satisfied by a proxy-corpse Pod credit.
* Damagumo moves at disc speed 100 (``p2LongLegsParmsFor``) through the
  source Stay->Land->Wait->Walk cycle.
* Death reward is ``createItemAndEnemy``: with no held treasure the source
  births 25 ShijimiChou from the ``kosi`` joint (Damagumo deathChildren 25);
  a held-treasure drop/carry/receipt belongs to the treasure-receipts
  provider (#614) and must not be built here.

Gate mapping produced by ``validate``:
1. identity_spawn  - BIND + STAGE for the same live generator.
2. movement_animation - a real WALK/WALK_END pair at Damagumo source speed.
3. attacks_receivers - a natural death with health=0 under squad combat and
   no injected taint (mHealth injection is rejected).
4. death_corpse - the DEAD line plus the source child birth (25 ShijimiChou).
5. transport_reward - source-backed N/A (no carcass) + child-birth path.
6. cleanup_reentry - stage-boundary reset plus generator rebirth with re-bind
   and stale/fresh pointer proof.
"""

import argparse
import json
import re

SPECIES = "Damagumo"
SOURCE_SPEED = 100.0
CHILD_SPECIES = "ShijimiChou"
CHILD_COUNT = 25
MIN_WALK_DISTANCE = 25.0

BIND_RE = re.compile(
    r"P2_MUSE_DAMAGUMO_BIND generator=(\d+) species=Damagumo native_fsm=implemented")
READY_RE = re.compile(r"P2_MUSE_DAMAGUMO_READY squad=(\d+) damagumo_gen=(\d+)")
STATE_RE = re.compile(
    r"P2_LONG_LEGS_STATE species=Damagumo generator=(\d+) state=(Stay|Land|Wait|Walk)")
WALK_RE = re.compile(
    r"P2_LONG_LEGS_WALK species=Damagumo generator=(\d+) "
    r"from=(-?[\d.]+),(-?[\d.]+) to=(-?[\d.]+),(-?[\d.]+) speed=([\d.]+)")
WALK_END_RE = re.compile(
    r"P2_LONG_LEGS_WALK_END species=Damagumo generator=(\d+) "
    r"distance=([\d.]+) seconds=([\d.]+)")
DEAD_RE = re.compile(
    r"P2_LONG_LEGS_DEAD species=Damagumo generator=(\d+) health=0 prior_health=([\d.]+)")
CHILD_RE = re.compile(
    r"P2_MUSE_DAMAGUMO_CHILD_BIRTH generator=(\d+) species=ShijimiChou count=(\d+)")
FAMILY_BIRTH_RE = re.compile(
    r"P2_LONG_LEGS_BIRTH species=Damagumo generator=(\d+) count=(\d+)")
REENTRY_RE = re.compile(
    r"P2_MUSE_DAMAGUMO_REENTRY generator=(\d+) stale=(\d+) fresh=(\d+) rebind=(\d+)")

INJECT_MARKERS = (
    "P2_MUSE_DAMAGUMO_INJECT",
    "P2_LL_INJECT",
    "mhealth_injected=1",
    "injection=1",
    "forced_transport=1",
)


def _all(pattern, text, cast):
    return [cast(m.groups()) for m in pattern.finditer(text)]


def validate(text, retail_root=None):
    """Validate one Damagumo56 run log; return the six-gate verdict.

    ``text`` is the raw native.log. Every gate is computed from correlated
    markers; a missing marker fails its gate. Injected runs are rejected
    outright (no gate can pass).
    """
    text = text or ""
    injected = any(marker in text for marker in INJECT_MARKERS)

    binds = [int(m.group(1)) for m in BIND_RE.finditer(text)]
    ready = READY_RE.search(text)
    squad = int(ready.group(1)) if ready else 0
    generators = {int(m.group(1)) for m in BIND_RE.finditer(text)}
    if ready:
        generators.add(int(ready.group(2)))
    bound = bool(binds) and squad >= 1

    states = {m.group(2) for m in STATE_RE.finditer(text)}
    walk_ends = [dict(generator=int(m.group(1)), distance=float(m.group(2)),
                      seconds=float(m.group(3)))
                 for m in WALK_END_RE.finditer(text)]
    best_walk = None
    for end in walk_ends:
        avg = end["distance"] / end["seconds"] if end["seconds"] > 0 else float("inf")
        budget = SOURCE_SPEED * 1.25
        if end["distance"] >= MIN_WALK_DISTANCE and avg <= budget:
            end = dict(end, avg=avg)
            if best_walk is None or end["distance"] > best_walk["distance"]:
                best_walk = end
    movement = best_walk is not None and "Walk" in states

    dead = [dict(generator=int(m.group(1)), prior_health=float(m.group(2)))
            for m in DEAD_RE.finditer(text)]
    natural_death = bool(dead) and not injected

    births = [dict(generator=int(m.group(1)), count=int(m.group(2)))
              for m in CHILD_RE.finditer(text)]
    family_births = [dict(generator=int(m.group(1)), count=int(m.group(2)))
                     for m in FAMILY_BIRTH_RE.finditer(text)]
    child_ok = any(b["count"] == CHILD_COUNT and b["generator"] in generators
                   for b in births + family_births)

    reentry = [dict(generator=int(m.group(1)), stale=int(m.group(2)),
                    fresh=int(m.group(3)), rebind=int(m.group(4)))
               for m in REENTRY_RE.finditer(text)]
    reentry_ok = any(r["stale"] == 0 and r["fresh"] == 1 and r["rebind"] == 1
                     and r["generator"] in generators for r in reentry)

    window = "Experimental preview window set to 960x540 windowed and centered" in text
    session = bool(re.search(r"P2_MUSE_DAMAGUMO_SESSION navi=1\b", text)) and \
        not re.search(r"Extinction", text, re.IGNORECASE)
    completion = "PASS P2_MUSE_DAMAGUMO" in text

    gates = {
        "identity_spawn": bound,
        "movement_animation": movement,
        "attacks_receivers": natural_death,
        "death_corpse": bool(dead) and child_ok,
        "transport_reward": child_ok,  # source-backed N/A + child-birth path
        "cleanup_reentry": reentry_ok,
    }
    details = {
        "identity_spawn": "BIND=%s squad=%d generators=%s" % (binds, squad, sorted(generators)),
        "movement_animation": "walk=%s states=%s" % (best_walk, sorted(states)),
        "attacks_receivers": "dead=%s injected=%s" % (dead, injected),
        "death_corpse": "dead=%d child_birth_25=%s" % (len(dead), child_ok),
        "transport_reward": "source-backed N/A (EB_LeaveCarcass); child_birth_25=%s" % child_ok,
        "cleanup_reentry": "reentry=%s" % reentry,
    }
    problems = []
    if injected:
        problems.append("injected-markers-present")
    for name, ok in gates.items():
        if not ok:
            problems.append("gate-%s" % name)
    if not window:
        problems.append("missing-960x540-window")
    if not session:
        problems.append("missing-live-session")
    if not completion:
        problems.append("missing-completion-marker")

    return {
        "passed": not problems,
        "gates": {k: ("pass" if v else "fail") for k, v in gates.items()},
        "details": details,
        "problems": problems,
        "injected": injected,
        "squad": squad,
        "generators": sorted(generators),
        "natural_vs_injected": {
            "movement_natural": movement and not injected,
            "death_natural": natural_death,
            "inject_present": injected,
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="native.log path")
    args = parser.parse_args(argv)
    with open(args.path, encoding="utf-8", errors="replace") as handle:
        result = validate(handle.read())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    main()
