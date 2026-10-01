# Lane 47 — cave-wave QA sweep on the frozen integrated pin

Lane 47 / opencode DeepSeek worker session / parent spec #468, lane issue #485.
Mode: **Acceptance**. QA/report only on an immutable pin; no production edits.

## Slot class / routine addressed; missing model piece

- **Addressed:** independent reproduction of the *whole* cave chain on one
  frozen integrated pin — lane-41 generation, lane-43 live `P2_CAVE_GEN`,
  lane-44 rooms/timeline, lane-45 real geometry + electric gate, lane-46
  physical item spawn/carry/receipt — plus lane-40's checker for the six
  acceptance-contract items, with every result labelled natural / proxy /
  injected.
- **Missing model piece:** no lane had run lanes 41→46 together on one pin and
  scored them with lane-40. This slice adds the report assembler
  `experimental/pikmin2_cave_lane47_qa.py` and the reproduced evidence under
  `output/dsw/l47-out/`.
- **Boundary respected:** no production source was edited on either branch. All
  native hooks/generators/checkers were consumed as-is. No second generator or
  checker was written.

## Bases, heads, dirty state, ordered commits

- Root worktree `output/dsw/l47-root`, branch `deepseek/p2-l47`.
  Base = head = `a9cea5b34bb4db4806951accad6ce08d5e2a9b7b` (clean at start).
- Native worktree `output/dsw/native-l47`, branch `deepseek/p2-l47-native`.
  Base = head = `6da0364f5756cdcea80805939f2cb0d929a25cdc` (clean; **no native
  commits**, no native source change was needed).
- Ordered root commits:
  1. `lane47: cave-wave QA report assembler + tests (#485)` —
     `experimental/pikmin2_cave_lane47_qa.py`,
     `tests/test_pikmin2_cave_lane47_qa.py`
  2. this handoff — `lane47: cave-wave QA sweep handoff (#485)`
- Dirty state at handoff: the two owned files above are the only tracked
  additions; all generated evidence stays under `output/dsw/l47-out/` (ignored,
  not committed).

## Owned files; generator hooks and provider/consumer agreements

Root (owned, new):

- `experimental/pikmin2_cave_lane47_qa.py` — parses every `P2_CAVE_*` runtime
  marker plus a `P2_RECEIPTS_1` ledger, consumes a lane-40 report (both its
  stdout and its nested report-file shape) and a lane-40 negative-control
  report, and emits a fail-closed `p2-cave-lane47-qa/1` report. A contract item
  is a pass only when its evidence is natural; proxy/injected never passes.
- `tests/test_pikmin2_cave_lane47_qa.py` — 19 focused synthetic tests (marker
  grammar, malformed tolerance, nested vs stdout checker shape, negative-control
  retry handling, staged-grant downgrade, exit codes, determinism).
- this document.

Provider → consumer agreements used as-is (no countersignature changes):

- lane 34/36/40 seeded table → lane 41 `P2_CAVE_FLOOR_V1` via
  `experimental.pikmin2_cave_lane41_{reconcile,generator}.py`;
- lane 40 `pikmin2_cave_spike` report (`generation_invariant.generation_pass`,
  `reroll_invariance`, `end_to_end_loop`, `seed_determinism`, per-layout
  `retry_required`) is the acceptance authority the QA report cites;
- lane 41 `p2-cave-observed-layout/1` (`source: engine`) → lane 44 rooms →
  lane 45 geometry → lane 46 items;
- lane 06 `pc_p2_receipt_host_*` receipt provider (pre-handle revision) is the
  ledger the QA report reads.

## Already integrated vs actually new

- Already integrated on the pin: lanes 34–46 (schema, growth, leaves,
  item/gate placement, buds, AP logic, spike/checker, native generator, live
  hook, proxy rooms, real geometry/egate, physical items/receipt).
- Actually new: the independent, single-pin reproduction of that whole chain and
  the fail-closed QA assembler + report. No production code is new.

## Build evidence (native `6da0364f`, clean, `ninja -n="ninja: no work to do."`)

From `output/dsw/l47-build-evidence.txt`:

```
lane=l47 target=p2_cave_generator_test native=6da0364f... exe=...\p2_cave_generator_test.exe sha256=ed595d48e81fcf30b96ec1d165d6819f33fd5ae1c774571c2ff7fd3bd4a58b79
lane=l47 target=pikmin_pc              native=6da0364f... exe=...\native-l47-build\bin\nectar.exe sha256=1ff8a2372e254e7892eada0bfe50cc36d45ca2dba3147e158dce1d19090214ad
lane=l47 target=p2_cave_rooms_test     native=6da0364f... sha256=2e2ee7377469e0203077e2ad188fbd1507a0ffaf20981242efb094c1d3d01214
lane=l47 target=p2_cave_geometry_test  native=6da0364f... sha256=27e7667659f61fe4fe8cd1200b7c15ae7216f6d09917f1b41af64a75f5ef21d6
lane=l47 target=p2_cave_items_test     native=6da0364f... sha256=44321b724cf65d0e44df57234d3c4c9727aee6ca2feef6c3bc08bd048d6c3330
```

Live fixture (`tools/preview_p2_room.cpp`, link harness `scripts/build_pikmin2_fixture.py`,
`--expected-native-head 6da0364f...`): `output/dsw/l47-out/fixture/fixture.exe`
(`status: built`).

The four native one-consumer gates all PASS on the pin:
`PASS p2 cave generator: forced choke/leaves/gate, choke dominance, …`;
`PASS p2 cave rooms: proxy bridge, parse, hazard timeline, reroll invariance`;
`PASS p2 cave geometry: real model plan, proxy rejection, gate actor binding`;
`PASS p2 cave items: parse, placement, rejections, projection`.

Root tests: `py -3.12 -m pytest tests/test_pikmin2_cave_spike.py
tests/test_pikmin2_cave_lane41_generator.py tests/test_pikmin2_cave_lane41_reconcile.py
tests/test_pikmin2_cave_lane43_live.py tests/test_pikmin2_cave_rooms.py
tests/test_pikmin2_cave_geometry.py tests/test_pikmin2_cave_lane46_items.py
tests/test_pikmin2_cave_lane47_qa.py -q` → **111 passed**.

## Fixture / seed and observed generation evidence (exact paths)

- Floor `forest_1` floor 1, frozen seed `468001`; alt seed `468002`;
  spike table + scenarios + negative controls from
  `l47-root/tests/fixtures/pikmin2_cave_spike/`.
- Lane-41 generation: `output/dsw/l47-out/lane41/` —
  `p2-cave-observed-layout.json` (+`-reroll.json`), `p2-cave-lane41-report.json`.
  Marker exactly:
  `P2_CAVE_GEN source=engine cave=forest_1 floor=1 seed=468001 segments=6
  chokes=1 leaves=2 buds=0 gates=1 entrance=forest_1:f1:segment:0
  hole=forest_1:f1:segment:1 salt=0 attempts=1`.
- Lane-40 checker: `output/dsw/l47-out/checker/positive.json`
  (`pass=true, generation_pass=true, evidence=natural`, reroll + 3 scenarios +
  seed determinism all true) and the negative control
  `output/dsw/l47-out/checker/negative_missing_leaf.json`
  (`pass=false`, `retry_required=true`, findings `missing leaf leaf_water_0`).
- Lane-43 live: `output/dsw/l47-out/lane43/live-run.log`,
  `lane43-live-report.json` (`pass=true`, `standalone_matches=true`,
  `control_markers=0`, 960×540 window).
- Lane-44 rooms timeline: `output/dsw/l47-out/run-rooms/rooms-run.log` —
  `P2_CAVE_ROOMS_TIMELINE` fresh (hole=0/elec=0/water=0/untagged=1),
  `come_back_with_yellow` (elec=1), `return_with_yellow_and_blue` (hole=1), and
  `PASS cave rooms: proxy floor, live squad keys, hazard timeline (proxy geometry)`.
- Lane-45 geometry + lane-46 items: `output/dsw/l47-out/run-salt0/items-run.log`
  and `items-run-restart.log` —
  `P2_CAVE_GEOMETRY_READY nodes=6 real=4 proxy=2 gate_actors=2 geometry=real`,
  `P2_CAVE_GEOMETRY_DRAW nodes=6 models=4 gates=2 geometry=real`,
  `P2_CAVE_ITEM_ACTOR` ×3, `P2_CAVE_ITEMS_READY items=3 tagged=2 untagged=1`,
  `P2_CAVE_ITEM_FREE_RELEASE target=treasure_elec count=12`,
  `P2_CAVE_ITEM_NATURAL_CARRY transport=8`,
  `P2_CAVE_ITEM_RECEIPT … leaf_elec_0 … new=1 result=1`; the restart pass gives
  `new=0 result=0` with the ledger unchanged.
- Ledger: `output/dsw/l47-out/run-salt0/p2-cave-item-receipts.txt`.
- Assembled report: `output/dsw/l47-out/qa-report.json` (`p2-cave-lane47-qa/1`).

## Acceptance contract 1–6 results (natural vs proxy/injected)

| # | Contract item | Result on this pin | Evidence class |
|---|---|---|---|
| 1 | Generation invariant | **PASS** — engine layout; choke is a cut vertex; lane-40 `generation_pass=true` | **natural** |
| 2 | Seed determinism | **PASS** — `check_determinism` 468001 vs 468002 | **natural** (checker) |
| 3 | Re-roll invariance | **PASS** — two engine layouts for 468001 keep the table/requirements | **natural** |
| 4 | Reachability | **PASS** — only the water choke and the required elec leaf/gate exist; no ambient/off-slot hard gate | **natural** |
| 5 | End-to-end loop | **PARTIAL** — real item spawn, real natural carry, real exactly-once receipt, and the model timeline is green, **but** ability acquisition is staged (`P2_CAVE_ROOMS_GRANT natural_acquire=0 staged=1` ×2), the layout/room geometry is proxy and there is no carry-blocking | **proxy** (collection natural, timeline staged) |
| 6 | Failure handling | **PASS** — a layout missing a forced leaf is rejected with `retry_required=true` | **natural** (control) |

The QA assembler reports `pass=false` **only** because item 5 is proxy; items
1–4 and 6 are natural. No generation artefact is hand-placed or
fixture-injected: the only fixture is the frozen seeded *table* (the input),
and both observed layouts are `source: engine`. The negative control is a
fixture by design and is never counted as a PASS.

## Re-roll / restart / cross-seed

- **Re-roll:** two engine layouts for seed 468001 pass the invariant and keep
  identical requirements; geometry differs. Live re-entry reroll not re-run
  (lane-40 checker `reroll_invariance.pass=true` is the authority).
- **Restart:** the lane-46 restart pass re-spawned the three items, carried
  naturally (`transport=9`) and received `leaf_elec_0` as a durable duplicate
  (`new=0 result=0`); the `P2_RECEIPTS_1` ledger stayed at one row.
- **Cross-seed:** not re-run live; lane-40 `check_determinism` (468001 vs
  468002) passes and lane-41's alt-seed report is `generation_pass=true`.

## Known limitations; next consumer

- **Item 5 is not natural.** Ability acquisition is recolouring a Pikmin
  (`staged=1`, `natural_acquire=0`); the gate does not physically block carry;
  geometry is proxy. This matches lanes 44/45/46 own `PARTIAL` labels and is the
  single open acceptance item. Owning lanes: 44 (timeline), 45 (gate carry /
  real water+elec meshes), 46 (items).
- **Integrated fixture timing.** The items fixture did not self-terminate within
  240 s (timed out) and the restart pass exited `1` after the durable duplicate;
  only a clean rooms-only run directory reproduces the lane-44
  `P2_CAVE_ROOMS_TIMELINE`, because the geometry/items hooks default to their
  config filenames and preempt the rooms loop. This is a harness observation,
  not a production failure. Owning lane: 44.
- **Known lane limitations unchanged:** lane 45 uses a converted dry unit for
  the water nodes and an approximate bind-pose e-gate; lane 46 draws every
  item with one proxy `treasure.mod`; lane 46/06 receipt-provider revisions must
  be reconciled at integration (lane 01/06).
- **Next consumer:** the integrator (lane 01) should treat items 1–4 and 6 as
  QA-reproduced natural on `a9cea5b3`/`6da0364f`, and keep item 5 open with
  lanes 44/45/46. Re-run this lane's report after any change to the
  rooms/geometry/items hooks.

ONE exact reproduction command (from `output/dsw/l47-root`, after the builds
recorded above):

```powershell
py -3.12 -m experimental.pikmin2_cave_lane47_qa --live-log C:/Users/alari/pikmin-randomizer/output/dsw/l47-out/lane43/live-run.log --live-log C:/Users/alari/pikmin-randomizer/output/dsw/l47-out/run-rooms/rooms-run.log --live-log C:/Users/alari/pikmin-randomizer/output/dsw/l47-out/run-salt0/items-run.log --live-log C:/Users/alari/pikmin-randomizer/output/dsw/l47-out/run-salt0/items-run-restart.log --checker C:/Users/alari/pikmin-randomizer/output/dsw/l47-out/checker/positive.json --failure-checker C:/Users/alari/pikmin-randomizer/output/dsw/l47-out/checker/negative_missing_leaf.json --receipts C:/Users/alari/pikmin-randomizer/output/dsw/l47-out/run-salt0/p2-cave-item-receipts.txt --out C:/Users/alari/pikmin-randomizer/output/dsw/l47-out/qa-report.json
```

Exit `1` with `classification = {generation_invariant, seed_determinism,
reroll_invariance, reachability, failure_handling: natural, end_to_end_loop:
proxy}` — the honest verdict, not a wrapper failure.

## Subagent usage

Three subagents were started in parallel before the core work.

- `explore` **source audit** — **used as-is, then corrected at the consumer.**
  It produced the exact marker table, env vars and natural/proxy labels. Its
  claim that the lane-40 report exposes top-level `generation_pass`/`evidence`
  was only half right: the CLI stdout does, the report *file* nests them under
  `generation_invariant`. I found this while wiring the module and made the
  assembler accept both shapes. Saved ~30–40 min of reading.
- `explore` **artifact inventory** — **used as-is.** Mapped every existing
  run dir/fixture/provenance and the host-only vs build+GL split, which is what
  let me reuse the lane-45 asset overlay instead of rebuilding the convert
  pipeline. Saved ~25–35 min.
- `general` **QA validator + pytest** — **used after one review round.** Its
  module parsed markers correctly and ran 16 synthetic tests green, but it
  hardcoded top-level checker keys and classified `end_to_end_loop` as natural
  whenever a receipt existed. I rewrote the checker normalisation, derived
  reachability and failure-handling from the real lane-40 report, and added the
  honest staged-grant downgrade (now 19 tests). Draft time saved ~40–60 min;
  the review correction cost ~25 min.
- Cost: three concurrent startups on a shared host; one delegated audit claim
  (checker shape) and one delegated classification rule both needed correction,
  reinforcing that subagent conclusions are claims to verify.

## Findings filed on owning lanes (exact IDs/commits/paths)

| Owning lane / issue | Finding | Evidence | Status |
|---|---|---|---|
| 44 (#482) | Integrated fixture preempts `P2_CAVE_ROOMS_TIMELINE` when geometry/items configs are present; rooms-only run dir required | `output/dsw/l47-out/run-rooms/rooms-run.log` vs `run-salt0/items-run.log` | open (harness) |
| 44/45/46 (#482/#483/#484) | Contract item 5 remains PARTIAL/proxy: staged ability acquisition, proxy geometry, no carry-blocking | `output/dsw/l47-out/qa-report.json` (`end_to_end_loop: proxy`) | open (acceptance) |
| 45 (#483) | Water choke/leaf uses a converted dry unit; e-gate approximate | `run-salt0/items-run.log` geometry nodes | known |
| 46/06 (#484) | Receipt-provider revision must be reconciled at integration | `pc_p2_cave_items.cpp` vs lane-06 branch | known |
