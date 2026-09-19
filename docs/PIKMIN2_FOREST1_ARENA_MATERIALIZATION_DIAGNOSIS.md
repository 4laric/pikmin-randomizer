# Forest_1 staged-arena materialization diagnosis (issue #790)

Bounded diagnosis for recovery 28e4c77c (blocked
cave-forest1-collision-routes-obs #773; downstream
shard-caves-forest-forest1-p1 #154). Consumes the gen-13 evidence
read-only: `output/workflow/autofill/planning-shards/caves-forest/
prepared/forest1-collision-obs-out/run-collision2.log` sha256
`de7812cce5a59c20650a59f0cbae7f13e8cde146988dcd59547072b525fe40b7`
(1714 lines). Diagnosis only; never an engine unblock. No ADMIT.

## Observed evidence (exact counts)

- `P2_CAVE_READY floor=1 survivors=20` x1; `P2_CAVE_RESTORE` x20.
- `P2_FOREST1_COLLISION_OBSERVE` x34, ALL identical: `squad=0 births=1
  grounded=1 moved=0 live_actors=1` (ticks 600..20400).
- `[PC Generator] default: initialised 24 recognised generators,
  spawned 24 creatures`; plant: 30 recognised, 30 spawned.
- Zero `P2_CAVE_GENERATE_*` markers: the staged generate package
  (7 units, 7 rooms, 18 doors, 36 links on disk) was never parsed.
- 2 `DVDOpen ... FAILED` lines: `dataDir/stages/chal0/1.gen` and
  `init.gen` absent from assets.
- No `P2_FIXTURE_CAPTAIN_DOWN`, no BLOCKED, no PASS.

## Attribution (verified file:symbol pins)

- A1 staged package never parsed: `native/pc_port/pc_p2_cave_generate.h`
  `P2_CAVE_GENERATE_*` (present only on the #129 provider line via
  commit 1a0904ac; absent from the maintained native line). Owner:
  #773 fixture setup (generate-path invocation).
- A2 missing stage files: `native/pc_port/pc_p2_cave.cpp`
  `pc_p2_cave_setup`. Owner: arena asset staging via #773 setup.
- A3 spawned-vs-addressable: `native/src/plugPikiKando/generator.cpp`
  `GeneratorMgr::init` (sums `mAliveCount` per generator). 54 engine
  creatures vs 1 addressed: observer counting scope. Owner: #773.
- B restore-without-squad: `native/pc_port/pc_p2_cave.cpp`
  `pc_p2_cave_setup` + `P2_CAVE_RESTORE` + `P2_CAVE_READY` (recolors
  live Piki from `pikiMgr`, requires `spawned.size()==squad.size()`).
  20 restored, squad max 0: restored Piki never join squad membership.
  Owner: #773 observer squad definition first; engine Piki/Navi
  follow behavior second.

## Captain safety #632

No runtime run in this slice; guard labelling only. Any follow-on
observation must adopt `scripts/p2_fixture_captain_guard.h` sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`,
check orimaDead/deadState/HP<=1 before observed ticks, emit
`CAPTAIN_DOWN` + exit BLOCKED, park the captain out of reach.

## Tooling

`experimental/pikmin2_forest1_arena_materialization_diagnosis.py`
(counts + attribution, fail-closed) with focused tests
(`tests/test_pikmin2_forest1_arena_materialization_diagnosis.py`).
All six gates UNTESTED.
