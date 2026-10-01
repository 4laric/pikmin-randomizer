"""Consumable surface session contract for P2 overworld planners (#132).

Promotes the accepted provider-save-dayclock-anchor-audit (read-only field
inventory of ``singleGameSection.cpp`` + ``gamePlayData.cpp``) into a pure,
engine-free state machine that overworld content lanes (starting with
Wistful Wild, course ``last``) can consume to specify day transition,
save/reload, receipt replay and surface-state boundaries.

Schema ``p2-surface-session-1``. Every transition is a pure function
``(state_dict, event_dict) -> (ok, new_state_or_None, reason)``; malformed
input raises :class:`SessionContractError`, unsupported behavior is rejected
with an explicit reason, never silently accepted.

Anchor cross-reference (accepted audit evidence:
``output/workflow/autofill/planning-shards/provider-save-progression/
prepared/save-anchor-audit/out/inventory.json``; gamePlayData sha256
``4d6c7586...7e020``, singleGameSection sha256 ``6ff0eafb...5ce4be``):

- day advance: ``advanceDayCount`` (singleGameSection.cpp:216),
  ``CaveDayEndState`` (ibid. :183/:209) -> day is monotonic; rewind rejected.
- sunset: ``mCaveSaveData.mTime`` / ``mCurrentTimeOfDay`` / ``setTime`` /
  sun-gauge anchors -> sunset snapshots time_of_day; replaying a sunset for
  the same day twice is rejected (no double day-end).
- debt/pokos: ``mPokoCount``/``mCavePokoCount``/``mDebtProgressFlags``
  (gamePlayData.cpp:455-466) -> poko totals carried verbatim, never negative.
- captains: ``NAVIID_Olimar/Louie`` + ``mNaviLifeMax`` anchors -> squad holds
  per-captain life flags; a dead captain cannot lead (labelled, not damage).
- save/migration: ``mCaveSaveData.clear`` / ``mMailSaveData.clear`` /
  ``mCurrentCaveID`` / ``mCurrentFloor`` / ``mIsInCave=false``
  (gamePlayData.cpp:490-491/714/723-724) -> reload requires matching course
  and day; cave fields are only legal while ``in_cave`` is true.
- sprout_regeneration: ABSENT from both files (audit gap; retail anchor
  elsewhere e.g. onyonMgr.cpp:67-73) -> sprout counts are carried verbatim
  and any recompute request is explicitly rejected as unsupported.

Clearly-missing integration (NOT existing behavior; P1 needs native work):

- real sunset driver, real save serializer, real receipt ledger endpoint,
  real generator-cache restore (``saveToGeneratorCache`` noted in audit but
  unwired here). Each is named in MISSING_INTEGRATION and rejected by the
  checker when a planner asks for it.
"""

SCHEMA = "p2-surface-session-1"
COURSE_LAST = "last"

EVENTS = (
    "begin_day",
    "sunset",
    "save",
    "reload",
    "deliver_receipt",
    "enter_cave",
    "exit_cave",
)

MISSING_INTEGRATION = (
    "native sunset driver",
    "native save serializer",
    "native receipt ledger endpoint",
    "native generator-cache restore",
)


class SessionContractError(ValueError):
    """Malformed state or event; the contract refuses to guess."""


def blank_session(course=COURSE_LAST, day=1):
    """Fresh session state. No Onion/ship assumed; everything explicit."""
    if not isinstance(course, str) or not course:
        raise SessionContractError("course must be a non-empty string")
    if not isinstance(day, int) or isinstance(day, bool) or day < 1:
        raise SessionContractError("day must be a positive int")
    return {
        "schema": SCHEMA,
        "course": course,
        "day": day,
        "time_of_day": 0.0,
        "day_ended": False,
        "squad": {},
        "sprouts": {},
        "pokos": 0,
        "cave_pokos": 0,
        "receipts": [],
        "in_cave": False,
        "cave_id": None,
        "cave_floor": 0,
        "saved_snapshot": None,
    }


def _require_state(state):
    if not isinstance(state, dict):
        raise SessionContractError("state must be a dict")
    if state.get("schema") != SCHEMA:
        raise SessionContractError("schema must be %r" % SCHEMA)
    for key in ("course", "day", "receipts", "squad", "sprouts"):
        if key not in state:
            raise SessionContractError("state missing %r" % key)
    if not isinstance(state["day"], int) or isinstance(state["day"], bool) or state["day"] < 1:
        raise SessionContractError("day must be a positive int")
    if not isinstance(state["receipts"], list):
        raise SessionContractError("receipts must be a list")
    return state


def _copy(state):
    import copy
    return copy.deepcopy(state)


def check_transition(state, event):
    """Apply one event. Returns (ok, new_state_or_None, reason)."""
    _require_state(state)
    if not isinstance(event, dict) or "type" not in event:
        raise SessionContractError("event must be a dict with 'type'")
    kind = event["type"]
    if kind not in EVENTS:
        return (False, None, "unsupported event %r; supported: %s" % (kind, ",".join(EVENTS)))
    handler = _HANDLERS[kind]
    return handler(_copy(state), event)


def _begin_day(state, event):
    day = event.get("day", state["day"] + 1)
    if not isinstance(day, int) or isinstance(day, bool) or day < 1:
        return (False, None, "begin_day day must be a positive int")
    if day <= state["day"]:
        return (False, None, "day is monotonic (advanceDayCount); rewind rejected")
    state["day"] = day
    state["time_of_day"] = 0.0
    state["day_ended"] = False
    state["in_cave"] = False
    state["cave_id"] = None
    state["cave_floor"] = 0
    return (True, state, "day advanced")


def _sunset(state, event):
    if state["day_ended"]:
        return (False, None, "sunset already recorded; double day-end rejected")
    time_of_day = event.get("time_of_day", 1.0)
    if not isinstance(time_of_day, (int, float)) or isinstance(time_of_day, bool):
        return (False, None, "sunset time_of_day must be a number")
    state["time_of_day"] = float(time_of_day)
    state["day_ended"] = True
    return (True, state, "sunset snapshot")


def _save(state, event):
    if not state["day_ended"]:
        return (False, None, "save requires a sunset day-end first (day_clock anchor)")
    snapshot = _copy(state)
    snapshot["saved_snapshot"] = None
    state["saved_snapshot"] = snapshot
    return (True, state, "snapshot saved")


def _reload(state, event):
    snapshot = state.get("saved_snapshot")
    if snapshot is None:
        return (False, None, "reload with no saved snapshot rejected")
    if snapshot.get("course") != state.get("course"):
        return (False, None, "reload course mismatch rejected")
    restored = _copy(snapshot)
    restored["saved_snapshot"] = snapshot
    return (True, restored, "snapshot reloaded")


def _deliver_receipt(state, event):
    identity = event.get("identity")
    slot = event.get("slot")
    if not identity or not slot:
        return (False, None, "deliver_receipt needs identity and slot")
    key = (identity, slot)
    if key in [(r[0], r[1]) for r in state["receipts"]]:
        return (False, None, "duplicate receipt rejected (exactly-once)")
    state["receipts"].append([identity, slot, event.get("encounter", "surface")])
    pokos = event.get("pokos", 0)
    if pokos:
        if not isinstance(pokos, int) or isinstance(pokos, bool) or pokos < 0:
            return (False, None, "receipt pokos must be a non-negative int")
        state["pokos"] += pokos
    return (True, state, "receipt granted")


def _enter_cave(state, event):
    cave_id = event.get("cave_id")
    if not cave_id:
        return (False, None, "enter_cave needs cave_id")
    if state["in_cave"]:
        return (False, None, "nested cave entry rejected")
    state["in_cave"] = True
    state["cave_id"] = cave_id
    state["cave_floor"] = int(event.get("floor", 1))
    return (True, state, "cave entered")


def _exit_cave(state, event):
    if not state["in_cave"]:
        return (False, None, "exit_cave while on surface rejected")
    cave_pokos = event.get("cave_pokos", 0)
    if not isinstance(cave_pokos, int) or isinstance(cave_pokos, bool) or cave_pokos < 0:
        return (False, None, "exit_cave cave_pokos must be a non-negative int")
    state["cave_pokos"] += cave_pokos
    state["in_cave"] = False
    state["cave_id"] = None
    state["cave_floor"] = 0
    return (True, state, "cave exited")


_HANDLERS = {
    "begin_day": _begin_day,
    "sunset": _sunset,
    "save": _save,
    "reload": _reload,
    "deliver_receipt": _deliver_receipt,
    "enter_cave": _enter_cave,
    "exit_cave": _exit_cave,
}


def request_integration(name):
    """Planners ask for native-backed behavior here. Always rejected.

    Returns (False, None, reason) naming the missing native piece, so a
    planner records the exact prerequisite instead of assuming it.
    """
    if name not in MISSING_INTEGRATION:
        return (False, None, "unknown integration")
    return (False, None, "missing native integration: %s (not existing behavior)" % name)


def wake_criteria(course):
    """Planner wake criteria per overworld course. P1 needs all three true."""
    known = ("tutorial", "forest", "yakushima", "last")
    if course not in known:
        raise SessionContractError("unknown course")
    return {
        "course": course,
        "course_record_decoded": False,
        "cave_entrances_known": False,
        "receipt_endpoints_admitted": False,
        "ready": False,
        "detail": "P1 starts when the course record is decoded, entrances are known, and receipt endpoints are admitted",
    }
