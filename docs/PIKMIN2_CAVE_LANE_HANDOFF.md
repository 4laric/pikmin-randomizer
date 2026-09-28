# Cave lane handoff — 2026-09-13 (#381)

Owner: Codex using shared GitHub account **4laric**. User requested handoff;
no new cave implementation is running after this handoff. Parent scope is
[#154](https://github.com/4laric/pikmin-randomizer/issues/154), coordination
[#186](https://github.com/4laric/pikmin-randomizer/issues/186). Full cave acceptance
remains open. Read this guide before continuing the repeated “proceed” work.

## Start here

The latest runtime candidate is **PR #377**, frozen root
`f3c103ecce5e6080dfad4ee88f904ec5002c4397`. Both floor3 treasures are installed
together and hauled by 20 Reds into one exact **380-Poko** economy. A fresh
process starts from the actual captured 150-Poko intermediate ledger: green
credits zero, donut credits 230, and final ledger bytes match the first run.
This is **engineering economy persistence**, not full world/campaign resume.

Its native baseline is **PR #368**, native
`e0418c798e808bd1b29217532ebb36f4f0d89406`. A diagnosed particle query bug treated
overhead terrain as deep ground penetration and pushed the donut sideways.
The correction bounds matched floor height/normal selection for grounded,
lifted, sufficiently crewed imported static-map cargo. Legacy branches and wall
tracing remain intact. Actual first/replay donut hauling and green regression
passed, with source-query and wall controls and focused peer review.

Donor pellet dimensions remain **radius20 / height14**, versus source donut
**radius50 / height5**. Imported models and source economy do not establish
authentic cargo physics. Source placement and directed graph are unchanged.

## Frozen open candidates

All PRs in this table were **open**, not assumed merged, when checked for this
handoff. Numbers in the last column are declared PR bases; “maintained” means
`codex/pikmin2-room-preview`. Branch names and full hashes are available from
the linked PRs; abbreviated hashes below uniquely identify recorded candidates.

| PR | Frozen root | Purpose | Base |
|---|---|---|---|
| [326](https://github.com/4laric/pikmin-randomizer/pull/326) | `040314f` | Host floor3 terminal failure | maintained |
| [328](https://github.com/4laric/pikmin-randomizer/pull/328) | `b177632` | Native floor3 failure and exit42 | maintained |
| [331](https://github.com/4laric/pikmin-randomizer/pull/331) | `ced0110` | Restartable floor3 failure supervisor | maintained |
| [332](https://github.com/4laric/pikmin-randomizer/pull/332) | `48b744f` | Floor4 assembly and native traversal | 328 |
| [335](https://github.com/4laric/pikmin-randomizer/pull/335) | `551b793` | Floor5 boss-room geometry survey | maintained |
| [336](https://github.com/4laric/pikmin-randomizer/pull/336) | `95df3cd` | Explicit diagnostic floor4 native entry | 332 |
| [339](https://github.com/4laric/pikmin-randomizer/pull/339) | `584b0d0` | Floor4 Violet source plan, retained at population20+ | 335 |
| [341](https://github.com/4laric/pikmin-randomizer/pull/341) | `cf4d648` | Actual floor4 Violet conversion/pluck | 336 |
| [345](https://github.com/4laric/pikmin-randomizer/pull/345) | `891847b` | Green treasure source haul plan | 339 |
| [355](https://github.com/4laric/pikmin-randomizer/pull/355) | `d10d348` | Green hauling, exact150 receipt/replay | 341 |
| [359](https://github.com/4laric/pikmin-randomizer/pull/359) | `4c9bda9` | Donut source haul plan | 345 |
| [360](https://github.com/4laric/pikmin-randomizer/pull/360) | `ef5fc27` | Pre-receipt cargo terminal diagnostics | 355 |
| [362](https://github.com/4laric/pikmin-randomizer/pull/362) | `691866d` | Donut first haul and preserved failed replay | 360 |
| [368](https://github.com/4laric/pikmin-randomizer/pull/368) | `4d6fbcd` | Overhead-contact correction and passing replay | 362 |
| [377](https://github.com/4laric/pikmin-randomizer/pull/377) | `f3c103e` | Both treasures / partial-economy restart | 368 |

**The runtime chain does not contain the separate source-plan chain.** #355
consumes #345 artifacts; #362/#377 also consume #359 artifacts. Integrate both.
#331/#335 have private joined ancestry despite their declared maintained base;
inspect actual DAG and diffs, not only the table. In shared Python floor survey
merges, retain both engineering floor5 support and token-bound floor4 guards.
No token authorizes successful floor3-to-floor4 host progression.

## Local workspaces and assets

All paths are beneath `C:/Users/alari/pikmin-randomizer/` unless absolute below.
Do not edit a submitted head or overwrite its captured run. Start a new private
branch/worktree and fresh output directories. Never edit original BBFT or the
research checkout, relink shared Archipelago, or push the native repository.

| Location | Use |
|---|---|
| `output/p2-beasts-both-haul` | Latest runtime sources; this documentation branch is based on #377 |
| `output/p2-beasts-donut-fix` | Frozen #368 source export and causal/fixed evidence |
| `output/native-beasts-donut-fix` | Frozen native `e0418c79`, private build; local untracked build logs are expected |
| `output/p2-beasts-floor3-track` | Earlier floor3/4 source, assemblies and runtime evidence |
| `output/p2-cave-lane` | Separate source-plan branch, host receiver/supervisor and boss-room survey history |
| `output/p2-root-integration` | Integration-owned checkout: read-only to cave workers |
| `native/pikmin2-research` | Read-only source research |
| `C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso` | Local GPVE01 rev0 disc, 995557376 bytes; never redistribute |
| `C:/Users/alari/bbft/dist/cohesion/pikmin/assets` | Read-only P1 asset base |
| `output/p2-cave-catalog-batch/audit-final/catalog.json` | Source cave catalog |
| `output/p2-mapcode0-batch/import` | Correct MapCode0 unit import |
| `output/pikmin2-pod111/import-02` / `output/pikmin2-purple113/import-05` | Pod and Purple banks |

Source packages under `output/p2-beasts-floor3-track/output/`:
`floor3-295/final-a` (models/roster), `floor3-306/final-a` (assembly),
`floor4-330/first` (floor4 assembly). Final-floor assets are in
`output/p2-cave-lane/output/beasts318/final-a`.

Frozen plans under `output/p2-cave-lane/output/`:
`beasts344/first/haul.json` (green, SHA256
`fdfe3547276574a3655196e543fcf12177f1b2a750853ff726d39f21171034c6`),
`beasts357-final/first/haul.json` (donut, SHA256
`8b4473f051ffc894e87fea21d98d1d70e3d783ff8d0d1c6381f6f7d8c5380139`).

## Evidence and interfaces to preserve

- **Latest:** `output/p2-beasts-both-haul/output/both371/verification.json`;
  [both-haul guide](PIKMIN2_BEASTS_BOTH_HAUL.md). First run
  `4325179c03a646a4bb81c75a950c3d39` (36/33 trace points), restart
  `86ee1673c2554f4bbc1fb41767ba1247` (36/32), peaks20 each.
  Eleven tests/62 subtests plus independent evidence review passed.
- **Physics correction:** `output/p2-beasts-donut-fix/output/donut365/verification.json`;
  [ground guide](PIKMIN2_BEASTS_DONUT_GROUND.md). Private build591 steps,
  compiled64 eligibility cases, eight real-map queries, wall trace, eleven
  tests/66 subtests; donut first/replay37/38 points and green36 passed.
- **Earlier failures remain evidence:** `output/p2-beasts-floor3-track/output/donut361`.
  #362 first delivery passed but fresh-process rehaul failed. #368 fixes that
  diagnosed case; never rewrite #362 acceptance as a pass.
- **Terminal:** `output/p2-beasts-floor3-track/output/cargo-terminal356`;
  [terminal guide](PIKMIN2_BEASTS_CARGO_TERMINAL.md). Single cargo, exact opt-in
  token, zero Pokos only. Extinction/knockout exit42 passed before receipt;
  after receipt lifecycle is disabled. Host cargo-free receiver deliberately
  rejects cargo-diagnostic evidence. No multi-cargo terminal marker is enabled.
- Earlier native floor3 failures, floor4 entry/Violet and host supervisors have
  reproduction and hash tables in their corresponding `docs/PIKMIN2_BEASTS_*`
  guides. Original actual host floor3 checkpoint remains at
  `output/p2-cave-lane/output/beasts314-final/ledger/surface-ledger.json`;
  copy it for probes, never mutate it.

Reserved cargo generators: **63000 green**, **63001 donut**. Identities:
`forest_1:floor3:treasure:dia_c_green:0` and
`forest_1:floor3:treasure:donutswhite:0`. Pod `(-85,0,-280)`;
green `(-85,0,-960)` and donut `(175,20.5,-55)`. Native registry count is
configured cargo count, not live actor count. Delivery kills the pellet:
do not dereference its pointer afterward. The legacy `treasure-receipt.txt`
only covers the first preview actor; two-cargo proof uses per-instance Pod
events and the exact economy ledger.

Partial150 ledger SHA256:
`530496e73e288c54695be73e05568441b8707acf345d020d8dc0e5a22b11b344`.
Final380 ledger SHA256:
`71e1c489271e826dffa8df66eacf47f3d216ce529ef3dce3bf4cb1f57b595155`.
Reopening the ledger rejects both duplicate IDs. No all-credited380 fresh-world
run was claimed by #377; partial restart respawns and rehauls the green actor.

## Recommended next work

1. Integration task serializes the pending stacks and checks combined native
   exports. Do not repeat every standalone run without a changed dependency or
   unresolved concern. Review the floor contact fix when merging shared physics.
2. Define campaign receipt semantics before enabling postreceipt/multi-cargo
   failure or successful descent: collection identity, atomic checkpoint/economy
   commit, replay, surviving squad, re-entry and collected-actor suppression.
   Existing diagnostic tokens/unsigned evidence are not campaign authorization.
3. Complete source floor3 hazards/actors, natural recruitment and authentic
   cargo physics. Coordinate fixed-hazard/flora ownership (#349/#353) rather
   than creating competing native implementations.
4. Finish floor4 cargo/carried treasure and floor5 Queen/radar/geyser integration;
   coordinate Queen owner (#256). Boss-room walking is not boss completion.
5. Exercise natural combat, descent, retreat, extinction, cave exit, re-entry,
   reload and surface accounting before closing #154. All-five-floor source
   coverage and engineering fixtures do not satisfy that checklist.

Before implementation, record scope/acceptance in an assigned issue (owner Codex
using shared4laric). Follow AGENTS.md and PIKMIN2_WORKFLOW.md. Inspect inherited
scripts for absolute paths. Link external fixtures with
`python -m scripts.build_pikmin2_fixture --source <private-native> --build <private-build> --fixture <fresh.cpp> --output <fresh-dir> --expected-native-head <full-sha>`.
Use the exact documented build configuration; do not guess CMake option names.
Assets, binaries, logs, saves and receipt ledgers stay local.

Integration task is **Engine Lane**, ID
`01a08d46-d7ee-7c11-b2e0-f853596d7346`. All preceding milestone handoffs were sent
there. This document is a snapshot, so recheck PR state and ownership before
resuming; do not assume a later merge from this guide alone.
