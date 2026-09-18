#!/usr/bin/env python3
"""Save durable-payload pin-discovery registry (lane save-durable-payload-pin-discovery).

Read-only audit result for the wired kusachi stage (ch_NARI_01kusachi, ui_index 3):
no durable save-payload writer exists on that path, so the registry records an
ABSENT verdict with exact pins and the owner/shared-review contract. Stdlib only.
Fail-closed: anything unexpected is reported, never passed.
"""

import argparse
import json
import os
import sys

SCHEMA = "p2-save-durable-payload-pins-1"

VERDICT = "ABSENT"

# Exact audit pins. Native paths are branch-relative; commits name the branch tip
# where each file was read (git show, read-only).
PINS = {
    "schema": SCHEMA,
    "verdict": VERDICT,
    "stage": {"cave_id": "ch_NARI_01kusachi", "ui_index": 3},
    "challenge_module": {
        "files": ["pc_port/pc_p2_challenge_persistence.h",
                  "pc_port/pc_p2_challenge_persistence.cpp"],
        "native_commit": "3916d9a4d854851b7637579b3d196a1c4ed6a90a",
        "branch": "codex/autofill-challenge-persistence-engine-callsite-native-rebase",
        "finding": "probe-only: recordSave/recordLoad/recordClear/recordHighscore/"
                   "recordUnlock/recordReceiptDedup/recordReentry set in-memory flags "
                   "and printf P2_CHALLENGE_<STEM> markers; zero fopen/fwrite/"
                   "ofstream/CARD calls anywhere in the translation unit",
    },
    "overworld_serializer": {
        "files": ["pc_port/pc_p2_overworld_save.h",
                  "pc_port/pc_p2_overworld_save.cpp"],
        "native_commit": "38305eea11200e517897bbc137a58bde40f927b4",
        "finding": "real writer p2overworldsave::saveSession (ofstream, "
                   "P2_OVERWORLD_SAVE_SAVED) exists but is overworld-session "
                   "grammar only (area/day/squad), takes an explicit caller path, "
                   "and has no challenge caveId binding and no CARD card0 writes",
    },
    "card_filesystem": {
        "files": ["pc_port/dolphin_stubs/card_stubs.cpp"],
        "finding": "CARDInit (line 129) creates <run>/save/bbft_sessions/<ts>/card0; "
                   "CARDCreate (line 175) and CARDWrite (line 211) exist but have no "
                   "callers on the kusachi path; card0 in the #781 gen2 run dir is empty",
        "session_card_path": "<run>/save/bbft_sessions/<timestamp>/card0",
    },
    "retail_writer": {
        "files": ["src/plugPikiColin/memoryCard.cpp",
                  "src/plugPikiColin/cardutil.cpp"],
        "finding": "MemoryCard::writeOneGameFile (memoryCard.cpp:542) via cardutil "
                   "is driven only by the retail save UI flow, which the headed "
                   "kusachi run never reaches",
    },
    "owner_contract": {
        "verdict": "ABSENT",
        "producer": "new durable challenge-payload writer for p2_challenge_save_<caveId>, "
                    "natural home the #713 challenge-persistence module (CARDCreate/CARDWrite "
                    "payload or ofstream sidecar plus private save-dir staging)",
        "shared_review": "4laric/pikmin-randomizer#186 for the pc_bbft.cpp call chain",
        "alternative": "challenge grammar in the #736 overworld serializer",
        "consumers": ["kusachi-persistence-obs (#781)", "p2-challenge-ch_nari_01kusachi-p1 (#533)"],
    },
}


def registry():
    """Return a deep copy of the pins registry."""
    return json.loads(json.dumps(PINS))


def verify_run_dir(run_dir):
    """Check a headed run dir for durable payload evidence. Fail-closed dict."""
    problems = []
    if not os.path.isdir(run_dir):
        return {"verdict": "REFUSED", "problems": ["missing-run-dir"], "payloads": []}
    payloads = []
    for root, _dirs, files in os.walk(run_dir):
        rel = os.path.relpath(root, run_dir)
        if rel.split(os.sep)[0] != "save":
            continue
        for name in files:
            if name in ("native.log", "run-result.json", "run-inputs.json",
                        "run-metadata.json", "p2-challenge-stage-select.txt"):
                continue
            payloads.append(os.path.join(rel, name))
    if payloads:
        problems.append("unexpected-payload-files-present")
    return {"verdict": "ABSENT" if not payloads else "UNEXPECTED",
            "problems": problems, "payloads": sorted(payloads)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("pins")
    verify = sub.add_parser("verify-run")
    verify.add_argument("--dir", required=True)
    args = parser.parse_args(argv)
    if args.command == "pins":
        print(json.dumps(registry(), indent=1, sort_keys=True))
        return 0
    result = verify_run_dir(args.dir)
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result["verdict"] == "ABSENT" and not result["problems"] else 1


if __name__ == "__main__":
    raise SystemExit(main())