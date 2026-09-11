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
RED = 'Red Onion'
ITEM_IDS[RED] = ITEM_BASE + 8
IMPACT_ACCESS = 'Pikmin: Impact Site Access'
ITEM_IDS[IMPACT_ACCESS] = ITEM_BASE + 9
START_AREAS = {
    'impact-day2': (0, 'The Impact Site', IMPACT_ACCESS),
    'foh-day2': (1, 'The Forest of Hope', FOREST_ACCESS),
    'navel-day2': (2, 'The Forest Navel', NAVEL_ACCESS),
    'spring-day2': (3, 'The Distant Spring', SPRING_ACCESS),
    'trial-day2': (4, 'The Final Trial', TRIAL_ACCESS),
}
POSITRON = 'Pikmin: Positron Generator'
ALL_PART_IDS = {**PART_IDS, POSITRON: 27}


def starting_color(manifest):
    return manifest.get('starting_color', 'red')


def color_inventory(inventory, manifest):
    owned = dict(inventory)
    owned[{'red': RED, 'yellow': YELLOW, 'blue': BLUE}[starting_color(manifest)]] = 1
    return owned
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
IMPACT_EXPLORATION = {f'Explore: The Impact Site - {objective}': (0, objective, (IMPACT_ACCESS,)) for objective in ('Land', 'Scout')}
ALL_EXPLORATION = {**EXPLORATION, **IMPACT_EXPLORATION}
ALL_AREA_NAMES = EXPANDED_NAMES + tuple(IMPACT_EXPLORATION) + (POSITRON,)
ALL_AREA_LOCATION_IDS = {name: LOCATION_BASE + i for i, name in enumerate(ALL_AREA_NAMES)}
TOTAL_POPULATION = {f"Population: {n} total Pikmin": n for n in (20, 40, 60, 80, 100, 150, 200, 300, 500)}
DELIVERY_BESTIARY = {name.replace('Bestiary: ', 'Bestiary: Deliver '): name for name in BESTIARY}
COLLECTION_NAMES = NAMES + tuple(TOTAL_POPULATION) + tuple(DELIVERY_BESTIARY) + tuple(ALL_EXPLORATION) + (POSITRON,)
COLLECTION_LOCATION_IDS = {name: ALL_AREA_LOCATION_IDS[name] if name in ALL_AREA_LOCATION_IDS else LOCATION_BASE + len(ALL_AREA_NAMES) + i
                           for i, name in enumerate(tuple(TOTAL_POPULATION) + tuple(DELIVERY_BESTIARY))}
COLLECTION_LOCATION_IDS = {name: ALL_AREA_LOCATION_IDS.get(name, COLLECTION_LOCATION_IDS.get(name)) for name in COLLECTION_NAMES}

# Filled from the native loaded pellet config audit, not the maximum carrier count.
NATIVE_PART_WEIGHTS = {0: 30, 1: 50, 2: 40, 3: 40, 4: 20, 5: 20, 6: 20, 7: 20, 8: 20, 9: 30, 10: 15, 11: 20, 12: 15, 13: 30, 14: 15, 15: 15, 16: 30, 17: 25, 18: 25, 19: 30, 20: 15, 21: 30, 22: 30, 23: 20, 24: 25, 25: 30, 26: 40, 27: 20, 28: 20, 29: 10}
PART_WEIGHTS = {name: NATIVE_PART_WEIGHTS[part] for name, part in PART_IDS.items()}


def active_names(manifest):
    if manifest['schema'] >= 7: return COLLECTION_NAMES
    if manifest['schema'] >= 5: return ALL_AREA_NAMES
    return EXPANDED_NAMES if manifest["schema"] >= 2 else NAMES


def field_capacity(inventory, expanded=True, starting_flarlic=2):
    return min(100, 10 * (starting_flarlic + inventory.get(FLARLIC, 0))) if expanded else 100


def can_reach(name, inventory, expanded=False, starting_flarlic=2, carry_strength=1):
    if name in CHECK_REQUIREMENTS:
        needs = CHECK_REQUIREMENTS[name]
        minimum = (PART_WEIGHTS.get(name, 0) + carry_strength - 1) // carry_strength if expanded else 0
    elif expanded and name in POPULATION:
        needs, minimum = (), POPULATION[name]
    elif expanded and name in BESTIARY:
        needs, minimum = BESTIARY[name][1], 20
    elif expanded and name in EXPLORATION:
        stage, objective, needs = EXPLORATION[name]
        if objective == "Scout":
            needs = needs + (YELLOW, BLUE)  # conservative pending route playtest
        minimum = 1 if objective == "Land" else 20
    else:
        return False
    return all(inventory.get(item, 0) > 0 for item in needs) and field_capacity(inventory, expanded, starting_flarlic) >= minimum


def progression_pool(manifest):
    unlocks = list(UNLOCKS)
    if manifest['schema'] >= 5:
        unlocks = [YELLOW, BLUE] + [access for profile, (_, _, access) in START_AREAS.items() if profile != manifest['profile']]
    elif manifest.get('profile') == 'navel-day2':
        unlocks[unlocks.index(NAVEL_ACCESS)] = FOREST_ACCESS
    if starting_color(manifest) != 'red':
        unlocks[unlocks.index({'yellow': YELLOW, 'blue': BLUE}[starting_color(manifest)])] = RED
    return unlocks + ([FLARLIC] * (10 - manifest.get("starting_flarlic", 2)) if manifest["schema"] >= 2 else [])


def route_strength(name, manifest):
    if 'color_stats' not in manifest: return 1
    # Retain the legacy route audit: red access is assumed for every part,
    # with yellow/blue where needed. Credit only the weakest required profile,
    # so all members of a qualifying mixed crew meet this lower bound.
    required = {RED} | (set(CHECK_REQUIREMENTS.get(name, ())) & {RED, YELLOW, BLUE})
    if name == POSITRON: required = {RED, YELLOW, BLUE}
    colors = {RED: 'red', YELLOW: 'yellow', BLUE: 'blue'}
    return min(manifest['color_stats'][colors[item]]['carry'] for item in required)


def can_reach_manifest(name, inventory, manifest):
    if manifest['schema'] >= 7:
        if name not in COLLECTION_LOCATION_IDS: return False
        if name in TOTAL_POPULATION:
            if TOTAL_POPULATION[name] <= 20: return True
            owned = color_inventory(inventory, manifest)
            start = START_AREAS[manifest['profile']][1]
            return bool(start == 'The Forest of Hope' or inventory.get(FOREST_ACCESS, 0)
                        or ((start == 'The Forest Navel' or inventory.get(NAVEL_ACCESS, 0)) and owned.get(RED, 0)))
        if name in DELIVERY_BESTIARY:
            # Carry-home approaches remain conservative until route playtests.
            owned = color_inventory(inventory, manifest)
            if not all(owned.get(c, 0) for c in (RED, YELLOW, BLUE)): return False
            return can_reach_manifest(DELIVERY_BESTIARY[name], inventory, {**manifest, 'schema': 6})
    if manifest['schema'] < 3:
        return can_reach(name, inventory, manifest['schema'] == 2, manifest.get('starting_flarlic', 2))
    start = START_AREAS[manifest['profile']][1]
    owned = color_inventory(inventory, manifest) if manifest['schema'] >= 4 else dict(inventory)
    moved_species = name == 'Bestiary: Spotty Bulborb' and manifest.get('enemy_mask', 0) & 2
    if moved_species:
        # Untagged adult Bulbears were verified in Distant Spring's native boot.
        # Protected dwarf Bulborbs remain in Forest of Hope; no new source assumed.
        return (start == 'The Distant Spring' or inventory.get(SPRING_ACCESS, 0)) and all(owned.get(c, 0) for c in (RED, YELLOW, BLUE))
    if manifest['schema'] >= 5:
        if name not in ALL_AREA_LOCATION_IDS: return False
        if name in POPULATION and POPULATION[name] > 20:
            # Only audited legacy farming access can justify higher populations.
            farm = start == 'The Forest of Hope' or inventory.get(FOREST_ACCESS, 0)
            farm = farm or ((start == 'The Forest Navel' or inventory.get(NAVEL_ACCESS, 0)) and owned.get(RED, 0))
            if not farm: return False
    if name not in POPULATION:
        area = check_area(name)
        access = next(access for _, title, access in START_AREAS.values() if title == area)
        if area != start and not inventory.get(access, 0):
            return False
    if manifest['schema'] >= 5 and name in IMPACT_EXPLORATION:
        return IMPACT_EXPLORATION[name][1] == 'Land' or all(owned.get(c, 0) for c in (RED, YELLOW, BLUE))
    if manifest['schema'] >= 5 and name == POSITRON:
        return all(owned.get(c, 0) for c in (RED, YELLOW, BLUE)) and field_capacity(owned, True, manifest.get('starting_flarlic', 2)) * route_strength(name, manifest) >= NATIVE_PART_WEIGHTS[27]
    # Evaluate existing conservative color/weight rules after area access.
    if manifest['schema'] >= 4:
        # Legacy routes assumed permanent red access. Preserve that assumption
        # explicitly until individual fire-free part/scout routes are audited.
        needs_red = name in PART_IDS or (name in EXPLORATION and EXPLORATION[name][1] == 'Scout') or name == 'Bestiary: Fiery Blowhog'
        if name in BESTIARY and check_area(name) == 'The Forest Navel':
            needs_red = True  # The approaches were only modeled with reds available.
        # Do not assume non-red Navel squads can farm beyond their starting 20.
        if name in POPULATION and POPULATION[name] > 20 and start == 'The Forest Navel':
            needs_red = not inventory.get(FOREST_ACCESS, 0)
        if needs_red and not owned.get(RED, 0):
            return False
    for access in (NAVEL_ACCESS, SPRING_ACCESS, TRIAL_ACCESS):
        owned[access] = 1
    return can_reach(name, owned, True, manifest.get('starting_flarlic', 2), route_strength(name, manifest))


def item_pool(manifest):
    progression = progression_pool(manifest)
    return progression + [REPAIR] * (len(active_names(manifest)) - len(progression))


def check_area(name):
    if name in TOTAL_POPULATION: return 'The Forest of Hope'
    if name in DELIVERY_BESTIARY: return check_area(DELIVERY_BESTIARY[name])
    if name == POSITRON or name in IMPACT_EXPLORATION: return 'The Impact Site'
    if name in CHECK_AREAS:
        return CHECK_AREAS[name]
    if name in POPULATION:
        return "The Forest of Hope"
    if name in BESTIARY:
        needs = BESTIARY[name][1]
        return ("The Forest Navel" if NAVEL_ACCESS in needs else
                "The Distant Spring" if SPRING_ACCESS in needs else "The Forest of Hope")
    return tuple(AREA_ACCESS)[EXPLORATION[name][0] - 1]
