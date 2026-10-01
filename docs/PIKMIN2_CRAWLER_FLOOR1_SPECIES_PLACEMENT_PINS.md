# Crawler floor-1 species placement pins (issue #778; downstream #562)

Lane `enemies-3-crawler-floor1-placement-pins`. Owner: Codex through shared
account 4laric. Read-only pin verification against the canonical native
checkout at `a95040b6` (no native edits, no builds, no runtime). Owns ONLY:

- `experimental/pikmin2_crawler_floor1_species_placement_pins.py`
- `tests/test_pikmin2_crawler_floor1_species_placement_pins.py`
- `docs/PIKMIN2_CRAWLER_FLOOR1_SPECIES_PLACEMENT_PINS.md`

## Verdicts (all six gates UNTESTED; no gameplay claim)

### 1. Species-level placement: ABSENT for all three (engine has no slots)

| species | roster id | decomp source | port status | owner |
|---|---|---|---|---|
| Wealthy/10 (Iridescent Glint Beetle) | 10 | `pikmin2-research/include/Game/Entities/Wealthy.h` (`Obj : Kogane::Obj`, `EnemyID_Wealthy`) | ABSENT — decomp-only, no port implementation | #131 species fidelity + species-integration owner |
| Hana/84 (Creeping Chrysanthemum) | 84 | `pikmin2-research/include/Game/Entities/Hana.h` (`Obj : ChappyBase::Obj`) | ABSENT — decomp-only; port has only an incidental name mapping (`pc_p2_batch3.cpp:68`) | #131 species fidelity + species-integration owner |
| Ooinu_s/49 | 49 | `include/PlantMgr.h:22-23` (`PLANT_Ooinu_s = 6`, birdseye speedwell, small) | ABSENT as enemy placement — **it is flora, not an enemy** | flora/plant mechanics owner (not enemy admission) |

The #562 consumer observed all 15 roster ids `SPAWN_COVERED` with a live squad
(pool `4_units_c_e_j_l_conc.txt`). That is preview-generic liveness, recorded
read-only as context — it is not species-level placement proof for any of the
three above.

### 2. ItemGateMgr gate fixture grammar: ABSENT (no manager to grammar-ize)

`ItemGateMgr` exists only as decomp (`pikmin2-research/src/plugProjectKandoU/itemGate.cpp`,
`include/Game/Entities/ItemGate.h` with `GateStates`/`GateColor`). No port gate
manager exists, so a fixture grammar would be invented, not verified. Owner:
unassigned — request owner assignment via #570 (gate/cargo mechanics), with
#186 review if shared semantics are involved.

### 3. Collision/routes observation points: ABSENT (nothing crawler-applicable)

No crawler-applicable collision/routes observation points exist in the port.
Nearest generic mechanisms, listed read-only (not claimed as coverage):
`preview_p2_room.cpp` (generic preview), `pc_p2_bigtreasure_map_trace.cpp` and
`pc_p2_bombsarai_map_trace.cpp` (family-specific). Observation points must be
built, not found. Owner: the #562 consumer's own fixture extension, with #129
navigation semantics noted as related (not assigned).

## Downstream implementation specs outlined (for #562; not staged here)

1. Species fidelity proofs for Wealthy/Hana via #131 once ported.
2. Ooinu_s plant-placement proof via flora mechanics.
3. ItemGateMgr port + fixture grammar (owner TBD via #570).
4. Crawler collision/routes observation in the #562 fixture.

Machine-readable forms live in `registry()` and `downstream_specs()` of the
pins module. Dependencies #129/#130/#131 recorded, never duplicated.

## Evidence

Focused suite 9/9 green (hermetic). Guard `scripts/p2_fixture_captain_guard.h`
sha256 `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`
consumed read-only; no guard provider created, no runtime run, no observed
ticks. Captain safety #632 N/A this turn.
