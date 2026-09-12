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
from .stats import UPGRADE_ITEMS, upgrade_pool, current_profiles
ITEM_IDS.update({name: ITEM_BASE + 10 + i for i, name in enumerate(UPGRADE_ITEMS)})
from .benefits import ALL_BENEFIT_ITEMS as BENEFIT_ITEMS, benefit_pool
ITEM_IDS.update({name: ITEM_BASE + 30 + i for i, name in enumerate(BENEFIT_ITEMS)})
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

from .obstacles import OBSTACLES
FINE_POPULATION = {f"Population: {n} total Pikmin": n for n in
                   (*range(20, 101, 10), 125, 150, 175, 200, *range(250, 501, 50))}
PERMANENT_NAMES = COLLECTION_NAMES + tuple(n for n in FINE_POPULATION if n not in TOTAL_POPULATION) + tuple(OBSTACLES)
PERMANENT_LOCATION_IDS = {**COLLECTION_LOCATION_IDS, **{n: LOCATION_BASE + 100 + i
    for i, n in enumerate(PERMANENT_NAMES[len(COLLECTION_NAMES):])}}

# Schema 9 keeps existing AP IDs; retired scout IDs are never reused.
NEW_BESTIARY = {
    # native species, representative audited area, minimum carrier bodies
    "Bestiary: Deliver Dwarf Bulbear": (31, 'The Distant Spring', 3),
    "Bestiary: Deliver Wogpole": (25, 'The Distant Spring', 1),
    "Bestiary: Deliver Spotty Bulbear": (32, 'The Distant Spring', 10),
    "Bestiary: Deliver Yellow Wollywog": (0, 'The Distant Spring', 7),
    "Bestiary: Defeat Puffy Blowhog": (16, 'The Distant Spring', 1),
    "Bestiary: Deliver Swooping Snitchbug": (11, 'The Distant Spring', 3),
    "Bestiary: Deliver Breadbug": (8, 'The Forest Navel', 3),
    "Bestiary: Deliver Puffstool": (9, 'The Forest Navel', 10),
    "Bestiary: Deliver Armored Cannon Beetle": (17, 'The Forest of Hope', 30),
    "Bestiary: Deliver Pearly Clamclamp Pearl": (13, 'The Impact Site', 3),
    "Bestiary: Deliver Mamuta": (24, 'The Impact Site', 8),
}
MODERN_COLLECTION_NAMES = tuple(n for n in COLLECTION_NAMES if not n.endswith(' - Scout')) + tuple(NEW_BESTIARY)
MODERN_PERMANENT_NAMES = MODERN_COLLECTION_NAMES + tuple(n for n in PERMANENT_NAMES if n not in COLLECTION_NAMES)
MODERN_LOCATION_IDS = {**PERMANENT_LOCATION_IDS, **{n: LOCATION_BASE + 200 + i for i, n in enumerate(NEW_BESTIARY)}}

COLOR_POPULATION = {f"Population: {n} total {color} Pikmin": (color, n)
                    for color in ('Red', 'Yellow', 'Blue') for n in FINE_POPULATION.values()}
MODERN_LOCATION_IDS.update({name: LOCATION_BASE + 300 + i for i, name in enumerate(COLOR_POPULATION)})


COMPACT_POPULATION = {f"Population: {n} total {color} Pikmin": (color, n)
                      for color in ("Red", "Yellow", "Blue") for n in (10, 25, 50, 100)}
MODERN_LOCATION_IDS.update({name: LOCATION_BASE + 400 + i for i, name in enumerate(
    n for n in COMPACT_POPULATION if n not in MODERN_LOCATION_IDS)})


def population_checks(manifest):
    if manifest.get("compact_population"): return COMPACT_POPULATION
    thresholds = FINE_POPULATION if has_permanent(manifest) else TOTAL_POPULATION
    if manifest.get('color_population'):
        return {name: row for name, row in COLOR_POPULATION.items() if row[1] in thresholds.values()}
    return thresholds


def has_permanent(manifest):
    return manifest.get('permanent_checks', False) if manifest['schema'] >= 9 else manifest['schema'] == 8

def modern_names(permanent, no_exploration=False, color_population=False, compact_population=False):
    names = MODERN_PERMANENT_NAMES if permanent else MODERN_COLLECTION_NAMES
    if color_population:
        names = tuple(n for n in names if n not in FINE_POPULATION) + tuple(population_checks({'schema': 9, 'permanent_checks': permanent, 'color_population': True, 'compact_population': compact_population}))
    return tuple(n for n in names if not n.startswith('Explore:')) if no_exploration else names

# Corpse minima verified through native PelletConfig, including legacy species.
BESTIARY_WEIGHTS = {3: 3, 4: 10, 18: 1, 19: 1, 20: 1, 15: 7, 30: 5, 33: 7}
BESTIARY_TARGETS = {name: (BESTIARY[legacy][0], BESTIARY_WEIGHTS[BESTIARY[legacy][0]])
                    for name, legacy in DELIVERY_BESTIARY.items()}
BESTIARY_TARGETS.update({name: (row[0], row[2]) for name, row in NEW_BESTIARY.items()})


def bestiary_sources(name, manifest):
    from .enemies import sources_for
    if name not in BESTIARY_TARGETS or 'enemy_layout' not in manifest: return []
    return sources_for(manifest['enemy_layout'], BESTIARY_TARGETS[name][0])

# Filled from the native loaded pellet config audit, not the maximum carrier count.
NATIVE_PART_WEIGHTS = {0: 30, 1: 50, 2: 40, 3: 40, 4: 20, 5: 20, 6: 20, 7: 20, 8: 20, 9: 30, 10: 15, 11: 20, 12: 15, 13: 30, 14: 15, 15: 15, 16: 30, 17: 25, 18: 25, 19: 30, 20: 15, 21: 30, 22: 30, 23: 20, 24: 25, 25: 30, 26: 40, 27: 20, 28: 20, 29: 10}
PART_WEIGHTS = {name: NATIVE_PART_WEIGHTS[part] for name, part in PART_IDS.items()}


def active_names(manifest):
    if manifest['schema'] >= 9: return modern_names(has_permanent(manifest), manifest.get("no_exploration", False), manifest.get("color_population", False), manifest.get("compact_population", False))
    if manifest['schema'] >= 8: return PERMANENT_NAMES
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
    unlocks += upgrade_pool(manifest) if manifest.get('progressive_color_stats') else []
    return unlocks + ([FLARLIC] * (10 - manifest.get("starting_flarlic", 2)) if manifest["schema"] >= 2 else [])


def route_strength(name, manifest, inventory=None):
    profiles = current_profiles(manifest, inventory)
    if not profiles: return 1
    # Retain the legacy route audit: red access is assumed for every part,
    # with yellow/blue where needed. Credit only the weakest required profile,
    # so all members of a qualifying mixed crew meet this lower bound.
    required = {RED} | (set(CHECK_REQUIREMENTS.get(name, ())) & {RED, YELLOW, BLUE})
    if name == POSITRON: required = {RED, YELLOW, BLUE}
    colors = {RED: 'red', YELLOW: 'yellow', BLUE: 'blue'}
    return min(profiles[colors[item]]['carry'] for item in required)


def can_reach_manifest(name, inventory, manifest):
    if 'enemy_layout' in manifest and name in BESTIARY_TARGETS:
        if name not in active_names(manifest): return False
        owned = color_inventory(inventory, manifest)
        if not all(owned.get(c, 0) for c in (RED, YELLOW, BLUE)): return False
        profiles = current_profiles(manifest, inventory)
        strength = min(row['carry'] for row in profiles.values()) if profiles else 1
        if field_capacity(inventory, True, manifest.get('starting_flarlic', 2)) * strength < BESTIARY_TARGETS[name][1]: return False
        start = START_AREAS[manifest['profile']][0]
        for row in bestiary_sources(name, manifest):
            access = next(access for stage, _, access in START_AREAS.values() if stage == row['stage'])
            if row['stage'] == start or inventory.get(access, 0): return True
        return False
    if manifest['schema'] >= 9:
        if name not in active_names(manifest): return False
        if name in NEW_BESTIARY:
            species, area, bodies = NEW_BESTIARY[name]
            start = START_AREAS[manifest['profile']][1]
            owned = color_inventory(inventory, manifest)
            # Preserve conservative return routes; swapped Bulbears can use Hope.
            if species in (31, 32) and manifest.get('enemy_mask', 0) & (1 if species == 31 else 2):
                area = 'The Forest of Hope'
            access = next(a for _, title, a in START_AREAS.values() if title == area)
            return bool((start == area or inventory.get(access, 0))
                and all(owned.get(c, 0) for c in (RED, YELLOW, BLUE))
                and field_capacity(inventory, True, manifest.get('starting_flarlic', 2)) >= bodies)
    if has_permanent(manifest) and name in OBSTACLES:
        stage, kind, _, _ = OBSTACLES[name]
        _, area, access = next(row for row in START_AREAS.values() if row[0] == stage)
        owned = color_inventory(inventory, manifest)
        return bool((START_AREAS[manifest['profile']][1] == area or inventory.get(access, 0))
                    and all(owned.get(c, 0) for c in (RED, YELLOW, BLUE))
                    and (kind != 102 or field_capacity(inventory, True, manifest.get('starting_flarlic', 2)) >= 100))
    if manifest['schema'] >= 7:
        ids = MODERN_LOCATION_IDS if manifest['schema'] >= 9 else PERMANENT_LOCATION_IDS if manifest['schema'] >= 8 else COLLECTION_LOCATION_IDS
        population = population_checks(manifest)
        if name not in ids: return False
        if name in population:
            count = population[name]
            if manifest.get('color_population'):
                color, count = count
                if not color_inventory(inventory, manifest).get(color + ' Onion', 0): return False
            if count <= 20 and (not manifest.get('color_population') or color.lower() == starting_color(manifest)): return True
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
        return all(owned.get(c, 0) for c in (RED, YELLOW, BLUE)) and field_capacity(owned, True, manifest.get('starting_flarlic', 2)) * route_strength(name, manifest, inventory) >= NATIVE_PART_WEIGHTS[27]
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
    return can_reach(name, owned, True, manifest.get('starting_flarlic', 2), route_strength(name, manifest, inventory))


def item_pool(manifest):
    progression = progression_pool(manifest)
    slots = len(active_names(manifest)) - len(progression)
    if manifest.get('benefit_items'):
        repair_count = manifest.get('repair_pool_count', REPAIR_COUNT)
        return progression + [REPAIR] * repair_count + benefit_pool(slots - repair_count, no_heal=manifest.get("compact_population", False), bomb_weight=manifest.get("bomb_rock_weight", 0))
    return progression + [REPAIR] * slots


def check_area(name):
    if name in NEW_BESTIARY: return NEW_BESTIARY[name][1]
    if name in FINE_POPULATION or name in COLOR_POPULATION or name in COMPACT_POPULATION: return 'The Forest of Hope'
    if name in OBSTACLES:
        return next(area for stage, area, _ in START_AREAS.values() if stage == OBSTACLES[name][0])
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
