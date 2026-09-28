# ch_MAT_yellow_purple_white P1 private runtime import (lane p2-challenge-ch-mat-yellow-purple-white-p1, #552)

P1 layer for the ch_MAT_yellow_purple_white challenge stage (`ui_index` 19).
The P1 module `experimental/content_lanes/ch_mat_yellow_purple_white.py` sits on
top of the reviewed P0 adapter and adds manifest validation plus private
run-layout staging. It never forks the parser: the P0 adapter (reserved
hyphenated filename) is loaded by path and its baseline cross-check, real-source
pin and forbidden-key guards are reused verbatim.

## Contract (from the canonical baseline, read at runtime)

- Source stage key `ch_MAT_yellow_purple_white` (never the display title).
- `floors = 1`, `floor_seconds = [230.0]`, `bitter_sprays = 0`,
  `spicy_sprays = 2`, `ui_index = 19`.
- Native color/maturity roster preserved verbatim (7x3 matrix; total 60).
- Runtime-shaped keys (`placements`, `actors`, `spawn_layout`, `scores`,
  `results`) are refused; stage definitions are not runtime state.

## P1 import path

- `validate_p1_manifest(manifest, root)` — fails closed on any drift from the
  P0 baseline (identity, floors, timers, roster, sprays, ui_index, legacy time);
  refuses fabricated runtime keys.
- `stage_run_layout(manifest, output, root, native_root)` — writes
  `stage-manifest.json`, `p1-input-package.json` (schema
  `p2-challenge-ch_mat_yellow_purple_white-p1-v1`, P0 source pin, host-mode
  module hashes) and `run-plan.json` into a private run layout, each with a
  SHA-256 record.
- `p1_main(manifest_path, output, root, native_root)` — CLI entry.
- `host_mode_pins(native_root)` — hash-pins the integrated host-mode consumer
  module `native/pc_port/pc_p2_challenge_mode.{h,cpp}`.

## Integrated host-mode contract consumed

`native/pc_port/pc_p2_challenge_mode.cpp` (#651) provides stage select by
`ui_index`, `applySquadAndSprays`, the `mTimeLimit` countdown with per-floor
extension, and the retry/reset boundary, emitting
`P2_CHALLENGE_MODE_<WHAT>` markers. The run plan records this contract and the
captain-safety #632 ordering: guard FIRST after idle
(`orimaDead`/`NaviDead`/HP<=1, `CAPTAIN_DOWN` + BLOCKED, parked captain),
then observe the live starting squad and any collision/routes/actors.

## Captain safety #632

Mandatory for any observed tick: adopt `scripts/p2_fixture_captain_guard.h`
(sha256 `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`) or
a tested equivalent; park the captain outside attack reach when not testing
captain hits; no blanket invincibility; protected observation is labelled and
cannot prove captain damage.

## Honest status / remaining blockers

- The P1 import path, validation and staging are delivered and unit-tested.
- The available shared host-mode fixture (`#656` harness) executes only the
  standalone host-mode state machine over a labelled SAMPLE table under the
  #632 guard. It is explicitly NOT an engine boot: it cannot select this retail
  stage by `ui_index`, and it observes no collision, routes, actors or captain
  health. Engine stage boot for challenge stages depends on the integrated
  #672/#695 boot path owned by other lanes.
- All six gates stay UNTESTED unless genuinely observed; no playability claim
  beyond observed evidence; no ADMIT, no ledger writes.

Tests: `tests/content_lanes/test_ch_mat_yellow_purple_white.py` (P1 boundary,
staging, host-mode pin and CLI cases) alongside the P0 suite.
