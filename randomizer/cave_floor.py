"""Opt-in bounded forest_1 floor contract. No population inference from capacity."""
import hashlib
import json

POLICY = "forest1-bounded-v1"
NAMES = ("Pikmin 2: forest_1 F1 Water Treasure", "Pikmin 2: forest_1 F1 Electric Treasure")
# Appended range; no historical location is renumbered.
LOCATION_IDS = {name: 0x504B0000 + 1000 + i for i, name in enumerate(NAMES)}
ITEMS = dict(zip(("treasure_water", "treasure_elec"), NAMES))


def resolve(seed, slot):
    from experimental.pikmin2_cave_schema import validate_floor_table, slot_id
    material = json.dumps([POLICY, str(seed), slot], separators=(",", ":")).encode()
    floor_seed = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    sid = lambda kind, index: slot_id("forest_1", 1, kind, index)
    table = dict(schema=1, seed=str(floor_seed), cave_id="forest_1", floor=1,
        unit_pool=POLICY, unit_candidates=["room_north3_1_tsuchi"],
        segments=[dict(slot_id=sid("segment", i), index=i) for i in range(2)],
        chokes=[dict(slot_id=sid("choke", 0), index=0, after_segment=0,
                     before_segment=1, hazard="water", kind="hard", hardness="hard", unit="way2_tsuchi")],
        leaves=[dict(slot_id=sid("leaf", i), index=i, segment=i, hazard=h, item_slots=1)
                for i,h in enumerate(("water", "elec"))],
        buds=[dict(slot_id=sid("bud", i), index=i, segment=i, species=s, count=5)
              for i,s in enumerate(("blue", "yellow"))],
        treasures=[dict(treasure_id=t, slot_id=sid("leaf", i), segment=i, leaf_hazard=h)
                   for i,(t,h) in enumerate((("treasure_water","water"),("treasure_elec","elec")))],
        hole=dict(slot_id=sid("segment", 1), segment=1), generated=True, geometry_rerolls=True)
    validate_floor_table(table)
    return dict(policy=POLICY, table=table)


def requirements(floor):
    from .catalog import BLUE, YELLOW
    # Derive path hazards from the same table sent to native generation. Local
    # buds are deliberately NOT a capacity-based OR: capacity is not supply.
    colors = {"water": BLUE, "elec": YELLOW}
    table = floor["table"]
    result = {}
    for treasure in table["treasures"]:
        hazards = {treasure["leaf_hazard"]}
        hazards.update(c["hazard"] for c in table["chokes"] if c["before_segment"] <= treasure["segment"])
        result[ITEMS[treasure["treasure_id"]]] = [[{"item": colors[h]}] for h in sorted(hazards)]
    return result


def validate(manifest):
    if manifest.get("mode") != "solo":
        raise ValueError("bounded cave AP delivery is not implemented")
    if manifest.get("schema") != 9:
        raise ValueError("bounded cave requires modern checks")
    expected = resolve(manifest["seed"], manifest["slot"])
    if manifest.get("p2_cave_floor") != expected or manifest.get("cave_requirements") != requirements(expected):
        raise ValueError("incompatible bounded cave content or requirements")
