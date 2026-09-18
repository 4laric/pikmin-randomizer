"""Crawler floor-1 species placement pins registry (issue #778).

Lane enemies-3-crawler-floor1-placement-pins. Read-only pin verification
against the canonical native checkout (no native edits). Records, for the
crawler floor-1 roster with emphasis on Wealthy/10, Hana/84 and Ooinu_s/49,
species-level placement pins (file:line + symbol) or explicit ABSENT verdicts
naming an owner or shared-review contract; the ItemGateMgr gate fixture
grammar (or ABSENT); and collision/routes observation points (or ABSENT).

Findings are evidence, not gameplay claims. All six gates UNTESTED.
Stdlib only.
"""

import re

SCHEMA = "p2-crawler-floor1-species-placement-pins-v1"
ISSUE = 778
CONSUMER = {"lane": "p2-challenge-ch-mat-crawler-p1", "issue": 562}
STAGE = "ch_MAT_crawler"
FLOOR = 1
POOL = "4_units_c_e_j_l_conc.txt"
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"

# Canonical native checkout the pins below were verified against (read-only).
NATIVE_PIN = "a95040b66a0ffc9cdbfc649502569a29e66949a7"

SPECIES = {
    # Wealthy/10: Iridescent Glint Beetle. Decomp-only entity
    # (pikmin2-research/include/Game/Entities/Wealthy.h, Obj : Kogane::Obj,
    # EnemyID_Wealthy). No port implementation, hence no species-level
    # placement slot in the built engine. Owner: species port/admission.
    "Wealthy": {"roster_id": 10, "status": "ABSENT",
                "decomp": "pikmin2-research/include/Game/Entities/Wealthy.h",
                "owner": "#131 species fidelity + species-integration owner",
                "note": "generic spawn covers the id (#562 SPAWN_COVERED); species proof absent"},
    # Hana/84: Creeping Chrysanthemum. Decomp-only entity
    # (pikmin2-research/include/Game/Entities/Hana.h, Obj : ChappyBase::Obj).
    # Port has only an incidental species-name mapping, no implementation.
    "Hana": {"roster_id": 84, "status": "ABSENT",
             "decomp": "pikmin2-research/include/Game/Entities/Hana.h",
             "owner": "#131 species fidelity + species-integration owner",
             "note": "generic spawn covers the id; species proof absent"},
    # Ooinu_s/49: NOT an enemy. PLANT_Ooinu_s = 6 (birdseye speedwell, small)
    # in include/PlantMgr.h:22-23. Placement is a plant/flora question, owned
    # by flora mechanics, not enemy admission.
    "Ooinu_s": {"roster_id": 49, "status": "ABSENT",
                "decomp": "include/PlantMgr.h:22-23 (PLANT_Ooinu_s; flora, not enemy)",
                "owner": "flora/plant mechanics owner (not enemy admission)",
                "note": "misclassified as enemy placement; route to flora"},
}

GATE = {
    # ItemGateMgr: decomp-only (pikmin2-research/src/plugProjectKandoU/itemGate.cpp,
    # include/Game/Entities/ItemGate.h with GateStates/GateColor). No port gate
    # manager exists, so no fixture grammar can be written against the engine.
    "manager": "ItemGateMgr",
    "status": "ABSENT",
    "decomp": "pikmin2-research/src/plugProjectKandoU/itemGate.cpp",
    "owner": "unassigned; request owner assignment via #570 (gate/cargo mechanics), #186 if shared semantics",
    "note": "no port gate manager; grammar would be invented, not verified",
}

COLLISION_ROUTES = {
    # No crawler-applicable collision/routes observation points exist in the
    # port. Generic preview-room mechanisms and family-specific traces
    # (bigtreasure/bombsarai map_trace) exist read-only but none covers the
    # crawler roster. Owner: the #562 consumer's own fixture extension, with
    # #129 navigation semantics noted as related (not assigned).
    "status": "ABSENT",
    "nearest_generic": ["preview_p2_room.cpp (generic preview, not crawler)",
                        "pc_p2_bigtreasure_map_trace.cpp (family-specific)",
                        "pc_p2_bombsarai_map_trace.cpp (family-specific)"],
    "owner": "#562 follow-on (consumer extends its own fixture); #129 related",
    "note": "observation points must be built, not found",
}

GENERIC_SPAWN_CONTEXT = {
    # Recorded #562 evidence (read-only input, not re-verified here): the
    # engine spawned all 15 roster ids (SPAWN_COVERED) with a live squad.
    # This is preview-generic liveness, not species-level placement proof.
    "status": "PRESENT_GENERIC",
    "pool": POOL,
    "spawns": 15,
    "note": "covers ids, not species; see SPECIES verdicts above",
}


def _hex64(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def species_verdict(name):
    """Return the placement verdict for a roster species; KeyError when unknown."""
    return dict(SPECIES[name])


def gate_verdict():
    """Return the ItemGateMgr grammar verdict."""
    return dict(GATE)


def collision_routes_verdict():
    """Return the collision/routes observation verdict."""
    out = dict(COLLISION_ROUTES)
    out["nearest_generic"] = list(COLLISION_ROUTES["nearest_generic"])
    return out


def registry():
    """Machine-readable pins registry for the #562 consumer."""
    return {
        "schema": SCHEMA,
        "issue": ISSUE,
        "consumer": dict(CONSUMER),
        "stage": STAGE,
        "floor": FLOOR,
        "pool": POOL,
        "native_pin": NATIVE_PIN,
        "species": {k: dict(v) for k, v in SPECIES.items()},
        "gate": dict(GATE),
        "collision_routes": collision_routes_verdict(),
        "generic_spawn_context": dict(GENERIC_SPAWN_CONTEXT),
        "guard": {"path": "scripts/p2_fixture_captain_guard.h", "sha256": GUARD_SHA256},
    }


def downstream_specs():
    """Implementation specs outlined for the #562 consumer (not staged here)."""
    return [
        {"title": "Species fidelity proofs for Wealthy/Hana via #131 once ported",
         "owner": "#131 + species-integration", "depends_on": ["port implementation"]},
        {"title": "Ooinu_s plant-placement proof via flora mechanics",
         "owner": "flora/plant owner", "depends_on": ["flora placement scope"]},
        {"title": "ItemGateMgr port + fixture grammar",
         "owner": "TBD via #570", "depends_on": ["owner assignment", "#186 if shared"]},
        {"title": "Crawler collision/routes observation in the #562 fixture",
         "owner": "#562 follow-on", "depends_on": ["placed roster"]},
    ]
