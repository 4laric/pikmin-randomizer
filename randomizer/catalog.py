"""Inherited Pikmin catalog; native route validation remains pending.

Part indices/names follow native include/Pellet.h. Area membership is checked
against retail stages/stage1, stage2, stage3 and last generator part IDs (Geiger
Counter and Guard Satellite are enemy drops). Color routes follow the pinned
Pikmin AP reference; see output/overnight1/pikmin-routes.md for audit limits. Onion
*discovery* never requires the item it can award, avoiding circular unlocks.
"""
YELLOW = "Yellow Onion"
BLUE = "Blue Onion"
NAVEL_ACCESS = "Pikmin: Forest Navel Access"
SPRING_ACCESS = "Pikmin: Distant Spring Access"
TRIAL_ACCESS = "Pikmin: Final Trial Access"
ITEM_NAMES = (YELLOW, BLUE, NAVEL_ACCESS, SPRING_ACCESS, TRIAL_ACCESS)

PART_NAMES = {
    0: "Bowsprit", 1: "Gluon Drive", 2: "Anti-Dioxin Filter", 3: "Eternal Fuel Dynamo",
    5: "Whimsical Radar", 6: "Interstellar Radio", 7: "Guard Satellite", 8: "Chronos Reactor",
    9: "Radiation Canopy", 10: "Geiger Counter", 11: "Sagittarius", 12: "Libra",
    13: "Omega Stabilizer", 14: "Ionium Jet 1", 15: "Ionium Jet 2", 16: "Shock Absorber",
    17: "Gravity Jumper", 18: "Pilot's Seat", 19: "Nova Blaster", 20: "Automatic Gear",
    21: "Zirconium Rotor", 22: "Extraordinary Bolt", 23: "Repair-type Bolt", 24: "Space Float",
    25: "Massage Machine", 26: "Secret Safe", 28: "Analog Computer", 29: "UV Lamp",
}
PART_IDS = {"Pikmin: " + name: index for index, name in PART_NAMES.items()}
AREA_PARTS = {
    "The Forest of Hope": (3, 5, 9, 10, 11, 16, 19, 22),
    "The Forest Navel": (2, 7, 12, 13, 14, 17, 20, 24, 28),
    "The Distant Spring": (0, 1, 6, 8, 15, 18, 21, 23, 25, 29),
    "The Final Trial": (26,),
}
AREA_ACCESS = {
    "The Forest of Hope": None,
    "The Forest Navel": NAVEL_ACCESS,
    "The Distant Spring": SPRING_ACCESS,
    "The Final Trial": TRIAL_ACCESS,
}
CHECK_AREAS = {"Pikmin: " + PART_NAMES[index]: area for area, indices in AREA_PARTS.items() for index in indices}
# Factual color requirements from TheLynk/Archipelago P1Data.py at
# 59a392a12f9c4a7f6aba76d4f184e27423c51f6b. Red is always available in BBFT.
# Preserve the reference's conservative colors (e.g. Gravity Jumper needs blue).
YELLOW_PARTS = frozenset((5, 7, 8, 9, 10, 12, 19, 21, 22, 26, 29))
BLUE_PARTS = frozenset((1, 2, 6, 8, 9, 10, 11, 12, 14, 15, 17, 21, 23, 25, 26, 28))
REFINED_REQUIREMENTS = {
    name: ((YELLOW,) if PART_IDS[name] in YELLOW_PARTS else ())
          + ((BLUE,) if PART_IDS[name] in BLUE_PARTS else ())
          + ((AREA_ACCESS[area],) if AREA_ACCESS[area] else ())
    for name, area in CHECK_AREAS.items()
}
CHECK_AREAS.update({"Pikmin: Yellow Onion Discovery": "The Forest of Hope",
                    "Pikmin: Blue Onion Discovery": "The Forest Navel"})
REFINED_REQUIREMENTS.update({"Pikmin: Yellow Onion Discovery": (),
                           "Pikmin: Blue Onion Discovery": (NAVEL_ACCESS,)})
# Old slot data has no refined-logic marker. Retain its exact original rules.
CHECK_REQUIREMENTS = {
    name: (() if index in (3, 16) else (YELLOW, BLUE))
          + ((AREA_ACCESS[CHECK_AREAS[name]],) if AREA_ACCESS[CHECK_AREAS[name]] else ())
    for name, index in PART_IDS.items()
}
CHECK_REQUIREMENTS.update({"Pikmin: Yellow Onion Discovery": (),
                           "Pikmin: Blue Onion Discovery": (NAVEL_ACCESS,)})

GAME = "Pikmin Randomizer"
LOCATION_BASE = 0x504B0000
ITEM_BASE = 0x504B1000
REPAIR = "Ship Repair"
UNLOCKS = ITEM_NAMES
NAMES = tuple(PART_IDS) + ("Pikmin: Yellow Onion Discovery", "Pikmin: Blue Onion Discovery")
LOCATION_IDS = {name: LOCATION_BASE + i for i, name in enumerate(NAMES)}
ITEM_IDS = {name: ITEM_BASE + i for i, name in enumerate((*UNLOCKS, REPAIR))}
REPAIR_COUNT = len(NAMES) - len(UNLOCKS)

# Schema-2 additions only. Never reorder the schema-1 names or item IDs.
FLARLIC = "Progressive Flarlic"
ITEM_IDS[FLARLIC] = ITEM_BASE + 6
FOREST_ACCESS = "Pikmin: Forest of Hope Access"
ITEM_IDS[FOREST_ACCESS] = ITEM_BASE + 7
POPULATION = {f"Population: {n} Pikmin in the field": n for n in range(20, 101, 10)}
BESTIARY = {
    "Bestiary: Dwarf Bulborb": (3, ()),
    "Bestiary: Spotty Bulborb": (4, ()),
    "Bestiary: Female Sheargrub": (18, ()),
    "Bestiary: Male Sheargrub": (19, ()),
    "Bestiary: Shearwig": (20, ()),
    "Bestiary: Fiery Blowhog": (15, (NAVEL_ACCESS,)),
    "Bestiary: Water Dumple": (30, (SPRING_ACCESS, BLUE)),
    "Bestiary: Wollywog": (33, (NAVEL_ACCESS, BLUE)),
}
EXPLORATION = {}
for stage, (area, access) in enumerate(AREA_ACCESS.items(), 1):
    for objective in ("Land", "Scout"):
        EXPLORATION[f"Explore: {area} - {objective}"] = (stage, objective, (access,) if access else ())
EXPANDED_NAMES = NAMES + tuple(POPULATION) + tuple(BESTIARY) + tuple(EXPLORATION)
ALL_LOCATION_IDS = {name: LOCATION_BASE + i for i, name in enumerate(EXPANDED_NAMES)}

# Filled from the native loaded pellet config audit, not the maximum carrier count.
NATIVE_PART_WEIGHTS = {0: 30, 1: 50, 2: 40, 3: 40, 4: 20, 5: 20, 6: 20, 7: 20, 8: 20, 9: 30, 10: 15, 11: 20, 12: 15, 13: 30, 14: 15, 15: 15, 16: 30, 17: 25, 18: 25, 19: 30, 20: 15, 21: 30, 22: 30, 23: 20, 24: 25, 25: 30, 26: 40, 27: 20, 28: 20, 29: 10}
PART_WEIGHTS = {name: NATIVE_PART_WEIGHTS[part] for name, part in PART_IDS.items()}


def active_names(manifest):
    return EXPANDED_NAMES if manifest["schema"] >= 2 else NAMES


def field_capacity(inventory, expanded=True):
    return min(100, 20 + 10 * inventory.get(FLARLIC, 0)) if expanded else 100


def can_reach(name, inventory, expanded=False):
    if name in CHECK_REQUIREMENTS:
        needs = CHECK_REQUIREMENTS[name]
        minimum = PART_WEIGHTS.get(name, 0) if expanded else 0
    elif expanded and name in POPULATION:
        needs, minimum = (), POPULATION[name]
    elif expanded and name in BESTIARY:
        needs, minimum = BESTIARY[name][1], 20
    elif expanded and name in EXPLORATION:
        stage, objective, needs = EXPLORATION[name]
        if objective == "Scout":
            needs = needs + (YELLOW, BLUE)  # conservative pending route playtest
        minimum = 20
    else:
        return False
    return all(inventory.get(item, 0) > 0 for item in needs) and field_capacity(inventory, expanded) >= minimum


def progression_pool(manifest):
    unlocks = list(UNLOCKS)
    if manifest.get('profile') == 'navel-day2':
        unlocks[unlocks.index(NAVEL_ACCESS)] = FOREST_ACCESS
    return unlocks + ([FLARLIC] * 8 if manifest["schema"] >= 2 else [])


def can_reach_manifest(name, inventory, manifest):
    if manifest['schema'] < 3:
        return can_reach(name, inventory, manifest['schema'] == 2)
    start = 'The Forest Navel' if manifest['profile'] == 'navel-day2' else 'The Forest of Hope'
    if name not in POPULATION:
        area = check_area(name)
        access = FOREST_ACCESS if area == 'The Forest of Hope' else AREA_ACCESS[area]
        if area != start and not inventory.get(access, 0):
            return False
    # Evaluate existing conservative color/weight rules after area access.
    owned = dict(inventory)
    for access in (NAVEL_ACCESS, SPRING_ACCESS, TRIAL_ACCESS):
        owned[access] = 1
    return can_reach(name, owned, True)


def item_pool(manifest):
    progression = progression_pool(manifest)
    return progression + [REPAIR] * (len(active_names(manifest)) - len(progression))


def check_area(name):
    if name in CHECK_AREAS:
        return CHECK_AREAS[name]
    if name in POPULATION:
        return "The Forest of Hope"
    if name in BESTIARY:
        needs = BESTIARY[name][1]
        return ("The Forest Navel" if NAVEL_ACCESS in needs else
                "The Distant Spring" if SPRING_ACCESS in needs else "The Forest of Hope")
    return tuple(AREA_ACCESS)[EXPLORATION[name][0] - 1]
