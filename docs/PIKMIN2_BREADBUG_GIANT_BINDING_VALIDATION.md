# Breadbug lane batch 3: Giant/nest display-binding validation (#220)

Follows batch 2 (commit `23c7f8a`). The native track unblocked the Giant/nest
display dependency (native `7faa644` / root `f9f0839`, issue #229; root doc
`output/p2-root-integration/docs/PIKMIN2_GIANT_BREADBUG_RUNTIME_ACCEPTANCE.md`).
This batch validates that binding against lane assets and records the evidence.
Implementation owner: Codex on shared 4laric. No root-worktree, native, beetle
or Mamuta files were modified.

## Binding provenance (verified, not assumed)

Root profile `output/p2-root-integration/output/p2-giant-breadbug-binding/profile-a`
carries 11 models. Byte-for-byte hash comparison against this lane's extraction
(`output/p2-lifecycle-batch/breadbug-lane-03`) confirms all 11 are the lane's
converted files: 5 `lane_ootake_wait1_*` + 5 `lane_ootake_move1_*` =
`OoPanModoki/wait1_*.mod`/`move1_*.mod`, and `lane_nest_nest.mod` =
`PanHouse/nest.mod`. `lane_profile_sha256` equals the batch-2 install profile
(`e32a67d9…c2061d`). Binding clip frame sets and durations match the lane
sampled poses (wait 59f, move 54f).

## Runtime validation (local rerun of the root acceptance)

`experimental.pikmin2_giant_breadbug_runtime run` (root module, unmodified)
with the frozen fixture `fixture01/build/fixture.exe`
(SHA-256 `44324475…f1e8b9`) and workspace-local P1 assets, output
`output/p2-root-integration/output/p2-giant-breadbug-runtime/kimi-validation-01`:

| Mode | Checks (completion/setup/draw/reset/reload/ground/no-small/no-rewards) | Result |
|---|---|---|
| wait | 8/8 | PASS |
| move | 8/8 | PASS |
| nest | 8/8 | PASS |
| disabled | 8/8 (no setup/draw, as required) | PASS |

- Baseline assertions in every run: `actors=0 cargo=0 repairs=1`, with the
  native `unchanged_actors_cargo_repairs` PASS line — the display binding
  changes no gameplay counts and creates no cargo/receipt.
- Display placement id 229001 at (103.058197, 30, 1906.487915), yaw 0 — an
  engineering ground sample near the captain, not a source P2 placement.
- Captures inspected visually: Giant body/face clearly visible in wait and
  move, leaf-covered nest mound visible in nest mode, model absent after
  reset, restored after reload. PNG/PPM hashes in `result.json`.
- Existing GX depth-texture warning appears in all modes including disabled
  (pre-existing engine behavior, not caused by the binding).

The interactive `Play-wait/move/nest.cmd` launchers were not driven by UI
automation here (they hold a window open for manual QA); the identical
stage/fixture/profile was exercised through the root module's noninteractive
`run` path, which is the same acceptance flow minus the keep-open marker.

## Explicitly not validated (still root-owned / unimplemented)

Giant actor registration, cargo contest, Purple-only press, boss behavior,
owner-linked nest storage/recovery/save, animated texture-matrix fidelity.
A display binding is not an actor.

## Tests

New `tests/test_pikmin2_breadbug_giant_binding.py` (8 tests): binding↔lane-03
byte correspondence and lane-profile tracking, clip frame/duration parity with
lane poses, all-mode check completeness, setup/draw/reset/reload marker counts,
unchanged actors/cargo/repairs assertions, engineering-placement labeling, and
capture recording. Full suite result recorded in the issue comment.
