# Lane 45 — Real cave geometry + electric gate actor (parent #468, lane issue #483)

Lane 45 / opencode DeepSeek worker session / parent spec #468, lane issue #483.
Mode: **Implementation**. This lane replaces the lane-44 proxy floor squares for the
hazard-bearing cave nodes with real converted unit models and a real electric-gate
actor, while leaving the lane-41 layout and the lane-44 ability timeline unchanged.

## Slot class / routine addressed; missing model piece

- **Routine addressed:** geometry/model **instantiation** and **gate actor placement**
  for `choke`/`leaf`/`gate` nodes. Lane 44 drew every cave-room node as a proxy
  square/line and had no real model or gate object; lane 45 adds the missing consumer
  that loads converted unit `.mod` files through the port's own `gameflow.loadShape`
  path, draws them at the node transforms, and instantiates a real electric-gate actor
  that delivers the lane-10 `InteractDenki` receiver.
- **Missing model piece:** the host `P2_CAVE_GEOMETRY_1` plan (node -> converted model
  + gate actor), the native parser, the real-model draw path, and the gate actor were
  all absent. Inventory found no `cave_geometry` module anywhere in either worktree.
- **Boundary respected:** the lane-41 generator, lane-44 layout/timeline logic, lane-39
  AP logic and lane-46 items were not changed. Only small, labelled hooks were added to
  lane-44-owned `pc_p2_cave_rooms.cpp` (skip a node whose real model loaded) and to the
  shared `pc_p2_cave.cpp` setup/tick/draw seams.

## Bases, heads, dirty state, ordered commits

- Root base `87dd05fb0cd7479e0f3545b1b2942f829b6ef105` (branch `deepseek/p2-l45`).
  - `8e606183 lane45: host real-geometry plan bridge and focused tests (#483)`
  - this document (root head)
- Native base `2d64d65dee0041f9b0e3be73cd34d8c40f663cfe` (branch `deepseek/p2-l45-native`).
  - `99c3e233 lane45: real cave-unit geometry + electric gate actor, one-consumer test and draw hook (#483)`
  - `5ca5f907 lane45: one-shot real-geometry draw marker for live evidence (#483)` (native head)
- Dirty state at handoff: none tracked on either branch. All generated evidence
  (converted models, geometry plans, staged runs, fixture, logs) stays under
  `output/dsw/l45-out/` (ignored, not committed).

## Owned files; generator hooks; provider/consumer agreements

Root (owned):

- `experimental/pikmin2_cave_geometry.py` — host bridge: consumes the lane-44
  `p2-cave-rooms.json`, assigns one real converted unit model per `choke`/`leaf`/`gate`
  node and a gate actor per electric leaf/gate, emits `p2-cave-geometry.json` and the
  canonical `P2_CAVE_GEOMETRY_1` text. Public API: `build_geometry`,
  `geometry_text`, `parse_geometry_text`, `validate_geometry`, `geometry_marker`.
  Fail-closed: proxy/missing-model/electrified-without-gate all refuse `valid`.
- `tests/test_pikmin2_cave_geometry.py` — 12 tests (round-trip, real/proxy classify,
  missing model, missing gate, on-disk model check, malformed/truncated/duplicate,
  determinism, optional lane-44 integration).
- this document.

Native (owned):

- `pc_port/pc_p2_cave_geometry.h` — engine-free plan structs, `P2_CAVE_GEOMETRY_1`
  parser, `p2CaveGeometryIsReal`, node/plan markers. One-consumer test includes only this.
- `pc_port/pc_p2_cave_geometry_engine.h` / `.cpp` — engine glue: opt-in
  `PIKMIN_CAVE_GEOMETRY` (default `p2-cave-geometry.txt`) + optional
  `PIKMIN_CAVE_GEOMETRY_MODELS` prefix; loads real models via `gameflow.loadShape` +
  texture `attach()`, draws with `makeSRT`/`updateAnim`/`drawshape`, owns the live
  `P2CaveElecGate` actor (open on electric-immune Pikmin, else `InteractDenki`).
- `tools/p2_cave_geometry_test.cpp` — one-consumer gate.
- `CMakeLists.txt` — `pc_p2_cave_geometry.cpp` in `PC_PORT_SOURCES`; `p2_cave_geometry_test`.
- Hooks in shared `pc_port/pc_p2_cave.cpp` (labelled, opt-in): include,
  `pc_p2_cave_geometry_shutdown()` at setup start, `pc_p2_cave_geometry_setup()` after
  the lane-44 rooms setup, `pc_p2_cave_geometry_tick()` at the top of `pc_p2_cave_tick`,
  and one `pc_p2_cave_geometry_draw(gfx)` next to the rooms draw.

Provider/consumer agreements:

- **Consumes** the lane-44 `p2-cave-rooms.json` (node ids preserved verbatim) and the
  lane-41 layout through it.
- **Consumes** lane-36 leaf-unit identities for model selection and lane-37 gate
  placement (`elec` leaf/gate -> electric gate actor). No lane-36/37 code changed.
- **Produces** the `P2_CAVE_GEOMETRY_1` plan for the native consumer. The native parser
  was cross-checked against the root emitter (same marker line).
- **Reuses** the lane-09 converter (`experimental.pikmin2_convert.convert`) and the
  lane-44 engine path; no second room/import pipeline was built.

## Already integrated vs actually new

- Already integrated: lane-41 generator/observed layout; lane-40 checker; lane-44 proxy
  rooms, live loop and draw hook; lane-36 leaf catalog; lane-37 gate placement; lane-09
  converter; lane-10 `InteractDenki`.
- Actually new: the `P2_CAVE_GEOMETRY_1` host plan + validator; the native parser,
  real-model load/draw path and per-node markers; the real electric-gate actor and its
  `InteractDenki` delivery; the proxy-square suppression for loaded nodes; the
  one-consumer and focused tests; the converted forest_1 unit + P2 e-gate assets.

## Build evidence

`output/dsw/l45-build-evidence.txt` (native head, exe SHA-256, `ninja -n`):

```
2026-09-15T15:50:26 lane=l45 target=pikmin_pc native=5ca5f907e6acdc016ca6e76c1b410bc2d7f4e4a3 dirty=no
  exe=...\native-l45-build\bin\nectar.exe
  sha256=8a3c291c3f439bf526b2641abd15457053c76271f92bbaa3c6bd4e5ed4057ed6 ninja_n="ninja: no work to do."
2026-09-15T15:30:40 lane=l45 target=p2_cave_geometry_test native=2d64d65d... dirty=yes
  exe=...\native-l45-build\p2_cave_geometry_test.exe
  sha256=b164f6ef496fd6b4b35e700d616c2d013ecbc9f51c1fb8e33164102e1c801c5d ninja_n="ninja: no work to do."
```

One-consumer test prints
`PASS p2 cave geometry: real model plan, proxy rejection, gate actor binding`.
Focused root tests: `py -3.12 -m pytest tests/test_pikmin2_cave_geometry.py
tests/test_pikmin2_cave_rooms.py tests/test_pikmin2_cave_leaf.py -q` -> `59 passed, 1 skipped`.

## Fixture / seed and observed generation evidence

- Floor: `forest_1` floor 1, frozen seed `468001`, lane-41 layout
  `output/dsw/l41-out/p2-cave-observed-layout.json` (water choke; elec leaf + elec gate;
  water leaf; untagged `juji_key_fc`).
- Real converted assets (regenerated this lane, strict where the converter allows):
  - forest_1 units: `output/dsw/l45-out/forest_1-units-strict/units.json` (11/14 strict;
    `room_north3_1_tsuchi` used for the choke/leaves)
  - P2 electric gate: `output/dsw/l45-out/gate-a/e-gate/e-gate/e-gate.mod`
    (from `user/Kando/objects/gates/e-gate-arc.szs`; approximate materials + rigid
    bind-pose bake, because the strict converter rejects multiple joints/stages)
  - staged for the run: `output/dsw/l45-out/models/courses/pikmin2room/p2cave_room_north3_1_tsuchi.mod`
    (sha256 `1f44eae1a8b52e09231dc2b177583d7a28743f2a665e68590d1b66253d5e5f09`) and
    `.../p2cave_e_gate.mod` (sha256 `98693b7912151efaa4313ed0663f8bbc73c1a59a36b9bae366f90c8192d23f48`)
- Geometry plans: `output/dsw/l45-out/geometry-salt0/p2-cave-geometry.txt` (sha256
  `8fd0f4ada928dd70f9fc72e9ce01bccbcf76c9e827f06cd246433f4dd13b7eeb`) and
  `.../geometry-salt7/p2-cave-geometry.txt` (sha256 `8232f3b501a7cbb84f93bb266a398ab62044ffba3c0ae69afede94e4b4ce54c6`).
- Live run (960x540 centred window, `PIKMIN_P2_ROOM_WINDOW=960x540`, `PYTHONUTF8=1`,
  GL-slot-wrapped, fixture main = `tools/preview_p2_room.cpp`):
  - run dir `output/dsw/l45-out/rooms-preview/1c47d613230e46e5a3157ae29780a081/`
  - salt0: `geometry-run.log`; salt7: `geometry-run-salt7.log`
  - capture `p2-cave-rooms.ppm`; fixture sha256 `dfe10334b4a997c04ff76da374e8108b387c8352099f02bc94e9610de6382bf6`

Observed markers (salt 0):

```
P2_CAVE_GEOMETRY_NODE id=choke_water_0     kind=choke hazard=water class=real model=courses/pikmin2room/p2cave_room_north3_1_tsuchi.mod proxy=0
P2_CAVE_GEOMETRY_NODE id=leaf_elec_0       kind=leaf  hazard=elec  class=real model=courses/pikmin2room/p2cave_room_north3_1_tsuchi.mod proxy=0
P2_CAVE_GEOMETRY_NODE id=leaf_water_0      kind=leaf  hazard=water class=real model=courses/pikmin2room/p2cave_room_north3_1_tsuchi.mod proxy=0
P2_CAVE_GEOMETRY_NODE id=gate:leaf_elec_0  kind=gate  hazard=elec  class=real model=courses/pikmin2room/p2cave_e_gate.mod proxy=0
P2_CAVE_GEOMETRY_GATE id=leaf_elec_0      hazard=elec actor=p2_elec_gate model=courses/pikmin2room/p2cave_e_gate.mod placed=1
P2_CAVE_GEOMETRY_GATE id=gate:leaf_elec_0 hazard=elec actor=p2_elec_gate model=courses/pikmin2room/p2cave_e_gate.mod placed=1
P2_CAVE_GEOMETRY_READY nodes=6 real=4 proxy=2 gate_actors=2 geometry=real cave=forest_1 floor=1 seed=468001 salt=0
P2_CAVE_GEOMETRY_DRAW nodes=6 models=4 gates=2 geometry=real
P2_CAVE_GEOMETRY_GATE_DENKI id=leaf_elec_0 actor=p2_elec_gate target=1 accepted=1 target_state=35
P2_CAVE_GEOMETRY_GATE_DENKI id=gate:leaf_elec_0 actor=p2_elec_gate target=1 accepted=1 target_state=35
P2_CAVE_ROOMS_TIMELINE tag=fresh_floor_no_abilities hole=0 treasure_elec=0 treasure_water=0 untagged=1
P2_CAVE_ROOMS_TIMELINE tag=come_back_with_yellow  hole=0 treasure_elec=1 treasure_water=0 untagged=1
P2_CAVE_ROOMS_TIMELINE tag=return_with_yellow_and_blue hole=1 treasure_elec=1 treasure_water=1 untagged=1
PASS cave rooms: proxy floor, live squad keys, hazard timeline (proxy geometry)
```

`target_state=35` is `PIKISTATE_DenkiDying`: the real electric receiver accepted a
non-immune Pikmin from the real gate actor. (The lane-44 `P2_CAVE_ROOMS_*` "proxy
geometry" text is lane-44's own fixture wording; the lane-45 markers above are the
authoritative real-geometry evidence.)

## Acceptance contract 1–6 results (injected vs natural)

| # | Contract item | Result | Evidence class |
|---|---|---|---|
| 1 | Generation invariant | unchanged from lane 41/40 (not re-run) | natural (lane 41) |
| 2 | Seed determinism | unchanged; geometry plan mirrors the frozen table | natural/model |
| 3 | Re-roll invariance | **PASS** — salt0/salt7 share the identical `P2_CAVE_ROOMS_PROJECTION` and both `geometry=real`; their geometry plans differ in gx/gz | natural table, real geometry |
| 4 | Reachability | unchanged — live timeline identical to lane 44 (only the water choke gates the hole) | natural gating over real geometry |
| 5 | End-to-end loop | **PARTIAL** — same staged timeline as lane 44; additionally the real gate actor delivered `InteractDenki` (`accepted=1`, `DenkiDying`) | real gate hazard; staged ability acquisition |
| 6 | Failure handling | unchanged for generation; the geometry plan is fail-closed (proxy/missing-model/electrified-without-gate refuse `valid`) | root + native tests |

Real vs labelled: the choke/leaf/gate nodes are drawn by real converted `.mod` meshes
(`P2_CAVE_GEOMETRY_DRAW models=4 gates=2`), not proxy squares. Honest caveats:
the leaf/choke meshes are the real converted forest_1 unit `room_north3_1_tsuchi`, not
biome-specific water/electric unit meshes (see limitations); the e-gate mesh is a real
converted P2 electric-gate model with approximate materials and a rigid bind-pose bake.
No proxy artefact is claimed as a generation PASS; generation evidence still belongs to
the lane-41/40 line.

## Re-roll / restart / cross-seed

- **Re-roll:** salt 0 and salt 7 give byte-identical logical projections and both
  instantiate the same four real models at different grid cells -> the table holds while
  the real geometry rerolls.
- **Restart:** not evaluated (needs the lane-11 checkpoint pass); named dependency.
- **Cross-seed:** not re-run live; lane 40 `check_determinism` remains the authority.

## Known limitations; next consumer

- **Water leaf/choke mesh is a converted dry unit.** The lane-36 designated water leaf
  `room_kingchap_b_tsuchi` cannot be converted by the current converter
  (`Water-volume conversion not implemented`), so the water nodes reuse the real
  converted forest_1 dry unit `room_north3_1_tsuchi` with the hazard taken from the
  seeded table. Converting a water unit needs a converter change.
- **E-gate mesh is approximate + bind-pose baked** (multi-joint, multi-stage). It is a
  real converted P2 electric-gate model, but not retail-faithful open/close animation.
- **No carry collision/blocking.** The gate actor delivers `InteractDenki` and opens to
  electric-immune Pikmin; it does not physically block Pikmin carrying across the door.
  Pikmin carry-blocking remains with the engine's gate/collision work.
- **Staged ability acquisition.** As in lane 44, the `come_back_with_yellow` step
  recolours a Pikmin rather than acquiring a treasure; the gate-open event was not
  observed live because the staged Yellow stands at the entrance, not the gate.
- **One flaky non-zero exit** was observed on one repeat of the salt-0 run (same
  markers, no PASS); two subsequent runs exited 0. Treat the live fixture as
  timing-sensitive and require the PASS line.
- **Next consumers:** lane 01 (integrate the hooks/plan), lane 36/09 (convert
  biome-correct water/elec unit meshes), lane 40 QA (re-run its checker and the spike
  with real geometry), lane 46 (items/collection).

## ONE exact reproduction command

Prerequisites are the staged run dir
`output/dsw/l45-out/rooms-preview/1c47d613230e46e5a3157ae29780a081/` (room preview,
converted models copied under `assets/dataDir/courses/pikmin2room/`, `p2-cave-entry.txt`,
`p2-cave-rooms.txt`, `p2-cave-geometry.txt`, `fixture.exe`). From that directory:

```
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l45 -- C:/Users/alari/pikmin-randomizer/output/dsw/l45-out/rooms-preview/1c47d613230e46e5a3157ae29780a081/fixture.exe --experimental-pikmin2-room
```

with `PIKMIN_P2_ROOM_WINDOW=960x540`, `PYTHONUTF8=1`, `PIKMIN_CAVE_ROOMS=p2-cave-rooms.txt`,
`PIKMIN_CAVE_GEOMETRY=p2-cave-geometry.txt` and MinGW on `PATH`. Expect
`P2_CAVE_GEOMETRY_READY ... geometry=real`, `P2_CAVE_GEOMETRY_DRAW nodes=6 models=4
gates=2 geometry=real`, unchanged `P2_CAVE_ROOMS_TIMELINE` rows and `PASS cave rooms`.
Root tests: `py -3.12 -m pytest tests/test_pikmin2_cave_geometry.py -q` -> `12 passed`.

## Subagent usage

Three subagents started in parallel before the core work.

- `explore` **native geometry/actor source audit** — used as-is. It found the real model
  path (`gameflow.loadShape` + `updateAnim`/`drawshape`), the draw seam, the electric
  receiver plumbing, and the two blockers (no forest_1 unit meshes, no P2 gate actor) —
  a large time saving (~30–40 min) and it steered the whole slice.
- `explore` **existing-candidate inventory** — used as-is. Pinned the lane-44
  `P2_CAVE_ROOMS_1` grammar, the lane-41 node ids/fields and every consumer, so the new
  grammar extended rather than broke them (~20–30 min).
- `general` **root geometry bridge + pytest** — used after one review pass. The module
  and 12 tests were correct on first run; I corrected scope (model absence stays proxy,
  not an exception) and verified the grammar against the native parser myself (~30 min).
- Cost: three concurrent startups on a shared host. Subagent conclusions were treated as
  claims and each was re-verified (the audit's asset-missing finding drove the converter
  work; the bridge's grammar was cross-checked with the native test binary).
