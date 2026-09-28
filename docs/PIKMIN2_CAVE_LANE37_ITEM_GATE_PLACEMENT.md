# PIKMIN2_CAVE_LANE37_ITEM_GATE_PLACEMENT

Lane 37 / opencode deepseek-v4.1-flash session (root branch `deepseek/p2-l37`, native
branch `deepseek/p2-l37-native`) / parent spec #468 + lane issue #476.

Concrete slot class / routine addressed; missing model piece:
Tagged item and gate placement (cave fan-out lane 37). Implemented the placement
decision core for the frozen slot table: tagged treasure -> matching-hazard leaf,
untagged treasure -> normal pool, gates restricted to choke/leaf doors, the elec
alcove door forced to an electric gate, and no gate on a door the table does not
mark required. This is the engine-free equivalent of the native
`RandItemUnit::setItemSlot` + `RandGateUnit::setGateDoor` pair. The missing model
piece this unlocks is the item/gate binding layer over lane 34's seeded table.

Root base/head; native base/head; dirty state; ordered commits:
- Root base `fba8d5eb0767950f56486bd2738598eb99a4645d`, code head
  `e2c6bb4b5e28168e33fe87dafd9a858d537ee783` (the handoff doc is the tip commit on
  the lane branch), clean.
  - `e2c6bb4b` lane37: tagged cave item and gate placement validator over seeded
    floor table (#476)
- Native base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`, head
  `9538a3cee4f5719488d1d5f97b922dc1803902a9`, clean.
  - `9538a3ce` lane37: engine-free cave item/gate placement routine with
    one-consumer test (#476)

Owned files; generator hooks and provider/consumer agreements:
- Root (new): `experimental/pikmin2_cave_item_gate_placement.py` (planner +
  validator + `P2_CAVE_ITEM`/`P2_CAVE_GATE` marker parser),
  `tests/test_pikmin2_cave_item_gate_placement.py`.
- Native (new): `pc_port/pc_p2_cave_item_gate_placement.h` (header-only, no engine
  types), `tools/test_p2_cave_item_gate_placement.cpp`; CMake hook: one item added
  to the existing engine-free `foreach(policy IN ITEMS ...)` gate list in
  `CMakeLists.txt:1012`.
- Provider/consumer: the frozen floor table is lane 34's seeded artifact. This
  routine consumes it; lane 35's `MapUnitGenerator` port calls
  `p2CavePlanItemSlots`/`p2CavePlanGateDoors` (or `p2CavePlanPlacement`) and emits
  the markers; lane 40/39 parse the markers with the root validator
  (`parse_native_trace` + `validate_placement`). The Python
  `p2-cave-floor-table-v1` field/enum vocabulary (`segment/choke/leaf/bud`,
  `water/elec/fire/poison`) matches the lane 34 scaffold in `l34-root`, not a new
  schema.

What is already integrated; what is actually new:
- Already integrated: `pc_p2_cave.*` checkpoint/anchor/transfer hooks; the surface
  placement bridge; P2 treasure actor hooks (otakara/bigtreasure).
- Actually new: there was **no cave map generator at all** in the native port
  (no `MapUnitGenerator`/`RandMapUnit`/`RandGateUnit`/`RandItemUnit`/
  `gameCaveInfo`/`gameMapParts`; lanes 34-36 have landed zero commits), so no
  item/gate placement existed. This lane authors the placement decision routine
  and its validator, and fixes the `forest_1` floor 1 two-seed fixture.

Build evidence line (native commit, exe SHA-256, ninja -n):
`2026-09-15T13:00:08 lane=l37 target=p2_cave_item_gate_placement_test
native=b805d9c626e4f4558c95aef7cac311a5d9a2068f dirty=yes
exe=.../native-l37-build/p2_cave_item_gate_placement_test.exe
sha256=86af27f33e3df318d63745911dd1f540bf99e98d705314911d82f68ecba51d16
ninja_n="ninja: no work to do."`
(full line in `output/dsw/l37-build-evidence.txt`). Root suite:
`py -3.12 -m pytest tests/test_pikmin2_cave_item_gate_placement.py -q` -> `11
passed`. Broader cave subset -> `3 failed, 274 passed`; the 3 failures
(`test_pikmin2_bulbmin_bridge`, `test_pikmin2_bulbmin_mother`,
`test_pikmin2_cave_transfer`) are pre-existing g++ compile failures against the
stale root `engine/` mirror and were failing before this change.

Fixture/seed used; observed generation evidence with exact paths:
Floor `forest_1` floor 1, seeds **20771** and **42209** (the second varies the
choke hazard water->elec so the seeded tables genuinely differ). Tables:
`output/dsw/l37-out/forest_1_floor1_seed20771.json`,
`output/dsw/l37-out/forest_1_floor1_seed42209.json`. Native routine trace (real
binary output, fixture-injected inputs, not a live cave):
`output/dsw/l37-out/l37-native-placement.log`. Root cross-consumer reconciliation
of that exact trace is exercised by
`tests/test_pikmin2_cave_item_gate_placement.py::test_native_trace_reconciles_across_seeds`
(it reads the sibling `l37-out` log, or `PIKMIN_CAVE_L37_TRACE`).

Acceptance contract 1-6 results (or the subset in scope), injected vs natural:
- (1) Generation invariant — **not proven**. No engine generator exists yet; the
  routine consumes a supplied table. INJECTED.
- (2) Seed determinism — **proven at planning level** for the two frozen tables:
  different seed -> different table -> different gate/item records; each table
  yields zero violations. INJECTED tables (a real seeded table must come from
  lanes 34/35).
- (3) Re-roll invariance — **by construction**: placement is a pure function of
  the frozen table, so an unchanged table re-plans identically. No runtime
  re-entry was run (no generator). INJECTED.
- (4) Reachability — **partial**: a plan never puts a gate on a segment door and
  never places a gate on an unrequired door, and the elec leaf door is always
  electrified; "hole never behind an unrequired hard gate" holds for the planned
  records. No live floor was traversed. INJECTED.
- (5) End-to-end loop — **not attempted** (lane 40 spike; requires the generator).
- (6) Failure handling — **not attempted** (lane 35 retry owns it).
No generation PASS is claimed; every positive result above is fixture-injected.

Re-roll / restart / cross-seed result (or named remaining dependency):
Cross-seed: seeds 20771/42209 both validate with zero violations and differ in
their choke gate. Re-roll/restart: not run — blocked on the lane 35 native cave
generator, which does not exist in this build.

Known limitations; next consumer; ONE exact reproduction command:
Limitations: engine-free decision core only; no live cave generation; the
water choke is modelled as a corridor (`gate=none`) not a hard gate; gate kinds
are limited to `none|elec` in this slice; the second frozen table is a deliberate
variation rather than an independently generated seed table. Next consumer:
lane 35 (`MapUnitGenerator` port) calls the native routine; lanes 39/40 consume
the markers/logic. Reproduction:
`py -3.12 -m pytest tests/test_pikmin2_cave_item_gate_placement.py -q`
(from `output/dsw/l37-root`).

Subagent usage:
- `explore` #1 (source audit): established that the native port has no cave
  generator and located the reference `RandItemUnit::setItemSlot` /
  `RandGateUnit::setGateDoor` semantics. Used as-is; it directly shaped the native
  routine's function names and input shape.
- `explore` #2 (candidate inventory): listed the existing cave modules/tests/
  markers and ran the cave pytest subset (which surfaced the 3 pre-existing
  failures). Used as-is.
- `general` #3 (root validator + pytest): wrote both root files from a frozen
  schema/marker spec. Used as-is for the module; I added the native-trace
  reconciliation test (the subagent's two-seed difference came from varying the
  choke hazard, which I kept). All 11 tests pass.
- Net: the read-heavy audit/inventory ran concurrently with my native work and
  saved roughly 30-45 minutes of source digging; the delegated validator needed no
  correction beyond the extra reconciliation test.
