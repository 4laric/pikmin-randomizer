"""P0 source-import-contract adapter for p2-cave-yakushima_4 (issue #161).

Lane shard-caves-yakushima-yakushima4-p0, generation 3. P0 only: no native
build, no runtime, no ADMIT, no playability claim. Issue #161 stays OPEN.

Reuses the shared importers, never forked:
  experimental.pikmin2_cave_catalog.parse   (definition decode)
  experimental.pikmin2_pod.pellet_catalog   (treasure/cargo universe)
  experimental.pikmin2_assets.disc_files / archive_files (ISO access)

Records the observed source sha256, floor/pool coverage and per-floor
roster counts, and cross-checks the real decode against the catalogued
baseline in docs/PIKMIN2_CONTENT_INVENTORY.json (story_caves yakushima_4).
Fails closed with the exact missing prerequisite; no invented values.
"""
import hashlib
import json
import re
from pathlib import Path

LANE = "shard-caves-yakushima-yakushima4-p0"
ISSUE = 161
SOURCE_ID = "yakushima_4"
SCHEMA = "p2-cave-yakushima_4-p0/1"
EXPECTED_FLOORS = 5
DEFAULT_ISO = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")
RESEARCH_ROOT = Path("C:/Users/alari/pikmin-randomizer/native/pikmin2-research")
PELLET_LIST = "user/Abe/Pellet/us/pelletlist_us.szs"
PELLET_CONFIGS = ("otakara_config.txt", "item_config.txt")
EXPECTED_POOLS = (
    "2_units_gw_l_conc.txt",
    "3_units_h_k_pypes_conc.txt",
    "3_units_f_g_m_conc.txt",
    "4_units_d_j_n_o_conc.txt",
    "1_units_manh_boss_conc.txt",
)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def locate_source(iso_path=None):
    iso = Path(iso_path) if iso_path is not None else DEFAULT_ISO
    if not iso.is_file():
        return {"available": False, "iso": None, "prerequisite":
                "legal local US GPVE01 ISO exposing user/Mukki/mapunits/"
                "caveinfo/yakushima_4.txt (read-only input; no invented values)"}
    return {"available": True, "iso": str(iso), "prerequisite": None}


def _read_disc(iso, catalog, path):
    at, size = catalog[path]
    with iso.open("rb") as handle:
        handle.seek(at)
        data = handle.read(size)
    if len(data) != size:
        raise ValueError("truncated disc source: " + path)
    return data


def build_universes(iso_path=None, research_root=None):
    from experimental.pikmin2_assets import archive_files, disc_files
    from experimental.pikmin2_pod import pellet_catalog

    found = locate_source(iso_path)
    if not found["available"]:
        raise ValueError(found["prerequisite"])
    iso = Path(found["iso"])
    research = Path(research_root) if research_root else RESEARCH_ROOT
    enemy_path = research / "src/plugProjectYamashitaU/enemyInfo.cpp"
    if not enemy_path.is_file():
        raise ValueError("missing read-only research source: %s" % enemy_path)
    enemy_ids = set(re.findall(r'\{"([A-Za-z0-9_]+)"',
                               enemy_path.read_text(encoding="utf-8")))
    if not enemy_ids:
        raise ValueError("no enemy names decoded from enemyInfo.cpp")
    catalog = disc_files(iso)
    if PELLET_LIST not in catalog:
        raise ValueError("missing disc pellet list: " + PELLET_LIST)
    archive = archive_files(_read_disc(iso, catalog, PELLET_LIST))
    treasure_ids = set()
    for name in PELLET_CONFIGS:
        if name not in archive:
            raise ValueError("missing pellet config: " + name)
        treasure_ids.update(pellet_catalog(archive[name].decode("shift_jis")))
    if not treasure_ids:
        raise ValueError("no treasure/cargo names decoded")
    return enemy_ids, treasure_ids


def decode(iso_path=None, research_root=None):
    import experimental.pikmin2_cave_catalog as cave_catalog
    from experimental.pikmin2_assets import disc_files

    found = locate_source(iso_path)
    if not found["available"]:
        raise ValueError(found["prerequisite"])
    iso = Path(found["iso"])
    enemy_ids, treasure_ids = build_universes(iso_path, research_root)
    catalog = disc_files(iso)
    path = cave_catalog.BASE + "/caveinfo/" + SOURCE_ID + ".txt"
    if path not in catalog:
        raise ValueError("cave definition absent from ISO: " + path)
    data = _read_disc(iso, catalog, path)
    parsed = dict(cave_catalog.parse(data.decode("shift_jis"), enemy_ids,
                                     treasure_ids))
    parsed["source_path"] = path
    parsed["source_bytes"] = len(data)
    parsed["source_sha256"] = sha256_bytes(data)
    return parsed


def _decoded_floors(parsed):
    rows = []
    for floor in parsed["floors"]:
        rows.append({
            "first": floor["first_floor"],
            "last": floor["last_floor"],
            "unit_pool": floor["parameters"].get("f008"),
            "enemies": len(floor["enemies"]),
            "treasures": len(floor["treasures"]),
            "gates": len(floor["gates"]),
            "caps": len(floor["caps"]),
            "treasure_ids": [t["treasure_id"] for t in floor["treasures"]],
        })
    return rows


def audit(iso_path=None, research_root=None, inventory_doc=None,
          parsed=None):
    parsed = parsed if parsed is not None else decode(iso_path, research_root)
    floors = _decoded_floors(parsed)
    coverage = [f["first"] for f in floors]
    if coverage != list(range(1, EXPECTED_FLOORS + 1)):
        raise ValueError("floor coverage is not contiguous 1..%d: %s"
                         % (EXPECTED_FLOORS, coverage))
    findings = []
    pools = [f["unit_pool"] for f in floors]
    if tuple(pools) != EXPECTED_POOLS:
        findings.append("unit pool sequence differs from catalogued baseline")

    baseline = None
    if inventory_doc is not None:
        caves = inventory_doc.get("story_caves")
        if not isinstance(caves, list):
            raise ValueError("inventory document has no story_caves list")
        baseline = next((c for c in caves if c.get("id") == SOURCE_ID), None)
        if baseline is None:
            raise ValueError("inventory has no story_caves entry: " + SOURCE_ID)
        base_floors = baseline["floors"]
        if len(base_floors) != len(floors):
            findings.append("floor count differs from catalogued baseline")
        else:
            for got, want in zip(floors, base_floors):
                if got["first"] != want["first"] or got["unit_pool"] != want["unit_pool"]:
                    findings.append("floor %s framing differs" % got["first"])
                if got["enemies"] != len(want["enemy_ids"]):
                    findings.append("floor %s enemy count differs" % got["first"])
                if got["treasures"] != len(want["treasure_ids"]):
                    findings.append("floor %s treasure count differs" % got["first"])

    blockers = [
        "P1 runtime import: no native cave/floor runtime consumes this decode "
        "(cave generation provider #129; save/progression #132)",
        "asset closure: per-unit arc/texts.szs presence is not verified here "
        "(shared cave inventory owns unit asset checks)",
        "runtime deps #128/#131/#140/#144/#145/#146 remain open for playable "
        "acceptance",
    ]
    return {
        "schema": SCHEMA,
        "lane": LANE,
        "issue": ISSUE,
        "source_id": SOURCE_ID,
        "source_path": parsed["source_path"],
        "source_bytes": parsed["source_bytes"],
        "source_sha256": parsed["source_sha256"],
        "definition_count": parsed["definition_count"],
        "floor_count": parsed["floor_count"],
        "floors": floors,
        "unit_pools": pools,
        "baseline_floor_count": len(baseline["floors"]) if baseline else None,
        "findings": findings,
        "blockers": blockers,
        "generated": False,
        "limitations": [
            "Static source decode only; no runtime, placement or gameplay run.",
            "Weights/counts are definition inputs, not final spawn instances.",
            "Unit asset closure beyond referenced pool names is not asserted here.",
        ],
        "reused_importers": [
            "experimental.pikmin2_cave_catalog.parse",
            "experimental.pikmin2_pod.pellet_catalog",
            "experimental.pikmin2_assets.disc_files/archive_files",
        ],
    }


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, default=None)
    parser.add_argument("--research-root", type=Path, default=None)
    parser.add_argument("--inventory", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    inventory = (json.loads(args.inventory.read_text(encoding="utf-8"))
                 if args.inventory else None)
    packet = audit(args.iso, args.research_root, inventory)
    text = json.dumps(packet, indent=2, sort_keys=False)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
