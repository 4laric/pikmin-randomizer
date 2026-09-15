# Lane 44 — playable cave floor + live loop (parent #468, lane issue #482)

Lane 44 / opencode worker session / parent spec #468, lane issue #482.
Mode: **Acceptance**. This lane owns the last two cave-wave acceptance items:
instantiate a lane-41 layout as enterable floor geometry through the port room
path and observe the come-back-with-yellow loop.

## Slot class / routine addressed; missing model piece

- **Routine addressed:** room/unit **instantiation** and the **live loop**. The
  lane-41 generator emits a logical `p2-cave-observed-layout/1` graph; nothing
  turned that graph into anything the running port could draw, enter or gate on.
  The port has no P2 `MapUnitInterface`/`RandMapUnit` room loader, so this slice
  adds the one missing consumer: a deterministic **proxy** room/unit grid with
  hazard-key gating, plus the engine draw/tick hook and a live fixture loop.
- **Missing model piece:** a playable projection of the seeded table. Inventory
  found no `p2-cave-rooms` / `cave_rooms` / proxy-geometry module anywhere in
  either worktree.
- **Boundary respected:** the lane-41 generator algorithm was not changed; no AP
  logic (39), QA harness (40), alcove assets (36/09) or generator (41) was
  touched. The host overlay reuses the existing `preview_pikmin2_room.py` room
  path; no second import pipeline was built.

## Bases, heads, dirty state, ordered commits

- Root base `2f50d39530b1917dafd9d0d2994b818717d14936` (branch `deepseek/p2-l44`).
  - `7abc79a2 lane44: proxy room/unit instantiation bridge + tests (#482)`
  - `fa86969f lane44: live proxy rooms evidence tests and handoff (#482)`
- Native base `346378a07861143162a623d00ccdb603d1b45200` (branch
  `deepseek/p2-l44-native`).
  - `94cf7c48 lane44: proxy cave-room module, one-consumer test and draw hook (#482)`
  - `ebc45ab0 lane44: keep granted keys in the live rooms timeline and log the projection (#482)`
- Dirty state at handoff: none tracked on either branch; generated evidence
  stays under `output/dsw/l44-out/` (ignored, not committed).

## Owned files; generator hooks; provider/consumer agreements

Root (owned):

- `experimental/pikmin2_cave_rooms.py` — instantiation bridge: consumes a
  `p2-cave-observed-layout/1` graph, validates it through lane-40's
  `validate_layout`, lays each node on a deterministic BFS-layer proxy grid
  (layer row spacing `cell + salt%4`, per-salt stagger) and emits
  `p2-cave-rooms.json` / `p2-cave-rooms-report.json` / the native
  `P2_CAVE_ROOMS_1` text (`p2-cave-rooms.txt`). Node ids, kinds, hazards,
  `segment_index`, items and every edge are preserved verbatim.
- `tests/test_pikmin2_cave_rooms.py` — 15 focused tests (id/edge preservation,
  proxy label, salt-stable logic + rerolled geometry, strict text round-trip,
  fail-closed, lane-41 layout integration, and the live-timeline evidence tests).
- this document.

Native (owned):

- `pc_port/pc_p2_cave_rooms.h` — engine-free parser + gating/reachability logic
  (`P2CaveRoomLayout`, `P2CaveAbilities`, `p2CaveRoomsParse`,
  `p2CaveRoomsReachable` with a bounded bud-key fixpoint,
  `p2CaveRoomsLogicalProjection`, `p2CaveRoomsMarker`).
- `pc_port/pc_p2_cave_rooms_engine.h` / `.cpp` — engine glue: opt-in
  `PIKMIN_CAVE_ROOMS` (default `p2-cave-rooms.txt`), live squad keys from the
  real `pikiMgr`, nearest-unit lookup and the proxy floor drawer.
- `tools/p2_cave_rooms_test.cpp` — one-consumer gate.
- `tools/preview_p2_cave.inc` — the live rooms loop (`caveRoomsFixture`), run
  when `pc_p2_cave_rooms_active()`.
- `CMakeLists.txt` — `pc_port/pc_p2_cave_rooms.cpp` in `PC_PORT_SOURCES`;
  `p2_cave_rooms_test` target.

Hook in the shared file `pc_port/pc_p2_cave.cpp` (labelled, opt-in): include
`pc_p2_cave_rooms_engine.h`, `pc_p2_cave_rooms_shutdown()` at setup start,
`pc_p2_cave_rooms_setup()` next to the lane-41 generator hook, and one
`pc_p2_cave_rooms_draw(gfx)` call at the top of `pc_p2_cave_draw_transition`.

Provider/consumer agreements used as-is:

- lane 41 `p2-cave-observed-layout/1` (node ids `choke_water_0`, `leaf_elec_0`,
  `leaf_water_0`, `gate:leaf_elec_0`, segment `forest_1:f1:segment:N`) is the
  bridge input; the bridge never rewrites node ids.
- lane 40 `pikmin2_cave_spike.validate_layout` is the layout validator; the
  checker and its scenario schema are consumed, not re-implemented.
- The port room path (`--experimental-pikmin2-room`, `pc_pikipelago_room_preview`,
  `tools/preview_p2_room.cpp`, `scripts/preview_pikmin2_room.py`,
  `p2-cave-entry.txt`) is reused unchanged.

## Already integrated vs actually new

- Already integrated: lane-41 generator and the `source: engine` layout; lane-40
  checker; the room-preview entry path; cave entry/restore/anchor/draw.
- Actually new: the proxy room/unit instantiation bridge and native module, the
  live squad-key gating, the engine draw hook, the live rooms loop, and the
  one-consumer + live-evidence tests.

## Build evidence

`output/dsw/l44-build-evidence.txt` (native head, exe SHA-256, `ninja -n`):

```
2026-09-15T15:01:59 lane=l44 target=pikmin_pc native=ebc45ab02ec88b26c0b4c8d171bbb043608d5250 dirty=no
  exe=...\native-l44-build\bin\nectar.exe
  sha256=137dc718dfbc51e390adc745f72be5ce68b31d8c69c181b3a08242fa83a68523 ninja_n="ninja: no work to do."
```

One-consumer test: `p2_cave_rooms_test.exe` (SHA-256
`de8dfb52b15e79e507de81b340c9f939cf818d88940be11b5bd5be2895395a1c`), prints
`PASS p2 cave rooms: proxy bridge, parse, hazard timeline, reroll invariance`.

Live room fixture (`scripts/build_pikmin2_fixture.py`, native head `ebc45ab0`):
`output/dsw/l44-out/fixture-2/fixture.exe`, SHA-256
`55509ec606c709f08b7f131899c0b1cbb50288332b383480ae7145204b0928a8`.

## Fixture / seed and observed generation evidence

- Floor: `forest_1` floor 1, frozen seed `468001`, lane-41 layout
  `output/dsw/l41-out/p2-cave-observed-layout.json` (water choke; elec leaf +
  elec gate; water leaf; untagged `juji_key_fc` in the entrance segment).
- Proxy configs (bridge output, geometry labelled `proxy`):
  `output/dsw/l44-out/rooms-salt0/p2-cave-rooms.txt` (salt 0) and
  `output/dsw/l44-out/rooms-salt7/p2-cave-rooms.txt` (salt 7).
- Live run (960×540 centred window, `PIKMIN_P2_ROOM_WINDOW=960x540`,
  GL slot-wrapped): `output/dsw/l44-out/rooms-live/rooms-run-salt0.log`,
  `rooms-run-salt7.log`, capture `p2-cave-rooms.ppm`.
- Lane-40 checker report (lane-41 engine layout, natural):
  `output/dsw/l44-out/rooms-checker/report.json` —
  `pass=true, generation_pass=true, evidence=natural`.

Live markers (salt 0; salt 7 is identical except `salt=7`):

```
P2_CAVE_ROOMS_READY units=6 geometry=proxy cave=forest_1 floor=1 seed=468001 salt=0 hard=4 entrance=forest_1:f1:segment:0 hole=forest_1:f1:segment:1
P2_CAVE_ROOMS_ENTER id=forest_1:f1:segment:0 unit_at=forest_1:f1:segment:0 geometry=proxy proxy=1
P2_CAVE_ROOMS_TIMELINE tag=fresh_floor_no_abilities hole=0 treasure_elec=0 treasure_water=0 untagged=1
P2_CAVE_ROOMS_TIMELINE tag=come_back_with_yellow       hole=0 treasure_elec=1 treasure_water=0 untagged=1
P2_CAVE_ROOMS_TIMELINE tag=return_with_yellow_and_blue hole=1 treasure_elec=1 treasure_water=1 untagged=1
PASS cave rooms: proxy floor, live squad keys, hazard timeline (proxy geometry)
```

## Acceptance contract 1–6 results (natural vs injected)

| # | Contract item | Result | Evidence class |
|---|---|---|---|
| 1 | Generation invariant | **PASS, natural** — lane-40 checker on the lane-41 engine layout: `generation_pass=true`, choke is a cut vertex | natural (lane 41) |
| 2 | Seed determinism | **PASS** — checker determinism 468001 vs 468002 unchanged | natural/model |
| 3 | Re-roll invariance | **PASS** — two salts give identical live logical projections and different geometry files; engine-free test and checker reroll both pass | natural table, proxy geometry |
| 4 | Reachability | **PASS (proxy)** — only hard gates are the water choke and elec leaf/gate the table requires; hole is behind the water choke | proxy |
| 5 | End-to-end "come back with yellow" loop | **PARTIAL** — the live timeline is natural module output from the real squad (fresh: elec/water/hole all gated, untagged reachable; +yellow: elec opens, water/hole stay gated; +blue: all open) and the lane-40 model loop passes; ability acquisition is staged and no physical item is collected | natural gating over proxy geometry; staged acquisition |
| 6 | Failure handling | not re-run — unchanged from lane 41 (rejection after retries) | lane 41 |

The layout/generation is natural (engine-produced). The **geometry is proxy**
and is labelled as such everywhere (`geometry=proxy`, `proxy=1`, report
`geometry: "proxy"`). No proxy artefact is claimed as a generation PASS.

## Re-roll / restart / cross-seed

- **Re-roll:** two salts (0 and 7) over the same observed layout give
  byte-identical `P2_CAVE_ROOMS_PROJECTION` lines and different
  `P2_CAVE_ROOMS_*` configs → the table holds while the proxy geometry rerolls.
- **Cross-seed:** not re-run live; lane-40 `check_determinism` (468001 vs
  468002) passes in `rooms-checker/report.json`.
- **Restart:** not evaluated (needs a real save/checkpoint pass); named
  dependency: lane 11 checkpoint invariants.

## Known limitations; next consumer

- **Geometry is proxy.** No P2 `MapUnitInterface` room is loaded; units are
  drawn as floor squares/edges/gates/markers on the existing converted room.
  "Enterable" means the captain was staged onto the entrance proxy cell and the
  live module reported that unit; it is not real terrain traversal.
- **No physical item collection.** The ability loop observes reachability
  transitions, not a carried treasure; item meshes and gate collision are not
  instantiated.
- **Ability acquisition is staged** (a Red is recoloured) and labelled
  `natural_acquire=0 staged=1`; the gating decision itself is the natural module
  output over the real squad.
- **Next consumers:** lane 01 (integrate the draw hook and the room config),
  lanes 36/37 (swap the proxy leaf/choke cells for real alcove/gate units),
  lane 40 QA (re-run its checker against the live artefacts).

## Subagent usage

Three subagents started in parallel before the core work.

- `explore` **native room/unit audit** — used as-is. Gave the exact hook sites
  (`pc_p2_cave_setup/tick/draw_transition`), config grammars, the proxy-marker
  draw pattern and the species/immunity API. Saved ~30–45 min of reading.
- `explore` **candidate inventory** — used as-is. Confirmed there was no rooms
  module to reuse and pinned the lane-41 node-id/schema fields the bridge must
  preserve. Saved ~20–30 min.
- `general` **root bridge + pytest** — used after review. The module and tests
  were correct on first run (13 passed); I reviewed the grammar, then corrected
  one thing myself: the report's lane number (#481 → #482) and added the live
  evidence tests. Saved ~30–40 min.
- Cost: three concurrent startups on a shared host. No subagent output needed
  rework beyond the review corrections above.

## ONE exact reproduction command

Build the one-consumer gate, then run it (from `output/dsw/l44-root`):

```
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l44 --target p2_cave_rooms_test
$env:PATH="C:\msys64\mingw64\bin;$env:PATH"
& C:/Users/alari/pikmin-randomizer/output/dsw/native-l44-build/p2_cave_rooms_test.exe C:/Users/alari/pikmin-randomizer/output/dsw/l44-out/rooms-salt0/p2-cave-rooms.txt
```

Expect `P2_CAVE_ROOMS_READY units=6 geometry=proxy ...` then
`PASS p2 cave rooms: ...`. Tests:
`py -3.12 -m pytest tests/test_pikmin2_cave_rooms.py -q` → `15 passed`.

### Live GL appendix (slot-wrapped, 960×540)

```
# 1) bridge both salts
py -3.12 -m experimental.pikmin2_cave_rooms --layout C:/Users/alari/pikmin-randomizer/output/dsw/l41-out/p2-cave-observed-layout.json --out-dir C:/Users/alari/pikmin-randomizer/output/dsw/l44-out/rooms-salt0 --salt 0
py -3.12 -m experimental.pikmin2_cave_rooms --layout C:/Users/alari/pikmin-randomizer/output/dsw/l41-out/p2-cave-observed-layout.json --out-dir C:/Users/alari/pikmin-randomizer/output/dsw/l44-out/rooms-salt7 --salt 7
# 2) build pikmin_pc + the room fixture, stage the room, drop in the configs, then
#    run the fixture under the GL slot with PIKMIN_P2_ROOM_WINDOW=960x540 and
#    PIKMIN_CAVE_ROOMS=p2-cave-rooms.txt (or p2-cave-rooms-salt7.txt).
```
