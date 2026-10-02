"""Final-source food metadata and conservative growth evaluation.

This candidate does not change generation or legacy population rules. Logical
route/combat branches must be reviewed before a supplier can justify growth;
decoded coordinates alone do not establish a route or a gameplay guarantee.
"""
from __future__ import annotations

import copy
import json

VERSION = "final-population-supply-v1"
COLORS = ("blue", "red", "yellow")  # Loaded PelletConfig color enum.
# Genuine owners must install independently reviewed, immutable UID route and
# Onion retrieval proofs here. Saved manifests/YAML cannot create these proofs.
STATIC_ROUTES = {}
STATIC_BOOTSTRAPS = {}
# Audited P1 native corpse identities; never applied to a P2 host vehicle.
P1_CORPSE_CONFIG = {3: "tkch", 4: "tksw", 8: "tkco", 9: "tkki", 11: "tkna",
                    15: "tkta", 17: "tkbe", 18: "tkka", 19: "tkkb", 20: "tkkc",
                    24: "tkmu", 25: "tkot", 30: "tknm", 31: "tkcb", 32: "tksb", 33: "tkfw"}


def repeatable_at_cap(row):
    """Source-backed calendar/reload condition, not physical farming acceptance."""
    schedule = row["schedule"]
    first, expiry = schedule["first_day"], schedule["expires_after_day"]
    if first is None or first > 29 or (expiry is not None and expiry < 29):
        return False
    cached = row["carry_flags"] & 1
    if cached:
        return bool(row["carry_flags"] & 4) and row["respawn_days"] == 0
    return schedule["mode"] == "every-visit" or (
        schedule["mode"] == "daily-file" and first == 29)


def resolve(manifest, reviewed_routes=None, inputs=None):
    """Snapshot final identities, suppression, counts, timing and guaranteed food.

    Missing route/combat review remains explicit and contributes no logic supply.
    P2 module overrides are intentionally unquantified until independently audited.
    """
    if inputs is None:
        from .population_supply_data import INPUTS
        inputs = INPUTS
    from .enemy_catalog import validate, P2_KILL_CHECK_SPECIES
    validate(manifest["enemy_catalog"], manifest)
    final = {row["uid"]: row for row in manifest["enemy_catalog"]["sources"]}
    from .seed import _default_admitted_placement
    arenas = {row["id"]: row for row in _default_admitted_placement().get("arenas", [])}
    suppressed = {uid for row in manifest["p2_layout"].get("boss_arenas", {}).get("placed", [])
                  for uid in arenas[row["arena"]]["suppress_uids"]}
    configs = {row["model_id"]: row for row in inputs["configs"]}
    routes = reviewed_routes or {}
    from .catalog import UNLOCKS, FLARLIC
    from .stats import UPGRADE_ITEMS
    allowed_requirements = set(UNLOCKS) | set(UPGRADE_ITEMS) | {FLARLIC}
    for uid, branch in routes.items():
        if (type(uid) is not int or type(branch) is not dict
                or branch.get("version") != "source-backed-logic-v1"
                or not isinstance(branch.get("evidence"), str) or not branch["evidence"]
                or type(branch.get("requires")) is not list
                or not set(branch["requires"]) <= allowed_requirements
                or type(branch.get("carrier_colors")) is not list
                or not branch["carrier_colors"] or not set(branch["carrier_colors"]) <= set(COLORS)):
            raise ValueError("invalid reviewed supplier logic branch")
    suppliers = []
    for raw in inputs["generators"]:
        uid = raw["uid"]
        source = final.get(uid)
        row = dict(uid=uid, source_record=raw["source_record"], file_sha256=raw["file_sha256"],
                   stage=raw["stage"], kind=raw["kind"], count=raw["count_min"],
                   schedule=copy.deepcopy(raw["schedule"]), carry_flags=raw["carry_flags"],
                   respawn_days=raw["respawn_days"], repeatable_at_cap=repeatable_at_cap(raw),
                   game=source["game"] if source else "p1",
                   species=source["species"] if source else raw["species"],
                   suppressed=uid in suppressed, carrier_slots=0, carry_min=0,
                   yields={color: 0 for color in COLORS}, reason="unquantified supplier",
                   logic_route=copy.deepcopy(routes.get(uid)))
        config = None
        if row["suppressed"]:
            row["reason"] = "arena suppression"
        elif row["count"] <= 0:
            row["reason"] = "zero guaranteed spawn count"
        elif row["game"] != "p1":
            row["reason"] = ("P2 defeat without corpse" if row["species"] in P2_KILL_CHECK_SPECIES
                             else "P2 production module yield not yet audited")
        elif raw["kind"] == "pellet":
            config = configs.get(raw["pellet_id"])
            row["reason"] = "loose pellet"
        elif raw["kind"] == "teki" and row["species"] == 7:
            p = raw["personality"]
            if p["pellet_chance"] == 1 and p["pellet_min"] > 0 and 0 <= p["pellet_kind"] < 4:
                # A fully grown Posy emits its guaranteed minimum number. Any
                # current/random color gives at least the worst nonmatching yield.
                size = (1, 5, 10, 20)[p["pellet_kind"]]
                config = configs[f"pb{size:02}"]
                row["count"] *= p["pellet_min"]
                row["reason"] = "fully grown guaranteed Pellet Posy drop"
                row["requires_fully_grown"] = True
                row["random_drop_color"] = True
            else:
                row["reason"] = "Posy drop has no guaranteed positive minimum"
        elif raw["kind"] == "teki" and source is not None:
            config = configs.get(P1_CORPSE_CONFIG.get(row["species"]))
            row["reason"] = "P1 native corpse; probabilistic extra pellets excluded"
        elif raw["kind"] == "teki":
            row["reason"] = "P1 source outside resolved persistent catalog; final corpse identity not asserted"
        if config and config["kind"] != 3 and min(config["matching_yield"], config["other_yield"]) > 0:
            row["carry_min"], row["carrier_slots"] = config["carry_min"], config["carrier_slots"]
            row["yields"] = {color: (config["matching_yield"] if config["color"] == index
                                     and not row.get("random_drop_color") else config["other_yield"])
                             for index, color in enumerate(COLORS)}
        suppliers.append(row)
    return dict(version=VERSION, config_sha256=inputs["config_sha256"],
                day_policy=manifest["day_policy"], suppliers=suppliers,
                qualification="reviewed logical branches required; physical gameplay acceptance separate")


def growth_bound(snapshot, manifest, inventory, color, *, day=29, consumed=None, activated=(),
                 usable_carriers=None):
    """Guaranteed unconsumed gross sprouts; infinity only for usable repeated food.

    Consumption is supplied by the caller; no save/reconnect call manufactures
    sources or clears consumed food. Finite initial waves are counted once.
    Usable carriers are an explicit per-color witness, not Onion ownership,
    stored stock, delivery items or the field capacity. Missing evidence is zero.
    """
    if snapshot.get("version") != VERSION or snapshot.get("day_policy") != "repeat-day29-v1":
        raise ValueError("unsupported saved population supply")
    if color not in COLORS or type(day) is not int or not 1 <= day <= 29:
        raise ValueError("invalid population color/day")
    if usable_carriers is None:
        usable_carriers = {}
    if (type(usable_carriers) is not dict or not set(usable_carriers) <= set(COLORS)
            or any(type(value) is not int or value < 0 for value in usable_carriers.values())):
        raise ValueError("invalid usable carrier counts")
    from .catalog import color_inventory, field_capacity, START_AREAS
    from .stats import current_profiles
    owned = color_inventory(inventory, manifest)
    if not owned.get(color.title() + " Onion", 0):
        return 0
    profiles = current_profiles(manifest, inventory)
    strength = profiles.get(color, {}).get("carry", 1)
    capacity = field_capacity(inventory, True, manifest.get("starting_flarlic", 2))
    start = START_AREAS[manifest["profile"]][0]
    consumed = consumed or {}
    total = 0
    for row in snapshot["suppliers"]:
        branch = row["logic_route"]
        if (row["suppressed"] or row["count"] <= 0 or row["yields"][color] <= 0
                or not branch or branch.get("version") != "source-backed-logic-v1"
                or not branch.get("evidence")):
            continue
        access = next(access for stage, _, access in START_AREAS.values() if stage == row["stage"])
        if row["stage"] != start and not inventory.get(access, 0):
            continue
        schedule = row["schedule"]
        first, last, expiry = schedule["first_day"], schedule["last_activation_day"], schedule["expires_after_day"]
        if first is None or first > day or (expiry is not None and expiry < day):
            continue
        if last is not None and day > last and row["uid"] not in activated:
            continue
        if not all(owned.get(item, 0) for item in branch["requires"]):
            continue
        if color not in branch["carrier_colors"]:
            continue
        if row.get("requires_fully_grown") and not branch.get("allows_fully_grown_posy"):
            continue
        minimum = (row["carry_min"] + strength - 1) // strength
        if minimum > min(row["carrier_slots"], capacity, usable_carriers.get(color, 0)):
            continue
        if row["repeatable_at_cap"]:
            return float("inf")
        used = consumed.get(row["uid"], 0)
        if type(used) is not int or used < 0:
            raise ValueError("invalid supplier consumption")
        total += max(0, row["count"] - used) * row["yields"][color]
    return total


def can_reach_population(snapshot, manifest, inventory, count, color=None, **state):
    """Keep the starting20; higher counts require actual usable saved food."""
    if type(count) is not int or count <= 0 or (color is not None and color not in COLORS):
        raise ValueError("invalid population target")
    from .catalog import starting_color
    initial = 20 if color is None or color == starting_color(manifest) else 0
    if count <= initial:
        return True
    # One color alone is a conservative total-population witness. Taking the
    # maximum avoids assigning the same finite food simultaneously to colors.
    bounds = [growth_bound(snapshot, manifest, inventory, destination, **state)
              for destination in ((color,) if color else COLORS)]
    return max(bounds) >= count - initial


def resolve_static(manifest):
    """Production proposal: renewable food only, with code-owned route proofs."""
    if not STATIC_ROUTES or not STATIC_BOOTSTRAPS:
        raise ValueError("population supply has no reviewed renewable/bootstrap witnesses")
    snapshot = resolve(manifest, STATIC_ROUTES)
    witnessed = {row["uid"]: row for row in snapshot["suppliers"] if row["logic_route"]}
    if set(witnessed) != set(STATIC_ROUTES) or any(
            row["suppressed"] or not row["repeatable_at_cap"] or row["count"] <= 0
            or not any(row["yields"].values()) for row in witnessed.values()):
        raise ValueError("static population witness is not an admitted renewable supplier")
    return snapshot


def validate_snapshot(snapshot, manifest):
    """Reconstruct immutable input/route facts; reject any saved-field change."""
    expected = resolve_static(manifest)
    if (type(snapshot) is not dict
            or json.dumps(snapshot, sort_keys=True, separators=(",", ":"), allow_nan=False)
            != json.dumps(expected, sort_keys=True, separators=(",", ":"), allow_nan=False)):
        raise ValueError("population supply differs from reviewed source snapshot")
    return True


def static_can_reach_population(snapshot, manifest, inventory, count, color=None):
    """Monotone AP proposal, distinct from observations of current living bodies.

    Only reviewed renewable food can justify growth, so separate milestones
    cannot overcommit the same finite body. Bootstrap proofs must establish
    stock withdrawal and route usability, not merely Onion ownership.
    """
    validate_snapshot(snapshot, manifest)
    from .catalog import color_inventory, starting_color
    owned = color_inventory(inventory, manifest)
    carriers = {}
    for destination, proof in STATIC_BOOTSTRAPS.items():
        if (destination not in COLORS or proof.get("version") != "onion-retrieval-v1"
                or not proof.get("evidence") or type(proof.get("requires")) is not list):
            raise ValueError("invalid reviewed Onion retrieval witness")
        if owned.get(destination.title() + " Onion", 0) and all(
                owned.get(item, 0) for item in proof["requires"]):
            carriers[destination] = 20 if destination == starting_color(manifest) else 5
    renewable = copy.deepcopy(snapshot)
    for row in renewable["suppliers"]:
        if not row["repeatable_at_cap"]:
            row["logic_route"] = None
    return can_reach_population(renewable, manifest, inventory, count, color,
                                usable_carriers=carriers)
