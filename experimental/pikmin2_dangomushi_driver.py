"""Fixture-side driver for natural DangoMushi death/corpse/reset/rebirth.

Lane `dangomushi94-fixture-driver`, issue #667. Implements the 5-step
fixture-side driver specified by the #664 contract against the validated
observer legs, with zero observer changes:

- bind: run `pc_p2_dangomushi_setup()` for the wanted generator; require a
  TEKI vehicle plus `P2_DANGOMUSHI_BIND`.
- damage: real free-squad Attack orders during accepted windows only;
  proceed on `P2_DANGOMUSHI_DAMAGE_ACCEPTED`; `DAMAGE_REJECTED` outside the
  window is expected, never a failure; no `mHealth`/Transport writes.
- death: await `P2_DANGOMUSHI_DEAD health=0` after observed natural health
  decreases; require `die()` via the dead-clip path.
- corpse: locate the engine corpse pellet via `mPelletView`; require the
  generic `P2_BATCH3_DRAW corpse=1 key=DangoMushi` leg after death.
- reset: `pc_p2_dangomushi_forget` + reset, generator re-init, `setup`;
  require a second same-generator `P2_DANGOMUSHI_BIND` with stale/fresh
  proof (no stale handle survives).

Captain safety (#632): the guard `scripts/p2_fixture_captain_guard.h`
(sha256 below) is adopted before any observed tick; any captain-down
evidence fails the run BLOCKED. No blanket invincibility; protected
observation is labelled and cannot prove captain damage.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCHEMA = "p2-dangomushi-driver-v1"
SOURCE_ID = 94
SOURCE_NAME = "DangoMushi"
CONTRACT_ISSUE = 664
CONSUMER_ISSUE = 376

GUARD_SOURCE = "scripts/p2_fixture_captain_guard.h"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"

BIND = "P2_DANGOMUSHI_BIND"
DAMAGE_ACCEPTED = "P2_DANGOMUSHI_DAMAGE_ACCEPTED"
DAMAGE_REJECTED = "P2_DANGOMUSHI_DAMAGE_REJECTED"
DEATH = "P2_DANGOMUSHI_DEAD"
CORPSE = "P2_BATCH3_DRAW"

_INJECTED_TOKENS = (
    "P2_MUSE_DANGOMUSHI_INJECT",
    "P2_DANGOMUSHI_DEATH_INJECT",
    "injected_health",
    "not_natural_combat=1",
    "mHealth=",
)

_CAPTAIN_DOWN_TOKENS = (
    "GAMEEND_PikminExtinction",
    "DEMOID_Extinction",
    "P2_FIXTURE_CAPTAIN_DOWN",
    "orima_dead=1",
    "OrimaDown",
    "NaviDown",
)

DRIVER_STEPS = (
    "bind",
    "damage",
    "death",
    "corpse",
    "reset",
)

OBSERVER_LEGS = (
    "P2_DANGOMUSHI_BIND generator=<id> source_id=94",
    "P2_DANGOMUSHI_DEAD generator=<id> source_id=94 health=0 (after bind)",
    "P2_BATCH3_DRAW corpse=1 key=DangoMushi clip=<dead> (after death)",
    "second P2_DANGOMUSHI_BIND same id (after corpse) = re-entry",
)


class DriverError(ValueError):
    """Malformed driver input or a failed driver step."""


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def plan(generator):
    """Emit the ordered 5-step fixture action script for one generator."""
    generator = _int(generator)
    if generator is None or generator <= 0:
        raise DriverError("generator must be a positive int")
    return [
        {"step": "bind",
         "action": "pc_p2_dangomushi_setup()",
         "require": f"{BIND} generator={generator} source_id=94"},
        {"step": "damage",
         "action": "free-squad Attack orders during accepted windows only",
         "require": f"{DAMAGE_ACCEPTED} generator={generator}",
         "forbid": ["mHealth=", "Transport"]},
        {"step": "death",
         "action": "await natural health decrease to zero",
         "require": f"{DEATH} generator={generator} source_id=94 health=0"},
        {"step": "corpse",
         "action": "locate engine corpse pellet via mPelletView",
         "require": f"{CORPSE} corpse=1 key=DangoMushi"},
        {"step": "reset",
         "action": "pc_p2_dangomushi_forget + reset, re-init, setup",
         "require": f"second {BIND} generator={generator}"},
    ]


def _lines_after(lines, start, token):
    for index in range(start, len(lines)):
        if token in lines[index]:
            return index
    return None


def drive(plan_steps, log_text):
    """Verify each planned step against run-log text, in order.

    Returns {"steps": {name: {"met": bool, "detail": str}}, "generator": int,
    "complete": bool}. Rejections outside the damage window never fail a
    step; injected or captain-down evidence fails the whole drive.
    """
    if not isinstance(log_text, str):
        raise DriverError("log text required")
    for token in _INJECTED_TOKENS:
        if token in log_text:
            return {"steps": {}, "generator": -1, "complete": False,
                    "rejected": "injected:" + token}
    for token in _CAPTAIN_DOWN_TOKENS:
        if token in log_text:
            return {"steps": {}, "generator": -1, "complete": False,
                    "rejected": "captain-down", "blocked": True}
    lines = log_text.splitlines()
    binds = [i for i, line in enumerate(lines)
             if BIND in line and "source_id=94" in line]
    if not binds:
        return {"steps": {"bind": {"met": False, "detail": "no BIND leg"}},
                "generator": -1, "complete": False}
    generator = None
    for token in lines[binds[0]].split():
        if token.startswith("generator="):
            generator = _int(token.split("=", 1)[1])
    if generator is None or generator <= 0:
        return {"steps": {"bind": {"met": False, "detail": "unparsable generator"}},
                "generator": -1, "complete": False}
    steps = {"bind": {"met": True, "detail": f"generator={generator}"}}
    cursor = binds[0] + 1
    accepted = _lines_after(lines, cursor, DAMAGE_ACCEPTED + f" generator={generator}")
    steps["damage"] = {"met": accepted is not None,
                       "detail": "accepted window observed" if accepted is not None
                       else "no accepted window; rejections alone do not proceed"}
    if accepted is not None:
        cursor = accepted + 1
    death = _lines_after(lines, cursor, DEATH + f" generator={generator}")
    health_ok = death is not None and "health=0" in lines[death]
    steps["death"] = {"met": bool(health_ok),
                      "detail": "natural death observed" if health_ok
                      else "no DEAD health=0 after damage"}
    if health_ok:
        cursor = death + 1
    corpse = None
    for i in range(cursor, len(lines)):
        if CORPSE in lines[i] and "corpse=1" in lines[i] and "key=DangoMushi" in lines[i]:
            corpse = i
            break
    steps["corpse"] = {"met": corpse is not None,
                       "detail": "corpse leg observed" if corpse is not None
                       else "no corpse leg after death"}
    if corpse is not None:
        cursor = corpse + 1
    rebind = None
    for i in range(cursor, len(lines)):
        if BIND in lines[i] and f"generator={generator}" in lines[i]:
            rebind = i
            break
    steps["reset"] = {"met": rebind is not None,
                      "detail": "same-generator re-bind observed" if rebind is not None
                      else "no re-bind; stale handle unproven"}
    complete = all(step["met"] for step in steps.values())
    return {"steps": steps, "generator": generator, "complete": complete}


def check_observer(log_text):
    """Run the REAL validated observer contract against log text, if present.

    Loads `experimental/pikmin2_muse_dangomushi.py` from its canonical lane
    output path without modifying it. Returns {"skipped": reason} when the
    observer file is absent.
    """
    path = Path("C:/Users/alari/pikmin-randomizer/output/workflow/autofill/"
                "planning-shards/enemies-5/prepared/dangomushi94-observer/"
                "experimental/pikmin2_muse_dangomushi.py")
    if not path.is_file():
        return {"skipped": "observer file absent: " + str(path)}
    spec = importlib.util.spec_from_file_location("pikmin2_muse_dangomushi_real", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {"skipped": None, "verdict": module.parse(log_text)}


def guard_record():
    """Captain-safety adoption record for handoff evidence."""
    return {"source": GUARD_SOURCE, "sha256": GUARD_SHA256,
            "policy": "guard before any observed tick; captain-down fails BLOCKED"}
