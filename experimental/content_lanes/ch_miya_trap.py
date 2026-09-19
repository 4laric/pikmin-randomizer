"""P1 runtime-import path for P2 Challenge 27: ch_MIYA_trap (issue #560).

Lane p2-challenge-ch-miya-trap-p1, generation 2. This module owns ONLY the P1
import path; the P0 decode helpers live in the sibling P0 adapter
``p2-challenge-ch_miya_trap.py`` (owned by lane p2-challenge-ch_miya_trap),
which is imported read-only via importlib and never edited or forked.

What this module does (stdlib only):

- Validates a P0-decoded stage manifest for ch_MIYA_trap: exactly the 1
  decoded floor with a unit pool plus enemy/treasure rosters, the 7-row
  starting roster (total 25, only cell [3][2] == 25), the positive floor
  timer [300.0], sprays 2/2 and ui_index 26. Anything else raises fail-closed.
- Stages a private run layout: ``stage-manifest.json`` (validated copy),
  ``p1-input-package.json`` (stage key, floors, squad total, timers, sprays,
  ui) and ``run-plan.json`` (ordered observation plan with the captain
  guard first and honest-gates policy). No runtime is executed here.
- ``p1_main()`` drives staging from a manifest file; ``main()`` is a thin
  CLI over it.

No native build, no runtime, no ADMIT, no playability claim. All six gates
stay UNTESTED unless genuinely observed by a later runtime run.
"""

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


def _load_p0():
    path = Path(__file__).with_name("p2-challenge-ch_miya_trap.py")
    spec = importlib.util.spec_from_file_location("p2_challenge_ch_miya_trap", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p0 = _load_p0()

CAVE_ID = p0.SOURCE_ID
P1_SCHEMA = "p2-challenge-ch-miya-trap-p1-v1"


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_p1_manifest(manifest):
    """Check a P0 manifest carries everything the P1 import needs."""
    if not isinstance(manifest, dict):
        raise ValueError("P1 manifest must be a dict")
    if manifest.get("cave_id") != CAVE_ID:
        raise ValueError("P1 stage mismatch")
    floors = manifest.get("floors")
    if not isinstance(floors, list) or len(floors) != p0.EXPECTED_FLOORS:
        raise ValueError("P1 needs exactly the %d decoded floor(s)" % p0.EXPECTED_FLOORS)
    staged = []
    for n, floor in enumerate(floors, 1):
        if not isinstance(floor, dict):
            raise ValueError("P1 floor malformed")
        for key in ("unit_pool", "enemies", "treasures"):
            if key not in floor:
                raise ValueError("P1 floor missing field")
        if not isinstance(floor["enemies"], list) or not floor["enemies"]:
            raise ValueError("P1 floor has no enemy roster")
        if not isinstance(floor["unit_pool"], str) or not floor["unit_pool"]:
            raise ValueError("P1 floor has no unit pool")
        staged.append({
            "number": n,
            "unit_pool": floor["unit_pool"],
            "enemies": [e["source_token"] for e in floor["enemies"]],
            "treasures": [t["treasure_id"] for t in floor["treasures"]],
        })
    roster = manifest.get("starting_roster")
    if not isinstance(roster, list) or len(roster) != 7:
        raise ValueError("P1 starting roster malformed")
    if any(not isinstance(row, list) or len(row) != 3 for row in roster):
        raise ValueError("P1 starting roster rows must each hold 3 maturities")
    squad_total = sum(int(v) for row in roster for v in row)
    if squad_total != p0.EXPECTED_TOTAL_PIKMIN:
        raise ValueError("P1 starting squad total must be %d" % p0.EXPECTED_TOTAL_PIKMIN)
    for color, maturity in p0.EXPECTED_NONZERO_CELLS:
        if roster[color][maturity] <= 0:
            raise ValueError("P1 starting roster missing pinned cell [%d][%d]" % (color, maturity))
    timers = manifest.get("floor_seconds")
    if not isinstance(timers, list) or [float(v) for v in timers] != [float(v) for v in p0.EXPECTED_FLOOR_SECONDS]:
        raise ValueError("P1 floor timers must preserve %s" % (p0.EXPECTED_FLOOR_SECONDS,))
    sprays = manifest.get("sprays", {})
    if not isinstance(sprays, dict):
        raise ValueError("P1 sprays malformed")
    if int(sprays.get("bitter", -1)) != 2 or int(sprays.get("spicy", -1)) != 2:
        raise ValueError("P1 sprays must preserve bitter 2 / spicy 2")
    if manifest.get("ui_index") != 26:
        raise ValueError("P1 ui_index must preserve 26")
    return {
        "cave_id": CAVE_ID,
        "floors": staged,
        "squad_total": squad_total,
        "floor_seconds": [float(v) for v in timers],
        "sprays": {"bitter": int(sprays.get("bitter", 0)),
                   "spicy": int(sprays.get("spicy", 0))},
        "ui_index": int(manifest.get("ui_index", 0)),
    }


def stage_run_layout(manifest, output):
    """Validate the manifest and write the private P1 run layout."""
    staging = validate_p1_manifest(manifest)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    files = {}

    def write(name, payload):
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        (output / name).write_text(text, encoding="utf-8")
        files[name] = sha256(text)

    write("stage-manifest.json", manifest)
    write("p1-input-package.json", {
        "schema": P1_SCHEMA,
        "cave_id": staging["cave_id"],
        "floors": staging["floors"],
        "squad_total": staging["squad_total"],
        "floor_seconds": staging["floor_seconds"],
        "sprays": staging["sprays"],
        "ui_index": staging["ui_index"],
    })
    write("run-plan.json", {
        "schema": P1_SCHEMA,
        "order": [
            "boot private runtime with the input package (fresh arena, starting-Pikmin overlay, centred 960x540)",
            "captain guard FIRST (orimaDead/NaviDead/HP<=1, CAPTAIN_DOWN + BLOCKED, parked captain)",
            "observe live starting squad (no immediate extinction)",
            "observe actual collision/routes/actors per floor with receipt-parseable markers",
            "record honest six-gate evidence; no playability claim beyond observed evidence",
        ],
        "gates": "all six UNTESTED unless genuinely observed",
    })
    return {"files": files, "cave_id": staging["cave_id"],
            "floors": len(staging["floors"])}


def p1_main(manifest_path, output):
    """Stage the run layout from a manifest file on disk."""
    manifest_path = Path(manifest_path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("P1 manifest unreadable: %s" % exc) from None
    result = stage_run_layout(manifest, Path(output))
    print("P1 staged cave=%s floors=%d files=%s" % (
        result["cave_id"], result["floors"], sorted(result["files"])))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Stage the ch_MIYA_trap P1 run layout")
    parser.add_argument("manifest", help="P0-decoded stage manifest JSON")
    parser.add_argument("output", help="private run-layout directory")
    args = parser.parse_args(argv)
    p1_main(args.manifest, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
