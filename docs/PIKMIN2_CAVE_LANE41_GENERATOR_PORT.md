# Lane 41 — native cave-generator port (parent #468, lane #480)

Lane 41 / opencode worker session / parent spec #468, lane issue #480.

## Slot class / routine addressed

The whole generator pipeline over one canonical table:

- canonical lane-34 table schema reconciliation (lane 36 leaf shape + lane 40
  seeded shape -> lane-34 canonical);
- phased trunk growth with the forced choke on every path (lane 35 partition/RNG);
- leaf attachment (lane 36 shape);
- tagged item + gate placement through the lane-37 planner;
- candypop bud slot class through the lane-38 constraint;
- the retry-on-failure loop the decomp only has as a 500-iteration fall-through.

Missing model piece at lane start: the PC port had **no runtime cave generator**.
Lanes 35/37/38 shipped engine-free header-only policies with no engine caller;
lane 34 was host-only. This lane adds the single engine-side generator that reads
lane 34's table and consumes 35/37/38.

## Bases, heads, dirty state, ordered commits

- Root base `57925f90a9b3f312d13a9d5616fdb733812415b2` -> head
  `ae775409bfa45331fb3d5815e967cffc6e6e2580`, clean.
  - `ae775409 lane41: reconcile table shapes and drive the native cave generator (#480)`
- Native base `37adbb93e44f56789328d5e43eda465402b8bbf2` -> head
  `8ab071aca5c2ae398366d14ec458975b9f9612fe`, clean.
  - `795b0380 lane41: guard duplicate P2CaveHazard enum for the generator port (#480)`
  - `cc6dad81 lane41: native cave-generator port, engine hook and one-consumer test (#480)`
  - `4afbb95c lane41: keep only tagged items in the reroll-invariance projection (#480)`
  - `8ab071ac lane41: map bud species to layout hazard and cover the bud slot class (#480)`

## Owned files; generator hooks; provider/consumer agreements

Native (owned): `pc_port/pc_p2_cave_generator.h`, `pc_port/pc_p2_cave_generator.cpp`,
`tools/p2_cave_generator_test.cpp`, CMake source + test target entries.

Native (shared, labelled hooks only): `pc_port/pc_p2_cave.cpp` (opt-in runtime
hook + include), `pc_port/pc_p2_cave_growth.h` and
`pc_port/pc_p2_cave_item_gate_placement.h` (duplicate `P2CaveHazard` enum guarded
so one TU can include both; enumerator order identical, no behaviour change).

Root (owned): `experimental/pikmin2_cave_lane41_reconcile.py`,
`experimental/pikmin2_cave_lane41_generator.py`,
`tests/test_pikmin2_cave_lane41_reconcile.py`,
`tests/test_pikmin2_cave_lane41_generator.py`, this handoff.

Provider -> consumer agreements used as-is:

- lane 34 `pikmin2_cave_schema.validate_floor_table` is the canonical shape; the
  reconcile module maps lane-36/lane-40 onto it and never re-declares the schema.
- lane 35 `pc_p2_cave_growth.h`: `P2CaveRng`, `p2_cave_seed`, partition helpers.
- lane 37 `pc_p2_cave_item_gate_placement.h`: `p2CavePlanItemSlots`,
  `p2CavePlanGateDoors`.
- lane 38 `pc_p2_cave_bud_policy.h`: `validatePlacement` (rejects a bud behind
  its own gate).
- lane 40 `pikmin2_cave_spike.check_spike` is the acceptance checker; the native
  layout keeps the source table's slot ids so the checker's `node_id` lookups hit.

New public native surface: `p2CaveParseCanonical` /
`p2CaveWriteCanonical` (`P2_CAVE_FLOOR_V1` text), `p2CaveValidateCanonical`,
`p2CaveGenerateAttempt`, `p2CaveGenerateWithRetry`, `p2CaveLayoutJson`,
`p2CaveLayoutMarker`, `pc_p2_cave_generate_file`.

## Already integrated vs actually new

Already integrated: lanes 34/35/36/37/38/39/40 (merged on the wave branches);
the engine-free growth/item-gate/bud policies and their one-consumer tests.

Actually new: the first engine-side generator; the `P2_CAVE_FLOOR_V1` wire form;
the retry loop with a rejection path; the engine opt-in hook; the reconciliation
glue; and a lane-40-accepted `source: engine` layout.

## Build evidence

From `output/dsw/l41-build-evidence.txt` (clean line):

```
2026-09-15T13:34:10 lane=l41 target=p2_cave_generator_test native=8ab071aca5c2ae398366d14ec458975b9f9612fe dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l41-build exe=...\p2_cave_generator_test.exe sha256=85ea8601f416dfd445e831535033b0eeac168da5c976b0f8b6abc2cd3918ec0c ninja_n="ninja: no work to do." seconds=0
```

Engine TUs `pc_port/pc_p2_cave.cpp` and `pc_port/pc_p2_cave_generator.cpp` both
compile with the exact engine flags (`RC_CAVE=0`, `RC_GEN=0`; evidence in
`output/dsw/l41-out/l41-engine-syntax-evidence.txt`). The full `pikmin_pc` link
was not run this slice.

## Fixture / seed and observed generation evidence

- Table: `tests/fixtures/pikmin2_cave_spike/spike_table.json` (forest_1 floor 1,
  seed 468001, water choke, elec+water leaves, elec door gate, untagged
  `juji_key_fc`). This is the frozen spike _input_ (a seeded table), not a layout.
- Host-written native table: `output/dsw/l41-out/p2-cave-floor-table.txt`.
- Engine layouts: `output/dsw/l41-out/p2-cave-observed-layout.json`,
  `...-reroll.json` (both `"source": "engine"`).
- Checker report: `output/dsw/l41-out/p2-cave-lane41-report.json`
  (`generation_pass: true`, `evidence: natural`).
- Alt seed: `output/dsw/l41-out/alt-seed/` (seed 468002, 3 segments / 2 chokes /
  3 leaves / 1 bud / 2 gates) also `generation_pass: true`.
- Seed determinism: `output/dsw/l41-out/p2-cave-seed-determinism.json`.

Observed layout (seed 468001):

```
segment:0 --choke(water):1-- segment:1 (hole)
segment:0 -- leaf(elec):0 [treasure_elec] -- gate(elec)
segment:1 -- leaf(water):1 [treasure_water]
segment:0 [juji_key_fc]
```

## Acceptance contract results (natural vs injected)

1. Generation invariant — **PASS, natural**: required choke/leaves exist, the
   choke is a cut vertex (removing it disconnects entrance from hole), and the
   lane-40 checker returns `generation_pass=true` with `source=engine`.
2. Seed determinism — **PASS**: native test proves same seed+salt -> byte-identical
   layout; lane-40 `check_determinism` between 468001 and 468002 passes
   (`p2-cave-seed-determinism.json`).
3. Re-roll invariance — **PASS, natural**: two engine layouts for one seed both
   pass `check_layout` and keep the same requirements; the native logical
   projection is stable across salts.
4. Reachability — **PASS**: the only gate is an elec gate on the elec leaf door;
   hard gates appear only where the table's logic requires them.
5. End-to-end "come back with yellow" loop — **NOT RUN**; lane 40 owns the
   scenario harness. Named remaining dependency.
6. Failure handling — **PASS**: a table whose forced leaves exceed every salt's
   door budget is rejected after 8 retries (native test), never shipped.

No hand-placed or fixture-injected layout was used for the generation evidence;
the only fixture is the frozen seeded table, which is the generator's input.

## Re-roll / restart / cross-seed

Re-roll: two engine runs at one seed yield distinct geometry (unit/door rerolls)
with the same logical projection. Cross-seed: seed 468002 produces a different
table and layout, still `generation_pass=true`. Restart/checkpoint invariant is
owned by lane 11 and not exercised here.

## Known limitations; next consumer

- The generator realizes the seeded structural graph as the engine unit graph.
  It does **not** yet load/instantiate P2 `MapUnitInterface` rooms or render a
  live cave scene, so "engine-generated" means the engine-linked generator module
  computed the layout from the frozen table; matching decomp Dolphin RNG/list
  order (`RandMapChecker` overlap checks included) is future work.
- Purple candypop buds have no lane-40 hazard vocabulary (mapped to none).
- The in-engine hook is opt-in via `PIKMIN_CAVE_GENERATOR_TABLE` /
  `PIKMIN_CAVE_GENERATOR_OUT`, compile-verified but not yet exercised inside a
  full `pikmin_pc`/nectar run.
- Next consumers: lane 40 QA (run the driver against its spike table), lane 01
  (integrate the runtime hook), lanes 35/37/38 (swap policy calls for real unit
  geometry), lane 39 (logic already consumes the lane-34 table).

## Subagent usage

- `explore` #1 (decomp source audit): used as-is for the routine table and the
  minimal-field list; its RNG-parity and termination risks shaped the retry loop
  and the limitation notes.
- `explore` #2 (existing-candidate inventory): used as-is; it corrected my
  assumption that `engine/` was current (it is a stale copy) and gave the exact
  lane-40 checker vocabulary and `source: engine` semantics.
- `general` #3 (reconcile module + pytest): used after review. I kept the module
  and test, then corrected the source-id preservation it did not cover (lane 40
  looks nodes up by the table's slot id, not lane-34's canonical id). Estimated
  saving ~45-70 min on the read-heavy audit/inventory and the first reconcile
  draft; the source-id correction cost ~15 min.

## One exact reproduction command

From `output/dsw/l41-root`, after building the tool once:

```
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l41 --target p2_cave_generator_test
$env:PATH="C:\msys64\mingw64\bin;$env:PATH"
py -3.12 -m experimental.pikmin2_cave_lane41_generator --table tests/fixtures/pikmin2_cave_spike/spike_table.json --tool C:/Users/alari/pikmin-randomizer/output/dsw/native-l41-build/p2_cave_generator_test.exe --out-dir C:/Users/alari/pikmin-randomizer/output/dsw/l41-out --rerolls 2
```

Expect `{"pass": true, "generation_pass": true, "evidence": "natural", ...}`.
