# Lane 36 — hazard leaf alcoves (cave-generation wave, #468 / lane issue #475)

## Lane 36 / owner-session / parent #468 + lane issue
Lane 36, DeepSeek unattended worker session (private worktrees `l36-root` /
`native-l36`), parent spec **#468**, lane issue **#475**. Implementation owner on
the shared account is recorded as Codex/4laric per AGENTS.md; this worker did not
write GitHub.

## Concrete slot class / routine addressed; missing model piece
**Slot class: Leaves (single-door hazard dead ends with exactly one item spawn).**
Routine addressed: hazard-leaf unit authoring/validation and leaf-to-segment
attachment planning — `experimental/pikmin2_cave_leaf.py`:
`classify_leaf_unit`, `validate_leaf_catalog`, `pick_leaf`, `attach_leaves`,
`build_leaf_catalog`.

Missing model pieces this slice does not supply (owned elsewhere): the lane-34
seeded table producer and the lane-35 unit-pool partition + phased trunk growth
(free doors). This slice defines and consumes the `p2-cave-leaf-table-v1`
producer contract and emits `p2-cave-leaf-plan-v1` for lane 37.

## Root base/head; native base/head; dirty state; ordered commits
- Root base `fba8d5eb0767950f56486bd2738598eb99a4645d` (branch `deepseek/p2-l36`).
- Root head `5808d730` — `lane36: hazard leaf alcove catalog, validator and attachment planner (#475)`.
- Native base/head `b805d9c626e4f4558c95aef7cac311a5d9a2068f` (branch
  `deepseek/p2-l36-native`), **unchanged** — no native source edit on this slice.
- Dirty state: both worktrees clean after the commit.

## Owned files; generator hooks and provider/consumer agreements
Owned / added:
- `experimental/pikmin2_cave_leaf.py` — classification, validation, selection,
  attachment planner, disc-backed catalog builder + CLI.
- `tests/test_pikmin2_cave_leaf.py` — 33 focused tests (31 pure + committed
  fixture; one opt-in real-catalog test on `PIKMIN2_CAVE_LEAF_CATALOG`).
- `docs/PIKMIN2_CAVE_LEAF_TABLE_EXAMPLE.json` — the injected example table.

Hooks / agreements:
- **Producer contract** `p2-cave-leaf-table-v1`: `{schema, floor,
  segments:[{segment, doors:[int]}], leaves:[{slot, segment, hazard}]}`. Lane 34
  seeds it; lane 35 supplies each segment's free doors after trunk growth.
- **Consumer contract** `p2-cave-leaf-plan-v1`: ordered `assignments`
  (`slot, segment, door, hazard, hardness, unit, treasure_slots, water`) plus
  `unused_doors`. Lane 37 places the tagged treasure into the assigned leaf and the
  matching gate/hazard actor at its door. `water` here is intrinsic
  (`waterbox.txt`); `elec`/`poison`/`fire` are actor hazards assigned by 37.
- No shared generator routine, shared host file, `pc_p2_cave.*` or CMake was
  touched, so nothing is needed from lane 01.

## What is already integrated; what is actually new
Reused (already on the base): `pikmin2_cave_catalog.inventory` (disc catalog),
`pikmin2_cave.unit_definition/tree/safe_name`, `pikmin2_collision.decode_room`
(layout spawn markers), `pikmin2_assets.archive_files/disc_files`.
New: leaf rules (one door; cap or room kind; exactly one `CGT_TreasureItem`=2
spawn; water only when `waterbox.txt` is non-empty), deterministic per-hazard
selection (dry alcove preferred for actor hazards, authored `*_hiba*` preferred
for fire), fail-closed catalog validation, and the first-free-door attachment
planner with door-exhaustion refusal.

## Build evidence line (native commit, exe SHA-256, ninja -n)
`2026-09-15T13:03:33 lane=l36 target=pikmin_pc native=b805d9c626e4f4558c95aef7cac311a5d9a2068f dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l36-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l36-build\bin\nectar.exe sha256=827f56905404108a553fcb34fae6f03a5965de282fd2564f1e7b8550bae4cb7f ninja_n="ninja: no work to do." seconds=205`
(appended to `output/dsw/l36-build-evidence.txt`). Baseline only: this slice
changed no native source, so the SHA is not attributable to lane 36.

## Fixture/seed used; observed generation evidence with exact paths
No AP seed (no runtime cave ran; lanes 34/35/40 own that). Disc GPVE01 rev 0.
Real disc scans, **natural**:
- `output/dsw/l36-out/catalog-a/catalog.json` — 14 caves / 105 floors / 96 pools.
- `output/dsw/l36-out/leaf-a/leaf_catalog.json` — 7 validated leaf units
  (sha256 `25E89D66…235FDB`); capacity water 4, elec/poison/fire 7.
- `output/dsw/l36-out/leaf-plan-a/leaf_catalog.json` — byte-identical catalog
  (same sha256), proving a second run is deterministic.
Observed real units: water `room_kingchap_b_tsuchi` (forest_3),
`room_north4x4k_1_conc`, `room_north4x4l_1_conc`, `room_north4x4l_1_tile`; dry
`room_north2x2_1_metal`, `room_north3_1_tsuchi`; authored fire
`room_north_1_hiba_tsuchi`. Each has exactly one door and exactly one
`CGT_TreasureItem` spawn.

Injected fixture table + plan (not a generated cave):
- `docs/PIKMIN2_CAVE_LEAF_TABLE_EXAMPLE.json` — `p2-cave-leaf-table-v1`, floor
  `forest_1:floor2`, water+elec slots on two fixture segments.
- `output/dsw/l36-out/leaf-plan-a/leaf_plan.json` (sha256 `10E4D821…A78E4`) —
  water-0 → segment 0/door 1 → `room_kingchap_b_tsuchi`; elec-0 → segment 1/door 1
  → `room_north2x2_1_metal`; unused door 0:[2].

Finding worth passing on: retail `item_cap_*`/`cap_*` are single-door caps but
carry **zero** `CGT_TreasureItem` markers, so they were correctly refused by the
"exactly one item spawn inside" rule; the generator (lane 37) must add the item
marker for caps, or use the single-door item rooms above.

## Acceptance contract 1-6 results, injected vs natural
- **1 Generation invariant** — *partial, natural (config only).* Validated that
  every authored leaf is a single-door dead end (cap or room) with exactly one
  treasure slot, and attachment consumes one distinct door per slot. The
  "on every path to the hole by construction" property needs lane 35's growth and
  was not tested.
- **2 Seed determinism** — *natural for the catalog* (two runs byte-identical,
  sha256 above); *injected for placement* (plan deterministic for a fixed fixture
  table). Same-AP-seed→same-per-floor-table is lane 34's.
- **3 Re-roll invariance** — not in scope; named dependency lane 35/40.
- **4 Reachability** — not in scope; named dependency lane 35/40; ambient hazards
  stay worst-case.
- **5 End-to-end loop** — not in scope; lane 40.
- **6 Failure handling** — *natural (fail-closed, tested).* 2-door units, corridor
  kinds, zero/two treasure spawns, unknown water state, wrong schema, duplicate
  units, water/dry support mismatch, unknown hazard, door exhaustion and missing
  segments all raise `ValueError`.

## Re-roll / restart / cross-seed result (or named remaining dependency)
Not applicable yet: no live cave was generated. Named remaining dependency: lane
35's phased growth must feed `attach_leaves` and lane 40 must re-enter a floor to
show the plan is stable. Cross-seed variation is lane 34's table.

## Known limitations; next consumer; ONE exact reproduction command
Limitations: catalog is a validated unit *selection*, not an assembled floor; a
single unit template may be reused across distinct leaf slots; actor hazards
(elec/poison/fire) are declared, not placed; no runtime/preview evidence.

Next consumer: **lane 37** (tagged item + gate placement reads the leaf plan);
then lane 35 (feed real segment doors) and lane 40 (spike/QA).

One exact reproduction command (run from the root worktree; the catalog
prerequisite is the one-line `pikmin2_cave_catalog` run in
`output/dsw/l36-out/catalog-a`):
```
py -3.12 -m experimental.pikmin2_cave_leaf --iso "C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso" --catalog "C:/Users/alari/pikmin-randomizer/output/dsw/l36-out/catalog-a/catalog.json" --output "C:/Users/alari/pikmin-randomizer/output/dsw/l36-out/leaf-repro" --table "docs/PIKMIN2_CAVE_LEAF_TABLE_EXAMPLE.json"
```
Expected: `{"units": 7, "capacity": {"water": 4, "elec": 7, "poison": 7, "fire": 7}, ..., "assignments": 2}`.

## Subagent usage
Three subagents were used per the brief:
1. `explore` — **source audit** of `native/pikmin2-research`: produced the
   unit/`CaveGenType`/waterbox/door-gate semantics table with `file:line`
   citations. **Used as-is** for design; its two key claims I independently
   verified against the disc data (unit kinds, single-door rooms with one
   `CGT_TreasureItem`, intrinsic `waterbox.txt`). Saved the full read of the decomp.
2. `explore` — **existing-candidate inventory** of both worktrees: confirmed no
   lane 34/35/37/38 artifact had landed and listed the reusable cave modules,
   tests and markers. **Used as-is**; directly shaped the decision to define the
   leaf-table contract here instead of waiting.
3. `general` — **tests/scaffolding**: wrote `tests/test_pikmin2_cave_leaf.py`
   against a spec I supplied, ran it (31 passed) and reported no failures. **Used
   as-is with one correction**: I re-read the file for the known leakage classes
   (hardcoded lane paths, tautologies, parallel functions) and found none; I then
   added the committed-fixture test and the opt-in real-catalog test and refined
   `pick_leaf` to prefer dry alcoves for actor hazards.
Estimated saving: ~30–40 minutes of read/test wall-clock; the delegated builder
needed no correction, consistent with the read-heavy delegation pattern.
