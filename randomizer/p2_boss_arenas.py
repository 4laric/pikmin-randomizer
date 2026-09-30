"""P2 boss arenas: P1 boss spawns that a P2 boss replaces (#899).

Owner ruling (2026-09-29, #3): P2 bosses are placed only in designated boss
arenas in the P1 maps, replacing the P1 boss there. This module is the source
catalogue of every P1 boss spawn. The rows were read from the retail
``dataDir/stages/*/*.gen`` files with ``scripts/audit_enemy_slots.py``:
GenObjectBoss ids 0 Spider, 1 Snake, 2 Slime, 3 King and 7 BoxSnake, plus the
teki-hosted bosses TEKI_Kinoko (9) and TEKI_Beatle (17). The catalogue also
records each arena's generator uids, day schedule and held drop, and whether
it is eligible today.

An arena is a set of P1 generator uids at one encounter site:

* ``spawn_uids`` are the generators that birth the P2 boss. The first one
  (the arena's ``primary_uid``) is bound to the boss through the ordinary
  ``ENEMY_P2`` line. The rest are the same encounter on other day files (the
  Impact Goolix has one generator per even day file); native re-keys them
  to the primary (``kAlias``), so the boss appears on each day the Goolix
  would and keeps one generator token.
* ``suppress_uids`` are P1 boss arena mates that native keeps empty while the
  arena holds a P2 boss (``native pc_port/pc_p2_boss_arena_policy.h``
  ``kSuppress``; ``tests/test_p2_boss_arenas.py`` pins the mirror).
* ``protected_drop`` names a held ship part or the goal boss. A protected
  arena is catalogued and measured but never eligible. Its placement slot
  carries ``protected: true``, which :func:`randomizer.p2_placement.evaluate`
  denies.
* ``held_part_transfer`` (#901) lifts that protection for an arena whose only
  protected drop is a ship part: the P2 boss born there holds the P1 boss's
  part (native ``pc_p2_boss_arena_birth`` puts the generator's pellet-config
  part in the personality ``mID``; teki-hosted arenas already carry it in the
  generator personality) and drops it on a real death through the generic
  BTeki death funnel (native ``pc_port/pc_held_part.cpp``). The part keeps its
  vanilla stage, so logic, checks and the Archipelago location are unchanged.
  Owner ruling (#901, 2026-09-29): P2 bosses may take every ship-part arena,
  and the Puffstool arena too ("the Omega Stabilizer (uf09) goes to the
  occupant"); the Puffstool *bestiary check* is not re-keyed (#905 decides
  bestiary). Only the goal boss (Emperor, Final Trial) stays protected
  ("leave alone for now (finale)", same ruling). #948 flipped the three
  part arenas and the Puffstool arena accordingly; the transfer mechanism is
  the same one the seed-generated holder run proved on #901.

The Hope Cannon Beetle (``hope_0-29_3073``, uid 2506165730) is deliberately
**not** an arena. It is already an ordinary admitted P2 slot, and turning it
into an arena would change every non-boss layout.

``ARENA_BOSS_SOURCES`` lists the P2 bosses whose *real-seed* placement is an
arena: the four the lane names (30 Queen, 73 BigTreasure, 94 DangoMushi,
later 66 Houdai). The other IS_ENEMY_BOSS species already proven on ordinary
slots (34/70 snagrets, 53 KingChappy, 56/69 Long Legs, 71/101 Bloysters)
keep their ordinary placement until the owner moves them.

Arena placement is a data rule, not a cast list (#948, CONTRIBUTING rule 4):
the boss profile is accepted on any slot whose measured clearance
(``radius``) covers the encounter ``footprint_radius``. Ordinary slots carry
the unmeasured default radius (100), so in a real seed only the measured
arenas qualify; a smoke seed (``scripts/p2_smoke_seed.py``) or a measured
ordinary slot places the same boss anywhere its footprint fits.
"""
from __future__ import annotations

ARENA_SCHEMA = "p2-boss-arena-v1"

# P2 bosses confined to boss arenas: source_id -> roster enum name.
ARENA_BOSS_SOURCES = {30: "Queen", 73: "BigTreasure", 94: "DangoMushi", 66: "Houdai", 40: "OoPanModoki"}

# GenObjectBoss ids (include/Boss.h GenBossID) and the teki boss hosts.
GENBOSS = {0: "Spider", 1: "Snake", 2: "Slime", 3: "King", 7: "BoxSnake"}

P1_BOSS_ARENAS = (
    {
        "id": "impact_goolix",
        "stage": 0,
        "p1_boss": "Goolix (GenObjectBoss Slime 2)",
        "p1_kind": "boss", "p1_type": 2,
        "center": [-815.7, 20.0, 654.3],
        # practice/{8,10,...,28}.gen@1764: days 9,11,...,29; no held part
        # (4 random-colour 5-pellets carry over to the P2 vehicle).
        "spawn_uids": [4019261003, 2380628347, 2299547974, 2215518465, 2163994940,
                       2654126479, 336062330, 284309319, 502023936, 421107517, 131114894],
        "suppress_uids": [],
        "first_day": 9,
        "respawn_days": 0,
        "protected_drop": None,
        "held_part_transfer": False,
    },
    {
        "id": "hope_snagret_pit",
        "stage": 1,
        "p1_boss": "Burrowing Snagret pair (BoxSnake 7 + Snake 1)",
        "p1_kind": "boss", "p1_type": 7,
        "center": [-867.4, -17.5, 3901.8],
        # stage1/0-29.gen@3264 BoxSnake (spawn) and @3428 Snake (suppressed);
        # days 2-30, respawn every 5 days; no held part. The BoxSnake spot is
        # the spawn because it is on the carry-route graph (route_distance
        # 166.9); the Snake spot is 241.6 from the nearest waypoint (route=0).
        "spawn_uids": [295337326],
        "suppress_uids": [2026735859],
        "first_day": 2,
        "respawn_days": 5,
        "protected_drop": None,
        "held_part_transfer": False,
    },
    {
        "id": "hope_snagret_part",
        "stage": 1,
        "p1_boss": "Burrowing Snagret (BoxSnake 7) holding a ship part",
        "p1_kind": "boss", "p1_type": 7,
        "center": [-460.0, -17.2, 3708.6],
        "spawn_uids": [4260179239],
        "suppress_uids": [],
        "first_day": 2,
        "respawn_days": 30,
        "protected_drop": "ship part (pellet config 29)",
        # #948: owner permits P2 bosses on every ship-part arena (#901); the
        # boss-arena birth path carries the pellet-config part in mID.
        # #924 evidence: a seed-placed P2 own-FSM occupant in this arena dropped uf06 and the
        # carried part fired CHECK 9 Pikmin: Geiger Counter (vanilla index), run g8, native
        # log sha256 c2389cd96d82daeea68df75de74463bb8c76b989c5e67e35e47625b39bdcfa1a.
        "held_part_transfer": True,
    },
    {
        "id": "navel_beady_long_legs",
        "stage": 2,
        "p1_boss": "Beady Long Legs (Spider 0)",
        "p1_kind": "boss", "p1_type": 0,
        "center": [1543.1, -195.1, 618.9],
        "spawn_uids": [304372265],
        "suppress_uids": [],
        "first_day": 2,
        "respawn_days": 30,
        "protected_drop": "ship part (pellet config 26)",
        "held_part_transfer": True,  # #948 / #901 owner ruling, as above
    },
    {
        "id": "navel_puffstool",
        "stage": 2,
        "p1_boss": "Puffstool (TEKI_Kinoko 9)",
        "p1_kind": "teki", "p1_type": 9,
        "center": [1394.5, -267.8, 1784.6],
        "spawn_uids": [2974383966],
        "suppress_uids": [],
        "first_day": 2,
        "respawn_days": 30,
        "protected_drop": "ship part uf09",
        # #948: owner ruling #901 (2026-09-29): "The arena may take a P2
        # occupant, and the Omega Stabilizer (uf09) goes to the occupant."
        # The Puffstool bestiary check is decided separately (#905).
        "held_part_transfer": True,
    },
    {
        "id": "spring_cannon_beetle",
        "stage": 3,
        "p1_boss": "Armored Cannon Beetle (TEKI_Beatle 17)",
        "p1_kind": "teki", "p1_type": 17,
        "center": [-450.9, 89.0, -941.4],
        "spawn_uids": [2903640892],
        "suppress_uids": [],
        "first_day": 2,
        "respawn_days": 30,
        "protected_drop": "ship part ust1",
        "held_part_transfer": True,  # #948 / #901 owner ruling, as above
    },
    {
        "id": "last_emperor",
        "stage": 4,
        "p1_boss": "Emperor Bulblax (King 3)",
        "p1_kind": "boss", "p1_type": 3,
        "center": [0.0, -25.0, 2700.0],
        "spawn_uids": [3759070123],
        "suppress_uids": [],
        "first_day": 2,
        "respawn_days": 30,
        "protected_drop": "ship part (pellet config 48) and the emperor_bulblax goal",
        # Owner: "Emperor arena: leave alone for now (finale). Stays
        # protected." (#901 comment 5892787827). Also unmeasured.
        "held_part_transfer": False,
    },
)


def arena_protected(arena):
    """True when the arena's held drop keeps a P2 boss out (#899/#901)."""
    return bool(arena["protected_drop"]) and not arena.get("held_part_transfer", False)


def arenas_by_id():
    return {arena["id"]: arena for arena in P1_BOSS_ARENAS}


def all_arena_uids():
    """Every catalogued P1 boss-arena generator uid (spawn + suppressed)."""
    uids = []
    for arena in P1_BOSS_ARENAS:
        uids += list(arena["spawn_uids"]) + list(arena["suppress_uids"])
    return uids


def alias_pairs():
    """(day-file uid, arena primary spawn uid) pairs, as native kAlias."""
    return [(uid, arena["spawn_uids"][0])
            for arena in P1_BOSS_ARENAS for uid in arena["spawn_uids"][1:]]


def suppress_pairs():
    """(suppressed uid, arena primary spawn uid) pairs, as native kSuppress."""
    return [(uid, arena["spawn_uids"][0])
            for arena in P1_BOSS_ARENAS for uid in arena["suppress_uids"]]


# Encounter descriptors per arena boss. ``footprint_radius`` is the flat,
# dry, wall-free disc the fight needs; it must not exceed the arena slot's
# measured clearance (``radius``), so a small arena rejects a large boss.
BOSS_ENCOUNTERS = {
    "DangoMushi": {
        "id": "dangomushi_arena", "source_id": 94, "family_lane": 25,
        "footprint_radius": 150.0, "helper_budget": 0,
        "required_gates": ["arena", "roll", "crush", "flick", "rock_rain", "death", "reward"],
        "notes": ("Segmented Crawbster arena (#899, #897): the roll crashes into the arena "
                  "wall by design, so it needs a floor of radius >= 150 rather than an open field."),
    },
    "Queen": {
        "id": "queen_arena", "source_id": 30, "family_lane": 24,
        "footprint_radius": 250.0, "helper_budget": 10,
        "required_gates": ["arena", "roll", "flick", "larva_birth", "death", "reward"],
        "notes": ("Empress Bulblax arena (#899, #256): territory 200 plus a 50 roll margin; "
                  "helper_budget is the native larva cap."),
    },
    "BigTreasure": {
        "id": "bigtreasure_arena", "source_id": 73, "family_lane": 32,
        "footprint_radius": 250.0, "helper_budget": 0,
        "required_gates": ["arena", "weapons", "element_attacks", "flick", "death", "reward"],
        "notes": "Titan Dweevil arena (#899, #246): 4-leg IK gait spans about 207 units.",
    },
    "OoPanModoki": {
        "id": "oopanmodoki_arena", "source_id": 40, "family_lane": 18,
        "footprint_radius": 200.0, "helper_budget": 0,
        "required_gates": ["arena", "wander", "haul", "press", "death", "reward"],
        "notes": ("Giant Breadbug arena (#958): the encounter disc is the source territory, fp09 200 "
                  "(oopanmodoki/enemyparm.txt); the haul runs the carry-route graph out of the arena, so "
                  "no larger floor is needed."),
    },
    "Houdai": {
        "id": "houdai_arena", "source_id": 66, "family_lane": 26,
        "footprint_radius": 250.0, "helper_budget": 0,
        "required_gates": ["arena", "walk", "volley", "flick", "death", "reward"],
        "notes": "Man-at-Legs arena (#899): admission waits for a real walk animation (owner ruling 4).",
    },
}

ARENA_GATES = ["placement.xyz", "placement.terrain", "placement.route", "bridge.spawn",
               "placement.boss_arena"]
ARENA_HELPER_CAPACITY = 10


def _arena_slot(arena, measured):
    evidence = measured.get("evidence", {}) if measured else {}
    return {
        "uid": arena["spawn_uids"][0],
        "label": arena["id"],
        "stage": arena["stage"],
        "terrain": "ground",
        "radius": float(measured["clear"]) if measured else 0.0,
        "water_depth": 0,
        "flight_space": False,
        "burrow_ground": True,
        "home": False,
        "helper_capacity": ARENA_HELPER_CAPACITY,
        "projectile_corridor": False,
        "corpse_route": bool(evidence.get("route")),
        "protected": arena_protected(arena),
        "boss_slot": True,
        "first_day": arena["first_day"],
        "respawn_days": arena["respawn_days"],
        "source_identity": f"p1_boss:{arena['p1_kind']}:{arena['p1_type']}",
        "cohort": None,
        "evidence": {key: bool(evidence.get(key)) for key in ("xyz", "terrain", "route")},
    }


def _arena_record(arena, measured):
    record = {
        "id": arena["id"],
        "stage": arena["stage"],
        "primary_uid": arena["spawn_uids"][0],
        "spawn_uids": list(arena["spawn_uids"]),
        "suppress_uids": list(arena["suppress_uids"]),
        "p1_boss": arena["p1_boss"],
        "p1_kind": arena["p1_kind"],
        "p1_type": arena["p1_type"],
        "center": list(arena["center"]),
        "first_day": arena["first_day"],
        "respawn_days": arena["respawn_days"],
        "protected_drop": arena["protected_drop"],
        "held_part_transfer": bool(arena.get("held_part_transfer", False)),
    }
    if measured:
        record["measured"] = dict(measured)
    return record


def apply_to_document(document, measurements, pool_ids=None):
    """Return ``document`` with the boss arenas, arena slots, descriptors and
    arena-boss profiles (re)written from this catalogue. Idempotent. Non-boss
    slots and profiles are left exactly as they are."""
    arena_uids = {arena["spawn_uids"][0] for arena in P1_BOSS_ARENAS}
    boss_names = set(BOSS_ENCOUNTERS)
    descriptor_ids = {spec["id"] for spec in BOSS_ENCOUNTERS.values()}
    slots = [slot for slot in document["slots"] if slot["uid"] not in arena_uids]
    slots += [_arena_slot(arena, measurements.get(arena["id"])) for arena in P1_BOSS_ARENAS]
    primaries = [arena["spawn_uids"][0] for arena in P1_BOSS_ARENAS
                 if not arena_protected(arena) and measurements.get(arena["id"])]
    profiles = [profile for profile in document["profiles"] if profile["identity"] not in boss_names]
    encounters = [enc for enc in document.get("encounters", []) if enc["id"] not in descriptor_ids]
    if pool_ids is None:
        from .seed import PLAYABLE_P2_SPECIES
        pool_ids = PLAYABLE_P2_SPECIES
    for identity, spec in BOSS_ENCOUNTERS.items():
        encounters.append({
            "id": spec["id"], "identity": identity, "terrains": ["ground"],
            "footprint_radius": spec["footprint_radius"], "helper_budget": spec["helper_budget"],
            "arena_slots": {"min": 1, "max": 1}, "phases": 1, "protected_drops": [],
            "required_gates": list(spec["required_gates"]), "notes": spec["notes"],
        })
        if spec["source_id"] not in pool_ids:
            # Descriptor only: the profile lands with the boss's pool admission.
            continue
        profiles.append({
            "identity": identity, "terrains": ["ground"], "family_lane": spec["family_lane"],
            "footprint_radius": spec["footprint_radius"], "min_water_depth": 0,
            "requires_flight_space": False, "requires_burrow_ground": False, "requires_home": False,
            "helper_budget": spec["helper_budget"], "requires_projectile_corridor": False,
            "requires_corpse_route": True, "is_boss": True, "encounter_descriptor": spec["id"],
            "accepted_gates": list(ARENA_GATES), "allow_protected": False,
            "requires_renewable_slot": False, "min_first_day": 0,
            "notes": (f"P2 source_id {spec['source_id']}; boss arena placement (#899, owner ruling "
                      "2026-09-29 #3): placed only in P1 boss arenas, replacing the P1 boss; "
                      "accepted on every measured, unprotected arena whose clearance fits the "
                      f"{spec['id']} footprint. Pool admission is still the family lane's natural "
                      "kill -> carry -> Onion receipt."),
            "cohort": None,
            "accepted_slot_uids": list(primaries),
        })
    result = dict(document)
    # Arena slots follow the ordinary slots, so slot-order consumers (and
    # tests that trim the ordinary slots) see the ordinary set first.
    result["slots"] = slots
    result["profiles"] = profiles
    result["encounters"] = encounters
    result["arenas"] = [_arena_record(arena, measurements.get(arena["id"])) for arena in P1_BOSS_ARENAS]
    return result


def main(argv=None):
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description="Write the P2 boss arenas into the placement document")
    parser.add_argument("document", type=Path)
    args = parser.parse_args(argv)
    document = json.loads(args.document.read_text(encoding="utf-8"))
    document = apply_to_document(document, ARENA_MEASUREMENTS)
    # #901: P1 ship-part holder teki slots (held_part_transfer per slot).
    from .p2_held_parts import apply_to_document as apply_held_parts
    document = apply_held_parts(document)
    from .p2_placement import validate_document
    validate_document(document)
    args.document.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return 0


# Native clearance/placement measurements at the arena spawn generator's
# birth position (native pc_p2_boss_arena.cpp P2_BOSS_ARENA_PROBE: 16 rays in
# 25-unit steps to 500, a ray stops at missing ground, water, a >20 height step
# or >60 from the floor; ``clear`` = smallest reach, ``median`` = typical
# reach; plus pc_p2_placement_probe P2_PLACEMENT_SLOT xyz/terrain/route).
# Runs: output/claude-orch/p2-boss-arenas/runs/m1-<area>-none, native
# claude/p2-boss-arenas exe sha256 574f2748..., PIKMIN_P2_BOSS_ARENA_PROBE=1
# (impact at PIKMIN_P2_TEST_START_DAY=9 so 8.gen's Goolix is live). The Final
# Trial is not a start area and stays unmeasured; an arena without a
# measurement is never eligible.
_M1 = "output/claude-orch/p2-boss-arenas/runs/m1-{}-none native.log sha256 {}"
ARENA_MEASUREMENTS = {
    "impact_goolix": {
        "uid": 4019261003, "clear": 275, "median": 350, "max": 500,
        "water_rays": 0, "wall_rays": 14, "offmap_rays": 0, "route_distance": 73.9,
        "evidence": {"xyz": True, "terrain": True, "route": True},
        "run": _M1.format("impact", "9d699fffeaf8ca4773981ef1bd111a5ebcc4ac66dbdd428d8643a1167cf00a67"),
    },
    "hope_snagret_pit": {
        "uid": 295337326, "clear": 200, "median": 488, "max": 500,
        "water_rays": 3, "wall_rays": 5, "offmap_rays": 0, "route_distance": 166.9,
        "evidence": {"xyz": True, "terrain": True, "route": True},
        "suppressed_mate": {"uid": 2026735859, "clear": 250, "median": 488, "route_distance": 241.6},
        "run": _M1.format("forest", "c3ec900e6fa7c04758c9858b7ca99a280aea71578c242baf2f338e3c94ebfd5c"),
    },
    "hope_snagret_part": {
        "uid": 4260179239, "clear": 200, "median": 412, "max": 500,
        "water_rays": 1, "wall_rays": 9, "offmap_rays": 0, "route_distance": 191.6,
        "evidence": {"xyz": True, "terrain": True, "route": True},
        "run": _M1.format("forest", "c3ec900e6fa7c04758c9858b7ca99a280aea71578c242baf2f338e3c94ebfd5c"),
    },
    "navel_beady_long_legs": {
        "uid": 304372265, "clear": 250, "median": 300, "max": 500,
        "water_rays": 0, "wall_rays": 15, "offmap_rays": 0, "route_distance": 44.2,
        "evidence": {"xyz": True, "terrain": True, "route": True},
        "run": _M1.format("navel", "ac2f2a17a4a8803b9328023f86ee0119fc4c57c461d8f21aa5457d6c65f11470"),
    },
    "navel_puffstool": {
        "uid": 2974383966, "clear": 350, "median": 412, "max": 500,
        "water_rays": 0, "wall_rays": 13, "offmap_rays": 0, "route_distance": 70.5,
        "evidence": {"xyz": True, "terrain": True, "route": True},
        "run": _M1.format("navel", "ac2f2a17a4a8803b9328023f86ee0119fc4c57c461d8f21aa5457d6c65f11470"),
    },
    "spring_cannon_beetle": {
        "uid": 2903640892, "clear": 250, "median": 300, "max": 500,
        "water_rays": 0, "wall_rays": 15, "offmap_rays": 0, "route_distance": 23.8,
        "evidence": {"xyz": True, "terrain": True, "route": True},
        "run": _M1.format("spring", "7d16e9ff55f100c4e0deb86b57e539e9f5a7a1bfb04106740b25735f47a59a47"),
    },
}


if __name__ == "__main__":
    raise SystemExit(main())
