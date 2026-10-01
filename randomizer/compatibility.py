"""Explicit external naming aliases; never rename persisted seed identities.

Reference: TheLynk/Archipelago Apworld-Pikmin, 24f4c1216e640b1b13ace84c330a1b627e3e3ea0.
Population aliases are deliberately excluded: squad size and total population
are different checks, even when color and threshold match.
"""
from copy import deepcopy
from .catalog import ALL_PART_IDS, ALL_AREA_LOCATION_IDS, MODERN_LOCATION_IDS

THELYNK_REFERENCE = "24f4c1216e640b1b13ace84c330a1b627e3e3ea0"
AREA_ABBREVIATIONS = dict(zip(
    ("The Impact Site", "The Forest of Hope", "The Forest Navel", "The Distant Spring", "The Final Trial"),
    ("TIS", "TFoH", "TFN", "TDS", "TFT")))
# Native UfoPartID order. These are physical identity facts, not progression rules.
_PARTS = (
    ("Bowsprit", "ust1", 3), ("Gluon Drive", "ust2", 3),
    ("Anti-Dioxin Filter", "ust3", 2), ("Eternal Fuel Dynamo", "ust4", 1),
    ("Main Engine", "ust5", 0), ("Whimsical Radar", "uf01", 1),
    ("Interstellar Radio", "uf02", 3), ("Guard Satellite", "uf03", 2),
    ("Chronos Reactor", "uf04", 3), ("Radiation Canopy", "uf05", 1),
    ("Geiger Counter", "uf06", 1), ("Sagittarius", "uf07", 1),
    ("Libra", "uf08", 2), ("Omega Stabilizer", "uf09", 2),
    ("#1 Ionium Jet", "uf10", 2), ("#2 Ionium Jet", "uf11", 3),
    ("Shock Absorber", "un01", 1), ("Gravity Jumper", "un02", 2),
    ("Pilot's Seat", "un03", 3), ("Nova Blaster", "un04", 1),
    ("Automatic Gear", "un05", 2), ("Zirconium Rotor", "un06", 3),
    ("Extraordinary Bolt", "un07", 1), ("Repair-type Bolt", "un08", 3),
    ("Space Float", "un09", 2), ("Massage Machine", "un10", 3),
    ("Secret Safe", "un11", 4), ("Positron Generator", "un12", 0),
    ("Analog Computer", "un13", 2), ("UV Lamp", "un14", 3),
)
_local_names = {index: name for name, index in ALL_PART_IDS.items()}
_local_ids = {**ALL_AREA_LOCATION_IDS, **MODERN_LOCATION_IDS}
PART_CROSSWALK = tuple(dict(
    native_index=index, fourcc=model, stage=stage,
    area=tuple(AREA_ABBREVIATIONS)[stage],
    local_location=_local_names.get(index),
    local_location_id=_local_ids.get(_local_names.get(index)),
    thelynk_item=name,
    thelynk_location=f"{tuple(AREA_ABBREVIATIONS.values())[stage]} - {name}",
    thelynk_item_id=71400 + index, thelynk_location_id=71400 + index,
) for index, (name, model, stage) in enumerate(_PARTS))


def part_identity(value):
    """Resolve a part index, fourCC, or exact supported name; reject ambiguity."""
    for row in PART_CROSSWALK:
        if (type(value) is int and value == row["native_index"]) or (
                type(value) is str and value in (row["fourcc"], row["local_location"],
                                                 row["thelynk_item"], row["thelynk_location"])):
            return deepcopy(row)
    raise ValueError("unknown ship-part identity: " + str(value))


def naming_crosswalk():
    return dict(schema=1, reference=THELYNK_REFERENCE, parts=deepcopy(PART_CROSSWALK),
                population_note="TheLynk counts followers; local checks count total population. No aliases.")


def restore_slot_manifest(slot_data):
    """Restore server-resolved generation, without consulting YAML or RNG."""
    from .seed import fingerprint
    if type(slot_data) is not dict or type(slot_data.get("manifest")) is not dict:
        raise ValueError("tracker slot data requires a manifest")
    manifest = deepcopy(slot_data["manifest"])
    if manifest.get("mode") != "ap":
        raise ValueError("tracker requires an AP manifest")
    if fingerprint(manifest) != slot_data.get("manifest_fingerprint"):
        raise ValueError("tracker manifest fingerprint mismatch")
    return manifest
