# Challenge 03toy stage-table row (issue #752)

Lane `toy-stage-table-row-native`. Owner: Codex through shared account 4laric.
Registers the `ch_NARI_03toy` boot-table row for the downstream #746 P1 lane.
SERIALIZED: the `pc_bbft.cpp` table integration + `CMakeLists.txt` membership
are owned by the #710/#736 line and are NOT implemented here.

## Row (pinned from #746 / #540 import baseline)

| field | value |
|---|---|
| cave_id | `ch_NARI_03toy` |
| source | `user/Mukki/mapunits/caveinfo/ch_NARI_03toy.txt` |
| source sha256 | `d74b49ac3d9a2388288b9cb868dd8717ff893fd522453b309740519be841f03c` |
| ui_index / table_order | 5 / 2 |
| floors / seconds | 2 / [100.0, 150.0] |
| roster | total 100 at cell [2][2] |
| sprays bitter/spicy | 2 / 2 |
| legacy / treasure | 0.0 / 0 |

## Owned files

- `native/pc_port/pc_p2_challenge_toy_stage.h` + `.cpp`: standalone row +
  lookup + marker emission, engine-free. The fixture TU compiles the `.cpp`
  in as its single definition site (no CMake target).
- `native/tools/p2_toy_stage_table_fixture.cpp`: guarded fixture (self-test,
  negative test, unknown refusal, window + resolution run, PASS).
- `scripts/build_p2_toy_stage_table.py`: private leased build/run helper.
- `docs/PIKMIN2_TOY_STAGE_TABLE_ROW.md`,
  `experimental/pikmin2_toy_stage_table_row.py`,
  `tests/test_pikmin2_toy_stage_table_row.py` (9 focused tests green).

## Evidence status (this turn)

- Row unit proof (no lease needed): standalone `g++` compile of the row TU +
  test main, exit 0; markers `P2_TOY_STAGE_TABLE` / `P2_TOY_STAGE_RESOLVED`
  (ui 5, floors 2, roster_total 100); unknown key refused
  (`P2_TOY_STAGE_REFUSED reason=unknown-stage`); `ROW_UNIT_PASS`.
- Full fixture build/run (leased `pikmin_pc` graph + window boot + marker log)
  BLOCKED on build capacity: pool 4/4 held at turn time, request queued
  (`toy-stage-table-row-native:2:build:...output/toy-stage-table-build`).
  The committed helper runs it unchanged once a slot frees.
- Guard `scripts/p2_fixture_captain_guard.h` sha256
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`
  (vendored read-only in the fixture; trip -> BLOCKED/86).

## Serialized follow-on (specified, not implemented; blocked)

`#710/#736` line owns `native/pc_port/pc_bbft.cpp` + `native/CMakeLists.txt`:
add the 03toy row to the boot table (or route lookup to this module) and add
`pc_port/pc_p2_challenge_toy_stage.cpp` to the target; land only after #736
releases those files, with #186 review. Downstream #746 boots 03toy after that.
Machine-readable spec in `integration_followon()`.

## Acceptance / gates

All six runtime gates UNTESTED. No other edits; no ADMIT.
