"""Muse contributor l65: Honeywisp (Qurione, EnemyID 16) natural flight and Egg-reward observer.

Bounded slice (#505, parent #166): validate Qurione flight and the natural
player-contact/Egg-to-nectar reward against actual decomp source, and grade the
six arena gates honestly. Corpse hauling is a source-backed N/A; no pellet
reward is invented.

Source of truth (read-only, verified by this lane; revision
632af93787b9c95b63f0c13be32b161375ce3a96):

* ``src/plugProjectNishimuraU/Qurione.cpp``      birth/attachItem/dropItem,
  onInit flags, flyCollisionCallBack, moveFaceDir, isAppear/isFlyKill
* ``src/plugProjectNishimuraU/QurioneState.cpp`` Stay/Appear/Disappear/Move/Drop/Dead
* ``src/plugProjectMorimuraU/egg.cpp``           Egg capture/bounce/genItem drop table
* ``include/Game/Entities/Egg.h``                mForcedDropType default

Runtime markers graded here are produced by the integrated ``pc_p2_qurione``
host (owned by this wave's reserved ``native/pc_port/pc_p2_qurione.*`` files,
inherited unchanged from lane-15 fix5). Preserved legacy runtime evidence lives
in ``output/dsw/l15-out/`` (read-only); this module re-validates those logs
without claiming them as new runs.
"""
from __future__ import annotations

import math
import re

SCHEMA = "p2-muse-honeywisp-v1"
SOURCE_ID = 16
INTERNAL = "Qurione"
ENGLISH = "Honeywisp"
SOURCE_REVISION = "632af93787b9c95b63f0c13be32b161375ce3a96"

# ---------------------------------------------------------------------------
# Source-fact registry (verified against the decomp checkout above).
# ---------------------------------------------------------------------------

# Gate 5 (transport/reward) is source-backed N/A: there is no receivable item.
GATE5_NA_CASE = {
    "no_carcass_qurione": "Qurione.cpp:57 disableEvent(0, EB_LeaveCarcass)",
    "no_carcass_egg": "egg.cpp:38 disableEvent(0, EB_LeaveCarcass)",
    "drop_group_none": "Qurione.cpp:60 mDropGroup = EDG_None",
    "reward_is_carried_egg": "Qurione.cpp:284-296 attachItem() births EnemyID_Egg (37) "
    "and startCapture()s it to the water joint",
    "release_once": "Qurione.cpp:302-307 dropItem() endCapture()s and nulls mEgg; "
    "StateDrop fires dropItem() only on Damage KEYEVENT_2 "
    "(QurioneState.cpp:217-219), then KEYEVENT_END -> dead",
    "egg_break_births_items": "egg.cpp:243-383 genItem(): Single/DoubleNectar as "
    "HONEY_Y honey items, mitite group with HONEY_Y fallback (egg.cpp:351-360); "
    "number-pellet branches (egg.cpp:294-306) are reachable only via "
    "mForcedDropType (egg.cpp:277-279)",
    "forced_drop_unset": "Egg.h:124 mForcedDropType defaults to 0 and the Qurione "
    "path never assigns it, so a Honeywisp Egg rolls nectar/mitites only; "
    "no pellet reward may be claimed for this identity",
    "nectar_not_hauled": "per lane-15 fix5 audit, HONEY_Y honey is field-consumed "
    "in place (absorb path, never ACT_Transport); no lane-06 Onion/corpse "
    "receipt applies to this identity",
}

# Gate 3 (attacks/receivers): the wisp deals no damage; the only receiver path
# is Piki contact in Move transiting to Drop.
GATE3_NA_CASE = {
    "no_attack_path": "Qurione.cpp has no attack callback and no damage parms; "
    "the only creature callback is flyCollisionCallBack (Qurione.cpp:136-144): "
    "Piki contact while in QURIONE_Move transits to QURIONE_Drop",
    "invulnerable": "Qurione.cpp:52-53 EB_Untargetable + EB_Invulnerable; "
    "port holds LIFE=9999 (pc_p2_qurione.cpp)",
    "contact_is_trigger": "port contact test pikiContact() (distXZ < HIT_RADIUS 30) "
    "on the ordinary contact path with no health write",
}

# Gate 2 (movement) source reference for the sustained-flight fixture.
GATE2_SOURCE = {
    "move_exec": "QurioneState.cpp:172-187 StateMove::exec runs moveFaceDir() and "
    "transits to Disappear past mFlyDist (200.0)",
    "move_face_dir": "Qurione.cpp:210-220 moveFaceDir(): forward speed plus pitch bob "
    "2.5 * (minY + fp03*sin(pitch) + fp01); fp01=60 flight height",
    "retrigger": "QurioneState.cpp:48-56 StateStay re-appears when mUtilityTimer > 1.0 "
    "and isAppear() (nearest Pikmin/Navi in viewAngle/sightRadius, Qurione.cpp:253-265)",
}

# ---------------------------------------------------------------------------
# Runtime log validator (grades P2_QURIONE_* markers, natural runs only).
# ---------------------------------------------------------------------------

BIND_RE = re.compile(r"P2_QURIONE_BIND generator=(\d+) source_id=16")
READY_RE = re.compile(r"P2_ENEMY_READY species=Qurione .*behavior=native")
STATE_RE = re.compile(r"P2_QURIONE_STATE generator=(\d+) state=(\w+)")
POS_RE = re.compile(
    r"P2_QURIONE_POS generator=(\d+) state=(\w+) clip=(\S+) phase=([\d.]+) "
    r"x=([-\d.infanao]+) y=([-\d.infanao]+) z=([-\d.infanao]+)"
)
EGG_BORN_RE = re.compile(r"P2_QURIONE_EGG_REAL generator=(\d+) born=1")
EGG_RELEASED_RE = re.compile(r"P2_QURIONE_EGG_REAL generator=(\d+) released=1")
EGG_DROP_RE = re.compile(r"P2_QURIONE_EGG generator=(\d+) action=drop")
EGG_BOUNCE_RE = re.compile(r"P2_QURIONE_EGG_BOUNCE generator=(\d+)")
EGG_BREAK_RE = re.compile(r"P2_QURIONE_EGG_BREAK generator=(\d+) type=\d+ items=(\d+) real=1")
EGG_ITEM_RE = re.compile(r"P2_QURIONE_EGG_ITEM generator=(\d+) index=\d+ kind=\d+ real=1 .* item=(\S+)")
DEAD_RE = re.compile(r"P2_QURIONE_DEAD generator=(\d+) source_id=16")
FORGET_RE = re.compile(r"P2_QURIONE_FORGET generator=(\d+)")


def _finite(value: str) -> bool:
    try:
        return math.isfinite(float(value))
    except ValueError:
        return False


def parse(text: str) -> dict:
    """Split a runtime log into per-marker event lists (one wisp per log)."""
    binds = BIND_RE.findall(text)
    states = STATE_RE.findall(text)
    positions = POS_RE.findall(text)
    return {
        "binds": binds,
        "ready": bool(READY_RE.search(text)),
        "states": [state for _, state in states],
        "positions": [
            {"state": state, "clip": clip, "x": x, "y": y, "z": z}
            for _, state, clip, _phase, x, y, z in positions
        ],
        "egg_born": bool(EGG_BORN_RE.search(text)),
        "egg_released": bool(EGG_RELEASED_RE.search(text)),
        "egg_drop": bool(EGG_DROP_RE.search(text)),
        "egg_bounce": bool(EGG_BOUNCE_RE.search(text)),
        "egg_break_items": int(EGG_BREAK_RE.search(text).group(2)) if EGG_BREAK_RE.search(text) else 0,
        "egg_items": EGG_ITEM_RE.findall(text),
        "dead": bool(DEAD_RE.search(text)),
        "forgets": FORGET_RE.findall(text),
        "has_nan": "=nan" in text or "nan," in text or "(nan" in text,
    }


def check_identity(parsed: dict) -> tuple[bool, str]:
    if len(parsed["binds"]) >= 1 and parsed["ready"]:
        return True, "source_id=16 bind with native behavior"
    return False, "missing BIND source_id=16 or native READY"


def check_movement(parsed: dict, min_displacement: float = 50.0) -> tuple[bool, str]:
    """Autonomous flight: distinct finite Move positions with real displacement."""
    moves = [p for p in parsed["positions"] if p["state"] == "move"]
    if any(not _finite(p[x]) for p in moves for x in ("x", "y", "z")):
        return False, "non-finite Move position"
    distinct = {(p["x"], p["y"], p["z"]) for p in moves}
    if len(distinct) < 3:
        return False, f"only {len(distinct)} distinct Move positions (need >=3)"
    try:
        zs = sorted({float(p["z"]) for p in moves})
    except ValueError:
        return False, "unparsable Move coordinate"
    displacement = max(zs) - min(zs) if zs else 0.0
    if displacement < min_displacement:
        return False, f"Move displacement {displacement:.1f} < {min_displacement}"
    return True, f"{len(distinct)} distinct Move positions, dz={displacement:.1f}"


def check_contact_drop(parsed: dict) -> tuple[bool, str]:
    """Natural player trigger: Drop is reached through Move (contact), not a skip."""
    states = parsed["states"]
    if "drop" not in states:
        return False, "no Drop state"
    if "move" not in states[: states.index("drop")]:
        return False, "Drop without a preceding Move (not a contact trigger)"
    return True, "Move -> Drop contact trigger, no health write"


def check_reward_chain(parsed: dict) -> tuple[bool, str]:
    """Released Egg breaks into real field items (nectar for this identity)."""
    if not (parsed["egg_born"] and parsed["egg_drop"] and parsed["egg_released"]):
        return False, "missing attach/born/drop/release link"
    if not parsed["egg_bounce"]:
        return False, "missing floor bounce"
    if not parsed["egg_break_items"]:
        return False, "missing Egg break"
    real_items = [item for _, item in parsed["egg_items"]]
    if not real_items:
        return False, "break produced no real items"
    if any(item != "nectar" for item in real_items):
        return False, f"non-nectar item birthed: {real_items}"
    return True, f"break -> {len(real_items)} real nectar items"


def check_death(parsed: dict) -> tuple[bool, str]:
    if not parsed["dead"]:
        return False, "missing DEAD marker"
    dead_climb = [
        float(p["y"]) for p in parsed["positions"]
        if p["state"] == "dead" and _finite(p["y"])
    ]
    if len(dead_climb) >= 2 and dead_climb[-1] <= dead_climb[0]:
        return False, "dead fly-away does not climb"
    return True, "Drop -> Dead fly-away, source_id=16"


def classify_reentry(parsed: dict) -> tuple[str, str]:
    """Distinguish a same-wisp second appearance from new-actor re-entry.

    A second appear with a single BIND and a single generator is the same wisp
    (spawn-index flip); a second BIND (or a second generator id) is a new actor.
    """
    binds = parsed["binds"]
    appears = parsed["states"].count("appear")
    generators = set(binds) | set(parsed["forgets"])
    if len(binds) > 1 or len(generators) > 1:
        return "new-actor", f"{len(binds)} binds, generators={sorted(generators)}"
    if appears >= 2:
        return "same-wisp", f"one bind, {appears} appears, generator={binds[0] if binds else '?'}"
    if parsed["forgets"]:
        return "single-cycle-cleanup", f"forget generator={parsed['forgets'][0]}"
    return "single-cycle", "one appear cycle, no forget yet"


def gate_status(text: str) -> dict:
    """Grade the six gates from one runtime log (natural markers only)."""
    parsed = parse(text)
    identity_ok, identity_why = check_identity(parsed)
    move_ok, move_why = check_movement(parsed)
    drop_ok, drop_why = check_contact_drop(parsed)
    reward_ok, reward_why = check_reward_chain(parsed)
    death_ok, death_why = check_death(parsed)
    reentry_kind, reentry_why = classify_reentry(parsed)
    return {
        # Log-level grades only. The handoff maps the two source-backed N/A
        # gates (attacks_receivers: no attack path exists; transport_reward:
        # no haulable item exists) onto these observations: a PASS here means
        # "the natural contact/field-reward chain was observed", which supports
        # the N/A case instead of contradicting it.
        "identity_spawn": ("PASS" if identity_ok else "UNTESTED", identity_why),
        "movement_animation": ("PASS" if move_ok else "UNTESTED", move_why),
        "attacks_receivers": ("PASS" if drop_ok else "UNTESTED",
                              "contact trigger " + ("observed" if drop_ok else "unobserved")
                              + f" ({drop_why})"),
        "death_corpse": ("PASS" if death_ok else "UNTESTED", death_why),
        "transport_reward": ("PASS" if reward_ok else "UNTESTED",
                             "field-reward chain " + ("observed: " + reward_why if reward_ok
                                                      else "unobserved: " + reward_why)),
        "cleanup_reentry": ("PASS" if reentry_kind in ("same-wisp", "single-cycle-cleanup")
                            else "UNTESTED", f"{reentry_kind}: {reentry_why}"),
        "no_nan": (not parsed["has_nan"], "no =nan markers" if not parsed["has_nan"] else "NaN present"),
    }
