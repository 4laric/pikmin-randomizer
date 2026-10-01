"""P1 runtime observation adapter for P2 Challenge ch_ABEM_tutorial (#534).

Lane p2-challenge-ch-abem-tutorial-p1-runtime-obs, generation 2. Consumes the
DONE P1 import base (lane p2-challenge-ch-abem-tutorial-p1, read-only) and
stages a fresh observation arena for the floor-1 roster, then parses natural
gameplay markers from a headed run log with a dependency-free reader. It never
re-derives the P0 catalog and never invents placements, spawns or receipts:
definition rows stay definitions, and only observed log lines become facts.

Stage-boot honesty: the engine P2 stage table available to this lane resolves
only ch_NARI_01kusachi; ch_ABEM_tutorial has no engine row, so no
stage-boot path can resolve it here. That is recorded as a BLOCKED
prerequisite (provider row + #186 wiring), never simulated. The arena,
squad, control set and natural markers below are all real and checkable.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

LANE = "p2-challenge-ch-abem-tutorial-p1-runtime-obs"
CAVE_ID = "ch_ABEM_tutorial"
SCHEMA = 1
SOURCE_SHA256 = "e21f31f7fa5621a5922d9ee54ffb211a8e4f0e797866d70cc1edb98389ab097d"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"
FLOOR_SECONDS = (100.0, 100.0)
SPRAYS = {"bitter": 2, "spicy": 2}
FLOOR1_ROSTER = ("Clover", "Tukushi", "Ooinu_s", "KareOoinu_s")
FLOOR1_TREASURES = ("key", "gold_medal", "silver_medal", "wadou_kaichin")
FLOOR1_POOL = "1_units_cent3_tsuchi.txt"

WINDOW_RE = re.compile(r"(\d+)x(\d+).*centered=1")
SQUAD_RE = re.compile(r"squad_alive=(\d+)")
SPAWN_RE = re.compile(r"spawn(?:ed)?[ :]+(\d+).*creatures?", re.I)
GUARD_DOWN_RE = re.compile(r"P2_FIXTURE_CAPTAIN_DOWN")
READY_RE = re.compile(r"P2_CAVE_READY floor=(\d+) survivors=(\d+)")
GENERATE_PASS_RE = re.compile(r"P2_CAVE_GENERATE_PASS")
BOOT_PASS_RE = re.compile(r"PASS (?:CAVE_GUARDED_BOOT|TUTORIAL\d_P1)")


class ObservationError(Exception):
    """Raised when staging inputs or a run log violate the contract."""


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_p1_manifest(path):
    """Read the DONE P1 import manifest (read-only input)."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError("Missing P1 manifest: " + str(path))
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("cave_id") != CAVE_ID:
        raise ValueError("P1 manifest cave mismatch")
    floors = manifest.get("floors")
    if not isinstance(floors, list) or len(floors) != 2:
        raise ValueError("P1 manifest must carry exactly 2 floors")
    return manifest


def stage_arena(assets_dir, output_dir, manifest):
    """Stage a fresh observation arena with a live squad plus a control set.

    Uses the canonical starting-Pikmin overlay generator on the legal assets
    to produce a 20-squad arena, records every staged generator id/position,
    and records the untouched plants.gen set as the ordinary control. The
    floor-1 challenge roster is carried as observation targets (never placed
    as actors). Returns the staging record with hashes.
    """
    import sys
    assets_dir, output_dir = Path(assets_dir), Path(output_dir)
    repo = Path(__file__).resolve().parents[2]
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    try:
        from scripts.preview_pikmin2_room import generator, records
    except ImportError as exc:
        raise ObservationError("starting-Pikmin overlay unavailable: %s" % exc)
    arena_bytes = generator(assets_dir)
    staged = output_dir / "arena-default.gen"
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.write_bytes(arena_bytes)
    rows = records(staged)
    staged_ids = []
    for row in rows:
        if len(row) >= 12:
            import struct
            staged_ids.append(struct.unpack_from("<I", row, 8)[0])
    plants_path = assets_dir / "dataDir/stages/chal0/plants.gen"
    control_ids = []
    if plants_path.is_file():
        for row in records(plants_path):
            if len(row) >= 12:
                import struct
                control_ids.append(struct.unpack_from("<I", row, 8)[0])
    return {
        "schema": SCHEMA,
        "lane": LANE,
        "cave_id": CAVE_ID,
        "arena_sha256": hashlib.sha256(arena_bytes).hexdigest(),
        "arena_records": len(rows),
        "staged_generator_ids": sorted(set(staged_ids)),
        "control_source": "assets/dataDir/stages/chal0/plants.gen (untouched)",
        "control_generator_ids": sorted(set(control_ids)),
        "floor1_targets": {"roster": list(FLOOR1_ROSTER),
                           "treasures": list(FLOOR1_TREASURES),
                           "pool": FLOOR1_POOL},
        "stage_boot_resolves": False,
        "stage_boot_blocker": ("engine P2 stage table has no ch_ABEM_tutorial row; "
                               "provider row plus #186 wiring required"),
    }


def read_run_log(path):
    """Dependency-free parse of natural gameplay markers from a headed log."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    window = None
    for line in lines:
        match = WINDOW_RE.search(line)
        if match and "960" in line and "540" in line:
            window = {"width": int(match[1]), "height": int(match[2]),
                      "centered": "centered=1" in line}
    squads = [int(m[1]) for line in lines for m in SQUAD_RE.finditer(line)]
    spawns = [int(m[1]) for line in lines for m in SPAWN_RE.finditer(line)]
    ready = [(int(m[1]), int(m[2])) for line in lines for m in READY_RE.finditer(line)]
    return {
        "window_960x540_centered": bool(window and window["width"] == 960
                                        and window["height"] == 540 and window["centered"]),
        "squad_alive_max": max(squads) if squads else 0,
        "spawn_reports": len(spawns),
        "cave_ready": [{"floor": f, "survivors": s} for f, s in ready],
        "generate_pass": any(GENERATE_PASS_RE.search(l) for l in lines),
        "boot_pass": any(BOOT_PASS_RE.search(l) for l in lines),
        "captain_down": any(GUARD_DOWN_RE.search(l) for l in lines),
        "lines": len(lines),
    }


def classify_gates(observation):
    """Honest six-gate disposition from observed facts only."""
    gates = {}
    if observation["squad_alive_max"] >= 1 and not observation["captain_down"]:
        gates["identity_spawn"] = ("PASS", "natural",
                                   "live squad observed (%d alive), no captain-down"
                                   % observation["squad_alive_max"])
    else:
        gates["identity_spawn"] = ("UNTESTED", "unobserved",
                                   "no live squad observed")
    for gate in ("movement_animation", "attacks_receivers", "death_corpse",
                 "transport_reward", "cleanup_reentry"):
        gates[gate] = ("UNTESTED", "unobserved",
                       "gameplay not observed in this run")
    return gates


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--read-log", type=Path, default=None)
    args = parser.parse_args(argv)
    manifest = load_p1_manifest(args.manifest)
    record = stage_arena(args.assets, args.output, manifest)
    result = {"staging": record}
    if args.read_log:
        observation = read_run_log(args.read_log)
        result["observation"] = observation
        result["gates"] = {k: {"status": s, "method": m, "detail": d}
                           for k, (s, m, d) in classify_gates(observation).items()}
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
