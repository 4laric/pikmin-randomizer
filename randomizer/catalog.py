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
