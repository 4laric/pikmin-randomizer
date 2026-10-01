# Rover challenge stage table row (issue #734)

Lane `rover-stage-table-row-native`, generation 2. Tooling-only provider
slice for the persistence call site (#561 consumer): no family FSM work, no
shared-file edits, no ADMIT, no gameplay PASS claim. Consumer integration
(BigFoot-style runtime) is a later bounded slice.

## What this delivers

A pinned, engine-free `ch_MAT_route_rover` (P2 Challenge 28, ui 27) stage
row plus fail-closed lookup, mirroring the `P2ChallengeStageRow` field
layout read-only:

- `native/pc_port/pc_p2_challenge_rover_stage.h` / `.cpp` — the single
  pinned row (cave path, source sha `e03eb33a...`, ui 27, table order 21,
  1 floor, 90.0 s, 3x20 starting roster, sprays 2/2, legacy 300.0) with
  `roverRow()` / `roverLookup()` / `roverRowMatches()` / `roverRowCount()`.
  Compiles with `-Ipc_port` only.
- `native/tools/p2_rover_stage_table_fixture.cpp` — guarded standalone
  fixture: 26 checks proving field-exact resolution, unknown/malformed key
  refusal, and tamper rejection, emitting `P2_ROVER_STAGE_RESOLVED` /
  `P2_ROVER_STAGE_REFUSED` markers.
- `scripts/build_p2_rover_stage_table.py` — compile+run+marker-validate
  driver recording executable/log hashes.
- `experimental/pikmin2_rover_stage_table_row.py` + `tests/` — contract,
  receipt-key-free marker grammar validator (9 tests).
- This file.

## Why a separate module (not an edit)

The engine boot table (`pc_bbft.cpp kP2ChallengeStages`) carries only
`ch_NARI_01kusachi`, so `--experimental-challenge-stage ch_MAT_route_rover`
resolves to nothing. The persistence fixture table already lists the rover
row, but that table is fixture-scoped data, not the boot path. Appending
the row to the boot table plus CMake membership is SERIALIZED follow-on
work owned by the #728/#725 lines — this lane must not touch
`pc_bbft.cpp` or `CMakeLists.txt`.

## SERIALIZED integration follow-on (specified, not executed)

1. Request owner #186 review with this packet (row values, hashes,
   fixture evidence below); land only on explicit approval.
2. Append the pinned row to `kP2ChallengeStages` in `pc_bbft.cpp` and add
   the provider sources to the owning CMake target (owner #728 line).
3. Re-run the guarded fixture against the integrated tree plus the
   `#730`-line boot-selection probe.

## Stage-flag boot resumption (documented behavior, not changed)

The engine boot records `--experimental-challenge-stage <cave_id>` via the
`P2_CHALLENGE_STAGE_FLAG cave=<key>` marker and resolves it through
`pc_p2_challenge_stage_selected()` → `pc_p2_challenge_stage_lookup()`.
With the rover row integrated, `--experimental-challenge-stage
ch_MAT_route_rover` resolves to ui 27 / 1 floor; today it resolves to
nothing (exit path unchanged). P1 `--experimental-challenge-level` is a
different namespace and stays untouched. No save-root, memory-card, or
progression semantics were altered here.

## #186 review gate

Integration (above) requires #186 review first. Status at handoff: NOT
requested yet — this packet is the review input. No decision is recorded
as granted; do not land on silence.

## Captain safety #632

This fixture boots no game world, so there is no Navi to observe (same
construction as the #727 load proof). Guard header
`scripts/p2_fixture_captain_guard.h` is adopted by reference for any future
game-world run of this harness; recorded sha256 `d2f678c9...` (full hash in
the handoff evidence record). No blanket invincibility exists anywhere in
this slice.

## Validation evidence (this turn, no runtime)

- 26/26 standalone native checks pass (`-Wall -Wextra -Werror`, exit 0).
- 9/9 contract tests pass.
- Executable + marker-log hashes recorded by the build driver; private
  CMake configure + `ninja -n` dry run recorded per the handoff.
- `scripts/check_p2_handoff_gates.py` is family-gate scoped and has no
  rows for this tooling lane; the six gates stay UNTESTED by construction.

## One exact reproduction command

```
cd <rover-stage-table-row-native-root worktree>
py -3.12 scripts/build_p2_rover_stage_table.py --native <native-worktree> --output <new-private-dir>   # built, 26/26
py -3.12 -m pytest tests/test_pikmin2_rover_stage_table_row.py -q   # 9 passed
```
