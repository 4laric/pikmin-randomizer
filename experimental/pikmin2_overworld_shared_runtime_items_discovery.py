#!/usr/bin/env python3
"""Pin + scope the three unowned #132 shared overworld runtime items (#724).

Read-only discovery over the accepted #658 save/session pin registry, the #707
overworld surface boot-path registry and the #151 surface-session handoff.
Produces, per item (native sunset driver, native receipt-ledger endpoint,
native generator-cache restore):

  * exact consumer file/line pins with the symbol token expected at that line,
  * the file SHA-256 recorded from the read-only research tree,
  * the provider-shard owner (#605 save-progression / #606 treasure-receipts /
    #607 cave-generation) and the #186 shared-semantics gate,
  * a concrete bounded implementation-scoping deliverable with acceptance.

Fail-closed: any missing file, missing line, or line whose token does not
match makes the packet INVALID (nonzero exit, no partial approval). No source
edits, no runtime, no ADMIT. The save serializer (#132 item 4) is excluded: it
is already covered by the published #712 conformance producer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# The read-only decomp research tree lives in the canonical workspace, not in
# this private root worktree (which has no native/ checkout). Override with
# PIKMIN2_RESEARCH_ROOT when running elsewhere.
CANONICAL_ROOT = "C:/Users/alari/pikmin-randomizer"
DEFAULT_RESEARCH_ROOT = os.environ.get(
    "PIKMIN2_RESEARCH_ROOT",
    os.path.join(CANONICAL_ROOT, "native", "pikmin2-research"))
SRC = "src/plugProjectKandoU"

SCHEMA = "p2-overworld-shared-runtime-items-1"

# Read-only upstream pins this discovery consumes (hashed by the packet).
UPSTREAM = {
    "658_pin_registry": {
        "path": ("output/workflow/autofill/planning-shards/overworld-last/prepared/"
                 "save-session-discovery-root/docs/PIKMIN2_SAVE_SESSION_PIN_DISCOVERY.md"),
        "sha256": "d5f8f469418ccf5810e89aa62cc48b0be46c821b8c79fea0d02d75e50b84c8c2",
    },
    "707_pin_registry": {
        "path": ("output/workflow/autofill/planning-shards/overworld-tutorial/prepared/"
                 "overworld-surface-boot-pin-discovery-launch/out/registry.json"),
    },
    "151_surface_session_handoff": {
        "path": ("output/workflow/autofill/planning-shards/overworld-last/prepared/"
                 "p1-last-surface-session-output/handoff.json"),
    },
}

ITEMS = (
    {
        "key": "native_sunset_driver",
        "title": "Native sunset driver (day start/end, sunset losses, surface time)",
        "contract_item": "native sunset driver",
        "owner_issue": 605,
        "owner_shard": "provider-save-progression",
        "review_186": ("day start/end and timer hooks sit on the shared section/FSM path; "
                       "route through the #186 shared-hook contract"),
        "pins": (
            {"file": SRC + "/singleGameSection.cpp", "line": 183,
             "token": "SingleGame::CaveDayEndState::init", "role": "cave day-end entry"},
            {"file": SRC + "/singleGameSection.cpp", "line": 209,
             "token": "SingleGame::CaveDayEndState::exec", "role": "cave day-end tick"},
            {"file": SRC + "/singleGameSection.cpp", "line": 486,
             "token": "SingleGameSection::enableTimer", "role": "day timer arming hook"},
            {"file": SRC + "/singleGameSection.cpp", "line": 500,
             "token": "SingleGameSection::disableTimer", "role": "day timer disarm hook"},
            {"file": SRC + "/singleGameSection.cpp", "line": 660,
             "token": "SingleGameSection::saveMainMapSituation", "role": "surface time capture"},
            {"file": SRC + "/singleGameSection.cpp", "line": 684,
             "token": "SingleGameSection::loadMainMapSituation", "role": "time restore on re-entry"},
        ),
        "open_subitems": (
            "Field-Pikmin sunset-loss enumeration has no sunset-named driver in src "
            "(only UI counters); the loss site must be pinned from the day-end flow, not assumed.",
        ),
        "deliverable": {
            "owned_files": (
                "experimental/pikmin2_sunset_driver_hook.py",
                "tests/test_pikmin2_sunset_driver_hook.py",
                "docs/PIKMIN2_SUNSET_DRIVER_HOOK.md",
            ),
            "acceptance": ("Hook-declaration adapter fires on the pinned day start/end and timer "
                           "arm/disarm transitions on a private fixture; the sunset-loss sub-item "
                           "is resolved or recorded ABSENT; six gates honest."),
        },
    },
    {
        "key": "native_receipt_ledger_endpoint",
        "title": "Native receipt-ledger endpoint (surface/area treasure receipt binding)",
        "contract_item": "native receipt ledger endpoint",
        "owner_issue": 606,
        "owner_shard": "provider-treasure-receipts",
        "review_186": ("the surface delivery binding is unscoped; route through the #186 "
                       "shared-hook contract rather than a silent hook"),
        "pins": (
            {"file": SRC + "/onyonMgr.cpp", "line": 195,
             "token": "Onyon::isSuckReady", "role": "delivery readiness gate"},
            {"file": SRC + "/onyonMgr.cpp", "line": 403,
             "token": "InteractSuckDone::actOnyon", "role": "pellet-to-poko delivery endpoint"},
            {"file": SRC + "/gamePlayData.cpp", "line": 800,
             "token": "PlayData::obtainPellet_Main", "role": "ledger accumulation entry"},
            {"file": SRC + "/gamePlayData.cpp", "line": 832,
             "token": "mPokoCount +=", "role": "ledger accumulation write"},
        ),
        "open_subitems": (
            "No receipt/ledger-named source exists in research; the pins above are the real "
            "delivery path and are the binding surface.",
        ),
        "deliverable": {
            "owned_files": (
                "experimental/pikmin2_receipt_ledger_binding.py",
                "tests/test_pikmin2_receipt_ledger_binding.py",
                "docs/PIKMIN2_RECEIPT_LEDGER_BINDING.md",
            ),
            "acceptance": ("Receipt-binding observer traces delivery-to-ledger on real callbacks "
                           "against the pinned endpoint with negatives refused and no receipt "
                           "fabrication; six gates honest."),
        },
    },
    {
        "key": "native_generator_cache_restore",
        "title": "Native generator-cache restore (cave/actor regeneration restore)",
        "contract_item": "native generator-cache restore",
        "owner_issue": 607,
        "owner_shard": "provider-cave-generation",
        "review_186": ("restore extends the accepted generator pin; route through the #186 "
                       "shared-hook contract"),
        "pins": (
            {"file": SRC + "/gameGeneratorCache.cpp", "line": 203,
             "token": "GeneratorCache::loadGenerators", "role": "course generator load"},
            {"file": SRC + "/gameGeneratorCache.cpp", "line": 281,
             "token": "GeneratorCache::slideCache", "role": "cache slide/rotation"},
            {"file": SRC + "/gameGeneratorCache.cpp", "line": 341,
             "token": "GeneratorCache::beginSave", "role": "save framing entry"},
            {"file": SRC + "/gameGeneratorCache.cpp", "line": 504,
             "token": "GeneratorCache::write", "role": "cache persist entry"},
            {"file": SRC + "/gameGeneratorCache.cpp", "line": 557,
             "token": "GeneratorCache::read", "role": "cache restore entry"},
            {"file": SRC + "/gameGeneratorCache.cpp", "line": 665,
             "token": "CourseCache::read", "role": "per-course restore"},
        ),
        "open_subitems": (),
        "deliverable": {
            "owned_files": (
                "experimental/pikmin2_generator_cache_restore.py",
                "tests/test_pikmin2_generator_cache_restore.py",
                "docs/PIKMIN2_GENERATOR_CACHE_RESTORE.md",
            ),
            "acceptance": ("Restore-conformance adapter proves cache write/read round-trip equality "
                           "and per-course restore on pinned fixtures with overflow/negative paths; "
                           "no generator-semantics change; six gates honest."),
        },
    },
)

DOWNLOADSTREAM_EXCLUDED = {
    "native save serializer": {
        "owner": "#712 provider-save-serializer-conformance (published)",
        "status": "EXCLUDED",
    }
}


class MissingPin(RuntimeError):
    """A required source pin is absent or changed."""


def sha256_file(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_pins(research_root=DEFAULT_RESEARCH_ROOT, items=ITEMS):
    """Verify every pin against the read-only research tree (fail-closed).

    Returns (ok, report, problems). A missing file, an out-of-range line, or a
    line whose token does not match is a hard problem; nothing is approved
    partially.
    """
    problems = []
    report = {"schema": SCHEMA, "research_root": research_root,
              "items": [], "excluded": DOWNLOADSTREAM_EXCLUDED}
    file_hashes = {}
    for item in items:
        verified = []
        for pin in item["pins"]:
            full = os.path.join(research_root, pin["file"].replace("/", os.sep))
            if not os.path.isfile(full):
                problems.append("%s: missing file %s" % (item["key"], pin["file"]))
                continue
            file_hashes.setdefault(pin["file"], sha256_file(full))
            with open(full, encoding="utf-8", errors="replace") as stream:
                lines = stream.read().splitlines()
            if pin["line"] < 1 or pin["line"] > len(lines):
                problems.append("%s: line %d out of range in %s"
                                % (item["key"], pin["line"], pin["file"]))
                continue
            text = lines[pin["line"] - 1]
            if pin["token"] not in text:
                problems.append("%s: token %r not found at %s:%d"
                                % (item["key"], pin["token"], pin["file"], pin["line"]))
                continue
            verified.append(dict(pin, text=text.strip(), file_sha256=file_hashes[pin["file"]]))
        report["items"].append({
            "key": item["key"],
            "title": item["title"],
            "contract_item": item["contract_item"],
            "owner_issue": item["owner_issue"],
            "owner_shard": item["owner_shard"],
            "review_186": item["review_186"],
            "verified_pins": verified,
            "pin_count": len(verified),
            "open_subitems": list(item["open_subitems"]),
            "deliverable": item["deliverable"],
        })
    report["file_hashes"] = file_hashes
    return (not problems), report, problems


def emit_packet(out_path, research_root=DEFAULT_RESEARCH_ROOT):
    ok, report, problems = verify_pins(research_root)
    report["ok"] = ok
    report["problems"] = problems
    if out_path is not None:
        with open(out_path, "w", encoding="utf-8", newline="") as stream:
            stream.write(json.dumps(report, indent=1, sort_keys=True) + "\n")
    return ok, report, problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research-root", default=DEFAULT_RESEARCH_ROOT)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    ok, report, problems = emit_packet(args.out, args.research_root)
    if args.out is None:
        print(json.dumps(report, indent=1, sort_keys=True))
    for problem in problems:
        print("REFUSED %s" % problem, file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
