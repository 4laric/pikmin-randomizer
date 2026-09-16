# Cave integration speedup (lanes 48/49/50) — integrator notes

Owner: Codex through shared account `4laric` (Muse contributor, lane
`muse-cave-integrator`, issue #519). Private worktrees only; the species P2
wave is untouched.

## What was integrated

Private root `output/msw/l74-root` branch `codex/muse-l74-cave-integrator`
and private native `output/msw/native-l74` branch
`codex/muse-l74-cave-integrator-native`, both based exactly on the cave-wave
heads (`c4d3c9b9` / `6da0364f`, i.e. `origin/claude/p2-cave-wave` and the
local `claude/p2-cave-wave-native`).

Accepted producer candidates (reviewed diffs, ancestry verified locally):

| Lane | Root commits | Native commits | Evidence class |
|---|---|---|---|
| 48 natural bud (#486) | `cacf2f39` validator + tests | `5dd3c804` bud actor + fixture + gate | NATURAL acquisition over proxy geometry; blue grant stays STAGED |
| 49 water/elec meshes (#487) | `452d7e21` converter + sidecar + 25 tests | none (base build only) | NATURAL disc conversion; water query is an offline `ATTR_Water` approximation (`native_consumer_implemented=false`) |
| 50 carry blocking (#488) | `df4a25f8`, `eeccc9ea` gates + tests + handoff | `9f677482`, `59058507`, `f42dedb9`, `e336e8fd` carry module + fixture + gate | NATURAL block/open/credit; attack-receiver gates use injected carriers with natural reactions |

Root merges were disjoint and clean. Native merges conflicted in exactly the
three expected shared seams (`CMakeLists.txt`, `pc_port/pc_p2_cave.cpp`,
`tools/preview_p2_cave.inc`); resolution keeps both lanes' include-and-hook
chains (bud + carry sources, both test targets, both fixtures, dispatcher
order carry → items → bud). The `pc_p2_cave_tick` order is carry, geometry,
bud. `pc_p2_cave_geometry.cpp` came in via lane 50 with the carry-handles
guard; meshes are still drawn by lane 45.

Shared-hook review (#186): lane 48 hooks (`pc_p2_cave.cpp`,
`pc_port/pc_p2_cave_geometry.cpp` untouched by 48, `CMakeLists.txt`,
`preview_p2_cave.inc`) and lane 50 hooks (same files plus
`pc_p2_cave_geometry.cpp` yield-to-carry guard) were reviewed as actual diffs
against the cave-wave base: all hooks are opt-in, additive, and leave normal
(non-preview) cave entry unchanged. Recorded via `accept-review` on
`muse-cave50`; lane 48/49 producer lanes keep their own review state.

## Build and test evidence (this integration)

Private build `output/msw/native-l74-build` under the canonical two-job
lease (`leased_run.py`):

- `pikmin_pc` configure + build, exit 0, native head `6403debc`, clean dirty
  state, executable `bin/nectar.exe` SHA-256
  `164fb32f9cdf64b99aa0a24723fee0ba6f6c1397675b8f0ab50e39d6c17e3160`,
  `ninja -n` dry run: `ninja: no work to do.`
- `p2_cave_bud_test`, `p2_cave_carry_test`, `p2_cave_geometry_test`,
  `p2_cave_items_test` all build (exit 0) and PASS.
- Root: 57 passed + 5 subtests across the lane 48/49/50 suites in the
  integrated root.

Fixture baseline (source-observed in the integrated trees, no new live GL
run in this slice): `scripts/preview_pikmin2_room.py` overlay calls
`ensure_pikmin_squad()`; `pc_port/pc_main.cpp` defaults to a 960×540 window
and calls `pc_window_center()` after persisted settings. Runtime PASS claims
below are carried from producer handoffs, not re-observed here.

## Limits / not claimed

- No fresh live GL run of the combined bud + carry + real-geometry fixture in
  this slice; lane 51 QA runs the combined live sweep against the frozen pin
  in `dependency-ready.json`.
- Lane 48: blue acquisition staged; converted bud model not drawn; per-bud
  count N not yet propagated through the lane-44 bridge.
- Lane 49: no native water query (`SeaMgr` semantics not reproduced); elec
  leaf/gate use approximate materials; water boxes are unit-local.
- Lane 50: re-roll/restart runs, higher frame-budget fixture PASS string, and
  full #186 sign-off remain open.
- No ADMIT, no default-branch/tag/force pushes, no species-wave writes.

## QA pin

Immutable artifact: `output/workflow/integration-speedup/l74/dependency-ready.json`
(root/native full pins, build hash + provenance, tests, carried runtime
evidence, exact lane 51 launch instructions). Lane 51 (`muse-cave51`,
issue #489) resumes on its preserved session via the controller once this pin
is published; its `muse-cave50` dependency clears only through the validated
receipt path.
