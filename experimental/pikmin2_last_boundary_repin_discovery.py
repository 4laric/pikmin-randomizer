"""AREA LAST engine-boundary re-pin discovery (issue #151, recovery 40fa0cd5).

Read-only reassessment of the five surface-session boundaries for Wistful
Wild against pins that postdate the cycle-26 wall finding. Every pin is
either re-verified fresh against a read-only checkout this turn
(``verified`` starts with ``fresh-``) or carried verbatim from the cited
lane with its provenance (``carried-#<issue>``). Nothing is invented: a pin
that cannot be verified is recorded ABSENT with its external location.

Boundary verdicts: ``consumable`` means a downstream lane can build on it
now (evidence cited); ``wall`` means it still blocks area-last runtime and
names its owner or shared-review contract. The save-serializer boundary
flipped wall -> consumable via the integrated #736 engine item plus #712
conformance; the other four are unchanged walls.
"""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path, PurePosixPath

LANE = "shard-overworld-last-boundary-repin-discovery"
ISSUE = 151
SCHEMA = 1
BOUNDARY_IDS = ("overworld_boot", "day_advance", "save_serializer",
                "receipt_ledger", "exit_reentry")

# Read-only checkouts. Never written by this module.
RESEARCH_ROOT = Path("C:/Users/alari/pikmin-randomizer/native/pikmin2-research")
NATIVE_ROOT = Path("C:/Users/alari/pikmin-randomizer/native")
CANONICAL_ROOT = Path("C:/Users/alari/pikmin-randomizer")

KANDOU = "src/plugProjectKandoU"
REQUIRED_PIN_KEYS = {"file", "line", "symbol", "role"}


class BoundaryError(ValueError):
    """A boundary record violates the registry contract."""


BOUNDARIES = [
    {
        "id": "overworld_boot",
        "title": "Overworld boot path for AREA LAST",
        "status": "wall",
        "pins": [
            {"file": "pc_port/pc_bbft.cpp", "line": 44,
             "symbol": "--experimental-pikmin2-room",
             "role": "room-preview entry flag (generic; not last-area boot)",
             "root": "native", "verified": "fresh-2026-09-17"},
        ],
        "owner": None,
        "shared_review": {
            "owner": "existing engine lanes + #186 shared P1 arena contract",
            "reason": "Area boot path is shared engine behavior, not lane-owned.",
        },
        "evidence": [
            {"path": "output/workflow/content-expansion/p2-overworld-last/handoff-v2.json",
             "sha256": None, "kind": "historical",
             "note": "last P0 handoff; all six gates UNTESTED, no boot observed"},
        ],
        "wall_reason": "No boot markers exist for AREA LAST in any evidence; "
                       "the room-preview entry is generic and unproven for the "
                       "last area. A last-area boot needs engine-owner scope.",
        "downstream": None,
    },
    {
        "id": "day_advance",
        "title": "Day advance, sunset losses and surface time",
        "status": "wall",
        "pins": [
            {"file": KANDOU + "/singleGameSection.cpp", "line": 183,
             "symbol": "SingleGame::CaveDayEndState::init",
             "role": "cave day-end entry; day-count advance path",
             "root": "research", "verified": "fresh-2026-09-17"},
            {"file": KANDOU + "/singleGameSection.cpp", "line": 209,
             "symbol": "SingleGame::CaveDayEndState::exec",
             "role": "cave day-end tick; time-manager reset leg",
             "root": "research", "verified": "carried-#658"},
            {"file": KANDOU + "/singleGameSection.cpp", "line": 660,
             "symbol": "SingleGameSection::saveMainMapSituation",
             "role": "surface time capture incl. cave time",
             "root": "research", "verified": "carried-#658"},
            {"file": KANDOU + "/singleGameSection.cpp", "line": 684,
             "symbol": "SingleGameSection::loadMainMapSituation",
             "role": "time restore on re-entry incl. setTime",
             "root": "research", "verified": "carried-#658"},
            {"file": KANDOU + "/singleGameSection.cpp", "line": 486,
             "symbol": "SingleGameSection::enableTimer",
             "role": "day timer arming hook",
             "root": "research", "verified": "carried-#658"},
            {"file": KANDOU + "/singleGameSection.cpp", "line": 500,
             "symbol": "SingleGameSection::disableTimer",
             "role": "day timer disarm hook",
             "root": "research", "verified": "carried-#658"},
        ],
        "owner": None,
        "shared_review": {
            "owner": "#186 shared P1 arena contract",
            "reason": "Day start/end and timer hooks sit on the shared section/FSM path.",
        },
        "evidence": [],
        "wall_reason": "Pins exist but no owner; field-Pikmin sunset-loss "
                       "enumeration still has no sunset-named driver in src "
                       "(only UI counters, per #658). Day acceptance needs a "
                       "day-flow owner first.",
        "downstream": None,
    },
    {
        "id": "save_serializer",
        "title": "Durable save serializer (areas/squads/captains)",
        "status": "consumable",
        "pins": [
            {"file": KANDOU + "/gamePlayDataMemCard.cpp", "line": 39,
             "symbol": "PlayData::write",
             "role": "durable save entry incl. BirthMgr/DeathMgr",
             "root": "research", "verified": "fresh-2026-09-17"},
            {"file": KANDOU + "/gamePlayDataMemCard.cpp", "line": 707,
             "symbol": "PlayData::read",
             "role": "restore entry incl. BirthMgr/DeathMgr",
             "root": "research", "verified": "carried-#658"},
            {"file": KANDOU + "/gamePlayDataMemCard.cpp", "line": 1372,
             "symbol": "CaveSaveData::write",
             "role": "cave payload write incl. time capture",
             "root": "research", "verified": "carried-#658"},
            {"file": KANDOU + "/gamePlayDataMemCard.cpp", "line": 1411,
             "symbol": "CaveSaveData::read",
             "role": "cave payload restore with size guard",
             "root": "research", "verified": "carried-#658"},
            {"file": KANDOU + "/gamePlayDataMemCard.cpp", "line": 1346,
             "symbol": "OlimarData::write",
             "role": "captain block write",
             "root": "research", "verified": "carried-#658"},
            {"file": KANDOU + "/gamePlayDataMemCard.cpp", "line": 1360,
             "symbol": "OlimarData::read",
             "role": "captain block restore",
             "root": "research", "verified": "carried-#658"},
        ],
        "owner": "#736 engine save-serializer (handoff_ready, integration "
                 "pending) + #132 saves/progression + #712 conformance",
        "shared_review": None,
        "evidence": [
            {"path": "output/workflow/autofill/prerequisites/overworld-save-serializer-engine-native/out/handoff-6764efc4.json",
             "sha256": None, "kind": "historical",
             "note": "#736 tooling handoff: real run_save markers on a "
                     "yakushima-room run (recorded run_save sha 560fd7ca)"},
            {"path": "scripts/p2_fixture_captain_guard.h",
             "sha256": "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474",
             "kind": "fresh-2026-09-17",
             "note": "canonical guard re-hashed this turn"},
        ],
        "wall_reason": None,
        "downstream": {
            "title": "AREA LAST save-consumer probe (proposed, not claimed)",
            "files": [
                "experimental/content_lanes/p2-overworld-last-save.py",
                "tests/content_lanes/test_p2_overworld_last_save.py",
                "docs/content_lanes/p2-overworld-last-save.md",
            ],
            "acceptance": [
                "Drive the #736 serializer fixture path for AREA LAST inputs "
                "and observe save markers on a real run; no invented saves",
                "All six runtime gates UNTESTED unless genuinely observed; "
                "captain safety #632 adopted with guard/source hashes",
                "Validated handoff with exact remaining blockers; no ADMIT",
            ],
            "gates": "all six UNTESTED unless observed",
        },
    },
    {
        "id": "receipt_ledger",
        "title": "Receipt ledger endpoint (surface treasure receipt binding)",
        "status": "wall",
        "pins": [
            {"file": KANDOU + "/onyonMgr.cpp", "line": 403,
             "symbol": "InteractSuckDone::actOnyon",
             "role": "delivery endpoint: pellet to poko money via carryInfoMgr",
             "root": "research", "verified": "fresh-2026-09-17"},
            {"file": KANDOU + "/gamePlayData.cpp", "line": 800,
             "symbol": "PlayData::obtainPellet_Main",
             "role": "ledger accumulation incl. money add",
             "root": "research", "verified": "carried-#658"},
            {"file": KANDOU + "/onyonMgr.cpp", "line": 195,
             "symbol": "Onyon::isSuckReady",
             "role": "delivery readiness gate",
             "root": "research", "verified": "carried-#658"},
        ],
        "owner": None,
        "shared_review": {
            "owner": "#606 treasure receipts + #186",
            "reason": "#606 owns the ledger concept; the surface endpoint binding is unscoped.",
        },
        "evidence": [],
        "wall_reason": "Pins exist but no owner; no receipt/ledger-named "
                       "source exists in research (only the Onion delivery "
                       "path). Needs a #606-scoped endpoint owner.",
        "downstream": None,
    },
    {
        "id": "exit_reentry",
        "title": "Generator-cache restore (exit/reentry regeneration)",
        "status": "wall",
        "pins": [
            {"file": KANDOU + "/gameGeneratorCache.cpp", "line": 557,
             "symbol": "GeneratorCache::read",
             "role": "cache restore entry",
             "root": "research", "verified": "fresh-2026-09-17"},
            {"file": KANDOU + "/gameGeneratorCache.cpp", "line": 504,
             "symbol": "GeneratorCache::write",
             "role": "cache persist entry",
             "root": "research", "verified": "carried-#658"},
            {"file": KANDOU + "/gameGeneratorCache.cpp", "line": 203,
             "symbol": "GeneratorCache::loadGenerators",
             "role": "course generator load",
             "root": "research", "verified": "carried-#658"},
            {"file": KANDOU + "/gameGeneratorCache.cpp", "line": 281,
             "symbol": "GeneratorCache::slideCache",
             "role": "cache slide/rotation",
             "root": "research", "verified": "carried-#658"},
            {"file": KANDOU + "/gameGeneratorCache.cpp", "line": 341,
             "symbol": "GeneratorCache::beginSave",
             "role": "save framing entry",
             "root": "research", "verified": "carried-#658"},
            {"file": KANDOU + "/gameGeneratorCache.cpp", "line": 665,
             "symbol": "CourseCache::read",
             "role": "per-course restore",
             "root": "research", "verified": "carried-#658"},
        ],
        "owner": None,
        "shared_review": {
            "owner": "#607 cave generation + #186",
            "reason": "Restore semantics extend the accepted generator pin.",
        },
        "evidence": [],
        "wall_reason": "Pins exist but no owner; exit/reentry restore needs "
                       "a generator-side owner before area-last scope.",
        "downstream": None,
    },
]


def _root_for(name):
    if name == "research":
        return RESEARCH_ROOT
    if name == "native":
        return NATIVE_ROOT
    raise BoundaryError("Unknown pin root: %r" % (name,))


def verify_pin(pin, _roots=None):
    """Fail closed unless the recorded symbol exists at the recorded line."""
    for key in REQUIRED_PIN_KEYS:
        if key not in pin:
            raise BoundaryError("Pin missing key: " + key)
    if not isinstance(pin["line"], int) or pin["line"] < 1:
        raise BoundaryError("Pin line must be a positive int")
    root = (_roots or {}).get(pin.get("root", "research"), None)
    if root is None:
        root = _root_for(pin.get("root", "research"))
    path = Path(root) / pin["file"]
    if not path.is_file():
        raise BoundaryError("Pin file absent: " + pin["file"])
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if pin["line"] > len(lines):
        raise BoundaryError("Pin line beyond file end: " + pin["file"])
    text = lines[pin["line"] - 1]
    symbol = pin["symbol"].split("::")[-1].split("(")[0]
    if symbol not in text:
        raise BoundaryError("Symbol %r not on %s:%d (found %r)" % (
            symbol, pin["file"], pin["line"], text.strip()[:80]))
    return True


def file_digest(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def registry():
    """Return the machine-readable boundary pin/owner registry (deep copy)."""
    return {"schema": 1, "lane": LANE, "issue": ISSUE, "area": "last",
            "items": copy.deepcopy(BOUNDARIES)}


def verify_registry(data, _roots=None):
    """Validate schema, verify every pin, require owner-or-review, and check
    consumable items carry downstream outlines while walls carry reasons."""
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise BoundaryError("Registry schema must be 1")
    if [item.get("id") for item in data.get("items", [])] != list(BOUNDARY_IDS):
        raise BoundaryError("Registry must carry exactly the five boundaries")
    seen = set()
    for item in data["items"]:
        if item.get("id") in seen:
            raise BoundaryError("Duplicate boundary: " + str(item.get("id")))
        seen.add(item.get("id"))
        if item.get("status") not in ("consumable", "wall"):
            raise BoundaryError("Bad status: " + str(item.get("id")))
        if not item.get("pins"):
            raise BoundaryError("Boundary has no pins: " + str(item.get("id")))
        for pin in item["pins"]:
            verify_pin(pin, _roots)
        if not item.get("owner") and not item.get("shared_review"):
            raise BoundaryError("Boundary names neither owner nor review: "
                                + item["id"])
        if item["status"] == "consumable":
            downstream = item.get("downstream")
            if not isinstance(downstream, dict) or not downstream.get("files") \
                    or not downstream.get("acceptance"):
                raise BoundaryError("Consumable boundary lacks downstream "
                                    "outline: " + item["id"])
            if item.get("wall_reason") is not None:
                raise BoundaryError("Consumable boundary carries wall_reason: "
                                    + item["id"])
        else:
            if not item.get("wall_reason"):
                raise BoundaryError("Wall boundary lacks reason: " + item["id"])
            if item.get("downstream") is not None:
                raise BoundaryError("Wall boundary carries downstream: "
                                    + item["id"])
    consumable = [item["id"] for item in data["items"]
                  if item["status"] == "consumable"]
    if not consumable:
        raise BoundaryError("At least one boundary must be consumable")
    return True


def main(argv=None):
    """Print the verified registry as JSON (all pins verified fresh)."""
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    data = registry()
    verify_registry(data)
    text = json.dumps(data, indent=2) + "\n"
    if args.output is not None:
        if args.output.suffix != ".json":
            raise BoundaryError("Registry output must be JSON")
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
