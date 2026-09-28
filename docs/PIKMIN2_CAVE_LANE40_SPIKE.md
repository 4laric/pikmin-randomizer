# Lane 40 — cave spike and independent acceptance checker (#479 / parent #468)

Owner session: headless DeepSeek worker lane 40. Issue: 4laric/pikmin-randomizer
#479; parent spec #468. This slice is QA tooling only; it does not touch native
production sources or run a second generator.

## What was addressed; missing model piece

- **Routine addressed:** the missing independent acceptance checker for the
  #468 cave model. No module in either worktree accepted or rejected a seeded
  per-floor table or a generated cave layout (inventory: no `choke`/`leaf`/`bud`
  schema, no seeded-table module, no cave acceptance checker existed).
- **New module:** `experimental/pikmin2_cave_spike.py` evaluates acceptance
  contract items 1–6 from `_cave_fanout.md` against a seeded structural table
  plus one or more observed floor layouts. It is fail-closed and labels
  `engine` evidence *natural* and anything else *injected*.
- **Missing model piece it defines for consumers:** the QA contract for a
  seeded table (`p2-cave-seeded-table/1`) and a generated layout
  (`p2-cave-observed-layout/1`), with the semantics lane 34/39 can publish
  against and lanes 35–38 can emit against.

## Root / native state and ordered commits

- Root worktree `output/dsw/l40-root`, branch `deepseek/p2-l40`.
  Base `fba8d5eb0767950f56486bd2738598eb99a4645d`.
- Native worktree `output/dsw/native-l40`, branch `deepseek/p2-l40-native`.
  Base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`; head unchanged; clean
  (`dirty=no`). No native source change was needed for this QA slice.
- Ordered commits (root):
  1. `b7500d9e6f8d609333ea408a1e91090ab172e2a9` — `lane40: cave spike acceptance
     checker + forest_1 fixtures + tests (#479)`
  2. this handoff document — `lane40: cave spike handoff (#479)`
- Dirty state at handoff: none tracked; generated evidence stays under
  `output/dsw/l40-out/` (ignored, not committed).

## Owned files; generator hooks and provider/consumer agreements

Owned (new, root only):

- `experimental/pikmin2_cave_spike.py` — checker + CLI.
- `tests/test_pikmin2_cave_spike.py` — 18 focused tests.
- `tests/fixtures/pikmin2_cave_spike/*.json` — spike table, three positive /
  reroll layouts and three negative controls, plus a scenario timeline and a
  second-seed table.
- `docs/PIKMIN2_CAVE_LANE40_SPIKE.md` — this handoff.

Provider/consumer agreement (proposed; not yet countersigned by 34/39 because
those lanes were still implementing when this ran):

- **Lane 34 (provider)** should publish the per-floor table in the
  `p2-cave-seeded-table/1` field layout: `seed`, `cave`, `floor`, ordered
  `segments`, ordered `chokes` (`kind`, `segment_index`), `leaves`
  (`hazard`, `segment_index`, `item_slot`), `buds` (`hazard`,
  `segment_index`, `count`), `treasures` (`tagged`, `hazard`, `segment_index`,
  `leaf`), and `hole.segment_index`.
- **Lanes 35–38 (generators)** should emit an observed layout in the
  `p2-cave-observed-layout/1` shape (`source`, `seed`, `cave`, `floor`, `nodes`
  with `kind` in `segment/choke/leaf/bud/gate` and optional `hazard`/`items`,
  `edges`, `entrance`, `hole`). A layout whose `source` is not `engine` is
  reported as *injected* and can never yield a `generation_pass`.
- **Lane 39 (logic)** can reuse `segment_requirements`, `treasure_requirements`
  and `hole_requirements` as the executable form of the seeded graph; bud
  alternative keys are modelled as `bud:<hazard>:s<seg>:n<count>` solutions so
  Pikmin-count tracking is explicit.

No generator routine was edited; no shared file (`teki.h`, `gameCaveInfo`,
`pc_p2_cave.*`, CMake, …) was touched.

## What is already integrated vs actually new

- Already integrated: the cave **entry/lifecycle** surface
  (`pc_port/pc_p2_cave.cpp`, anchor/entry/readiness/transfer headers), the
  source catalog/dependency parsers, and the source definitions. The port has
  **no runtime cave generator**; the original generator is only in the
  read-only research checkout (`RandMapMgr::create` "The CaveGen Function",
  `RandMapUnit`, `RandGateUnit`, `RandItemUnit`, `RandPlantUnit`, …).
- Actually new: the independent acceptance checker, its contract, the
  `forest_1` floor-1 spike fixtures, and the negative controls that make the
  checker's rejections testable.

## Build evidence

From `output/dsw/l40-build-evidence.txt` (wrapper `build_lane.py l40`,
`--target p2_cave_transfer_test`):

```
2026-09-15T13:02:29 lane=l40 target=p2_cave_transfer_test native=b805d9c626e4f4558c95aef7cac311a5d9a2068f dirty=no build_dir=.../native-l40-build exe=.../p2_cave_transfer_test.exe sha256=a2878c6237bb03e575a7673e118c32dfef502de38b018009d33e6a05a5d6a573 ninja_n="ninja: no work to do." seconds=10
```

The built frozen-pin gate runs clean: `PASS P2_CAVE_TRANSFER` (exit 0) with
MinGW on `PATH`.

## Fixture / seed used; generation evidence paths

- Spike floor: `forest_1` (Hole of Beasts) floor 1, frozen seed `468001`.
- Real source data (regenerated, not cache): catalog 14 caves / 105 floors / 96
  pools, sha256 `37073ac668e43755e6b513da502fea392323d7b0a87f03ffe3de6e3565ab8413`;
  dependencies 432 resources, sha256
  `966130bc36e1142646d882b09ee438d0f444c824ab2434e5167ac04fed2f2352`.
  `forest_1` floor 1 is definition 0, pool `1_units_cent3_tsuchi.txt` (7 units,
  18 doors / 36 links), 7 enemy rows, **1 treasure (`juji_key_fc`), 0 gates**.
- Evidence paths:
  - `output/dsw/l40-out/catalog/catalog.json` + `catalog-run.log`
  - `output/dsw/l40-out/dependencies/dependencies.json` + `dependencies-run.log`
  - `output/dsw/l40-out/spike/forest_1_source.json` / `.md` (real source)
  - `output/dsw/l40-out/spike/report_injected.json` (positive spike, injected)
  - `output/dsw/l40-out/spike/report_negative_{bypass,gate_offslot,missing_leaf}.json`

**No real engine-generated cave exists yet**, so every layout artefact here is
`source: fixture` (*injected*). The spike table assigns the two tagged treasures
(`treasure_water`, `treasure_elec`) and the water choke over real `forest_1`
floor-1 content; the slot assignment is hand-authored, not generated. The
checker's natural path is unit-tested (`source: engine` relabel of the fixture)
but no natural artefact is claimed.

## Acceptance contract results (injected vs natural)

| # | Contract item | Result | Evidence class |
|---|---|---|---|
| 1 | Generation invariant: required chokes/leaves/buds exist; each choke on every path (choke removal disconnects entrance→hole) | PASS model-level; negative bypass layout correctly rejected | injected |
| 2 | Seed determinism: same seed → identical table; changed seed → different table | PASS | model-level (fixture tables) |
| 3 | Re-roll invariance: two layouts for one seed keep the table and per-treasure/hole requirements | PASS | injected |
| 4 | Reachability: no ambient hard gate outside the floor's logic; gates only on choke/leaf doors | PASS; ambient-gate and off-slot-gate layouts correctly rejected | injected |
| 5 | End-to-end loop: fresh floor → unreachable; come back with yellow → elec treasure reachable, water treasure and hole still gated; +blue → all reachable; untagged `juji_key_fc` stays reachable/random | PASS (model-level timeline) | injected |
| 6 | Failure handling: layout missing a required leaf/choke/bud is rejected with `retry_required` | PASS (`report_negative_missing_leaf.json`) | injected (control) |

`generation_pass` is `false` for every artefact because none is engine-produced.
`model_pass` is `true` for the positive/reroll layouts and `false` for all three
negative controls.

## Re-roll / restart / cross-seed

- **Re-roll:** two layouts with different geometry for seed `468001` both pass
  the invariant and derive identical requirements (`reroll_invariance.pass`).
- **Cross-seed:** `spike_table_alt_seed.json` (seed `468002`) changes the choke
  set, treasure assignments and bud placement; `check_determinism` passes both
  the same-seed identity and the changed-seed difference.
- **Restart:** not evaluated — it needs an engine generator and a live floor.
  Named dependency: lanes 35–38 must land a runnable generator on the integrated
  build before a restart/re-entry run is possible.

## Known limitations; next consumer; reproduction

Limitations:

- The checker is a model/graph checker; it cannot itself produce a floor or
  prove engine geometry. Items 1–6 are therefore *injected* here.
- The retail `forest_1` floor-1 pool has **no** water/electric alcove unit and
  **0 gates**, so lanes 36/37 must author leaf/choke units and gate placement;
  the spike fixtures name the slots, not real unit assets.
- The provider/consumer field layout is proposed, not yet countersigned by
  lanes 34/39 (still implementing). If lane 34 publishes a different schema,
  this checker's loader must be adapted, not forked.

Next consumer: lane 40 follow-up (or the integrator) runs the same checker
against lane 35–38 engine output per the reproduction command below; lane 39
can import the requirement functions.

ONE exact reproduction command (from the root worktree):

```
py -3.12 -m experimental.pikmin2_cave_spike --table tests/fixtures/pikmin2_cave_spike/spike_table.json --layout tests/fixtures/pikmin2_cave_spike/spike_layout_fixture.json --layout tests/fixtures/pikmin2_cave_spike/spike_layout_reroll.json --scenario tests/fixtures/pikmin2_cave_spike/spike_scenarios.json --determinism tests/fixtures/pikmin2_cave_spike/spike_table_alt_seed.json --output output/dsw/l40-out/spike/report_injected.json
```

Tests: `py -3.12 -m pytest tests/test_pikmin2_cave_spike.py -q` → `18 passed`.

## Subagent usage

Started three subagents in parallel, then did the module/tests/build/handoff
myself.

- `explore` **source audit** (native generator surface): used as-is. Established
  the pivotal fact that the port has no runtime cave generator and cited the
  research-checkout generator functions. Saved roughly 30–45 min of reading.
- `explore` **candidate inventory**: used as-is. Confirmed the seeded-table /
  choke-leaf-bud schema / acceptance checker were all absent and mapped the
  existing cave tooling and markers. Saved roughly 20–30 min.
- `general` **real source-data regeneration**: used as-is after spot-checking
  the JSON against the catalog; it ran the existing catalog/dependency tools and
  extracted real `forest_1` floor-1 data into `l40-out`. Saved roughly 20 min.
- Cost: three concurrent agent startups on a shared host. One correction was
  needed during my own work (unused variable in the reroll check) — no subagent
  output needed rework.
