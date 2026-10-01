"""Yakushima4 floor-boundary checkpoint / persistence adapter (issue #784).

First bounded slice of the yakushima4 save/persistence work traced by the #779
pin-discovery handoff (e28c1c16) for downstream consumer
``shard-caves-yakushima-yakushima4-p1`` (#161). Tooling only: validates the
floor-boundary checkpoint write/read/validate sequence, persisted floor/roster
state and day/progression anchors against the landed #132 cave-save contract
(read-only). No engine edits, no runtime, no ledger/admission writes, no ADMIT.
All six arena gates stay UNTESTED.

Sources pinned read-only (from the #779 record):
  * cave-save contract: worktree commit 8aaf6cf6
      - engine/pc_port/pc_p2_cave_transfer.h:17-121  (wire format)
      - engine/pc_port/pc_p2_cave.cpp:123-169       (pc_p2_cave_checkpoint)
      - engine/tools/test_p2_cave_transfer.cpp      (schema asserts)
  * dayclock anchors: worktree commit 4fff74c7
      - singleGameSection.cpp:216 advanceDayCount
      - singleGameSection.cpp:183/:209 CaveDayEndState init/exec
      - mCaveSaveData / mCurrentCaveID / mCurrentFloor
  * surface session: worktree commit 7b6d25df (schema p2-surface-session-1)

Higher floors 2-5 and species admission are explicitly OUT of scope for this
slice: the contract parser itself only admits floor 1 or 2, and this adapter
refuses anything else with an exact blocker rather than guessing.
"""
import json
import math
import re
from pathlib import Path

SCHEMA = "p2-yakushima4-save-persistence-v1"

# --- #779 pin record (read-only contract pins) ------------------------------

ROOT_BASE = "36b868391e62cccf37d992aa2f796f3cc9c6dc31"
NATIVE_FLOOR1_PIN = "88188a1e3d687132baf4c2ab7c01b3c752ef4500"
DOWNSTREAM_CONSUMER = "shard-caves-yakushima-yakushima4-p1"

CONTRACT_PINS = {
    "cave_save": {
        "worktree_commit": "8aaf6cf6",
        "sections": {
            "wire_format": "pc_port/pc_p2_cave_transfer.h:17-121",
            "checkpoint_write": "pc_port/pc_p2_cave.cpp:123-169",
            "schema_asserts": "tools/test_p2_cave_transfer.cpp",
        },
    },
    "dayclock_anchors": {
        "worktree_commit": "4fff74c7",
        "sections": {
            "advance_day_count": "singleGameSection.cpp:216 advanceDayCount",
            "cave_day_end_state": "singleGameSection.cpp:183/:209 CaveDayEndState init/exec",
            "cave_progress": "mCaveSaveData/mCurrentCaveID/mCurrentFloor",
        },
    },
    "surface_session": {
        "worktree_commit": "7b6d25df",
        "sections": {"checker": "schema p2-surface-session-1 checker"},
    },
}

REQUIRED_CONTRACTS = ("cave_save", "dayclock_anchors", "surface_session")

# --- wire format (pc_p2_cave_transfer.h) ------------------------------------

P2_CAVE_MAX_SURVIVORS = 100
SUPPORTED_FLOORS = (1, 2)          # contract parser: floor != 1 && floor != 2 -> reject
OUT_OF_SCOPE_FLOORS = (3, 4, 5)    # higher floors: separate slice

# Species IDs and the minimum schema that can carry each (pc_p2_species_schema.h).
SPECIES_REQUIRED_SCHEMA = {0: 1, 1: 1, 2: 1, 3: 1, 4: 2, 5: 3}
SCHEMA_ENTRY_PREFIX = "P2_CAVE_ENTRY_"
SCHEMA_TRANSFER_PREFIX = "P2_CAVE_TRANSFER_"
_TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")


class SavePersistenceError(ValueError):
    """Fail-closed refusal: exact blocker recorded, nothing invented."""

    def __init__(self, blocker, detail=""):
        super().__init__((blocker + (": " + detail if detail else "")))
        self.blocker = blocker
        self.detail = detail


def _blocker(blocker, detail=""):
    return {"blocker": blocker, "detail": detail}


# --- pin record validation --------------------------------------------------


def _pin40(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise SavePersistenceError("invalid-pin", "%s must be a 40-hex pin, got %r" % (label, value))
    return value


def validate_pin_record(record):
    """Validate a #779-style pin record fail-closed.

    Requires the three landed #132 contracts, each with at least one nonempty
    section, and records the pins/sections exactly. Missing contract, missing
    section, or malformed input is refused with an exact blocker.
    """
    if not isinstance(record, dict):
        raise SavePersistenceError("malformed-record", "pin record must be a mapping")
    for key in ("root_base", "native_floor1_pin", "downstream", "contracts"):
        if key not in record:
            raise SavePersistenceError("missing-section", "pin record lacks %r" % key)
    _pin40(record["root_base"], "root_base")
    _pin40(record["native_floor1_pin"], "native_floor1_pin")
    if record["downstream"] != DOWNSTREAM_CONSUMER:
        raise SavePersistenceError("absent-provider", "downstream must be " + DOWNSTREAM_CONSUMER)
    contracts = record["contracts"]
    if not isinstance(contracts, dict):
        raise SavePersistenceError("malformed-record", "contracts must be a mapping")
    for name in REQUIRED_CONTRACTS:
        entry = contracts.get(name)
        if not isinstance(entry, dict):
            raise SavePersistenceError("missing-section", "contract %r absent" % name)
        commit = entry.get("worktree_commit")
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{7,40}", commit):
            raise SavePersistenceError("invalid-pin", "contract %r commit malformed" % name)
        sections = entry.get("sections")
        if not isinstance(sections, dict) or not sections or not all(
                isinstance(k, str) and isinstance(v, str) and v.strip() for k, v in sections.items()):
            raise SavePersistenceError("missing-section", "contract %r sections empty" % name)
    return {"schema": SCHEMA, "validated": True,
            "contracts": sorted(REQUIRED_CONTRACTS),
            "downstream": DOWNSTREAM_CONSUMER}


def default_pin_record():
    """The #779 record as landed (embedded, so this slice is self-contained)."""
    return {"root_base": ROOT_BASE, "native_floor1_pin": NATIVE_FLOOR1_PIN,
            "downstream": DOWNSTREAM_CONSUMER,
            "contracts": {name: dict(CONTRACT_PINS[name]) for name in REQUIRED_CONTRACTS}}


def load_pin_record(path):
    """Read an external pin record; refuse absent/malformed input."""
    p = Path(path)
    if not p.is_file():
        raise SavePersistenceError("absent-provider", "pin record file missing: %s" % path)
    try:
        body = json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise SavePersistenceError("malformed-record", "unreadable pin record: %s" % exc) from None
    return validate_pin_record(body)


# --- wire format parse / format ---------------------------------------------


def validate_checkpoint_text(text):
    """Parse a P2_CAVE_ENTRY_/TRANSFER_ payload per the #132 wire format.

    Returns the decoded record. Refuses unknown schema, bad token, unsupported
    floor, bad health/count, unsupported species for the schema, bad maturity
    and trailing data with the same clause names the engine reports.
    """
    if not isinstance(text, str) or not text.strip():
        raise SavePersistenceError("header", "checkpoint text required")
    lines = text.splitlines()
    header = lines[0].split() if lines else []
    if not header:
        raise SavePersistenceError("header", "empty header")
    direction = None
    schema = None
    version = header[0]
    for prefix, name in ((SCHEMA_ENTRY_PREFIX, "entry"), (SCHEMA_TRANSFER_PREFIX, "transfer")):
        if version.startswith(prefix):
            direction = name
            suffix = version[len(prefix):]
            schema = int(suffix) if suffix.isdigit() else -1
            break
    if direction is None:
        raise SavePersistenceError("header", "unknown header %r" % version)
    if schema not in (1, 2, 3):
        raise SavePersistenceError("header", "unknown schema version %r" % version)
    if len(lines) < 3:
        raise SavePersistenceError("header", "truncated checkpoint")
    token = lines[1].strip()
    if not _TOKEN_RE.fullmatch(token):
        raise SavePersistenceError("header", "bad token")
    fields = lines[2].split()
    if len(fields) != 3:
        raise SavePersistenceError("header", "malformed header row")
    try:
        floor = int(fields[0])
        health = float(fields[1])
        count = int(fields[2])
    except ValueError:
        raise SavePersistenceError("header", "non-numeric header field") from None
    if floor in OUT_OF_SCOPE_FLOORS:
        raise SavePersistenceError("out-of-scope-floor",
                                   "floor %d is a higher-floor slice, not floor-1+" % floor)
    if not (floor in SUPPORTED_FLOORS and math.isfinite(health) and 0 < health <= 1
            and 1 <= count <= P2_CAVE_MAX_SURVIVORS):
        raise SavePersistenceError("header", "floor/health/count out of range")
    if len(lines) != 3 + count:
        raise SavePersistenceError("trailing data", "row count does not match survivor count")
    squad = []
    for line in lines[3:]:
        parts = line.split()
        if len(parts) != 2:
            raise SavePersistenceError("Pikmin", "malformed survivor row")
        try:
            species, maturity = int(parts[0]), int(parts[1])
        except ValueError:
            raise SavePersistenceError("Pikmin", "non-numeric survivor") from None
        required = SPECIES_REQUIRED_SCHEMA.get(species)
        if required is None or required > schema or not (0 <= maturity <= 2):
            raise SavePersistenceError("Pikmin", "species/maturity unsupported by schema %d" % schema)
        squad.append({"species": species, "maturity": maturity})
    return {"schema": schema, "direction": direction, "token": token, "floor": floor,
            "health": health, "count": count, "squad": squad}


def transfer_schema(entry_schema, squad):
    """Write schema is bumped to the newest carried species, never downgraded."""
    write = entry_schema
    for s in squad:
        required = SPECIES_REQUIRED_SCHEMA.get(s["species"])
        if required is None:
            raise SavePersistenceError("Pikmin", "unknown species %r" % s["species"])
        if required > write:
            write = required
    return write


def format_floor_boundary_transfer(entry):
    """Render the floor-boundary transfer exactly as the engine writes it.

    ``entry`` needs token/floor/health/squad (schema optional; defaults to 1).
    """
    if not isinstance(entry, dict):
        raise SavePersistenceError("header", "entry mapping required")
    token = entry.get("token")
    if not isinstance(token, str) or not _TOKEN_RE.fullmatch(token):
        raise SavePersistenceError("header", "bad token")
    floor = entry.get("floor")
    if floor not in SUPPORTED_FLOORS:
        raise SavePersistenceError("out-of-scope-floor" if floor in OUT_OF_SCOPE_FLOORS else "header",
                                   "floor %r unsupported for this slice" % (floor,))
    health = entry.get("health")
    if not isinstance(health, (int, float)) or not math.isfinite(health) or not 0 < health <= 1:
        raise SavePersistenceError("header", "health out of range")
    squad = entry.get("squad")
    if not isinstance(squad, list) or not 1 <= len(squad) <= P2_CAVE_MAX_SURVIVORS:
        raise SavePersistenceError("header", "survivor count out of range")
    write = transfer_schema(int(entry.get("schema", 1)), squad)
    lines = [SCHEMA_TRANSFER_PREFIX + str(write), token,
             "%d %.9g %d" % (floor, health, len(squad))]
    for s in squad:
        lines.append("%d %d" % (s["species"], s["maturity"]))
    return "\n".join(lines) + "\n"


# --- floor/roster state and day anchors -------------------------------------


def validate_floor_boundary_state(state):
    """Validate persisted floor/roster state fail-closed.

    Requires a floor id in the supported range, a nonempty living-squad census
    whose size matches the declared count, and a NAV topology reference (rooms
    and links recorded from the #161 traversal evidence).
    """
    if not isinstance(state, dict):
        raise SavePersistenceError("malformed-state", "floor state must be a mapping")
    floor = state.get("floor_id")
    if floor in OUT_OF_SCOPE_FLOORS:
        raise SavePersistenceError("out-of-scope-floor",
                                   "floor %d is a higher-floor slice" % floor)
    if floor not in SUPPORTED_FLOORS:
        raise SavePersistenceError("malformed-state", "floor_id %r unsupported" % (floor,))
    squad = state.get("squad")
    if not isinstance(squad, list) or not squad:
        raise SavePersistenceError("malformed-state", "living-squad census required")
    if state.get("census") != len(squad):
        raise SavePersistenceError("malformed-state", "census does not match squad rows")
    for s in squad:
        if not isinstance(s, dict) or s.get("species") not in SPECIES_REQUIRED_SCHEMA:
            raise SavePersistenceError("malformed-state", "bad squad row")
    nav = state.get("nav_topology")
    if (not isinstance(nav, dict) or not isinstance(nav.get("rooms"), int) or nav["rooms"] < 1
            or not isinstance(nav.get("links"), int) or nav["links"] < 1):
        raise SavePersistenceError("malformed-state", "NAV topology reference (rooms/links) required")
    return {"floor_id": floor, "census": len(squad), "nav_topology": {"rooms": nav["rooms"], "links": nav["links"]}}


def validate_day_anchors(anchors):
    """Validate day/progression anchors fail-closed (day clock + cave progress)."""
    if not isinstance(anchors, dict):
        raise SavePersistenceError("malformed-anchors", "day anchors must be a mapping")
    day_count = anchors.get("day_count")
    if not isinstance(day_count, int) or day_count < 1 or day_count > 29:
        # The engine calendar repeats day 29 to stay inside the 30-entry diary.
        raise SavePersistenceError("malformed-anchors", "day_count must be 1..29")
    cave_id = anchors.get("mCurrentCaveID")
    if not isinstance(cave_id, str) or not cave_id.strip():
        raise SavePersistenceError("malformed-anchors", "mCurrentCaveID required")
    floor = anchors.get("mCurrentFloor")
    if floor not in SUPPORTED_FLOORS:
        raise SavePersistenceError("out-of-scope-floor" if floor in OUT_OF_SCOPE_FLOORS else "malformed-anchors",
                                   "mCurrentFloor %r unsupported" % (floor,))
    if anchors.get("cave_day_end_state") not in ("init", "exec"):
        raise SavePersistenceError("malformed-anchors", "CaveDayEndState init/exec required")
    if anchors.get("cave_save_data") not in ("present", "empty"):
        raise SavePersistenceError("malformed-anchors", "mCaveSaveData state required")
    return {"day_count": day_count, "mCurrentCaveID": cave_id, "mCurrentFloor": floor,
            "cave_day_end_state": anchors["cave_day_end_state"],
            "cave_save_data": anchors["cave_save_data"]}


# --- assembled audit --------------------------------------------------------


def audit_floor_boundary(record, checkpoint_text, state, anchors):
    """Assemble the fail-closed floor-boundary checkpoint audit.

    Validates the pin record, the checkpoint wire text, floor/roster state and
    day anchors, and refuses on the first exact blocker. Returns the validated
    persistence plan plus the contract citations.
    """
    pinned = validate_pin_record(record)
    parsed = validate_checkpoint_text(checkpoint_text)
    floor_state = validate_floor_boundary_state(state)
    day = validate_day_anchors(anchors)
    if parsed["floor"] != floor_state["floor_id"] or parsed["floor"] != day["mCurrentFloor"]:
        raise SavePersistenceError("mismatched-floor", "checkpoint/state/anchors disagree on floor")
    if parsed["count"] != floor_state["census"]:
        raise SavePersistenceError("mismatched-census", "checkpoint count and state census disagree")
    return {"schema": SCHEMA, "pinned": pinned, "checkpoint": parsed,
            "floor_state": floor_state, "day_anchors": day,
            "citations": {name: CONTRACT_PINS[name]["sections"] for name in REQUIRED_CONTRACTS},
            "limitations": ["Floor-1+ only; higher floors 2-5 and species admission are out of scope.",
                            "Tooling only: no engine change, no runtime claim, all arena gates UNTESTED."]}


def blockers(record=None, checkpoint_text=None, state=None, anchors=None):
    """Collect exact blockers for malformed/missing inputs instead of raising."""
    out = []
    checks = (
        ("pin-record", record if record is not None else default_pin_record(), validate_pin_record),
        ("checkpoint", checkpoint_text, validate_checkpoint_text),
        ("floor-state", state, validate_floor_boundary_state),
        ("day-anchors", anchors, validate_day_anchors),
    )
    for label, value, fn in checks:
        if value is None:
            out.append(_blocker("absent-provider", label + " input missing"))
            continue
        try:
            fn(value)
        except SavePersistenceError as exc:
            out.append(_blocker(exc.blocker, exc.detail))
    return out
