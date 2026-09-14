# P2 plant / Spectralid-sentinel native slice (lane 23, #171 / #448)

## Scope

This is lane 23's **plant scenery** slice on top of the delivered pure Python
behavior model (`experimental/pikmin2_flora_behavior.py`) and the audit
(`docs/PIKMIN2_FLORA_AUDIT.md`, #171). It adds a native, opt-in (sidecar-gated,
fail-closed, inert without the sidecar) policy layer over the port's existing
P1 `Plant` scenery actors (`include/PlantMgr.h`, `src/plugPikiKando/plantMgr.cpp`):

- **LOD sizing.** The repurposed general parameters are treated as LOD volumes
  (territory lifts the sphere; private/home radius define cylinders; fp01 on
  Clover and the brown figworts is the general floor offset). The bound plant's
  scale is clamped and the floor offset is applied only for floor-role species.
- **Spectralid sentinel.** Only `Tanpopo`/`Ooinu_l`/`Magaret` declare the
  Spectralid child and reserve slots; a generator carrying the sentinel spawns
  five yellow Spectralids on the plant's first touch. Any other species carrying
  the sentinel is **suppressed**.
- **Slot rule.** A non-reserved species never spawns Spectralids.

New files (native): `pc_port/pc_p2_plant_policy.h` (pure policy + strict
`P2_PLANT_1` parser), `pc_port/pc_p2_plant.{h,cpp}`. Additive registration in
`CMakeLists.txt`, `pc_p2_preview.cpp` and `gameCoreSection.cpp`.

## Source anchors

| Behavior | Value | Anchor |
|---|---|---|
| One Plants::Obj base, no FSM | empty subclass per species | `plantsMgr.h:36-39`, audit 89-99 |
| LOD volumes | territory sphere; private/home cylinders; fp01 floor offset | audit 99-102 |
| Clover floor offset | general fp01 40.0 (asset contract; audit 25.0 inert) | `FLORA_ASSETS` §5, `plantsMgr.cpp:46-48` |
| Brown figwort offsets | KareOoinu_s 45 / KareOoinu_l 20 disc | audit 100-102 |
| Sway on touch | mover speed > 1 past volume; captains sound only | `plants.cpp:141-166` |
| Spectralid sentinel | five yellow on first touch | `plants.cpp:187-201` |
| Slot reservation | `Tanpopo`/`Ooinu_l`/`Magaret` only | `enemyInfo.cpp:70,76,83`, `generalEnemyMgr.cpp:818-838` |
| Invulnerable scenery | no damage/death path | audit 89-99 |

The `P2_PLANT_1` sidecar is documented in `pc_p2_plant.cpp`; malformed input
aborts (fail-closed).

## Log contract

```text
P2_PLANT_READY generator=<id> species=<name> plant_type=<n> bound=1
P2_PLANT_LOD generator=<id> species=<name> territory=.. private=.. home=.. floor_role=.. floor_offset=.. scale=.. clamped=<0|1> reconstructed=<0|1> bound=<0|1>
P2_PLANT_SENTINEL_NONE generator=<id> species=<name> sentinel=0
P2_PLANT_SENTINEL_ARMED generator=<id> species=<name> per_touch=5 slot_reserved=1
P2_PLANT_SENTINEL_BLOCKED generator=<id> species=<name> reason=no_qurione_seam spawn=blocked
P2_PLANT_SENTINEL_SUPPRESSED generator=<id> species=<name> reason=no_reserved_slot
P2_PLANT_SCAN generator=<id> plant_type=<n>
```

`completion` requires the explicit `PASS P2_PLANT_NATIVE lod_sentinel_slot_rule`
line; the fixture self-terminates on a wall-clock ceiling and prints
`P2_PLANT_RUNTIME_BLOCKED <gate> reason=<reason>` instead of hanging.

## Implemented vs BLOCKED / remaining

**Implemented (native, this slice)**

- Generator-bound `Plant` actors with clamped LOD scale and floor-offset role.
- Sentinel slot-rule policy: reserved vs suppressed vs none.
- Non-sentinel plants never arm or spawn.
- `sways`/`touchSound` policy (speed/volume, captain-only sound).

**BLOCKED**

- **Spectralid spawn (`reason=no_qurione_seam`).** The lane-15 `pc_p2_qurione`
  module is a visual-only binder (setup/reset/forget/name/draw) over existing
  `TEKI_Qurione` actors; it exposes no spawn seam and its shared interface must
  not be changed. A reserved sentinel plant therefore reports
  `P2_PLANT_SENTINEL_BLOCKED` instead of forking the flier. Driving the existing
  module with a generated `TEKI_Qurione` that carries a generator id is the next
  step and requires a shared spawn hook.
- **Onion/seed accounting** and Piklopedia/`HasNoInfo` runtime UI are out of
  scope.

## Approximations and labeled injections

- The fixture stages three `Plant` generator records by cloning the practice
  `plants.gen` template and setting `mPlantType` and the little-endian
  `Generator::_70` id; this is a labeled fixture injection, not source
  placement.
- "Sizing" applies a clamped scale and the policy floor offset to the bound
  plant; it does not rebuild the LOD volume geometry (the audit treats the
  general parameters as volumes, which the renderer already consumes).
- The floor-offset reading is marked reconstructed (Clover asset-contract
  correction).

## Build and fixture provenance

- Native branch `opencode/p2-lane23-native`, commit
  `fc24c9e901416c8a1729b76b9133106f17496898` (base `57bb1a4e`), clean.
- Private build `output/p2-lane23-native-build`, Ninja; dry run
  `ninja: no work to do.`
- Fixture `output/p2-lane23-plant-fixture-1/build/fixture.exe`
  SHA-256 `345ef4631708c4319e72c15e1f0e30f7c31905391e31dad3384f51422471e054`,
  `provenance.json` status `built`, expected native head matches.
- GL fixture runs are serialized and owned by the coordinator. This lane built
  only; no runtime/gameplay acceptance is claimed.

### Staged assets (`pikmin2_plant_runtime.stage`)

- `dataDir/stages/chal0.ini` = `practice.ini` (map `courses/practice/practice.mod`),
- `dataDir/stages/chal0/default.gen` = practice goal records + 10 injected Red
  Pikmin (labeled squad injection),
- `dataDir/stages/chal0/plants.gen` = three injected `Plant` records
  (`Ooinu_l` 240021 sentinel, `Tanpopo` 240022 no sentinel, `Clover` 240023
  sentinel but not reserved),
- every other pre-existing `dataDir/stages/chal0/*.gen` overridden to an empty stage,
- `p2-cargo-free.txt` (`P2_CARGO_FREE_1`),
- `p2-plant.txt` = the strict `P2_PLANT_1` sidecar above.

Exact GL run command (from `output/p2-lane23-root`):

```powershell
$env:PIKMIN_P2_ROOM_WINDOW='960x540'
py -3.12 -m experimental.pikmin2_plant_runtime run --assets C:\Users\alari\bbft\dist\cohesion\pikmin\assets --output output/p2-lane23-plant-runtime-01 --exe C:\Users\alari\pikmin-randomizer\output\p2-lane23-plant-fixture-1\build\fixture.exe
```

## Validation

```text
py -3.12 -m pytest tests/test_pikmin2_plant_runtime.py -q   # 6 passed
py -3.12 -m pytest tests/ -q -k plant                       # 38 passed
g++ -std=c++17 -Wall -Wextra -Werror -I native-patches/plant tests/pikmin2_plant_policy.cpp
```

No runtime/native gameplay acceptance is claimed by this lane.
