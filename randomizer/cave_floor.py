"""Standalone developer cave descriptor; never a campaign or AP seed manifest."""
import hashlib
import json
import os
import time
from pathlib import Path

POLICY = "forest1-bounded-v1"
NAMES = ("Pikmin 2: forest_1 F1 Water Treasure", "Pikmin 2: forest_1 F1 Electric Treasure")
ITEMS = dict(zip(("treasure_water", "treasure_elec"), NAMES))
SCHEMA = "p2-bounded-developer-cave/1"


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
    # Derive path hazards from the same table sent to native generation. Local
    # buds are deliberately NOT a capacity-based OR: capacity is not supply.
    colors = {"water": "blue", "elec": "yellow"}
    table = floor["table"]
    result = {}
    for treasure in table["treasures"]:
        hazards = {treasure["leaf_hazard"]}
        hazards.update(c["hazard"] for c in table["chokes"] if c["before_segment"] <= treasure["segment"])
        result[treasure["treasure_id"]] = [colors[h] for h in sorted(hazards)]
    return result


def create(seed, slot="Player1"):
    if type(seed) is not str or not seed or type(slot) is not str or not slot:
        raise ValueError("cave seed and slot must be nonempty strings")
    floor = resolve(seed, slot)
    return dict(schema=SCHEMA, seed=seed, slot=slot, policy=POLICY,
                table=floor["table"], required_colors=requirements(floor))


def validate(descriptor):
    if type(descriptor) is not dict:
        raise ValueError("expected standalone developer cave descriptor")
    expected = create(descriptor.get("seed"), descriptor.get("slot"))
    # Canonical JSON also rejects bools substituted for integer fields.
    if json.dumps(descriptor, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True):
        raise ValueError("incompatible standalone cave descriptor (campaign/AP unsupported)")
    return descriptor


def fingerprint(descriptor):
    validate(descriptor)
    return hashlib.sha256(json.dumps(descriptor, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def atomic_write(path, text):
    """Cave-local journal replacement; never opens a campaign session."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    deadline = time.monotonic() + 1
    while True:
        try:
            os.replace(temporary, path)
            return
        except PermissionError as error:
            if os.name != "nt" or getattr(error, "winerror", None) not in (5, 32, 33) or time.monotonic() >= deadline:
                raise
            time.sleep(.01)
