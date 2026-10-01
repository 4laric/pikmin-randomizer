"""P0 import adapter for P2 Challenge 01: ch_ABEM_tutorial (issue #534).

Decodes the retail caveinfo definition
``user/Mukki/mapunits/caveinfo/ch_ABEM_tutorial.txt`` from a local US GPVE01
disc image, validates its hash and floor coverage against the catalogued lane
baseline, checks resource closure (unit pools, unit archives, light config),
and emits a metadata-only import manifest. Weighted Teki/Item/Cap rows stay
definitions: this module never fabricates runtime placements, spawn counts,
or completion behavior.

Shared parsing is reused by import, never reimplemented:
``experimental.pikmin2_cave`` (brace stream, unit definitions),
``experimental.pikmin2_cave_catalog`` (campaign-compatible section decode),
``experimental.pikmin2_assets`` (disc/catalog access),
``experimental.pikmin2_pod`` (treasure catalog).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_cave import unit_definition
from experimental.pikmin2_cave_catalog import parse as parse_cave
from experimental.pikmin2_pod import pellet_catalog

SCHEMA = "p2-challenge-ch_abem_tutorial-p0-v1"
CAVE_ID = "ch_ABEM_tutorial"
CAVE_PATH = "user/Mukki/mapunits/caveinfo/ch_ABEM_tutorial.txt"
UNITS_BASE = "user/Mukki/mapunits/units"
ARC_BASE = "user/Mukki/mapunits/arc"
LIGHT_PATH = "user/Abe/cave/normal_light_cha.ini"
PELLET_ARCHIVE = "user/Abe/Pellet/us/pelletlist_us.szs"
EXPECTED_SHA256 = "e21f31f7fa5621a5922d9ee54ffb211a8e4f0e797866d70cc1edb98389ab097d"

# Observed source facts (verified against the extracted definition; asserted
# by check_stage, not assumed).
EXPECTED_FLOORS = (
    {"unit": "1_units_cent3_tsuchi.txt",
     "enemies": ("Clover", "Tukushi", "Ooinu_s", "KareOoinu_s"),
     "treasures": ("key", "gold_medal", "silver_medal", "wadou_kaichin"),
     "caps": ()},
    {"unit": "2_MAT_mid1_nor2_tsuchi.txt",
     "enemies": ("Chappy_key", "Kochappy_be_dama_red", "Egg", "Clover",
                 "Tukushi", "Ooinu_s", "Ooinu_l", "KareOoinu_s", "KareOoinu_l"),
     "treasures": ("gold_medal", "silver_medal", "wadou_kaichin"),
     "caps": ("Egg",)},
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_disc_bytes(iso_path: Path, rel_path: str) -> tuple[bytes, str]:
    """Read one file from the disc image; fail closed on any defect."""
    if not iso_path.is_file():
        raise ValueError(f"Missing disc image: {iso_path}")
    catalog = disc_files(iso_path)
    if rel_path not in catalog:
        raise ValueError(f"Source absent from disc catalog: {rel_path}")
    offset, length = catalog[rel_path]
    with iso_path.open("rb") as disc:
        disc.seek(offset)
        data = disc.read(length)
    if len(data) != length:
        raise ValueError(f"Truncated disc source: {rel_path}")
    return data, sha256(data)


def load_enemy_ids(enemyinfo_cpp: Path) -> set[str]:
    if not enemyinfo_cpp.is_file():
        raise ValueError(f"Missing enemy catalog source: {enemyinfo_cpp}")
    raw = enemyinfo_cpp.read_bytes().decode("utf-8")
    ids = set(re.findall(r'\{"([A-Za-z0-9_]+)"', raw))
    if not ids:
        raise ValueError("Empty enemy catalog")
    return ids


def load_treasure_ids(iso_path: Path) -> set[str]:
    data, _ = read_disc_bytes(iso_path, PELLET_ARCHIVE)
    archive = archive_files(data)
    ids: set[str] = set()
    for name in ("otakara_config.txt", "item_config.txt"):
        if name not in archive:
            raise ValueError(f"Missing pellet config in archive: {name}")
        ids.update(pellet_catalog(archive[name].decode("shift_jis")))
    if not ids:
        raise ValueError("Empty treasure catalog")
    return ids


def decode(text: str, enemy_ids: set[str], treasure_ids: set[str]) -> dict:
    try:
        return parse_cave(text, enemy_ids, treasure_ids)
    except ValueError as exc:
        raise ValueError(f"Cave definition decode failed: {exc}") from None


def check_hash(actual: str) -> None:
    if actual != EXPECTED_SHA256:
        raise ValueError(
            f"Source hash mismatch: got {actual}, lane baseline {EXPECTED_SHA256}")


def check_stage(cave: dict) -> None:
    """Assert complete floor coverage and exact observed per-floor content."""
    if cave.get("definition_count") != 2 or cave.get("floor_count") != 2:
        raise ValueError(
            f"Floor coverage mismatch: definitions={cave.get('definition_count')} "
            f"floors={cave.get('floor_count')}, expected 2/2")
    floors = cave.get("floors", [])
    if len(floors) != 2:
        raise ValueError("Missing floor definitions")
    occupied = set()
    for floor in floors:
        occupied.update(range(floor["first_floor"], floor["last_floor"] + 1))
    if occupied != {1, 2}:
        raise ValueError(f"Floor range gap: occupied={sorted(occupied)}")
    for index, (floor, expected) in enumerate(zip(floors, EXPECTED_FLOORS)):
        if floor["parameters"].get("f008") != expected["unit"]:
            raise ValueError(
                f"Floor {index + 1} unit pool mismatch: "
                f"{floor['parameters'].get('f008')!r} != {expected['unit']!r}")
        got_enemies = tuple(e["source_token"] for e in floor["enemies"])
        if got_enemies != expected["enemies"]:
            raise ValueError(f"Floor {index + 1} enemy roster mismatch: {got_enemies}")
        got_treasures = tuple(t["treasure_id"] for t in floor["treasures"])
        if got_treasures != expected["treasures"]:
            raise ValueError(f"Floor {index + 1} treasure roster mismatch: {got_treasures}")
        got_caps = tuple(c["enemy"]["source_token"] for c in floor["caps"]
                         if not c["empty"])
        if got_caps != expected["caps"]:
            raise ValueError(f"Floor {index + 1} cap roster mismatch: {got_caps}")
        if floor["gates"]:
            raise ValueError(f"Floor {index + 1} has unexpected gate rows")


def check_metadata(details: dict) -> None:
    """Cross-check the catalogued lane baseline (timers, sprays, roster)."""
    if details.get("floors") != 2:
        raise ValueError("Lane baseline floor count changed")
    if [float(v) for v in details.get("floor_seconds", [])] != [100.0, 100.0]:
        raise ValueError("Lane baseline floor timers changed")
    if (details.get("bitter_sprays"), details.get("spicy_sprays")) != (2, 2):
        raise ValueError("Lane baseline spray counts changed")
    roster = details.get("pikmin_by_native_color_and_maturity", [])
    if len(roster) != 7 or [int(v) for v in roster[1]] != [50, 0, 0]:
        raise ValueError("Lane baseline starting roster changed")
    if any(any(int(v) != 0 for v in row) for i, row in enumerate(roster) if i != 1):
        raise ValueError("Lane baseline starting roster changed")
    if details.get("ui_index") != 0 or details.get("treasure_count_field") != 0:
        raise ValueError("Lane baseline stage fields changed")


def resource_closure(iso_path: Path, cave: dict) -> dict:
    """Verify every referenced unit pool, unit archive pair and light config.

    Presence-only: archives are never extracted here. Returns hashes of the
    decoded text pools plus the exact missing list (empty on success).
    """
    catalog = disc_files(iso_path)
    missing: list[str] = []
    pools: dict = {}
    with iso_path.open("rb") as disc:
        def read(path: str) -> bytes:
            at, size = catalog[path]
            disc.seek(at)
            data = disc.read(size)
            if len(data) != size:
                raise ValueError(f"Truncated disc source: {path}")
            return data

        for floor in cave["floors"]:
            pool = floor["parameters"]["f008"]
            pool_path = f"{UNITS_BASE}/{pool}"
            if pool_path not in catalog:
                missing.append(pool_path)
                continue
            raw = read(pool_path)
            try:
                definitions = unit_definition(raw.decode("shift_jis"))
            except (ValueError, UnicodeDecodeError) as exc:
                raise ValueError(f"Unit pool decode failed ({pool_path}): {exc}") from None
            units = []
            for unit in definitions:
                for suffix in ("arc.szs", "texts.szs"):
                    asset = f"{ARC_BASE}/{unit['name']}/{suffix}"
                    if asset not in catalog:
                        missing.append(asset)
                units.append(unit["name"])
            pools[pool_path] = {"sha256": sha256(raw), "units": units}
        light_present = LIGHT_PATH in catalog
        if not light_present:
            missing.append(LIGHT_PATH)
    if missing:
        raise ValueError(f"Resource closure gaps: {sorted(set(missing))}")
    return {"unit_pools": pools, "light": LIGHT_PATH}


def manifest(cave: dict, details: dict, closure: dict, hashes: dict) -> dict:
    return {
        "schema": SCHEMA,
        "cave_id": CAVE_ID,
        "source": CAVE_PATH,
        "source_sha256": hashes["cave"],
        "english_title": None,
        "floors": [
            {"number": n + 1,
             "unit_pool": floor["parameters"]["f008"],
             "light": floor["parameters"].get("f009"),
             "enemies": floor["enemies"],
             "treasures": floor["treasures"],
             "gates": floor["gates"],
             "caps": floor["caps"]}
            for n, floor in enumerate(cave["floors"])
        ],
        "starting_roster": details["pikmin_by_native_color_and_maturity"],
        "floor_seconds": [float(v) for v in details["floor_seconds"]],
        "sprays": {"bitter": details["bitter_sprays"], "spicy": details["spicy_sprays"]},
        "ui_index": details["ui_index"],
        "resource_closure": closure,
        "source_sha256_map": hashes,
        "generated": False,
        "limitations": [
            "Weights/counts are definition inputs, not final spawn instances or placements.",
            "No seeded topology, hole selection, actor placement or completion behavior is generated.",
            "English display title unresolved; source ID and UI index authoritative.",
            "Metadata is not runtime acceptance; P1/P2 require framework/generator pins.",
        ],
    }


def lane_details(lanes_json: Path) -> dict:
    data = json.loads(lanes_json.read_text(encoding="utf-8"))
    for lane in data.get("lanes", []):
        if lane.get("lane") == "p2-challenge-ch_abem_tutorial":
            return lane.get("details", {})
    raise ValueError("Lane entry missing from import plan")


def run(iso_path: Path, enemyinfo_cpp: Path, lanes_json: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    log: list[str] = []
    raw, digest = read_disc_bytes(iso_path, CAVE_PATH)
    log.append(f"source bytes={len(raw)} sha256={digest}")
    check_hash(digest)
    log.append("hash matches lane baseline")
    text = raw.decode("shift_jis")
    cave = decode(text, load_enemy_ids(enemyinfo_cpp), load_treasure_ids(iso_path))
    log.append(f"decoded floors={cave['floor_count']}")
    check_stage(cave)
    log.append("floor coverage + per-floor rosters verified")
    details = lane_details(lanes_json)
    check_metadata(details)
    log.append("lane baseline metadata cross-checked")
    closure = resource_closure(iso_path, cave)
    units = sum(len(p["units"]) for p in closure["unit_pools"].values())
    log.append(f"resource closure complete: pools={len(closure['unit_pools'])} units={units}")
    hashes = {"cave": digest}
    hashes.update({p: info["sha256"] for p, info in closure["unit_pools"].items()})
    result = manifest(cave, details, closure, hashes)
    (output / "manifest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output / "run.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    result["_log"] = log
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--enemyinfo", type=Path, required=True)
    parser.add_argument("--lanes-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.iso, args.enemyinfo, args.lanes_json, args.output)
    print(f"floors=2 units={sum(len(p['units']) for p in result['resource_closure']['unit_pools'].values())} "
          f"manifest={args.output / 'manifest.json'}")


P1_SCHEMA = "p2-challenge-ch_abem_tutorial-p1-v1"


def validate_p1_manifest(manifest: dict) -> dict:
    if not isinstance(manifest, dict):
        raise ValueError("P1 manifest must be a dict")
    if manifest.get("cave_id") != CAVE_ID:
        raise ValueError("P1 stage mismatch")
    floors = manifest.get("floors")
    if not isinstance(floors, list) or len(floors) != 2:
        raise ValueError("P1 needs exactly the 2 decoded floors")
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
    squad_total = sum(int(v) for row in roster for v in row)
    if squad_total <= 0:
        raise ValueError("P1 starting squad is empty")
    timers = [float(v) for v in manifest.get("floor_seconds", [])]
    if len(timers) != 2 or any(v <= 0 for v in timers):
        raise ValueError("P1 floor timers malformed")
    sprays = manifest.get("sprays", {})
    if not isinstance(sprays, dict):
        raise ValueError("P1 sprays malformed")
    return {
        "cave_id": CAVE_ID,
        "floors": staged,
        "squad_total": squad_total,
        "floor_seconds": timers,
        "sprays": {"bitter": int(sprays.get("bitter", 0)),
                   "spicy": int(sprays.get("spicy", 0))},
        "ui_index": int(manifest.get("ui_index", 0)),
    }


def stage_run_layout(manifest: dict, output: Path) -> dict:
    staging = validate_p1_manifest(manifest)
    output.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}

    def write(name: str, payload: object) -> None:
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        (output / name).write_text(text, encoding="utf-8")
        files[name] = sha256(text.encode("utf-8"))

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


def p1_main(manifest_path: Path, output: Path) -> dict:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"P1 manifest unreadable: {exc}") from None
    result = stage_run_layout(manifest, output)
    print(f"P1 staged cave={result['cave_id']} floors={result['floors']} "
          f"files={sorted(result['files'])}")
    return result


if __name__ == "__main__":
    main()
