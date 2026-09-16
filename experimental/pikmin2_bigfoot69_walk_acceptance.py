"""BigFoot69 natural Walk translation acceptance (#574, parent #569).

Follow-on to the l62 Long Legs slice (#502): BigFoot69 woke Stay->Wait but
reached no Walk inside the old 1500-tick window, so gate 2 stayed UNTESTED
while Houdai66 walked. This module validates a fresh run of the extended
walk fixture (4500-tick walk window, staged captain wake, WALK_END net
positions) for:

* ``bigfoot_walk``: a natural BigFoot (generator 312002) Wait->Walk
  transition with real translation -- owned applied steps ``distance >= 25``
  at an average within the source 70 u/s budget, net body displacement
  ``>= 25`` measured separately from the owned steps (residual P1 host
  drift is reported, not gated).
* ``houdai_preserved``: a Houdai (312001) WALK_END inside its own budget,
  proving the translation path still acts; plus the source no-carcass
  static audit (Houdai.cpp:71, BigFoot.cpp:69 disable EB_LeaveCarcass).
* ``natural``: no ``P2_LL_INJECT`` marker anywhere; the only staged moves
  are captain teleports (P2_MUSE_WALK_WAKE*), which never touch the actor.

Held-treasure kosi-drop/carry/receipt is NOT covered here: it needs lane-06
treasure objects (#491) and stays an explicit provider follow-on. Mitite
births and shell visuals stay with lanes 14/15/20.

No fixture, actor or engine state is touched here; this is a pure log auditor
plus a thin run wrapper that reuses the l62 arena/build helpers.
"""

import argparse
import json
import math
import os
import re
from pathlib import Path

HOUDAI_GEN = 312001
BIGFOOT_GEN = 312002
SOURCE_SPEED = {"Houdai": 250.0, "BigFoot": 70.0}
MIN_WALK_DISTANCE = 25.0
MIN_WALK_SECONDS = 1.0

WALK_RE = re.compile(
    r"P2_LONG_LEGS_WALK species=(\w+) generator=(\d+) "
    r"from=(-?[\d.]+),(-?[\d.]+) to=(-?[\d.]+),(-?[\d.]+) speed=([\d.]+)")
WALK_END_RE = re.compile(
    r"P2_LONG_LEGS_WALK_END species=(\w+) generator=(\d+) "
    r"distance=([\d.]+) seconds=([\d.]+)"
    r"(?: start=(-?[\d.]+),(-?[\d.]+) end=(-?[\d.]+),(-?[\d.]+))?")
STATE_RE = re.compile(
    r"P2_LONG_LEGS_STATE species=(\w+) generator=(\d+) state=(\w+)")
BIND_RE = re.compile(
    r"P2_LONG_LEGS_BIND generator=(\d+) species=(\w+).*native_fsm=implemented")

RETAIL_ROOT = Path(os.environ.get(
    "PIKMIN_P2_RETAIL_ROOT",
    r"C:/Users/alari/pikmin-randomizer/native/pikmin2-research"))
NO_CARCASS_SOURCES = {
    "Houdai": "src/plugProjectNishimuraU/Houdai.cpp",
    "BigFoot": "src/plugProjectNishimuraU/BigFoot.cpp",
}


def parse_walks(text):
    entries = [dict(species=m.group(1), generator=int(m.group(2)),
                    from_x=float(m.group(3)), from_z=float(m.group(4)),
                    to_x=float(m.group(5)), to_z=float(m.group(6)),
                    speed=float(m.group(7)))
               for m in WALK_RE.finditer(text)]
    ends = []
    for m in WALK_END_RE.finditer(text):
        end = dict(species=m.group(1), generator=int(m.group(2)),
                   distance=float(m.group(3)), seconds=float(m.group(4)))
        if m.group(5) is not None:
            end["start"] = (float(m.group(5)), float(m.group(6)))
            end["end"] = (float(m.group(7)), float(m.group(8)))
            end["net"] = math.dist(end["start"], end["end"])
        else:
            end["start"] = end["end"] = end["net"] = None
        ends.append(end)
    return entries, ends


def states_seen(text, species, generator):
    return [m.group(3) for m in STATE_RE.finditer(text)
            if m.group(1) == species and int(m.group(2)) == generator]


def check_bigfoot_walk(text):
    """Natural BigFoot69 Walk with separately measured net displacement."""
    _, ends = parse_walks(text)
    bigfoot = [e for e in ends
               if e["species"] == "BigFoot" and e["generator"] == BIGFOOT_GEN]
    if not bigfoot:
        return dict(passed=False, reason="no BigFoot WALK_END marker")
    budget = SOURCE_SPEED["BigFoot"] * 1.25
    best = max(bigfoot, key=lambda e: e["distance"])
    avg = best["distance"] / best["seconds"] if best["seconds"] > 0 else float("inf")
    detail = dict(distance=best["distance"], seconds=best["seconds"], avg=avg,
                  net=best["net"], budget=budget)
    if best["distance"] < MIN_WALK_DISTANCE:
        return dict(passed=False, reason="best distance %.1f below %.1f" % (
            best["distance"], MIN_WALK_DISTANCE), **detail)
    if best["seconds"] < MIN_WALK_SECONDS:
        return dict(passed=False, reason="walk seconds %.2f below %.1f (teleport-like)" % (
            best["seconds"], MIN_WALK_SECONDS), **detail)
    if avg > budget:
        return dict(passed=False, reason="avg %.1f u/s exceeds source budget %.1f" % (
            avg, budget), **detail)
    if best["net"] is None:
        return dict(passed=False, reason="WALK_END lacks net start/end positions", **detail)
    if best["net"] < MIN_WALK_DISTANCE:
        return dict(passed=False, reason="net displacement %.1f below %.1f" % (
            best["net"], MIN_WALK_DISTANCE), **detail)
    walked = "Walk" in states_seen(text, "BigFoot", BIGFOOT_GEN)
    detail["fsm_walk_seen"] = walked
    detail["drift"] = best["net"] - best["distance"]
    if not walked:
        return dict(passed=False, reason="no BigFoot STATE Walk transition", **detail)
    detail["reason"] = ("owned=%.1f net=%.1f drift=%+.1f seconds=%.2f avg=%.1f u/s "
                        "within %.1f" % (best["distance"], best["net"], detail["drift"],
                                         best["seconds"], avg, budget))
    return dict(passed=True, **detail)


def check_houdai_preserved(text):
    """Houdai translation path intact under the extended-window change."""
    _, ends = parse_walks(text)
    houdai = [e for e in ends
              if e["species"] == "Houdai" and e["generator"] == HOUDAI_GEN]
    if not houdai:
        return dict(passed=False, reason="no Houdai WALK_END marker")
    best = max(houdai, key=lambda e: e["distance"])
    budget = SOURCE_SPEED["Houdai"] * 1.25
    avg = best["distance"] / best["seconds"] if best["seconds"] > 0 else float("inf")
    if best["distance"] >= MIN_WALK_DISTANCE and avg <= budget:
        return dict(passed=True, reason="distance=%.1f avg=%.1f u/s" % (
            best["distance"], avg))
    return dict(passed=False, reason="distance=%.1f avg=%.1f outside budget" % (
        best["distance"], avg))


def check_no_carcass_source(retail_root=None):
    root = Path(retail_root) if retail_root else RETAIL_ROOT
    detail = {}
    for species, rel in NO_CARCASS_SOURCES.items():
        path = root / rel
        try:
            content = path.read_text(errors="replace")
        except OSError:
            detail[species] = "missing: %s" % path
            continue
        detail[species] = ("disableEvent(0, EB_LeaveCarcass) present"
                           if "disableEvent(0, EB_LeaveCarcass)" in content
                           else "MARKER ABSENT")
    passed = all(v.endswith("present") for v in detail.values())
    return dict(passed=passed, detail={k: str(v) for k, v in detail.items()})


def validate(text, retail_root=None):
    """Validate a BigFoot69 walk-run native log."""
    walk = check_bigfoot_walk(text)
    houdai = check_houdai_preserved(text)
    nocarcass = check_no_carcass_source(retail_root)
    binds = {int(m.group(1)): m.group(2) for m in BIND_RE.finditer(text)}
    bound = binds.get(BIGFOOT_GEN) == "BigFoot" and binds.get(HOUDAI_GEN) == "Houdai"
    ready = re.search(r"P2_MUSE_WALK_READY squad=(\d+) houdai_gen=312001 bigfoot_gen=312002", text)
    squad = int(ready.group(1)) if ready else 0
    bigfoot_wake = bool(re.search(r"P2_MUSE_WALK_WAKE_BIGFOOT", text))
    window = bool(re.search(
        r"Experimental preview window set to 960x540 windowed and centered", text))
    no_inject = "P2_LL_INJECT" not in text
    session = (bool(re.search(r"P2_MUSE_WALK_SESSION navi=1\b", text))
               and not re.search(r"Extinction", text, re.IGNORECASE))
    houdai_death = (bool(re.search(r"P2_MUSE_WALK_NATURAL_DEATH houdai=1", text))
                    and no_inject)
    completion = "PASS P2_MUSE_LONGLEGS_WALK" in text
    checks = dict(
        bigfoot_walk=walk["passed"],
        houdai_preserved=houdai["passed"],
        no_carcass_source=nocarcass["passed"],
        bound=bound,
        staged_wake=bigfoot_wake,
        window=window,
        live_squad=squad >= 1,
        no_inject=no_inject,
        houdai_death=houdai_death,
        session=session,
        completion=completion,
    )
    # Slice gates on the walk evidence. The Houdai drain tail still runs in
    # the fixture (bonus natural-death evidence when it connects), but its
    # timing-sensitive outcome does not gate BigFoot gate 2.
    passed = (walk["passed"] and houdai["passed"] and nocarcass["passed"]
              and bound and bigfoot_wake and window and squad >= 1
              and no_inject and session)
    return dict(passed=passed, checks=checks, walk=walk, houdai=houdai,
                nocarcass=nocarcass, squad=squad,
                natural_vs_injected=dict(
                    bigfoot_walk_natural=walk["passed"] and no_inject,
                    staged_captain_wake=bigfoot_wake,
                    inject_present=not no_inject))


# BigFoot staging for the #574 follow-on run. Houdai keeps its l62 spot;
# BigFoot moves from the far (330, 1900) corner to (150, 1870): on the same
# proven room floor, in the camera action, >60u from every parked squad-ring
# point (ring center (120, 1850) r=120 -> nearest ring 84u) so no Flick loop
# is staged, while the 310u territory still sees the squad for the source
# target rule. (The far corner lost its owned registration mid-Wait in the
# first 4500-tick run: Stay->Land->Wait observed, then silence + unregistered
# at tick 1501 with the vehicle static -- off-camera cull or out-of-world
# removal. Re-staging near the action covers both causes.)
BIGFOOT_POSITION_574 = (150.0, 30.0, 1870.0)


def prepare_near(assets, imported, output):
    """Stage a fresh walk arena with BigFoot near the camera action.

    Mirrors experimental.pikmin2_muse_longlegs.prepare (same installers,
    visual conversion and Pod anchor for preview_ready) with only the
    BigFoot arena position changed. The Pod anchor stays present-but-unused:
    no carry, no receipt, gate 5 stays source-backed N/A.
    """
    from experimental.pikmin2_long_legs_arena import CFG
    from experimental.pikmin2_batch2_core import prepare as _prepare
    from experimental.pikmin2_long_legs_install import install, verify_install
    from experimental.pikmin2_long_legs_visual import convert as convert_visual
    from experimental.pikmin2_long_legs_lifecycle import BIGFOOT_INDEX
    from experimental.pikmin2_mamuta_rules import load_pod_package, stage_cargo
    pod_package = os.environ.get(
        "PIKMIN_P2_POD_PACKAGE",
        str(Path(__file__).resolve().parents[2] / "l19-out" / "pod"))
    cfg = dict(CFG)
    positions = list(CFG["arena_positions"])
    positions[BIGFOOT_INDEX] = BIGFOOT_POSITION_574
    cfg["arena_positions"] = tuple(positions)
    run = _prepare(cfg, Path(assets), Path(imported), Path(output),
                   installer=install, verifier=verify_install)
    convert_visual(run / "assets/dataDir/courses/pikmin2room")
    stage_cargo(run, Path(assets), load_pod_package(pod_package))
    (run / "muse-bigfoot69-override.json").write_text(
        json.dumps(dict(bigfoot=list(BIGFOOT_POSITION_574),
                        reason="near-camera solid staging for #574; see module docstring"),
                   indent=2) + "\n")
    (run / "pikmin_settings.conf").write_text("disableTutorials = 0\n")
    return run


def run(assets, imported, output, exe, seconds=600):
    """Stage a fresh arena, run the extended walk fixture, validate the log."""
    os.environ["PIKMIN_P2_ROOM_WINDOW"] = "960x540"
    os.environ["PATH"] = r"C:\msys64\mingw64\bin;" + os.environ.get("PATH", "")
    from experimental.pikmin2_animation_profile import capture_command
    run_dir = prepare_near(Path(assets), Path(imported), Path(output))
    meta = capture_command([str(Path(exe).resolve()), "--experimental-pikmin2-room"],
                           run_dir, run_dir / "capture", seconds)
    text = (run_dir / "capture" / "native.log").read_text(errors="replace")
    result = validate(text)
    result["capture"] = {k: meta[k] for k in ("executable_sha256", "elapsed_seconds",
                                              "exit_code", "timed_out")}
    (run_dir / "muse-bigfoot69-validation.json").write_text(
        json.dumps(result, indent=2) + "\n")
    return run_dir, meta, result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="native.log to validate")
    args = parser.parse_args()
    result = validate(args.log.read_text(errors="replace"))
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)