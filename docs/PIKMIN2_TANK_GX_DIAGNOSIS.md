# Tank attack GX warning diagnosis

Issue #207, Tank lane. This is a diagnostic comparison on the private original P1 arena, not a gameplay or material fidelity acceptance test.

## Finding

The original P1-only case reproduces the GX warning sequence with no imported fire appearance and no static water display. The warnings do not begin during the observed Tank Attack samples: they begin after `demo56.cin` loads and `MoviePlayer: clearing top heap!` is logged. Adding the fire appearance yields the same sequence. Therefore the imported Tank pose/material bank and static water draw are not necessary causes of these warnings.

This identifies a baseline movie/render transition boundary, not the exact corrupt display-list owner. It does not prove that freeing a particular bank causes corruption, or that the flame receiver has a defect. No speculative converter, material, heap or receiver fix was made.

## Controlled comparison

All cases use the identical private attack-trigger fixture executable `output/p2-lifecycle-batch/tank-runtime-link-03/fixture.exe`, SHA256 `03825a7a77b4f647faa81d8dc062343c89ba7e24815f172246df9ce4d4f7c77f`. Its completed native snapshot is `b602d8c43dc6a1132821f787b99a28097c3c7521`, with exact inputs/source hashes and commands retained in link-01/provenance.json and link-03/commands.json. `scripts/pikmin2_tank_gx_fixture.cpp` preserves the exact compiled fixture source.

The arena, actual P1 Tank generators, captain observation point 100 units from the actor, native AI, tutorial dismissal and movie skip request are identical. Normal attacks are provoked by proximity; no enemy action/state/counter/velocity is written. The only case mutation is the private optional profile: absent; imported fire without water; imported fire plus noninteractive water. Original config bytes are retained. No live save or installed player binary is used.

The old movement gate deliberately cannot pass for the stationary attacking actor. Exit 1 is recorded as diagnostic termination, not relabeled success. The driver requires observed native Attack motion and reports warnings/chronology independently. It records executable hash and exact config hash before execution, bounds each child process to 100 seconds, and preserves all logs.

| Case | Native Attack samples | First GX warning line | demo56 load line | Warnings before demo56 |
|---|---:|---:|---:|---:|
| P1 only | 23 | 883 | 857 | 0 |
| Imported fire only | 22 | 935 | 909 | 0 |
| Imported fire + static water | 22 | 943 | 917 | 0 |

Reports are under `output/p2-lifecycle-batch/tank-gx-absent-01/result.json` `tank-gx-fire-01/result.json`, and `tank-gx-full-01/result.json`. Earlier failed `tank-native-01` evidence is unchanged.

The frozen source `src/plugPikiColin/moviePlayer.cpp` logs top-heap clearing immediately before `resetHeap(SYSHEAP_Movie, AYU_STACK_GROW_DOWN)` when its play list becomes empty. `CineShapeObject::init` in `src/plugPikiColin/cinePlayer.cpp` loads movie models through `gameflow.loadShape`. These are useful next instrumentation boundaries, not a demonstrated ownership bug. The next narrow diagnostic would tag display-list submissions with their owning shape and allocation/lifetime across that movie reset, compare invalid packet pointers against still-live shape storage, and only then propose a lifetime/state fix.

## Independent material limitation

A read-only source audit also confirms Tank and Wtank have two source color channels and two TEV stages, including enabled color lighting. Current baked MOD materials have lighting control 0 and one TEV stage. This loss can explain brightness differences and is being audited separately; it is not needed to reproduce the GX warning. Source/baked hashes and channel values are retained in `output/p2-lifecycle-batch/tank-material-audit.json`. No guessed recoloring or rescaling was applied.

## Reproduction and tests

Use `py -3.12 -m scripts.test_pikmin2_tank_gx_native --assets <local-assets> --profile <tank-assets-05> --exe <immutable-attack-fixture> --output <fresh-private-path> --mode absent|fire|full --timeout 100`. Supply the preserved attack-trigger fixture, not the later successful movement fixture.

`py -3.12 -m pytest -q tests/test_pikmin2_tank_gx_native.py` verifies native attack evidence is required and pre/post movie warning chronology cannot be mislabeled. Four tests pass.
