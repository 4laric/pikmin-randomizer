"""P0 import adapter for P2 Challenge ch_MAT_t_hunter_otakara (issue #555).

Decodes the retail caveinfo definition
``user/Mukki/mapunits/caveinfo/ch_MAT_t_hunter_otakara.txt`` from a local US
GPVE01 disc image, validates its hash and floor coverage against the catalogued
lane baseline, checks resource closure (unit pool, unit archives, light
config), and emits a metadata-only import manifest. Weighted Teki/Item rows
stay definitions: this module never fabricates runtime placements, spawn
counts, or completion behavior.

This is a treasure-hunter stage: the ItemInfo block lists the stage's target
treasures, and the TekiInfo block fields four elemental Otakara that carry
treasures. Shared parsing is reused by import, never reimplemented:
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

SCHEMA = "p2-challenge-ch_mat_t_hunter_otakara-p0-v1"
CAVE_ID = "ch_MAT_t_hunter_otakara"
CAVE_PATH = "user/Mukki/mapunits/caveinfo/ch_MAT_t_hunter_otakara.txt"
UNITS_BASE = "user/Mukki/mapunits/units"
ARC_BASE = "user/Mukki/mapunits/arc"
LIGHT_PATH = "user/Abe/cave/normal_light_cha.ini"
PELLET_ARCHIVE = "user/Abe/Pellet/us/pelletlist_us.szs"
EXPECTED_SHA256 = "25b3cfe3a9c95a77710facb0633326e33857781129477161724696e532cee4be"
EXPECTED_SHA256_BYTES = 1371

# Observed source facts (verified against the extracted definition; asserted
# by check_stage, not assumed). Teki rows are (source_token, weight, type).
EXPECTED_FLOORS = (
    {
        "unit": "1_MAT_manp_2_conc.txt",
        "enemies": (
            ("FireOtakara_be_dama_red", 10, 5),
            ("WaterOtakara_be_dama_blue", 10, 5),
            ("GasOtakara_flower_blue", 10, 5),
            ("FireOtakara_be_dama_red", 20, 1),
            ("WaterOtakara_be_dama_blue", 20, 1),
            ("GasOtakara_flower_blue", 20, 1),
            ("ElecOtakara_wadou_kaichin", 20, 1),
        ),
        "carried": (
            ("FireOtakara", "be_dama_red"),
            ("WaterOtakara", "be_dama_blue"),
            ("GasOtakara", "flower_blue"),
            ("FireOtakara", "be_dama_red"),
            ("WaterOtakara", "be_dama_blue"),
            ("GasOtakara", "flower_blue"),
            ("ElecOtakara", "wadou_kaichin"),
        ),
        "treasures": ("key", "saru_head", "badminton", "turi_uki", "toy_cat",
                      "chocolate_l", "toy_ring_c_blue", "ichigo_l", "ahiru_head",
                      "bird_hane"),
        "caps": (),
    },
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


def check_hash(actual: str, size: int | None = None) -> None:
    if actual != EXPECTED_SHA256:
        raise ValueError(
            f"Source hash mismatch: got {actual}, lane baseline {EXPECTED_SHA256}")
    if size is not None and size != EXPECTED_SHA256_BYTES:
        raise ValueError(
            f"Source size mismatch: got {size}, lane baseline {EXPECTED_SHA256_BYTES}")


def check_stage(cave: dict) -> None:
    """Assert complete floor coverage and exact observed per-floor content."""
    if cave.get("definition_count") != 1 or cave.get("floor_count") != 1:
        raise ValueError(
            f"Floor coverage mismatch: definitions={cave.get('definition_count')} "
            f"floors={cave.get('floor_count')}, expected 1/1")
    floors = cave.get("floors", [])
    if len(floors) != 1:
        raise ValueError("Missing floor definitions")
    occupied = set()
    for floor in floors:
        occupied.update(range(floor["first_floor"], floor["last_floor"] + 1))
    if occupied != {1}:
        raise ValueError(f"Floor range gap: occupied={sorted(occupied)}")
    for index, (floor, expected) in enumerate(zip(floors, EXPECTED_FLOORS)):
        if floor["parameters"].get("f008") != expected["unit"]:
            raise ValueError(
                f"Floor {index + 1} unit pool mismatch: "
                f"{floor['parameters'].get('f008')!r} != {expected['unit']!r}")
        got_enemies = tuple((e["source_token"], e["source_weight"], e["placement_type"])
                            for e in floor["enemies"])
        if got_enemies != expected["enemies"]:
            raise ValueError(f"Floor {index + 1} enemy roster mismatch: {got_enemies}")
        got_carried = tuple((e["enemy_id"], e["carried_treasure"])
                            for e in floor["enemies"])
        if got_carried != expected["carried"]:
            raise ValueError(f"Floor {index + 1} carried-treasure mismatch: {got_carried}")
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
    """Cross-check the catalogued lane baseline (floors, timers, roster)."""
    if int(details.get("floors")) != 1:
        raise ValueError("Lane baseline floor count changed")
    if [float(v) for v in details.get("floor_seconds", [])] != [180.0]:
        raise ValueError("Lane baseline floor timers changed")
    if int(details.get("table_order")) != 13:
        raise ValueError("Lane baseline table order changed")
    if int(details.get("ui_index")) != 23:
        raise ValueError("Lane baseline UI index changed")
    if int(details.get("treasure_count_field")) != 6:
        raise ValueError("Lane baseline treasure-count field changed")
    if float(details.get("legacy_time", -1)) != 300.0:
        raise ValueError("Lane baseline legacy time changed")
    if (details.get("bitter_sprays"), details.get("spicy_sprays")) != (0, 0):
        raise ValueError("Lane baseline spray counts changed")
    roster = details.get("pikmin_by_native_color_and_maturity", [])
    expected = [[0, 0, 25], [0, 0, 25], [0, 0, 25], [0, 0, 0], [0, 0, 25],
                [0, 0, 0], [0, 0, 0]]
    if [[int(v) for v in row] for row in roster] != expected:
        raise ValueError("Lane baseline starting roster changed")


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
        if LIGHT_PATH not in catalog:
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
        "source_bytes": EXPECTED_SHA256_BYTES,
        "english_title": None,
        "floors": [
            {"number": n + 1,
             "unit_pool": floor["parameters"]["f008"],
             "light": floor["parameters"].get("f009"),
             "room_count": floor["parameters"].get("f005"),
             "return_geyser": floor["parameters"].get("f007"),
             "alpha_attribute": floor["parameters"].get("f011"),
             "beta_attribute": floor["parameters"].get("f012"),
             "hidden_floor": floor["parameters"].get("f013"),
             "enemy_max": floor["parameters"].get("f002"),
             "item_max": floor["parameters"].get("f003"),
             "enemies": floor["enemies"],
             "treasures": floor["treasures"],
             "gates": floor["gates"],
             "caps": floor["caps"]}
            for n, floor in enumerate(cave["floors"])
        ],
        "starting_roster": details["pikmin_by_native_color_and_maturity"],
        "floor_seconds": [float(v) for v in details["floor_seconds"]],
        "legacy_time": float(details["legacy_time"]),
        "sprays": {"bitter": details["bitter_sprays"], "spicy": details["spicy_sprays"]},
        "ui_index": details["ui_index"],
        "treasure_count_field": details["treasure_count_field"],
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
        if lane.get("lane") == "p2-challenge-ch_mat_t_hunter_otakara":
            return lane.get("details", {})
    raise ValueError("Lane entry missing from import plan")


def run(iso_path: Path, enemyinfo_cpp: Path, lanes_json: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    log: list[str] = []
    raw, digest = read_disc_bytes(iso_path, CAVE_PATH)
    log.append(f"source bytes={len(raw)} sha256={digest}")
    check_hash(digest, len(raw))
    log.append("hash and size match lane baseline")
    text = raw.decode("shift_jis")
    cave = decode(text, load_enemy_ids(enemyinfo_cpp), load_treasure_ids(iso_path))
    log.append(f"decoded floors={cave['floor_count']}")
    check_stage(cave)
    log.append("floor coverage + per-floor rosters/carried treasures verified")
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
    units = sum(len(p["units"]) for p in result["resource_closure"]["unit_pools"].values())
    print(f"floors=1 units={units} manifest={args.output / 'manifest.json'}")


if __name__ == "__main__":
    main()
