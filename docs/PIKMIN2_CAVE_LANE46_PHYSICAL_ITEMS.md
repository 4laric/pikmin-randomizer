# Lane 46 — physical cave-item placement, carry and exactly-once receipt

Lane 46 / opencode DeepSeek worker session / parent spec #468, lane issue #484.

Mode: **Implementation**. This lane closes the "physical collection" ledger item:
lane 44 proved reachability over a proxy floor but placed, carried and credited
no physical treasure. This slice spawns real treasure actors at the generated
layout's item slots, lets the ordinary free-mode carry path deliver one, and
credits it exactly once through the lane-06 ordinary receipt provider.

## Slot class / routine addressed; missing model piece

- **Routine addressed:** item **spawn**, free-mode **carry** and **collection /
  receipt** for a generated cave floor.
- **Missing model piece:** the lane-41/44 graph carried item *names* on nodes but
  nothing turned a name into a real actor, and no path credited an arbitrary
  (non-enemy) treasure through the lane-06 receipt provider. `pc_p2_preview.cpp`
  only knew one global `pr05` "bolt" and the Pod economy; `pc_p2_cave_rooms.cpp`
  only gated and drew. This lane adds the one missing consumer: an
  engine-free placement parser/validator plus engine glue that spawns one real
  `Pellet` per item at its host unit, draws it with the converted treasure model,
  and grants it exactly once under a stable `(seed, reward, slot, encounter)` key.
- **Boundary respected:** the lane-41 generator, lane-39 AP logic and lane-44
  room geometry were not changed; items are placed *at* the layout slots. The
  reward seam is lane 06's `pc_p2_receipt_host_grant` (coordinate with 06); shared
  hooks are two labelled one-line calls in `pc_p2_cave.cpp` / `pc_p2_preview.cpp`
  for lane 01 to reconcile.

## Bases, heads, dirty state, ordered commits

- Root base `87dd05fb0cd7479e0f3545b1b2942f829b6ef105` -> head
  `bd74845caff14439960f9e9049e0839614597406`, clean (branch `deepseek/p2-l46`).
  - `6b4454fd lane46: physical cave-item placement bridge and focused tests (#484)`
  - `bd74845c lane46: physical collection handoff (#484)`
- Native base `2d64d65dee0041f9b0e3be73cd34d8c40f663cfe` (branch
  `deepseek/p2-l46-native`).
  - `527c6db9 lane46: physical cave-item placement, carry and exactly-once receipt (#484)`
  - `3da1d419 lane46: spawn cave items from the treasure model id, not mPelletId (#484)`
  - `fd8d0d64 lane46: count durable duplicate deliveries so restart runs terminate (#484)`
- Dirty state at handoff: none tracked on either branch; all generated evidence
  stays under `output/dsw/l46-out/` (ignored, not committed).

## Owned files; generator hooks; provider/consumer agreements

Root (owned, new):

- `experimental/pikmin2_cave_items.py` — physical-placement bridge: consumes a
  `p2-cave-observed-layout/1` graph, validates it through lane 40's
  `validate_layout`, and emits `P2_CAVE_ITEMS_1` (one 7-token row per item:
  `slot_id item host kind hazard tagged segment_index`) plus `p2-cave-items.json`
  and `p2-cave-items-report.json`. Fail-closed rules: a tagged `treasure_*` token
  must sit in a leaf whose hazard matches its tag; an untagged item must sit on a
  segment in the entrance segment; unknown tagged tokens and choke/gate/bud hosts
  are rejected.
- `tests/test_pikmin2_cave_lane46_items.py` — 19 focused tests (id/preservation,
  matching-leaf and entrance enforcement, every rejection class, lossless text
  round-trip, malformed input, `main()` end-to-end, projection determinism).
- this document.

Native (owned, new):

- `pc_port/pc_p2_cave_items.h` — engine-free parser/validator (`P2CaveItemPlacement`,
  `p2CaveItemsParse`, `p2CaveItemsValidatePlacement`, `p2CaveItemsMarker`,
  `p2CaveItemsProjection`).
- `pc_port/pc_p2_cave_items_engine.h` / `pc_p2_cave_items.cpp` — engine glue:
  opt-in `PIKMIN_CAVE_ITEMS` (default `p2-cave-items.txt`), validates against the
  live lane-44 rooms layout, spawns one real `Pellet` per item from the room
  treasure's model id (`pr05`), positions it on the host unit's ground, draws it
  with `courses/pikmin2room/treasure.mod`, and credits it through
  `pc_p2_receipt_host_grant`.
- `tools/p2_cave_items_test.cpp` — one-consumer gate; `tools/preview_p2_cave.inc`
  — the live items loop (`caveItemsFixture`).

Native (shared, labelled hooks only):

- `pc_port/pc_p2_cave.cpp` — `pc_p2_cave_items_shutdown()` at setup start and
  `pc_p2_cave_items_setup()` next to the lane-44 rooms hook.
- `pc_port/pc_p2_preview.cpp` — `pc_p2_cave_items_draw_pellet(...)` at the top of
  `pc_p2_preview_draw` and `pc_p2_cave_items_deliver(...)` at the top of
  `pc_p2_preview_deliver`. Both are one-line, labelled, and fall through for any
  pellet that is not a cave item.
- `CMakeLists.txt` — `pc_port/pc_p2_cave_items.cpp` in `PC_PORT_SOURCES`;
  `p2_cave_items_test` target.

Provider/consumer agreements used as-is:

- lane 41 `p2-cave-observed-layout/1` node ids and `items` arrays (bridge input);
- lane 40 `pikmin2_cave_spike.validate_layout` (layout validator, not re-implemented);
- lane 44 `pc_p2_cave_rooms_layout()` / `P2CaveRoomLayout` / `p2CaveRoomsWorldX/Z`
  (host units and their proxy world coordinates) — the items config is validated
  against the live rooms layout and refused on any cave/floor/seed/host drift;
- lane 06 `pc_p2_receipt_host_open` / `pc_p2_receipt_host_grant` /
  `pc_p2_receipt_host_ready` (`P2ReceiptHostResult::{Granted,Duplicate,Error}`),
  the ordinary durable exactly-once ledger. Reward identity is
  `treasure:<cave>:f<floor>:<slot_id>`, slot `host`, encounter `cave_treasure`,
  seed `<seed>`. This is the pre-handle revision of the lane-06 provider that is
  present on the cave-wave native branch; the handle-per-path revision lives on
  the lane-06 branch and must be reconciled at integration.

## What is already integrated; what is actually new

- Already integrated: lane 41 generator + `source: engine` layout; lane 44 proxy
  rooms/gating/draw; lane 40 checker; lane 06 `pc_p2_receipt_host.*` and
  `pc_p2_receipt.h`; the ordered `pr05` treasure `Pellet` the room preview already
  spawns.
- Actually new: the item-placement bridge and its grammar; the engine-free
  placement validator and one-consumer gate; real per-slot item actor spawning
  with a private carry config; the labelled converter-model draw hook; the
  lane-46 delivery interception into the lane-06 ledger; and the live items loop.

## Build evidence

From `output/dsw/l46-build-evidence.txt` (committed native heads, `dirty=no`):

```text
2026-09-15T16:01:41 lane=l46 target=p2_cave_items_test native=fd8d0d642bfac047f85df80bc7b20674cf6ab6bf dirty=no
  exe=...\native-l46-build\p2_cave_items_test.exe
  sha256=2ca6db8859cf3987d42a468059709a3ad96a8aa533fa2ba4318a844295ae1954 ninja_n="ninja: no work to do."
2026-09-15T15:50:12 lane=l46 target=pikmin_pc native=fd8d0d642bfac047f85df80bc7b20674cf6ab6bf dirty=no
  exe=...\native-l46-build\bin\nectar.exe
  sha256=1b00008e485c8f61296f3393eb99fce4110b71a75c61683a6152aa86af2ef458 ninja_n="ninja: no work to do."
```

One-consumer gate output:

```text
P2_CAVE_ITEMS_READY items=3 tagged=2 untagged=1 geometry=proxy cave=forest_1 floor=1 seed=468001
P2_CAVE_ITEMS_PROJECTION cave=forest_1 floor=1 seed=468001 [item:forest_1:f1:segment:0:0|juji_key_fc|forest_1:f1:segment:0|untagged] [item:leaf_elec_0:0|treasure_elec|leaf_elec_0|tagged] [item:leaf_water_0:0|treasure_water|leaf_water_0|tagged]
PASS p2 cave items: parse, placement, rejections, projection
```

Live room fixture (`scripts/build_pikmin2_fixture.py`, native head
`fd8d0d64`): `output/dsw/l46-out/fixture-3/fixture.exe`, SHA-256
`895842a852cfadc415315a53ab9fd5499242157ca72e4a6bc4bd49db4e851fc6`.

## Fixture/seed used; observed generation evidence

- Floor: `forest_1` floor 1, frozen seed `468001`. Layout
  `output/dsw/l41-out/p2-cave-observed-layout.json` (lane 41, `source: engine`).
- Items bridge output: `output/dsw/l46-out/items/p2-cave-items.txt` (+`.json`,
  `-report.json`): 3 items — untagged `juji_key_fc` in the entrance segment,
  tagged `treasure_elec` in `leaf_elec_0`, tagged `treasure_water` in
  `leaf_water_0`.
- Proxy rooms configs consumed: `output/dsw/l44-out/rooms-salt0/p2-cave-rooms.txt`
  and `output/dsw/l44-out/rooms-salt7/p2-cave-rooms.txt`.
- Live run directories (960×540 centred window, GL-slot-wrapped, `PIKMINUTF8`):
  - salt0 first run: `output/dsw/l46-out/items-preview-3/3a9be5f4217a45d1b86613a480f8389f/items-run.log`
    (+ `p2-cave-items.ppm`, `p2-cave-items-progress.ppm`, `p2-cave-item-receipts.txt`).
  - salt0 process restart: `.../items-run-restart.log` (same ledger file).
  - salt7 re-roll: `output/dsw/l46-out/items-preview-4/6b8c8209b1154515a74c08639b8b54be/items-run-salt7.log`.

Observed live markers (salt0 first run, natural free-mode carry):

```text
P2_CAVE_ITEM_ACTOR slot=item:forest_1:f1:segment:0:0 item=juji_key_fc host=forest_1:f1:segment:0 kind=segment tagged=0 x=0.000 y=-0.000 z=0.000
P2_CAVE_ITEM_ACTOR slot=item:leaf_elec_0:0 item=treasure_elec host=leaf_elec_0 kind=leaf tagged=1 x=72.000 y=-0.000 z=48.000
P2_CAVE_ITEM_ACTOR slot=item:leaf_water_0:0 item=treasure_water host=leaf_water_0 kind=leaf tagged=1 x=24.000 y=-0.000 z=144.000
P2_CAVE_ITEMS_READY items=3 tagged=2 untagged=1 geometry=proxy cave=forest_1 floor=1 seed=468001
P2_CAVE_ITEM_FREE_RELEASE target=treasure_elec count=20
P2_CAVE_ITEM_NATURAL_CARRY transport=10
P2_CAVE_ITEM_RECEIPT id=treasure:forest_1:f1:item:leaf_elec_0:0 item=treasure_elec host=leaf_elec_0 tagged=1 new=1 tag=cave_treasure seed=468001 result=1
P2_CAVE_ITEM_REDELIVER duplicate_call=1 events=5 new=3
PASS cave items: physical placement, real carry, exactly-once receipt (proxy geometry/model)
```

Durable ledger after the salt0 first run + restart (`p2-cave-item-receipts.txt`):

```text
P2_RECEIPTS_1
468001 treasure:forest_1:f1:item:forest_1:f1:segment:0:0 forest_1:f1:segment:0 cave_treasure
468001 treasure:forest_1:f1:item:leaf_elec_0:0 leaf_elec_0 cave_treasure
468001 treasure:forest_1:f1:item:leaf_water_0:0 leaf_water_0 cave_treasure
```

## Acceptance contract 1–6 results (natural vs injected)

| # | Contract item | Result | Evidence class |
|---|---|---|---|
| 1 | Generation invariant | **PASS (inherited, natural)** — the lane-40 checker's `generation_pass=true` on the lane-41 engine layout is unchanged; lane 46 additionally validates every item host against the live rooms layout (kind/hazard/segment) and refuses drift. | natural (lane 40/41/44), placement validation natural |
| 2 | Seed determinism | **PASS** — same seed+layout → identical `P2_CAVE_ITEMS_PROJECTION`; the projection is position-free. | natural/model |
| 3 | Re-roll invariance | **PASS** — the salt7 run re-rolled the geometry (coords `96,51` / `48,153` vs `72,48` / `24,144`) yet the item→host mapping and every reward identity were identical; all deliveries were durable duplicates (`new=0`). | natural placement, proxy geometry |
| 4 | Reachability | not re-derived here — lane 44 owns proxy reachability; items are only placed at their assigned hosts and do not add gates. | lane 44 |
| 5 | End-to-end loop | **PASS for the collection half, natural carry** — 3 real pellets spawned at their slots; free-mode Pikmin acquired a tagged treasure naturally (`transport=10`, no injected Transport assignment) and the ordinary carry delivered it; all three were credited exactly once. Ability acquisition/hazard gating remains lane 44's staged slice. | natural spawn/carry/receipt; geometry+model proxy |
| 6 | Failure handling | **PASS for placement** — a config whose host/kind/hazard/segment or cave/floor/seed disagrees with the rooms layout is refused at setup (`P2_CAVE_ITEMS FAILED reason=...`); the bridge rejects unknown tagged tokens and wrong hosts. Generator retry remains lane 41. | natural |

Honest labels: the **geometry is proxy** (lane 44) and the **treasure model is
proxy** — every item name is drawn with the single converted `treasure.mod`
(`PikminItem` names are logical ids, not distinct assets; per-treasure assets are
lane 09). The live stage is the private room-preview overlay (P1 assets +
converted room105, a scripted 20-red squad and Onion), not a real P2 campaign
cave. The carry endpoint here is the Onion `GoalItem` (`itemMgr->getContainer(Red)`)
because the fixture configures no Research Pod; the credited ledger is lane 06's
ordinary receipt provider. Nothing here is a generation PASS.

## Re-roll / restart / cross-seed

- **Re-roll:** salt0 vs salt7 give different proxy geometry while the item→host
  mapping and all reward identities are byte-identical; the second geometry's
  deliveries were durable duplicates (`new=0`), i.e. the table held while the room
  rerolled.
- **Restart:** a second process over the same ledger re-spawned the items,
  carried them naturally (`transport=8`) and received `new=0 result=0` for every
  item — exactly-once credit across a process restart, with exactly three rows in
  `p2-cave-item-receipts.txt`.
- **Cross-seed:** not re-run live; the bridge is a pure function of the layout, so
  a different seed only changes the layout's item set/hosts. Named remaining
  dependency: a seed-468002 live run.

## Known limitations; next consumer

- **Proxy geometry and proxy model.** No P2 `MapUnitInterface` room and no
  per-treasure assets; all items share the converted `treasure.mod`. The physical
  actor, carry route, endpoint, and receipt are real engine paths.
- **Preview stage.** The live evidence is the private room-preview overlay, not a
  natural cave entry from the field.
- **Lane-06 provider revision.** This branch carries the pre-handle
  `pc_p2_receipt_host_open(path)` singleton; the handle-per-path revision is on the
  lane-06 branch. Integration (lane 01) must reconcile the two so the cave items
  and the enemy/corpse path do not share one global ledger.
- **Endpoint.** With no Research Pod the carry endpoint is the Onion; a Pod
  fixture would exercise `pc_p2_preview_deliver`'s Pod branch instead.
- **Next consumers:** lane 01 (integrate the hooks and reconcile the receipt
  provider), lane 09 (real per-treasure models), lane 36 (real leaf alcove units),
  lane 40 QA (re-run its checker and the end-to-end loop against a generated
  cave), lane 39 (the seeded table already names the tagged treasures).

## Subagent usage

Three subagents started in parallel before the core work.

- `explore` **native treasure spawn/carry/receipt audit** — used as-is. It
  produced the decisive correction that the lane-06 native delivery host is *not*
  on the cave-wave branch and that the only native treasure actor is a `pr05`
  `Pellet`; it also pinned `Piki::graspSituation`, `PelletGoalState::exec` and the
  `pc_p2_preview_draw/deliver` seams. Saved ~60–90 min of reading.
- `explore` **existing-candidate inventory** — used as-is. Confirmed no cave-item
  or treasure-placement module exists, enumerated the lane-44/06 artifacts to
  reuse, and supplied the exact live-run overlay/env recipe. Saved ~30–45 min.
- `general` **root bridge + pytest** — used after review. The module and 19 tests
  were correct on first run; I reviewed the grammar and added the `entrance_segment`
  handling check. Saved ~40–60 min of drafting.
- Cost: three concurrent startups on a shared host. One later defect I fixed
  myself was a native mistake (`newPellet` keys on the model id, not `mPelletId`)
  that only the live run exposed.

## ONE exact reproduction command

From `C:/Users/alari/pikmin-randomizer/output/dsw/l46-root`, after the one-time
bridge + fixture build (fixture already at `output/dsw/l46-out/fixture-3`):

```powershell
# bridge the lane-41 layout to the native items grammar
py -3.12 -m experimental.pikmin2_cave_items --layout C:/Users/alari/pikmin-randomizer/output/dsw/l41-out/p2-cave-observed-layout.json --out-dir C:/Users/alari/pikmin-randomizer/output/dsw/l46-out/items
# build the native gate + exe (already recorded in the evidence file)
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l46 --target p2_cave_items_test
# live run (960x540, GL-slot-wrapped): see the run_fixture.py recipe in the handoff
```

Expect `P2_CAVE_ITEMS_READY items=3 tagged=2 untagged=1 geometry=proxy ...` and
`PASS cave items: physical placement, real carry, exactly-once receipt`. Unit
tests: `py -3.12 -m pytest tests/test_pikmin2_cave_lane46_items.py -q` → `19 passed`.
