'''Machine-readable enemy family/provider ownership map (#637).

Lane enemy-family-provider-ownership. Maps every audit roster ID to its
verified source family, existing owner or explicit module boundary:

- first-priority IDs 14/22/39/47/80/89 (enemies-1 ownership gap);
- unowned enemies-3 families from the latest enemies-3 report;
- UmiMushiBase100 as the structural nonactor parent (not audited).

Source facts are cited read-only from the decompilation
(native/pikmin2-research: include/Game/enemyInfo.h,
src/plugProjectYamashitaU/{enemyInfo,generalEnemyMgr}.cpp, family FSM
sources), docs/PIKMIN2_CONTENT_INVENTORY.json token counts, the newest
acceptance overlay, and live registry lane ownership. No runtime work is
fabricated: remaining_gates is null where no overlay row exists (unknown),
never upgraded.

owner_kind vocabulary: lane = a designated family lane exists (number +
issues); route = handled inside ANOTHER lane held module (routed_to names
it); alias = no actor (nest/resource alias, no manager case, no info row);
nonactor = manager base, not spawnable.
'''
import argparse
import copy
import json

GATES = ("identity_spawn", "movement_animation", "attacks_receivers",
         "death_corpse", "transport_reward", "cleanup_reentry")

OWNER_KINDS = ("lane", "route", "alias", "nonactor")
MODULE_STATUS = ("held", "claimed", "proposed")
FOLLOWON_KINDS = ("p0-audit", "gate-closure")

# Verified anchors (read-only sources, see docs/PIKMIN2_ENEMY_FAMILY_PROVIDER_OWNERSHIP.md):
# - enemyInfo.h enum names + common names; enemyInfo.cpp gEnemyInfo parent/flags.
# - generalEnemyMgr.cpp manager-case switch (94 cases; nests 39/64 absent).
# - Family FSMs: NishimuraU/{Tobi,Hiba,ElecHiba,GasHiba,Frog,Demon,Kogane,Hana,Queen,Qurione,BigTreasure,Pom},
#   MorimuraU/{tamagoMushi,umiMushi}, YamashitaU/{BlueChappy,pelplant}.
# - Overlay: output/p2-main-review/docs/PIKMIN2_ENEMY_ROSTER_EVIDENCE.json.
# - Inventory: docs/PIKMIN2_CONTENT_INVENTORY.json enemy_ids/treasure_ids token counts.
FAMILY_MAP = [
    {"source_id": 14, "enum_name": "Tobi", "common_name": "Shearwig",
     "family": "Sheargrub", "parent_id": None, "spawnable": True, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/src/plugProjectNishimuraU/Tobi.cpp",
                          "native/pikmin2-research/src/plugProjectNishimuraU/TobiMgr.cpp",
                          "native/pikmin2-research/src/plugProjectNishimuraU/TobiState.cpp"],
     "inventory_tokens": 4, "owner_kind": "lane",
     "owner": {"lane": 13, "issues": [120, 197],
               "note": "Sheargrub family (Uji paths); flight consult lane 15. No lane holds Tobi files."},
     "module_files": [{"path": "native/pc_port/pc_p2_tobi.h", "status": "proposed",
                       "note": "additive; must not fork pc_p2_sheargrub visuals"},
                      {"path": "native/pc_port/pc_p2_tobi.cpp", "status": "proposed",
                       "note": "additive Tobi actor + flight consult"}],
     "shared_module": None, "remaining_gates": None,
     "follow_on": {"slice_id": "TOBI14-P0", "kind": "p0-audit",
                   "files": ["experimental/pikmin2_tobi14_audit.py",
                             "tests/test_pikmin2_tobi14_audit.py",
                             "docs/PIKMIN2_TOBI14_AUDIT.md"],
                   "acceptance": ["Decode the Tobi definition from the NishimuraU Tobi FSM plus the enemyInfo row, with hashes or the exact missing bytes; no invented values",
                                  "Isolated metadata/import-contract adapter plus malformed/missing-input tests",
                                  "P1 blockers with owner refs (lanes 13/15); all six gates UNTESTED; no ADMIT"],
                   "owner": "lane 13 (#120/#197), flight consult lane 15"}},
    {"source_id": 22, "enum_name": "ElecHiba", "common_name": "Electrical wire",
     "family": "Hiba", "parent_id": None, "spawnable": True, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/src/plugProjectNishimuraU/Hiba.cpp",
                          "native/pikmin2-research/src/plugProjectNishimuraU/HibaMgr.cpp",
                          "native/pikmin2-research/src/plugProjectNishimuraU/ElecHiba.cpp",
                          "native/pikmin2-research/src/plugProjectNishimuraU/GasHiba.cpp"],
     "inventory_tokens": 13, "owner_kind": "lane",
     "owner": {"lane": 22, "issues": [170, 408],
               "note": "Blowhogs/Dweevils/fixed hazards incl. Hiba variants; module claimed in overlay."},
     "module_files": [{"path": "native/pc_port/pc_p2_hiba.h", "status": "claimed",
                       "note": "overlay-claimed; no registry holder; worktree copies only"},
                      {"path": "native/pc_port/pc_p2_hiba.cpp", "status": "claimed",
                       "note": "overlay-claimed; no registry holder; worktree copies only"}],
     "shared_module": None,
     "remaining_gates": ["identity_spawn", "attacks_receivers", "cleanup_reentry"],
     "follow_on": {"slice_id": "HIBA22-GATES", "kind": "gate-closure",
                   "files": ["native/pc_port/pc_p2_hiba.h",
                             "native/pc_port/pc_p2_hiba.cpp",
                             "tests/test_pikmin2_hiba_gates.py"],
                   "acceptance": ["Natural identity_spawn, attacks_receivers and cleanup_reentry evidence for ElecHiba22 within lane-22 ownership; owner review required; no ADMIT"],
                   "owner": "lane 22 (#170/#408)"}},
    {"source_id": 39, "enum_name": "PanModokiNest", "common_name": "Breadbug Nest",
     "family": "Breadbug nest alias", "parent_id": None, "spawnable": False, "has_info_row": False,
     "research_sources": ["native/pikmin2-research/include/Game/Entities/PanModokiBase.h"],
     "inventory_tokens": 0, "owner_kind": "alias", "owner": None,
     "module_files": [], "shared_module": None, "remaining_gates": None, "follow_on": None},
    {"source_id": 47, "enum_name": "Clover", "common_name": "Clover",
     "family": "Flora", "parent_id": None, "spawnable": True, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/src/plugProjectNishimuraU/Pom.cpp"],
     "inventory_tokens": 16, "owner_kind": "lane",
     "owner": {"lane": 23, "issues": [171],
               "note": "Flora/Candypops; pc_p2_plant claimed in overlay."},
     "module_files": [{"path": "native/pc_port/pc_p2_plant.h", "status": "claimed",
                       "note": "overlay-claimed by lane 23; no registry holder"},
                      {"path": "native/pc_port/pc_p2_plant.cpp", "status": "claimed",
                       "note": "overlay-claimed by lane 23; no registry holder"}],
     "shared_module": None, "remaining_gates": ["identity_spawn"], "follow_on": None},
    {"source_id": 80, "enum_name": "Tukushi", "common_name": "Horsetail",
     "family": "Flora", "parent_id": None, "spawnable": True, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/src/plugProjectNishimuraU/Pom.cpp"],
     "inventory_tokens": 1, "owner_kind": "lane",
     "owner": {"lane": 23, "issues": [171],
               "note": "No overlay row, no module; follow-on inside lane-23 family."},
     "module_files": [{"path": "native/pc_port/pc_p2_plant.h", "status": "claimed",
                       "note": "shared flora module claimed by lane 23; Tukushi coverage missing"}],
     "shared_module": None, "remaining_gates": None, "follow_on": None},
    {"source_id": 89, "enum_name": "Chiyogami", "common_name": "Chigoyami paper",
     "family": "Flora", "parent_id": None, "spawnable": True, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/src/plugProjectNishimuraU/Pom.cpp"],
     "inventory_tokens": 1, "owner_kind": "lane",
     "owner": {"lane": 23, "issues": [171],
               "note": "HasNoInfo flag; no overlay row, no module; follow-on inside lane-23 family."},
     "module_files": [{"path": "native/pc_port/pc_p2_plant.h", "status": "claimed",
                       "note": "shared flora module claimed by lane 23; Chiyogami coverage missing"}],
     "shared_module": None, "remaining_gates": None, "follow_on": None},
    {"source_id": 10, "enum_name": "Wealthy", "common_name": "Wealthy Beetle",
     "family": "Reward beetle", "parent_id": None, "spawnable": True, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/src/plugProjectNishimuraU/Kogane.cpp"],
     "inventory_tokens": 2, "owner_kind": "route",
     "owner": {"lane": 17, "issues": [168, 219],
               "note": "Routed: variant handled inside lane-17 Kogane module, no separate module."},
     "module_files": [{"path": "native/pc_port/pc_p2_kogane.h", "status": "held",
                       "note": "held by muse-kogane (done)"},
                      {"path": "native/pc_port/pc_p2_kogane.cpp", "status": "held",
                       "note": "held by muse-kogane (done)"}],
     "shared_module": "native/pc_port/pc_p2_kogane.cpp",
     "remaining_gates": ["identity_spawn", "movement_animation", "attacks_receivers",
                         "death_corpse", "transport_reward", "cleanup_reentry"],
     "follow_on": None},
    {"source_id": 16, "enum_name": "Qurione", "common_name": "Honeywisp",
     "family": "Flying", "parent_id": None, "spawnable": True, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/src/plugProjectNishimuraU/Qurione.cpp"],
     "inventory_tokens": 2, "owner_kind": "lane",
     "owner": {"lane": 15, "issues": [166],
               "note": "Module held by muse-honeywisp (done)."},
     "module_files": [{"path": "native/pc_port/pc_p2_qurione.h", "status": "held",
                       "note": "held by muse-honeywisp (done)"},
                      {"path": "native/pc_port/pc_p2_qurione.cpp", "status": "held",
                       "note": "held by muse-honeywisp (done)"}],
     "shared_module": None,
     "remaining_gates": ["movement_animation", "attacks_receivers", "transport_reward"],
     "follow_on": None},
    {"source_id": 17, "enum_name": "Frog", "common_name": "Wollywog",
     "family": "Frog", "parent_id": None, "spawnable": True, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/src/plugProjectNishimuraU/Frog.cpp",
                          "native/pikmin2-research/src/plugProjectNishimuraU/FrogMgr.cpp"],
     "inventory_tokens": 3, "owner_kind": "lane",
     "owner": {"lane": 16, "issues": [167],
               "note": "Frogs/aquatic; pc_p2_frog claimed in overlay."},
     "module_files": [{"path": "native/pc_port/pc_p2_frog.h", "status": "claimed",
                       "note": "overlay-claimed by lane 16; no registry holder"},
                      {"path": "native/pc_port/pc_p2_frog.cpp", "status": "claimed",
                       "note": "overlay-claimed by lane 16; no registry holder"}],
     "shared_module": None,
     "remaining_gates": ["attacks_receivers", "death_corpse", "transport_reward", "cleanup_reentry"],
     "follow_on": None},
    {"source_id": 24, "enum_name": "Tank", "common_name": "Puffy Blowhog",
     "family": "Blowhog", "parent_id": None, "spawnable": True, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/src/plugProjectNishimuraU/Ftank.cpp",
                          "native/pikmin2-research/src/plugProjectNishimuraU/FtankMgr.cpp"],
     "inventory_tokens": 8, "owner_kind": "lane",
     "owner": {"lane": 22, "issues": [170, 408],
               "note": "Tank family; pc_p2_tank claimed in overlay."},
     "module_files": [{"path": "native/pc_port/pc_p2_tank.h", "status": "claimed",
                       "note": "overlay-claimed by lane 22; no registry holder"},
                      {"path": "native/pc_port/pc_p2_tank.cpp", "status": "claimed",
                       "note": "overlay-claimed by lane 22; no registry holder"}],
     "shared_module": None,
     "remaining_gates": ["identity_spawn", "movement_animation", "attacks_receivers",
                         "death_corpse", "transport_reward", "cleanup_reentry"],
     "follow_on": None},
    {"source_id": 30, "enum_name": "Queen", "common_name": "Puffstool",
     "family": "Bulblax", "parent_id": None, "spawnable": True, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/src/plugProjectNishimuraU/Queen.cpp",
                          "native/pikmin2-research/src/plugProjectNishimuraU/QueenMgr.cpp"],
     "inventory_tokens": 0, "owner_kind": "lane",
     "owner": {"lane": 24, "issues": [172],
               "note": "Bulblax; pc_p2_queen claimed in overlay."},
     "module_files": [{"path": "native/pc_port/pc_p2_queen.h", "status": "claimed",
                       "note": "overlay-claimed by lane 24; no registry holder"},
                      {"path": "native/pc_port/pc_p2_queen.cpp", "status": "claimed",
                       "note": "overlay-claimed by lane 24; no registry holder"}],
     "shared_module": None, "remaining_gates": ["transport_reward"], "follow_on": None},
    {"source_id": 31, "enum_name": "Baby", "common_name": "Puffmin",
     "family": "Bulblax", "parent_id": None, "spawnable": True, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/src/plugProjectNishimuraU/Queen.cpp"],
     "inventory_tokens": 2, "owner_kind": "lane",
     "owner": {"lane": 24, "issues": [172],
               "note": "Dependent birth of Queen30; no separate FSM."},
     "module_files": [], "shared_module": None,
     "remaining_gates": ["identity_spawn", "movement_animation", "death_corpse", "cleanup_reentry"],
     "follow_on": None},
    {"source_id": 32, "enum_name": "Demon", "common_name": "Smoky Progg",
     "family": "Snitchbug/Demon", "parent_id": None, "spawnable": True, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/src/plugProjectNishimuraU/Demon.cpp",
                          "native/pikmin2-research/src/plugProjectNishimuraU/DemonMgr.cpp"],
     "inventory_tokens": 11, "owner_kind": "lane",
     "owner": {"lane": 30, "issues": [215, 242],
               "note": "Snitchbugs/Demon; pc_p2_demon_host claimed in overlay."},
     "module_files": [{"path": "native/pc_port/pc_p2_demon_host.h", "status": "claimed",
                       "note": "overlay-claimed by lane 30; no registry holder"},
                      {"path": "native/pc_port/pc_p2_demon_host.cpp", "status": "claimed",
                       "note": "overlay-claimed by lane 30; no registry holder"}],
     "shared_module": None,
     "remaining_gates": ["identity_spawn", "movement_animation", "attacks_receivers",
                         "death_corpse", "transport_reward", "cleanup_reentry"],
     "follow_on": None},
    {"source_id": 37, "enum_name": "Egg", "common_name": "Egg",
     "family": "Projectile", "parent_id": None, "spawnable": True, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/include/Game/Entities/Egg.h"],
     "inventory_tokens": 7, "owner_kind": "lane",
     "owner": {"lane": 20, "issues": [169],
               "note": "Cannon/projectile primitives; shared-module decision (family egg vs shared projectile) belongs to lane 20 review."},
     "module_files": [], "shared_module": None, "remaining_gates": None, "follow_on": None},
    {"source_id": 42, "enum_name": "BlueChappy", "common_name": "Blue Bulborb",
     "family": "Bulborb", "parent_id": None, "spawnable": True, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/src/plugProjectYamashitaU/BlueChappy.cpp",
                          "native/pikmin2-research/src/plugProjectYamashitaU/BlueChappyMgr.cpp"],
     "inventory_tokens": 8, "owner_kind": "lane",
     "owner": {"lane": 13, "issues": [120, 197],
               "note": "Bulborb family; no module, no overlay row; queued P0 candidate."},
     "module_files": [], "shared_module": None, "remaining_gates": None, "follow_on": None},
    {"source_id": 49, "enum_name": "Ooinu_s", "common_name": "Ooinu",
     "family": "Flora", "parent_id": None, "spawnable": True, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/src/plugProjectNishimuraU/Pom.cpp"],
     "inventory_tokens": 10, "owner_kind": "lane",
     "owner": {"lane": 23, "issues": [171],
               "note": "HasNoInfo flag; pc_p2_plant claimed in overlay."},
     "module_files": [{"path": "native/pc_port/pc_p2_plant.h", "status": "claimed",
                       "note": "overlay-claimed by lane 23; no registry holder"},
                      {"path": "native/pc_port/pc_p2_plant.cpp", "status": "claimed",
                       "note": "overlay-claimed by lane 23; no registry holder"}],
     "shared_module": None, "remaining_gates": ["identity_spawn"], "follow_on": None},
    {"source_id": 56, "enum_name": "Damagumo", "common_name": "Beady Long Legs",
     "family": "Long Legs", "parent_id": None, "spawnable": True, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/include/Game/Entities/Damagumo.h"],
     "inventory_tokens": 0, "owner_kind": "route",
     "owner": {"lane": 26, "issues": [173],
               "note": "Routed: handled inside lane-26 Long Legs module (live damagumo-family-staging-provider)."},
     "module_files": [{"path": "native/pc_port/pc_p2_long_legs.h", "status": "held",
                       "note": "held by muse-longlegs (done); live staging provider running"},
                      {"path": "native/pc_port/pc_p2_long_legs.cpp", "status": "held",
                       "note": "held by muse-longlegs (done); live staging provider running"}],
     "shared_module": "native/pc_port/pc_p2_long_legs.cpp",
     "remaining_gates": ["identity_spawn", "movement_animation", "attacks_receivers",
                         "death_corpse", "transport_reward", "cleanup_reentry"],
     "follow_on": None},
    {"source_id": 64, "enum_name": "JigumoNest", "common_name": "Jigumo nest",
     "family": "Aquatic nest alias", "parent_id": None, "spawnable": False, "has_info_row": False,
     "research_sources": ["native/pikmin2-research/include/Game/Entities/Nest.h", "native/pikmin2-research/src/plugProjectYamashitaU/generalEnemyMgr.cpp"],
     "inventory_tokens": 0, "owner_kind": "alias", "owner": None,
     "module_files": [], "shared_module": None, "remaining_gates": None, "follow_on": None},
    {"source_id": 68, "enum_name": "TamagoMushi", "common_name": "Mitite",
     "family": "Ground invertebrate", "parent_id": None, "spawnable": True, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/src/plugProjectMorimuraU/tamagoMushi.cpp"],
     "inventory_tokens": 2, "owner_kind": "lane",
     "owner": {"lane": 14, "issues": [165],
               "note": "Ground invertebrates; pc_p2_tamago claimed in overlay."},
     "module_files": [{"path": "native/pc_port/pc_p2_tamago.h", "status": "claimed",
                       "note": "overlay-claimed by lane 14; no registry holder"},
                      {"path": "native/pc_port/pc_p2_tamago.cpp", "status": "claimed",
                       "note": "overlay-claimed by lane 14; no registry holder"}],
     "shared_module": None, "remaining_gates": ["death_corpse", "transport_reward"],
     "follow_on": None},
    {"source_id": 69, "enum_name": "BigFoot", "common_name": "Raging Long Legs",
     "family": "Long Legs", "parent_id": None, "spawnable": True, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/include/Game/Entities/BigFoot.h"],
     "inventory_tokens": 0, "owner_kind": "route",
     "owner": {"lane": 26, "issues": [173],
               "note": "Routed: handled inside lane-26 Long Legs module; enemy-bigfoot69-walk done."},
     "module_files": [{"path": "native/pc_port/pc_p2_long_legs.h", "status": "held",
                       "note": "held by muse-longlegs (done)"},
                      {"path": "native/pc_port/pc_p2_long_legs.cpp", "status": "held",
                       "note": "held by muse-longlegs (done)"}],
     "shared_module": "native/pc_port/pc_p2_long_legs.cpp",
     "remaining_gates": ["transport_reward"], "follow_on": None},
    {"source_id": 73, "enum_name": "BigTreasure", "common_name": "Titan Dweevil",
     "family": "Titan", "parent_id": None, "spawnable": True, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/src/plugProjectNishimuraU/BigTreasure.cpp",
                          "native/pikmin2-research/src/plugProjectNishimuraU/BigTreasureMgr.cpp"],
     "inventory_tokens": 1, "owner_kind": "lane",
     "owner": {"lane": 32, "issues": [246],
               "note": "Titan Dweevil; pc_p2_bigtreasure claimed in overlay."},
     "module_files": [{"path": "native/pc_port/pc_p2_bigtreasure.h", "status": "claimed",
                       "note": "overlay-claimed by lane 32; no registry holder"},
                      {"path": "native/pc_port/pc_p2_bigtreasure.cpp", "status": "claimed",
                       "note": "overlay-claimed by lane 32; no registry holder"}],
     "shared_module": None,
     "remaining_gates": ["identity_spawn", "movement_animation", "attacks_receivers",
                         "death_corpse", "transport_reward", "cleanup_reentry"],
     "follow_on": None},
    {"source_id": 84, "enum_name": "Hana", "common_name": "Creeping Chrysanthemum",
     "family": "Ground invertebrate", "parent_id": None, "spawnable": True, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/src/plugProjectNishimuraU/Hana.cpp",
                          "native/pikmin2-research/src/plugProjectNishimuraU/HanaMgr.cpp"],
     "inventory_tokens": 3, "owner_kind": "lane",
     "owner": {"lane": 14, "issues": [165],
               "note": "Ground invertebrates; pc_p2_hana claimed in overlay."},
     "module_files": [{"path": "native/pc_port/pc_p2_hana.h", "status": "claimed",
                       "note": "overlay-claimed by lane 14; no registry holder"},
                      {"path": "native/pc_port/pc_p2_hana.cpp", "status": "claimed",
                       "note": "overlay-claimed by lane 14; no registry holder"}],
     "shared_module": None,
     "remaining_gates": ["death_corpse", "transport_reward", "cleanup_reentry"],
     "follow_on": None},
    {"source_id": 91, "enum_name": "KareOoinu_s", "common_name": "KareOoinu",
     "family": "Flora", "parent_id": None, "spawnable": True, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/src/plugProjectNishimuraU/Pom.cpp"],
     "inventory_tokens": 23, "owner_kind": "lane",
     "owner": {"lane": 23, "issues": [171],
               "note": "HasNoInfo flag; pc_p2_plant claimed in overlay."},
     "module_files": [{"path": "native/pc_port/pc_p2_plant.h", "status": "claimed",
                       "note": "overlay-claimed by lane 23; no registry holder"},
                      {"path": "native/pc_port/pc_p2_plant.cpp", "status": "claimed",
                       "note": "overlay-claimed by lane 23; no registry holder"}],
     "shared_module": None, "remaining_gates": ["identity_spawn"], "follow_on": None},
    {"source_id": 100, "enum_name": "UmiMushiBase", "common_name": "Bloyster base",
     "family": "Bloyster base", "parent_id": None, "spawnable": False, "has_info_row": True,
     "research_sources": ["native/pikmin2-research/src/plugProjectMorimuraU/umiMushiMgr.cpp"],
     "inventory_tokens": 0, "owner_kind": "nonactor", "owner": None,
     "module_files": [], "shared_module": None, "remaining_gates": None, "follow_on": None},
]


def load_map():
    """Return a deep copy of the family/provider map records."""
    return copy.deepcopy(FAMILY_MAP)


def validate_map(records=None):
    """Return a list of error strings; empty means the map is valid."""
    records = load_map() if records is None else records
    errors = []
    seen = {}
    for i, rec in enumerate(records):
        tag = "record[%d]" % i
        sid = rec.get("source_id")
        if sid in seen:
            errors.append("%s: duplicate source_id %r (also record[%d])" % (tag, sid, seen[sid]))
        else:
            seen[sid] = i
        kind = rec.get("owner_kind")
        if kind not in OWNER_KINDS:
            errors.append("%s: owner_kind %r not in %s" % (tag, kind, OWNER_KINDS))
            continue
        owner = rec.get("owner")
        if kind in ("lane", "route"):
            if not isinstance(owner, dict) or not isinstance(owner.get("lane"), int):
                errors.append("%s: kind %r requires owner {lane, issues}" % (tag, kind))
            elif not isinstance(owner.get("issues"), list) or not owner["issues"]:
                errors.append("%s: owner.issues must be a nonempty list" % tag)
        elif owner is not None:
            errors.append("%s: kind %r must have null owner" % (tag, kind))
        files = rec.get("module_files")
        if not isinstance(files, list):
            errors.append("%s: module_files must be a list" % tag)
            files = []
        else:
            for f in files:
                if f.get("status") not in MODULE_STATUS:
                    errors.append("%s: module status %r invalid" % (tag, f.get("status")))
                if not isinstance(f.get("path"), str) or not f["path"]:
                    errors.append("%s: module path must be a nonempty string" % tag)
        if kind in ("alias", "nonactor") and files:
            errors.append("%s: kind %r must not claim actor module files" % (tag, kind))
        if not rec.get("spawnable", True) and kind not in ("nonactor", "alias"):
            errors.append("%s: non-spawnable ID must use kind nonactor or alias" % tag)
        if not rec.get("has_info_row", True) and kind != "alias":
            errors.append("%s: ID without info-table row must use kind alias" % tag)
        shared = rec.get("shared_module")
        if shared is not None and shared not in [f.get("path") for f in files]:
            errors.append("%s: shared_module %r not in module_files" % (tag, shared))
        gates = rec.get("remaining_gates")
        if gates is not None:
            bad = [g for g in gates if g not in GATES]
            if bad:
                errors.append("%s: unknown gates %r" % (tag, bad))
        if not isinstance(rec.get("research_sources"), list) or not rec["research_sources"]:
            errors.append("%s: research_sources must be a nonempty list" % tag)
        if not isinstance(rec.get("inventory_tokens"), int) or rec["inventory_tokens"] < 0:
            errors.append("%s: inventory_tokens must be a non-negative int" % tag)
        follow = rec.get("follow_on")
        if follow is not None:
            if not isinstance(follow.get("slice_id"), str) or not follow["slice_id"]:
                errors.append("%s: follow_on.slice_id required" % tag)
            if follow.get("kind") not in FOLLOWON_KINDS:
                errors.append("%s: follow_on.kind invalid" % tag)
            if not isinstance(follow.get("files"), list) or not follow["files"]:
                errors.append("%s: follow_on.files must be nonempty" % tag)
            if not isinstance(follow.get("acceptance"), list) or not follow["acceptance"]:
                errors.append("%s: follow_on.acceptance must be nonempty" % tag)
            if not isinstance(follow.get("owner"), str) or not follow["owner"]:
                errors.append("%s: follow_on.owner required" % tag)
    ids = set(seen)
    for i, rec in enumerate(records):
        parent = rec.get("parent_id")
        if parent is not None and parent not in ids:
            errors.append("record[%d]: parent_id %r does not resolve in-map" % (i, parent))
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true",
                        help="print a human-readable ownership summary")
    args = parser.parse_args(argv)
    records = load_map()
    errors = validate_map(records)
    if args.report:
        kinds = {}
        for rec in records:
            kinds.setdefault(rec["owner_kind"], []).append(rec["source_id"])
        print(json.dumps({"records": len(records), "by_kind": kinds,
                          "follow_ons": [r["follow_on"]["slice_id"] for r in records
                                         if r["follow_on"]]}, indent=1))
    if errors:
        print("INVALID:")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)
    print("map valid: %d records" % len(records))


if __name__ == "__main__":
    main()