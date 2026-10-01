# Damagumo stage-table row for the P1 boot (issue #742)

Lane `damagumo-stage-table-row-native` (generation 2). Owner: Codex through
shared account 4laric. Coordinator blocked-producer follow-up for the stopped
consumer `p2-challenge-ch-muki-damagumo-p1` (#740, gen 2): scaffolding
committed but no run attempted because the engine table names no
ch_MUKI_damagumo (#730 empty; #705 selector only). No live damagumo-table
owner exists.

## Scope (own ONLY these new disjoint files)

- `native/pc_port/pc_p2_challenge_damagumo_stage.{h,cpp}`: pinned damagumo
  row + lookup, mirroring the engine `P2ChallengeStageRow` shape
  field-for-field (`pc_port/pc_bbft.cpp`, lane #675).
- `native/tools/p2_damagumo_stage_table_fixture.cpp`:
  standalone resolution fixture (see below).
- `scripts/build_p2_damagumo_stage_table.py`: private build + provenance.
- `docs/PIKMIN2_DAMAGUMO_STAGE_TABLE_ROW.md`: this file.
- `experimental/pikmin2_damagumo_stage_table_row.py`: pins + log observer.
- `tests/test_pikmin2_damagumo_stage_table_row.py`: fail-closed tests.

`#730` uncreated files untouched; `#736` untouched. SERIALIZED: landing the
row into the engine table (`pc_bbft.cpp`) and CMake membership is follow-on
work requiring #186 review (specified below, not done here).

## Pinned contract (#740 source)

cave `ch_MUKI_damagumo`, path
`user/Mukki/mapunits/caveinfo/ch_MUKI_damagumo.txt`, sha256
`c6f2dede22acb37cb0d939b1ee9670b103dc9408d3c9fe100000482891fefa9e`,
ui 6, table order 9, 1 floor, 150 s, roster row 2 leaf 50, bitter 0 /
spicy 1, legacy 0.0, treasure field 0.

## Fixture behavior

Standalone TU (row + lookup + C++ runtime only): `--cave-id` resolves by
exact id (`P2_DAMAGUMO_STAGE_RESOLVED` with roster/bitter/spicy/legacy/
treasure/source-prefix fields) or refuses anything else
(`P2_DAMAGUMO_STAGE_REFUSED`); `--expect-resolved` turns mismatches into
exit 1; `--captain-down` exercises the #632 negative path (exit 86,
`P2_FIXTURE_CAPTAIN_DOWN`). Captain inputs are SIMULATED and labelled;
guard vendored verbatim from `scripts/p2_fixture_captain_guard.h`
(sha256 `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`).
All six gates stay UNTESTED (`P2_DAMAGUMO_STAGE_GATES`). No engine boot,
no gameplay.

## Verification (this host)

- `tests/test_pikmin2_damagumo_stage_table_row.py`: 8 passed, 5 subtests
  (row pin, drift rejections, guard-header pin, good/refused/empty logs,
  captain-down block, wrong-value non-resolution).
- Leased private build of the untouched native tree (configure + full
  `pikmin_pc` link + `ninja -n` no-work) with exe SHA-256 recorded.
- Standalone fixture compiled `-Wall -Wextra -Werror`; resolution matrix
  (resolve/refuse/captain-down) green with marker-log hashes.

## #186 decision (recorded)

Shared edits (engine table row landing + CMake membership) are NOT made
here; the serialized integration follow-on is specified for owner review:
https://github.com/4laric/pikmin-randomizer/issues/186#issuecomment-5718272035 (filed, pending decision).

## Serialized integration follow-on (not this slice)

Land the pinned row into `pc_port/pc_bbft.cpp`
(`kP2ChallengeStages[]` + table order) and register the fixture TU in
`CMakeLists.txt`, both owned by #736, then re-run this fixture against the
engine-linked build. Downstream consumer: `p2-challenge-ch-muki-damagumo-p1`
(#740). No other edits. No ADMIT.

## Hashed packet

`out/damagumo-stage-table-packet.json` names exact commits/hashes (native
base 93603dc2) and the downstream consumer #740.
