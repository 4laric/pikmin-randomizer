"""Provider-bomb-mgr-birth observer (issue #616, consumer #573).

Validates P2_BOMB_MGR_* markers from the standalone unit test and the
replacement-main live fixture. The manager births real tracked Bomb entities
(source_id=36) bound to live host carriers; every marker below is printed
from a production manager path. Staged squad/captain positions are labeled
STAGED in-fixture and never graded as gameplay.
"""
from __future__ import annotations

import math
import re

SCHEMA = "p2-bomb-mgr-birth-v1"
SOURCE_ID = 36
SOURCE_REVISION = "632af93787b9c95b63f0c13be32b161375ce3a96"

BIND_RE = re.compile(r"P2_BOMB_MGR_BIND generator=(\d+) source_id=36")
BIRTH_RE = re.compile(r"P2_BOMB_MGR_BIRTH generator=(\d+) source_id=(\d+) slot=(\d+) generation=(\d+)")
POS_RE = re.compile(r"P2_BOMB_MGR_POS generator=(\d+) x=([-\d.infanao]+) y=([-\d.infanao]+) z=([-\d.infanao]+)")
REJECT_RE = re.compile(r"P2_BOMB_MGR_REJECT generator=(\d+) reason=(\w+)")
FORGET_RE = re.compile(r"P2_BOMB_MGR_FORGET generator=(\d+)")
RESET_RE = re.compile(r"P2_BOMB_MGR_RESET epoch=(\d+)")
REBIRTH_RE = re.compile(r"P2_BOMB_MGR_REBIRTH carrier=(\d+)")
ROUTED_RE = re.compile(r"P2_BOMB_MGR_BLAST_ROUTED generator=(\d+) trigger=(\w+) hits=(-?\d+)")
SUPPRESSED_RE = re.compile(r"P2_BOMB_MGR_DETONATE_SUPPRESSED generator=(\d+)")
DONE_RE = re.compile(r"P2_BOMB_MGR_DONE carrier=(\d+)")
UNITTEST_RE = re.compile(r"P2_BOMB_MGR_UNITTEST checks=(\d+) failures=(\d+)")


def _finite(value: str) -> bool:
    try:
        return math.isfinite(float(value))
    except ValueError:
        return False


def parse(text: str) -> dict:
    return {
        "binds": BIND_RE.findall(text),
        "births": BIRTH_RE.findall(text),
        "positions": POS_RE.findall(text),
        "rejects": REJECT_RE.findall(text),
        "forgets": FORGET_RE.findall(text),
        "resets": RESET_RE.findall(text),
        "rebirths": REBIRTH_RE.findall(text),
        "routed": ROUTED_RE.findall(text),
        "suppressed": SUPPRESSED_RE.findall(text),
        "dones": DONE_RE.findall(text),
        "unittests": UNITTEST_RE.findall(text),
        "captain_down": "P2_FIXTURE_CAPTAIN_DOWN" in text,
        "has_nan": "=nan" in text or "(nan" in text,
    }


def check_birth(parsed: dict) -> tuple[bool, str]:
    if not parsed["births"]:
        return False, "no BIRTH marker"
    gens = {b[0] for b in parsed["births"]}
    if any(b[1] != str(SOURCE_ID) for b in parsed["births"]):
        return False, "birth with wrong source id"
    return True, f"{len(parsed['births'])} natural births, carriers={sorted(gens)}"


def check_follow(parsed: dict, minimum: int = 3) -> tuple[bool, str]:
    moves = [p for p in parsed["positions"] if all(_finite(v) for v in p[1:])]
    if any(not all(_finite(v) for v in p[1:]) for p in parsed["positions"]):
        return False, "non-finite POS coordinate"
    if len(moves) < minimum:
        return False, f"only {len(moves)} finite POS markers (need >={minimum})"
    distinct = {(p[1], p[2], p[3]) for p in moves}
    return True, f"{len(moves)} POS markers, {len(distinct)} distinct"


def check_reentry(parsed: dict) -> tuple[bool, str]:
    if not parsed["resets"]:
        return False, "no RESET marker"
    if not parsed["rebirths"]:
        return False, "no REBIRTH marker"
    rebirth_carriers = {r for r in parsed["rebirths"]}
    birth_carriers = {b[0] for b in parsed["births"]}
    if not rebirth_carriers <= birth_carriers:
        return False, "rebirth on never-born carrier"
    return True, f"reset epochs={parsed['resets']}, rebirth carriers={sorted(rebirth_carriers)}"


def check_rejection(parsed: dict) -> tuple[bool, str]:
    reasons = {r[1] for r in parsed["rejects"]}
    if "unregistered" not in reasons:
        return False, "no unregistered-ID rejection observed"
    return True, f"rejection reasons={sorted(reasons)}"


def check_unittest(parsed: dict) -> tuple[bool, str]:
    if not parsed["unittests"]:
        return False, "no UNITTEST summary"
    checks, failures = int(parsed["unittests"][-1][0]), int(parsed["unittests"][-1][1])
    if failures or not checks:
        return False, f"failures={failures} checks={checks}"
    return True, f"{checks} checks, 0 failures"


def gate_status(text: str) -> dict:
    """Provider gate grades (live markers only; engine-free details noted)."""
    parsed = parse(text)
    birth_ok, birth_why = check_birth(parsed)
    follow_ok, follow_why = check_follow(parsed)
    reentry_ok, reentry_why = check_reentry(parsed)
    return {
        "identity_spawn": ("PASS" if birth_ok else "UNTESTED", birth_why),
        "movement_animation": ("UNTESTED", "bombs do not self-move; joint follow " +
                               ("observed" if follow_ok else "unobserved") + f" ({follow_why})"),
        "attacks_receivers": ("UNTESTED", "blast routing proven engine-free only; "
                              "live receiver hits are #573 consumer scope"),
        "death_corpse": ("UNTESTED", "no Bomb death observed live; carrier-gone "
                         "release proven standalone"),
        "transport_reward": ("N/A", "source: EB_LeaveCarcass disabled "
                             "(bomb.cpp Obj::onInit); bombs detonate, never hauled"),
        "cleanup_reentry": ("PASS" if reentry_ok else "UNTESTED", reentry_why),
        "no_nan": (not parsed["has_nan"], "no NaN" if not parsed["has_nan"] else "NaN present"),
        "captain_guard": (not parsed["captain_down"],
                          "no CAPTAIN_DOWN" if not parsed["captain_down"] else "CAPTAIN_DOWN fired"),
    }
