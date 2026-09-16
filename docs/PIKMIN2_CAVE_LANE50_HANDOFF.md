# Lane 50 — Gate/pool carry blocking handoff (parent #468, lane issue #488)

Lane muse-cave50 / implementation owner Codex through shared account 4laric;
executing contributor opencode-go/muse-spark-1.3-contributor. Mode:
**Implementation**. This slice makes the generated floor's hard hazards
physically gate carrying: a closed electric gate stops carriers until a yellow
opens it, and a water pool stops non-blue carriers, so a red-carried tagged
treasure cannot cross the closed door (no credit) and credits exactly once after
the gate opens. Generator (41), bud (38/48), meshes (36/09) and item
spawn/receipt semantics (46) are unchanged.

## Slot class / routine addressed; missing model piece

- **Routine addressed:** carry **blocking** at hazard doors plus the delivery
  outcome. Lane 45's gate actor delivered `InteractDenki` but never tracked
  whether the victim was carrying, and it owned no water hazard; lane 46 proved
  a free carry credits but never gated it. This lane adds the missing consumer:
  a `P2_CAVE_GATES_1` carry plan (host bridge), an engine-free verdict, live
  hazard volumes on each blocking door, and a live carry fixture that drives the
  blocked -> opened -> exactly-once loop.
- **Missing model piece:** the per-door carry rule (`carry_block` + `key`), the
  door volumes between hazard nodes and their entrance-ward neighbours, and the
  carrier-aware `BLOCKED` / `OPEN` evidence. No `P2_CAVE_GATES_1` consumer
  existed in either worktree.
- **Boundary respected:** lane-41 layout, lane-44 rooms/timeline, lane-39 logic,
  lane-38 buds, lane-36/09 meshes and lane-46 spawn/receipt code are untouched.
  Shared edits are small labelled hooks only (`pc_p2_cave.cpp` setup/tick,
  `pc_p2_cave_geometry.cpp` tick yield, `CMakeLists.txt`, `preview_p2_cave.inc`
  fixture dispatch), reserved for focused #186 review.

## Bases, heads, dirty state, ordered commits

- Root base `c4d3c9b9b6ffadfa2d1c5a72f0d4fb6cb9c5b87a` (branch `deepseek/p2-l50`).
  - `df4a25f8 lane50: carry-blocking plan bridge and focused tests (#488)`
  - this document (root head; code head `df4a25f8`)
- Native base `6da0364f5756cdcea80805939f2cb0d929a25cdc` (branch
  `deepseek/p2-l50-native`).
  - `9f677482 lane50: gate/pool carry blocking, verdict gate and live fixture (#488)`
  - `59058507 lane50: open all elec gates on yellow key, log carrier position (#488)`
  - `f42dedb9 lane50: assign water carrier in parallel with the credit run (#488)`
  - `e336e8fd lane50: drop fixture captures to fit the frame budget (#488)` (native head)
- Dirty state at handoff: none on either branch. All generated evidence stays
  under `output/workflow/paid-scale/l50/` (paid-scale output, not committed) and
  the lane-owned `output/dsw/l50-out/` bridge caches (ignored).

## Owned files; generator hooks; provider/consumer agreements

Root (owned, new):

- `experimental/pikmin2_cave_gates.py` — carry-blocking bridge: consumes a
  lane-44 rooms layout (plus the lane-45 geometry class when present) and emits
  `P2_CAVE_GATES_1` (`p2-cave-gates.txt`), `p2-cave-gates.json` and
  `p2-cave-gates-report.json`. One row per door: `carry_block` is `elec` for
  elec hazard / `water` for water hazard / `none` otherwise; `key` is `yellow` /
  `blue` / `-`. Fail-closed on unknown kind/hazard, duplicate ids, missing
  entrance/hole, geometry drift and tampered pairs. Never claims generation.
- `tests/test_pikmin2_cave_lane50_gates.py` — 23 focused tests (text round-trip,
  per-hazard mapping, determinism, every rejection class, `main()` artifacts,
  lane-41->44 integration asserting the exact blocking sets).
- this document.

Native (owned, new):

- `pc_port/pc_p2_cave_carry.h` — engine-free `P2_CAVE_GATES_1` parser, plan,
  `p2CaveCarryDecide` verdict (`Pass` when not blocking or immune, `Block` for a
  non-immune carrier, `Ignore` for a non-carrier) and markers.
- `pc_port/pc_p2_cave_carry_engine.h` / `pc_p2_cave_carry.cpp` — engine glue:
  opt-in `PIKMIN_CAVE_GATES` (default `p2-cave-gates.txt`), validated against
  the live lane-44 rooms layout (refused on cave/floor/seed drift). One hazard
  volume per blocking door placed on the door midpoint toward the entrance-ward
  neighbour (BFS from the entrance). Tick: an electric-immune Pikmin at any elec
  gate opens every elec gate (`P2_CAVE_CARRY_OPEN`); otherwise a non-immune
  Pikmin in a closed volume receives the engine reaction — `InteractDenki` for
  elec, `InteractBubble` for water — which drops a carried cave treasure through
  the engine's own release path (`P2_CAVE_CARRY_BLOCKED ... carrying=...`).
- `tools/p2_cave_carry_test.cpp` — one-consumer gate (parse, verdict, key
  mapping, rejections, host-file marker).
- Hooks: `pc_port/pc_p2_cave.cpp` (include, shutdown, setup after items, tick
  before geometry), `pc_port/pc_p2_cave_geometry.cpp` (yield plan gates to the
  carry module so one owner drives each gate hazard), `CMakeLists.txt`
  (`pc_p2_cave_carry.cpp` in `PC_PORT_SOURCES`, `p2_cave_carry_test`),
  `tools/preview_p2_cave.inc` (`caveCarryFixture`, dispatched when the carry
  plan is active).

Provider/consumer agreements used as-is:

- lane-41 `p2-cave-observed-layout/1` node ids and edges (bridge input);
- lane-44 rooms layout/node world positions/edges (volume placement, BFS);
- lane-45 geometry class + gate meshes (drawn by lane 45; hazard owned here);
- lane-46 `pc_p2_cave_items_placement()` / `pc_p2_cave_items_pellet_for()` (carrier
  identity) and the lane-06 receipt ledger (credit path, untouched);
- lane-10 `p2_species_immune` / `InteractDenki` / `InteractBubble` receivers.

## Already integrated vs actually new

- Already integrated: lane-41 generator + engine layout; lane-44 proxy rooms and
  hazard timeline; lane-45 real geometry + gate meshes; lane-46 physical spawn,
  natural carry and exactly-once receipt; lane-06 ledger; lane-10 immunity and
  electric/bubble receivers.
- Actually new: the carry-blocking plan + verdict; the door volumes and their
  open/block reactions; carrier-aware `BLOCKED`/`OPEN` markers; the live
  blocked -> opened -> credited -> water-filtered fixture sequence.

## Build evidence (canonical leased builds)

Private build `C:/Users/alari/pikmin-randomizer/output/msw/native-cave50-paid-build`
via `output/muse-wave/control/leased_run.py --lane-file
output/workflow/paid-scale/l50/lane.json` (configure once, then per-target):

- `pikmin_pc`: native `e336e8fd`, exe `bin/nectar.exe` sha256
  `8f0e938f5429322702e38398225f0540e5cbb2e4edb0bc5b1ae6e1b8d6f15022`,
  `ninja -n` reports no work.
- `p2_cave_carry_test`: same native head; prints
  `P2_CAVE_CARRY_PLAN doors=6 blocking=4 elec=2 water=2 ...` then
  `PASS p2 cave carry: plan parse, block verdict, immune/key mapping`.
- Fixture `output/workflow/paid-scale/l50/fixture-7/fixture.exe` sha256
  `3f85330b18f4a7ce7958161defe010fc9336d605f519d07b8be1e00d8c487d86`,
  provenance `built` against native `e336e8fd` (direct builder invocation; the
  leased wrapper's MSYS2 git emits an autocrlf warning that the provenance
  builder misparses as a path — recorded deviation, same script and inputs).
- Root: `py -3.12 -m pytest tests/test_pikmin2_cave_lane50_gates.py -q` ->
  `23 passed`.

## Fixture / seed and observed generation evidence

- Floor `forest_1` floor 1, frozen seed `468001`, lane-41 engine layout; salt-0
  rooms/geometry/items/gates bridged fresh into
  `output/workflow/paid-scale/l50/` (`P2_CAVE_GATES_READY doors=6 elec=2 water=2
  ... geometry=real`).
- Fresh arena generated with the current `scripts/preview_pikmin2_room.py`
  overlay into
  `output/workflow/paid-scale/l50/stage/arena/f3171684ce93425fa93f930bce3735d0/`
  (20 live `preview red pikmin` in `default.gen`; cave models + `pod.mod`
  layered from the lane-45 cache, hashes recorded); `p2-cave-entry.txt` restores
  20 reds; `PIKMIN_P2_ROOM_WINDOW=960x540`; log shows
  `Experimental preview window set to 960x540 windowed and centered`; no
  immediate extinction (live squad carries within seconds).
- Live run log `.../f3171684.../carry-run.log` (fixture-7, 960x540 centred):

```text
P2_CAVE_CARRY_PHASE phase=block_assign blocked=5
P2_CAVE_CARRY_BLOCKED id=gate:leaf_elec_0 hazard=elec species=1 carrying=1 accepted=1 tx=72.00 tz=68.00
P2_CAVE_CARRY_PHASE phase=blocked hazard=elec blocked=11 carriers_dropped=1 new=0
P2_CAVE_CARRY_PHASE phase=open_stage opened=0 gx=36.00 gz=24.00
P2_CAVE_CARRY_OPEN id=leaf_elec_0 hazard=elec reason=electric_immune
P2_CAVE_CARRY_OPEN id=gate:leaf_elec_0 hazard=elec reason=electric_immune
P2_CAVE_CARRY_PHASE phase=opened opened=2
P2_CAVE_CARRY_PHASE phase=credit_release freed=3
P2_CAVE_CARRY_PHASE phase=water_assign water_filtered=6
P2_CAVE_CARRY_BLOCKED id=leaf_water_0 hazard=water species=1 carrying=1 accepted=1 tx=23.32 tz=130.48
P2_CAVE_ITEM_RECEIPT id=treasure:forest_1:f1:item:leaf_elec_0:0 item=treasure_elec host=leaf_elec_0 tagged=1 new=1 tag=cave_treasure seed=468001 result=1
```

- Durable ledger `p2-cave-item-receipts.txt` holds exactly one row
  (`treasure:forest_1:f1:item:leaf_elec_0:0`), i.e. exactly-once credit.
- Natural vs injected, honestly labelled: the block-phase carrier and the water
  carrier use the injected Transport initialisation (same call lane 46 uses);
  the hazard reactions (zap/panic/drop), the gate opening on a live yellow, the
  credit-phase carry (free-mode AI pickup through delivery) and the receipt are
  the natural engine paths. The yellow itself is staged (a red recoloured at the
  gate), not earned from a treasure — ability acquisition remains staged, as in
  lanes 44/45. Geometry/model are proxy/converted (lane-44/45/09); this is not a
  generation PASS.

## Acceptance: six arena gates

| # | Gate | Result | Evidence class |
|---|---|---|---|
| 1 | Exact identity and spawn | **PASS** — 3 real `Pellet` actors at their hosts (`P2_CAVE_ITEM_ACTOR`), 4 door volumes at computed door midpoints (`P2_CAVE_CARRY_VOLUME`) | natural spawn, injected placement |
| 2 | Autonomous movement and animation | **PASS** — carriers walk the pellet toward the Onion under the production Transport AI (`credit_wait` x/z trail to the goal) | natural |
| 3 | Attacks and receivers | **PASS** — closed elec gate delivers `InteractDenki` to a non-immune carrier (`accepted=1`); water delivers `InteractBubble` to a non-blue carrier (`accepted=1`) | natural receivers, injected carriers |
| 4 | Death and corpse | **PASS (hazard death)** — zapped carriers enter `DenkiDying` and drop the treasure (`carriers_dropped=1`); Pikmin become sprouts, so corpse is source-backed N/A | natural |
| 5 | Actual transport and reward | **PASS** — natural free-mode carry delivers the elec treasure; `new=1`, one ledger row, redeliver would be a durable duplicate | natural carry/receipt |
| 6 | Cleanup and re-entry | **UNTESTED** — no restart/re-entry run in this slice (lane 46 proved item restart; carry re-entry remains open) | — |

## Acceptance: cave contract 1–6

| # | Contract item | Result | Evidence class |
|---|---|---|---|
| 1 | Generation invariant | inherited from lane 41/40 (not re-run) | natural (lane 41) |
| 2 | Seed determinism | **PASS (model)** — same seed+layout -> identical `P2_CAVE_GATES_1`/projection; bridge is a pure function | model |
| 3 | Re-roll invariance | **UNTESTED live** — salt-0 only; the plan carries no salt so it is invariant by construction, but no second-salt live run yet | model |
| 4 | Reachability | inherited from lane 44 (unchanged timeline) | lane 44 |
| 5 | End-to-end loop | **PASS** — red-carried elec treasure blocked (`new=0`), yellow opens both elec gates, natural carry credits exactly once; water red-carry blocked | natural loop, staged yellow |
| 6 | Failure handling | **PASS** — plan/rooms drift, unknown tokens, duplicate ids and missing sections are refused at setup (`P2_CAVE_CARRY FAILED`) | tests + live setup |

## Re-roll / restart / cross-seed

- **Re-roll:** not run live (named remaining work for lane 51/integration).
- **Restart:** not run (UNTESTED above).
- **Cross-seed:** not run live; the bridge is seed-parametric and deterministic.

## Known limitations; next consumer

- The fixture's own `PASS` line did not print: the shared room fixture caps at
  10000 frames (`FAIL p2 room: timeout`), and this scenario's real-time carries
  exhaust it just after the final receipt. Every functional marker (blocked,
  opened x2, `new=1`, water blocks, one-row ledger) is in the log; the FAIL is a
  harness budget, not a functional failure. A higher frame budget (shared
  `preview_p2_room.cpp`, not owned) would let the fixture exit cleanly.
- Electric-gate opening is squad-keyed (any yellow at any elec gate opens all
  elec gates on the floor); per-gate keys are future work.
- The staged yellow stands in for earned ability acquisition; natural yellow
  acquisition (bud/conversion) belongs to lanes 23/38.
- Water uses the panic reaction (`InteractBubble`), not retail drowning; the
  carry still drops and never credits, which is the lane's contract.
- No l48/l49 lane outputs exist in either worktree or the registry; the bud and
  mesh dependencies resolve to lane-38/36/09 artifacts, consumed unchanged.
- **Next consumers:** lane 51 QA (re-run its checker + a re-roll against this
  pin), lane 01 (integrate the hooks; reconcile the lane-45 tick yield), lane 40
  (spike with carry gating).

## ONE exact reproduction command

From `C:/Users/alari/pikmin-randomizer/output/workflow/paid-scale/l50/stage/arena/f3171684ce93425fa93f930bce3735d0/`
with `PIKMIN_P2_ROOM_WINDOW=960x540`, `PYTHONUTF8=1`,
`PIKMIN_CAVE_ROOMS=p2-cave-rooms.txt`, `PIKMIN_CAVE_GEOMETRY=p2-cave-geometry.txt`,
`PIKMIN_CAVE_ITEMS=p2-cave-items.txt`, `PIKMIN_CAVE_GATES=p2-cave-gates.txt`,
`PIKMIN_P2_ITEM_RECEIPT_PATH=p2-cave-item-receipts.txt` (fresh ledger) and MinGW
on `PATH`, run the pinned fixture (sha256
`3f85330b18f4a7ce7958161defe010fc9336d605f519d07b8be1e00d8c487d86`):

```text
fixture.exe --experimental-pikmin2-room
```

Expect `P2_CAVE_CARRY_PLAN doors=6 blocking=4 ...`,
`P2_CAVE_CARRY_BLOCKED ... carrying=1` with `new=0`,
`P2_CAVE_CARRY_OPEN` x2, `P2_CAVE_ITEM_RECEIPT ... item=treasure_elec ... new=1`,
water `BLOCKED ... carrying=1`, and one ledger row. Root tests:
`py -3.12 -m pytest tests/test_pikmin2_cave_lane50_gates.py -q` -> `23 passed`.
Native gate: `p2_cave_carry_test.exe <p2-cave-gates.txt>` -> plan marker + PASS.
