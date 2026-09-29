"""P1 ship-part holder teki slots that a P2 occupant may take over (#901).

A P1 teki generator whose personality ``mID`` is a UFO part (and whose
``Parameter0`` is unset) is a *holder*: the teki drops that part on death,
and delivering it to the ship fires the vanilla Archipelago location. The
campaign data marks these slots ``protected`` so the P1 enemy shuffle and P2
placement leave them alone.

``held_part_transfer`` lifts that protection for one slot. The seed may then
bind a P2 species there; native (``pc_port/pc_held_part.cpp``
``pc_held_part_transfers``) sees the binding, births the P2 occupant from the
same generator personality, so the occupant holds the part, logs
``P2_HELD_PART_ASSIGN ... via=slot``, and drops it through the generic BTeki
death funnel. The part keeps its stage, pellet and ship check, so logic and
locations are unchanged.

The binding itself is the contract between root and native: native transfers
any bound holder slot, and the root binds a holder slot only when its flag is
set here. A flag is flipped to ``True`` only with a real campaign run that
shows ASSIGN -> HOLD -> DROP -> carry -> the vanilla ship CHECK for a
seed-generated binding (``evidence``).

Not listed: the Pearly Clamclamp pearl holders. They carry the part through
``Parameter0`` (TaiShellStrategy), which native never transfers.
"""
from __future__ import annotations

HELD_PART_SCHEMA = "p2-held-part-slot-v1"

P1_HELD_PART_SLOTS = (
    {
        "uid": 613834665,
        "label": "spring_puffy_blowhog_uf02",
        "stage": 3,
        "p1_teki": 16,  # TEKI_Mar, Puffy Blowhog
        "part": "uf02",
        "location": "Pikmin: Interstellar Radio",
        "first_day": 2,
        "respawn_days": 0,
        "held_part_transfer": True,
        "evidence": ("output/claude-orch/p2-held-part runs b9/b10 (hand-bound BlueKochappy 44: "
                     "DROP via=die, carried, CHECK 5 = vanilla index) and the seed-generated "
                     "binding run recorded on #901"),
    },
    {
        "uid": 3406893972,
        "label": "navel_breadbug_un09",
        "stage": 2,
        "p1_teki": 8,  # TEKI_Collec, Breadbug
        "part": "un09",
        "location": "Pikmin: Space Float",
        "first_day": 2,
        "respawn_days": 0,
        "held_part_transfer": False,
        "evidence": ("u4/u5: DROP part=un09 via=die ok=1 (late un** shape); carry and CHECK not "
                     "yet proven"),
    },
)


def held_part_slots_by_uid():
    return {row["uid"]: row for row in P1_HELD_PART_SLOTS}


def slot_protected(row):
    return not row.get("held_part_transfer", False)


def _slot(row):
    proven = bool(row.get("held_part_transfer", False))
    return {
        "uid": row["uid"],
        "label": row["label"],
        "stage": row["stage"],
        "terrain": "ground",
        "radius": 100.0,
        "water_depth": 0,
        "flight_space": False,
        "burrow_ground": True,
        "home": False,
        "helper_capacity": 0,
        "projectile_corridor": False,
        "corpse_route": proven,
        "protected": slot_protected(row),
        "boss_slot": False,
        "first_day": row["first_day"],
        "respawn_days": row["respawn_days"],
        "source_identity": f"p1_holder:teki:{row['p1_teki']}:{row['part']}",
        "cohort": "ground",
        "evidence": {"xyz": proven, "terrain": proven, "route": proven},
    }


def apply_to_document(document):
    """Return ``document`` with the holder slots (re)written from this table.

    Idempotent. A transferable slot joins the ``accepted_slot_uids`` of every
    non-boss profile that is constraint-compatible with it; a protected one is
    listed (so the policy is visible) but accepted by nobody.
    """
    from .p2_placement import compatibility, normalize_profile, normalize_slot

    uids = {row["uid"] for row in P1_HELD_PART_SLOTS}
    slots = [slot for slot in document["slots"] if slot["uid"] not in uids]
    holders = [_slot(row) for row in P1_HELD_PART_SLOTS]
    profiles = []
    for profile in document["profiles"]:
        profile = dict(profile)
        if "accepted_slot_uids" in profile and not profile.get("is_boss"):
            accepted = [uid for uid in profile["accepted_slot_uids"] if uid not in uids]
            normalized = normalize_profile(profile)
            accepted += [slot["uid"] for slot in holders if not slot["protected"]
                         and not compatibility(normalize_slot(slot), normalized)]
            profile["accepted_slot_uids"] = accepted
        profiles.append(profile)
    result = dict(document)
    # Holder slots sit between the ordinary slots and the arena slots.
    arena_start = next((i for i, slot in enumerate(slots) if slot.get("boss_slot")), len(slots))
    result["slots"] = slots[:arena_start] + holders + slots[arena_start:]
    result["profiles"] = profiles
    result["held_parts"] = [_record(row) for row in P1_HELD_PART_SLOTS]
    return result


def _record(row):
    return {key: row[key] for key in ("uid", "label", "stage", "p1_teki", "part", "location",
                                      "held_part_transfer", "evidence")}
