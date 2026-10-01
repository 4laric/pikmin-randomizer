"""Resolved encounter/check identities for P1 campaigns containing P2 enemies.

The catalog is resolved before fill. Native host types never identify P2 checks.
The saved snapshot, not the current admission table, supplies session identities.
"""
from __future__ import annotations

from .campaign_data import CAMPAIGN_SOURCES, CAMPAIGN_SLOTS
from .enemies import enemy_type
from .catalog import BESTIARY_TARGETS, MODERN_LOCATION_IDS, LOCATION_BASE, modern_names

VERSION = "resolved-enemy-checks-v1"
CAPABILITY = "resolved-enemy-checks-v1"
# Reserved independently of sampling/order. Existing P1 IDs end below +0x600;
# item IDs start at +0x1000. P2 source IDs are retail stable identities (0..101).
P2_LOCATION_OFFSET = 0x600
NO_CHECK_SPECIES = frozenset((9, 10, 11, 16))  # Owner decision #888.
# Owner ruling #1088: "nah get rid of the jellyfloat corpses and the larva
# corpses let's stay P2-accurate"; extended to 66/69 ("yeah thanks").
# Preserve location names/IDs for existing AP worlds; new checks earn on defeat.
P2_KILL_CHECK_SPECIES = frozenset((31, 57, 66, 69, 72))
# Production corpse minima: pc_p2_campaign_policy.h selects these P1 vehicles;
# catalog.BESTIARY_WEIGHTS/NEW_BESTIARY contain the loaded pellet audit.
# Queen/Dango and Fuefuki replace that config in their own native modules.
P2_CARRY_MIN = {
    2: 10, 15: 3, 25: 7, 26: 5, 27: 1, 28: 3, 30: 20, 32: 3,
    33: 10, 34: 3, 35: 10, 38: 3, 40: 3, 41: 3, 43: 10, 44: 3,
    53: 10, 54: 8, 58: 3, 59: 3, 60: 3, 61: 3, 62: 3,
    63: 3, 67: 3, 68: 3, 70: 3, 71: 3, 73: 10,
    75: 30, 76: 3, 78: 7, 79: 3, 84: 3, 93: 3, 94: 20, 101: 3,
}


def p2_check_name(entry):
    return "Bestiary: Deliver P2 " + entry.common_name


def p2_location_id(source_id):
    if type(source_id) is not int or not 0 < source_id < 0x100:
        raise ValueError("invalid P2 check source ID")
    return LOCATION_BASE + P2_LOCATION_OFFSET + source_id


def all_location_ids():
    from experimental.pikmin2_enemy_roster import load_roster
    return {p2_check_name(entry): p2_location_id(entry.source_id) for entry in load_roster()
            if entry.source_id and entry.classification in ("enemy", "boss", "boss_helper")
            and entry.source_id not in NO_CHECK_SPECIES}


def legacy_names(manifest):
    return modern_names(manifest["permanent_checks"], manifest.get("no_exploration", False),
                        manifest.get("color_population", False),
                        manifest.get("compact_population", False), manifest.get("no_sticks", False))


def resolve(manifest, placement, roster, *, proxy_ids=()):
    """Apply exact generator replacement and arena suppression, then select checks.

    CAMPAIGN_SOURCES is the existing persistent P1 source audit, including sources
    outside the replacement pool. Placement supplies additional selected sources
    and their schedules (including groups and boss aliases).
    """
    layout = manifest["p2_layout"]
    entries = {entry.source_id: entry for entry in roster}
    slots = {row["uid"]: row for row in placement["slots"]}
    arenas = {row["id"]: row for row in placement.get("arenas", [])}
    schedules = {row["uid"]: row for row in CAMPAIGN_SLOTS}
    replacements = {}
    suppressed = set()
    for binding in layout["bindings"]:
        target = binding["target"]
        if not isinstance(target, str) or not target.isdigit() or int(target) == 0:
            raise ValueError("resolved catalog requires generator UID bindings")
        uid = int(target)
        if uid in replacements or uid not in slots:
            raise ValueError("duplicate or unknown catalog binding UID")
        replacements[uid] = binding["source_id"]
    for row in layout.get("boss_arenas", {}).get("placed", []):
        arena = arenas.get(row["arena"])
        if arena is None or any(replacements.get(int(t)) != row["source_id"] for t in row["targets"]):
            raise ValueError("catalog arena does not match bindings")
        for uid in arena["spawn_uids"]:
            if uid in replacements and replacements[uid] != row["source_id"]:
                raise ValueError("conflicting catalog arena alias")
            replacements[uid] = row["source_id"]
            slots.setdefault(uid, {**slots[arena["primary_uid"]], "uid": uid})
        suppressed.update(arena["suppress_uids"])
    if suppressed & replacements.keys():
        raise ValueError("catalog generator is both replaced and suppressed")

    actual = {row["uid"]: row["actual"] for row in manifest.get("campaign_layout", {}).get("assignments", [])}
    actual.update({row["uid"]: row["actual"] for row in manifest.get("spawn_layout", {}).get("assignments", [])})
    actual.update({row["uid"]: row["actual"] for row in manifest.get("group_layout", {}).get("assignments", [])})
    sources = []
    for row in CAMPAIGN_SOURCES:
        uid = row["uid"]
        if uid in replacements or uid in suppressed:
            continue
        sources.append(dict(uid=uid, game="p1", species=actual.get(uid, enemy_type(
            row["original"], manifest.get("enemy_mask", 0), row["protected"])),
            stage=row["stage"], first_day=row["first_day"], protected=row["protected"]))
    proxy_ids = set(proxy_ids)
    for uid, source_id in sorted(replacements.items()):
        slot = slots[uid]
        entry = entries.get(source_id)
        if entry is None:
            raise ValueError("catalog has unknown P2 source ID")
        sources.append(dict(uid=uid, game="proxy" if source_id in proxy_ids else "p2",
                            species=source_id, stage=slot["stage"],
                            first_day=slot.get("first_day", schedules.get(uid, {}).get("first_day", 2)),
                            protected=bool(slot.get("protected", False))))
    sources.sort(key=lambda row: (row["game"], row["species"], row["stage"], row["uid"]))

    checks = []
    for native_index, name in enumerate(legacy_names(manifest)):
        target = BESTIARY_TARGETS.get(name)
        if target is None:
            continue
        supplier = 10 if target[0] == 13 else target[0]
        available = [row for row in sources if row["game"] == "p1" and row["species"] == supplier
                     and (target[0] != 13 or not row["protected"])]
        if available:
            checks.append(dict(name=name, id=MODERN_LOCATION_IDS[name], game="p1", species=target[0],
                               event="defeat" if "Defeat " in name else "delivery",
                               carry_min=target[1],
                               native_index=native_index, sources=[row["uid"] for row in available]))
    placed = sorted({row["species"] for row in sources if row["game"] == "p2"} - NO_CHECK_SPECIES)
    for source_id in placed:
        kill_check = source_id in P2_KILL_CHECK_SPECIES
        if not kill_check and source_id not in P2_CARRY_MIN:
            raise ValueError(f"P2 {source_id} needs metadata in P2_CARRY_MIN or in P2_KILL_CHECK_SPECIES for AP checks")
        checks.append(dict(name=p2_check_name(entries[source_id]), id=p2_location_id(source_id),
                           game="p2", species=source_id, event="defeat" if kill_check else "delivery", native_index=None,
                           carry_min=1 if kill_check else P2_CARRY_MIN[source_id],
                           sources=[row["uid"] for row in sources
                                    if row["game"] == "p2" and row["species"] == source_id]))
    return dict(version=VERSION, sources=sources, checks=checks)


def validate(catalog, manifest=None):
    """Validate a saved catalog without consulting a changing admission table."""
    if type(catalog) is not dict or set(catalog) != {"version", "sources", "checks"} or catalog["version"] != VERSION:
        raise ValueError("invalid resolved enemy catalog")
    if type(catalog["sources"]) is not list or type(catalog["checks"]) is not list:
        raise ValueError("invalid resolved catalog tables")
    sources = {}
    for row in catalog["sources"]:
        if type(row) is not dict or set(row) != {"uid", "game", "species", "stage", "first_day", "protected"}:
            raise ValueError("invalid resolved source fields")
        if (type(row["uid"]) is not int or not 0 < row["uid"] < 2**32 or row["uid"] in sources
                or row["game"] not in ("p1", "p2", "proxy") or type(row["species"]) is not int
                or not 0 <= row["species"] < (35 if row["game"] == "p1" else 102)
                or type(row["stage"]) is not int or not 0 <= row["stage"] < 5
                or type(row["first_day"]) is not int or not 1 <= row["first_day"] <= 30
                or type(row["protected"]) is not bool):
            raise ValueError("invalid or duplicate resolved source")
        sources[row["uid"]] = row
    seen_names, seen_ids, seen_species = set(), set(), set()
    for row in catalog["checks"]:
        if type(row) is not dict or set(row) != {"name", "id", "game", "species", "event", "native_index", "sources", "carry_min"}:
            raise ValueError("invalid resolved check fields")
        game, species = row["game"], row["species"]
        if (game not in ("p1", "p2") or type(species) is not int or type(row["name"]) is not str
                or type(row["id"]) is not int or type(row["carry_min"]) is not int or not 1 <= row["carry_min"] <= 100
                or row["name"] in seen_names or row["id"] in seen_ids or (game, species) in seen_species
                or row["event"] not in ("delivery", "defeat")):
            raise ValueError("invalid or duplicate resolved check")
        if game == "p1":
            if (row["name"] not in BESTIARY_TARGETS or BESTIARY_TARGETS[row["name"]][0] != species
                    or MODERN_LOCATION_IDS[row["name"]] != row["id"]
                    or type(row["native_index"]) is not int or row["native_index"] < 0
                    or row["event"] != ("defeat" if "Defeat " in row["name"] else "delivery")):
                raise ValueError("invalid P1 resolved check identity")
        elif (species in NO_CHECK_SPECIES or row["id"] != p2_location_id(species)
              or row["native_index"] is not None
              or not row["name"].startswith("Bestiary: Deliver P2 ")):
            raise ValueError("invalid P2 resolved check identity")
        supplier = 10 if game == "p1" and species == 13 else species
        expected = [s["uid"] for s in catalog["sources"] if s["game"] == game and s["species"] == supplier
                    and (species != 13 or game != "p1" or not s["protected"])]
        if not expected or row["sources"] != expected:
            raise ValueError("missing, foreign or incomplete resolved check sources")
        seen_names.add(row["name"])
        seen_ids.add(row["id"])
        seen_species.add((game, species))
    expected_p2 = {s["species"] for s in sources.values() if s["game"] == "p2"} - NO_CHECK_SPECIES
    if {species for game, species in seen_species if game == "p2"} != expected_p2:
        raise ValueError("resolved catalog omits a placed P2 check")
    if manifest is not None:
        base = legacy_names(manifest)
        expected_p1 = set()
        for name in base:
            if name in BESTIARY_TARGETS:
                species = BESTIARY_TARGETS[name][0]
                supplier = 10 if species == 13 else species
                if any(s["game"] == "p1" and s["species"] == supplier
                       and (species != 13 or not s["protected"]) for s in sources.values()):
                    expected_p1.add(name)
        if {r["name"] for r in catalog["checks"] if r["game"] == "p1"} != expected_p1:
            raise ValueError("resolved catalog omits a surviving P1 check")
        for row in catalog["checks"]:
            if row["game"] == "p1" and (row["native_index"] >= len(base) or base[row["native_index"]] != row["name"]):
                raise ValueError("resolved P1 native index mismatch")
    return catalog


def active_names(manifest):
    """Retain base order; append P2 checks in stable source-ID order."""
    rows = validate(manifest["enemy_catalog"], manifest)["checks"]
    present = {row["name"] for row in rows}
    return tuple(n for n in legacy_names(manifest) if n not in BESTIARY_TARGETS or n in present) + tuple(
        row["name"] for row in rows if row["game"] == "p2")


def check_sources(name, manifest):
    catalog = manifest["enemy_catalog"]
    row = next((row for row in catalog["checks"] if row["name"] == name), None)
    if row is None:
        return []
    uids = set(row["sources"])
    return [source for source in catalog["sources"] if source["uid"] in uids]


def location_ids(manifest):
    checks = {row["name"]: row["id"] for row in manifest["enemy_catalog"]["checks"]}
    return {name: checks[name] if name in checks else MODERN_LOCATION_IDS[name]
            for name in active_names(manifest)}


def bootstrap(manifest):
    if "enemy_catalog" not in manifest:
        return ""
    checks = {row["name"]: row for row in manifest["enemy_catalog"]["checks"]}
    base = legacy_names(manifest)
    parts = ["ENEMY_CHECKS", "1", str(len(active_names(manifest)))]
    for name in active_names(manifest):
        row = checks.get(name)
        if row and row["game"] == "p2":
            sources = check_sources(name, manifest)
            parts += ["P", str(row["species"]), str(len(sources))]
            for source in sources:
                parts += [str(source["uid"]), str(source["stage"])]
        else:
            parts += ["L", str(base.index(name))]
    return " ".join(parts) + "\n"


def can_reach(name, inventory, manifest):
    from .catalog import START_AREAS, RED, YELLOW, BLUE, color_inventory, field_capacity
    from .stats import current_profiles
    check = next((row for row in manifest["enemy_catalog"]["checks"] if row["name"] == name), None)
    if check is None:
        return False
    owned = color_inventory(inventory, manifest)
    colors = {RED: "red", YELLOW: "yellow", BLUE: "blue"}
    available = [color for onion, color in colors.items() if owned.get(onion)]
    # Retain the existing conservative campaign route rule until individual
    # source routes have audited color requirements (#951 U30). The accepted
    # placement supplies legal targets, not proof of early low-cap combat.
    if len(available) != 3:
        return False
    profiles = current_profiles(manifest, inventory)
    strength = min(profiles.get(c, {}).get("carry", 1) for c in available)
    if field_capacity(inventory, True, manifest.get("starting_flarlic", 2)) * strength < check["carry_min"]:
        return False
    start = START_AREAS[manifest["profile"]][0]
    return any(source["stage"] == start or inventory.get(next(
        access for stage, _, access in START_AREAS.values() if stage == source["stage"]), 0)
               for source in check_sources(name, manifest))
