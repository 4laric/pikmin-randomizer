# Lane 43 — live cave-generator runtime hook (parent #468, lane issue #481)

Lane 43 / opencode DeepSeek worker session / parent spec #468, lane issue #481.

## Slot class / routine addressed; missing model piece

The whole lane-41 generator pipeline **exercised in a live engine process**. At
lane start the lane-41 hook existed and was compile-verified only; no live
nectar run had ever emitted `P2_CAVE_GEN`. This slice reaches
`pc_p2_cave_setup()` inside a real `nectar.exe --experimental-pikmin2-room`
960x540 run with `PIKMIN_CAVE_GENERATOR_TABLE` set, captures the marker and the
layout the running process wrote, and proves it matches the standalone native
generator for the same frozen table. No room geometry (lane 44) and no generator
algorithm change (lane 41).

Call chain (audited, native base `346378a0`):

- `pc_bbft_init` sets the preview flag from `--experimental-pikmin2-room`
  (`pc_port/pc_bbft.cpp:42-46`).
- `GameCoreSection::finalSetup` calls `pc_p2_preview_setup()`
  (`src/plugPikiKando/gameCoreSection.cpp:1403-1407`).
- `pc_p2_preview_setup()` calls `pc_p2_cave_setup()` at
  `pc_port/pc_p2_preview.cpp:290`.
- The lake-41 hook is the first block of `pc_p2_cave_setup()`
  (`pc_port/pc_p2_cave.cpp:94-106`), before the preview check at `:107` and the
  `p2-cave-entry.txt` parse at `:108`. It needs no live actor globals, but it is
  only reachable through the preview setup path.

## Bases, heads, dirty state, ordered commits

- Root base `2f50d39530b1917dafd9d0d2994b818717d14936` -> head `96e14fc0`,
  clean.
  - `96e14fc0 lane43: live cave-generator hook harness, marker/layout gate and tests (#481)`
- Native base `346378a07861143162a623d00ccdb603d1b45200` -> head
  `346378a0`, clean, **no native commits** (no native source change was needed;
  the existing hook was wired and run as-is).
- This handoff is the second root commit of the lane.

## Owned files; generator hooks; provider/consumer agreements

Root (owned, new):

- `experimental/pikmin2_cave_lane43_live.py` — `parse_marker`,
  `logical_projection`, `compare_live_and_standalone`, `check_live_generation`,
  `check_unset_env`, CLI. Turns the live log + layout into a natural-vs-injected
  verdict against a standalone layout.
- `experimental/pikmin2_cave_lane43_runtime.py` — one-command harness: reconcile
  + standalone generation, fresh room overlay, bounded live run, bounded
  unset-env control run, then the validator. Emits
  `lane43-live-report.json`.
- `tests/test_pikmin2_cave_lane43_live.py` — 17 synthetic tests for the gate.
- `docs/PIKMIN2_CAVE_LANE43_LIVE_HOOK.md` — this handoff.

Native (not modified, consumed as-is):

- `pc_port/pc_p2_cave.cpp:94-106` opt-in hook reading
  `PIKMIN_CAVE_GENERATOR_TABLE` / `PIKMIN_CAVE_GENERATOR_OUT`;
- `pc_port/pc_p2_cave_generator.{h,cpp}` (`P2_CAVE_FLOOR_V1` parse, retry loop,
  `p2-cave-observed-layout/1` JSON, `p2CaveLayoutMarker`);
- `pc_port/pc_p2_preview.cpp:290` caller; `pc_port/pc_bbft.cpp` flag.

Provider -> consumer agreements used as-is:

- lane 41 `pc_p2_cave_generate_file` is the only generator in the path;
- lane 34 `pikmin2_cave_schema.validate_floor_table` via lane 41's reconciliation
  (`experimental/pikmin2_cave_lane41_generator.verify`);
- lane 40 `pikmin2_cave_spike.check_spike` (standalone report shows
  `generation_pass: true`);
- `scripts.preview_pikmin2_room.prepare` supplies the private room overlay
  (junctions/hardlinks into the P1 asset root; shared assets never edited).

## What is already integrated; what is actually new

Already integrated: lanes 34-41 (schema, growth, leaves, item/gate placement,
buds, AP logic, spike, native generator port). The engine-free policies and
their one-consumer test were already on the wave branch.

Actually new: the first live-engine execution of the lane-41 generator hook; a
captured `P2_CAVE_GEN` marker plus the exact layout written by the running
process; a live-vs-standalone logical comparison; an unset-env control proof;
and a reproducible one-command harness. No native source is new.

## Build evidence

From `output/dsw/l43-build-evidence.txt` (native `346378a07861143162a623d00ccdb603d1b45200`,
clean):

```text
2026-09-15T14:36:15 lane=l43 target=pikmin_pc native=346378a0... dirty=no build_dir=...\native-l43-build exe=...\native-l43-build\bin\nectar.exe sha256=f1d87b38ccb349b23761db4de4fb4bbff18491cff597fe66af2cc966f526328d ninja_n="ninja: no work to do." seconds=222
2026-09-15T14:36:38 lane=l43 target=p2_cave_generator_test native=346378a0... dirty=no exe=...\p2_cave_generator_test.exe sha256=efae54d51c6940dad49336135a6ece76cccc8b368cd992a10b4a76a01c347397 ninja_n="ninja: no work to do." seconds=4
```

`pikmin_pc` (the full `nectar.exe` link) was run this slice, unlike lane 41.

## Fixture / seed and observed generation evidence

- Frozen spike table (generator **input**, not a layout):
  `tests/fixtures/pikmin2_cave_spike/spike_table.json`, forest_1 floor 1 seed
  468001, water choke, elec+water leaves, elec door gate, untagged
  `juji_key_fc`.
- Run directory (private overlay, one live run and one control run):
  `C:/Users/alari/pikmin-randomizer/output/dsw/l43-out/pipeline/overlay/5a9e3dadaf4544a59532050201195391`
- Standalone native table + layout:
  `C:/Users/alari/pikmin-randomizer/output/dsw/l43-out/pipeline/standalone/p2-cave-floor-table.txt`
  and `.../p2-cave-observed-layout.json`.
- Live process log:
  `C:/Users/alari/pikmin-randomizer/output/dsw/l43-out/pipeline/live-run.log`
  — line `P2_CAVE_GEN source=engine cave=forest_1 floor=1 seed=468001
  segments=6 chokes=1 leaves=2 buds=0 gates=1
  entrance=forest_1:f1:segment:0 hole=forest_1:f1:segment:1 salt=0 attempts=1`.
- Live layout written by the running engine:
  `C:/Users/alari/pikmin-randomizer/output/dsw/l43-out/pipeline/live-layout.json`
  (`"source": "engine"`).
- Unset-env control log:
  `C:/Users/alari/pikmin-randomizer/output/dsw/l43-out/pipeline/control-run.log`.
- Verdict: `C:/Users/alari/pikmin-randomizer/output/dsw/l43-out/pipeline/lane43-live-report.json`
  (`pass: true`, `generation.evidence: natural`, `standalone_matches: true`,
  `control.markers: 0`, `control.room_ready: true`,
  `control.window_960x540: true`).

The 960x540 centred window is confirmed in both logs
(`SDL2 Window & OpenGL Context initialized successfully (960x540)` and
`Experimental preview window set to 960x540 windowed and centered`).

Observed live layout (identical logical projection to standalone):

```text
segment:0 [juji_key_fc] --choke_water_0(water)-- segment:1 (hole)
segment:0 -- leaf_elec_0(elec) [treasure_elec] -- gate:leaf_elec_0(elec)
segment:1 -- leaf_water_0(water) [treasure_water]
```

## Acceptance contract results (natural vs injected)

This lane covers the runtime-hook slice; the model clauses are the lane-40/41
results and are labelled as inherited where not re-derived here.

1. **Generation invariant** — **PASS, natural.** The live process generated the
   layout from the frozen table; the logical projection matches the standalone
   native generator exactly (node kinds/hazards, edge set, entrance, hole,
   tagged-item hosts), and the inherited lane-40 `check_spike` on the standalone
   layout is `generation_pass: true`. The live layout is engine output, not
   hand-placed or fixture-injected.
2. **Seed determinism** — **PASS, inherited.** The standalone lane-40 report on
   seed 468001 is green; the live layout reproduces the same seed's logical
   projection. No new cross-seed comparison was run live.
3. **Re-roll invariance** — **NOT RUN live.** Only one live geometry was
   captured per run. Lane 41/40 own multi-salt reroll evidence; a live
   re-entry reroll remains a named dependency.
4. **Reachability** — **PASS, inherited/observed.** The live layout keeps the
   single elec gate on the elec leaf door; the water choke is the only trunk
   connector. No gate exists off the table's logic.
5. **End-to-end "come back with yellow" loop** — **NOT RUN.** Lane 40 owns the
   scenario harness.
6. **Failure handling** — **NOT RUN live.** Lane 41 covers the retry/rejection
   path in the standalone one-consumer test.

## Re-roll / restart / cross-seed

Not exercised live this slice. The harness intentionally runs the same table
once live; adding a second live reroll (new overlay, same table) and a
cross-seed live run is the natural extension and needs no native change.

## Known limitations; next consumer

- The hook still only computes and writes the layout; it does **not** install
  P2 `MapUnitInterface` rooms or render the generated cave in the scene. "Live"
  here means the engine-linked generator ran in the real game process, not that
  the generated geometry was played (lane 44).
- The two harness runs were bounded by a 45 s kill (`exit_code 1`,
  `timed_out: true` in the report) because the room preview does not
  self-terminate without a cave-entry fixture; one earlier raw run exited `-1`
  mid-loop after already writing the marker/layout, so budget for benign
  abnormal exits if a self-terminating entry fixture is not used.
- Purple candypop buds still map to no lane-40 hazard vocabulary (lane 41
  limitation, unchanged).
- Next consumers: lane 40 QA (drive its spike table through this harness for
  live end-to-end/re-roll evidence), lane 01 (integrate the runtime hook), lane
  44 (real room geometry), lane 39 (logic already reads the lane-34 table).

## Subagent usage

- `explore` #1 (runtime source audit): **used as-is.** It produced the decisive
  call chain and confirmed the hook runs before the preview/entry checks; this
  directly shaped the harness (no `p2-cave-entry.txt` needed).
- `explore` #2 (existing-candidate inventory + prior GL recipe): **used as-is,
  with one correction.** It correctly flagged `engine/` as a stale copy and
  supplied the slot/PATH/overlay recipe. I independently found that
  `cave-wave-build/bin/nectar.exe` already contained the marker string and then
  built my own `native-l43-build/bin/nectar.exe` rather than rely on it.
- `general` #3 (validator + pytest): **used as-is after review.** I read the
  module and tests, re-ran the 17-test file and the lane-41 tests (29 passed
  together). I then added the separate runtime harness myself, which was outside
  its grant.
- Estimated saving: ~90-120 min of read-heavy audit/inventory and the first
  validator draft. Cost: ~20 min reviewing the delegated code and writing the
  harness. The audit conclusion that the hook is reachable without the cave
  entry fixture was the single most useful delegated claim and was verified
  against the live run.

## One exact reproduction command

Build once (already recorded in the evidence file):

```powershell
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l43
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l43 --target p2_cave_generator_test
```

Then, from `C:/Users/alari/pikmin-randomizer/output/dsw/l43-root`, the single
GL-slot-wrapped command that reproduces the whole live gate:

```powershell
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l43 -- py -3.12 -m experimental.pikmin2_cave_lane43_runtime --exe C:/Users/alari/pikmin-randomizer/output/dsw/native-l43-build/bin/nectar.exe --tool C:/Users/alari/pikmin-randomizer/output/dsw/native-l43-build/p2_cave_generator_test.exe --table tests/fixtures/pikmin2_cave_spike/spike_table.json --out-dir C:/Users/alari/pikmin-randomizer/output/dsw/l43-out/pipeline --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --converted C:/Users/alari/pikmin-randomizer/output/pikmin2-room105 --live-timeout 45 --control-timeout 45
```

Expect `"pass": true`, `"standalone_matches": true`, `"control_markers": 0`.
