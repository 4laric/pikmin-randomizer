# P2 tutorial stage-table row provider (issue #754)

Lane `tutorial-stage-table-row-native`, blocked-producer follow-up for the
stopped consumer `p2-challenge-ch-abem-tutorial-p1-runtime-obs` (#534, gen 2):
no engine stage-boot path resolves ch_ABEM_tutorial and no game-linked
guarded fixture exists in its 3 root files. No live tutorial-table/fixture
owner exists. Implementation owner: Codex through shared account `4laric`.

## Owned files (NEW, disjoint)

- `native/pc_port/pc_p2_challenge_tutorial_stage.h` / `.cpp` - pinned
  tutorial row + fail-closed lookup (engine-free, `-Ipc_port` only).
- `native/tools/p2_tutorial_stage_guarded_fixture.cpp` - game-linked
  guarded replacement-main fixture (links the private pikmin_pc graph;
  tutorial row TU compiled in verbatim).
- `scripts/build_p2_tutorial_stage_table.py` - leased private
  configure/build/fixture/run driver with marker validation.
- `experimental/pikmin2_tutorial_stage_table_row.py` - pinned row,
  P2_TUTORIAL_STAGE_SELECT_1 record stager, log validator, contract.
- `tests/test_pikmin2_tutorial_stage_table_row.py` - focused tests.
- `docs/PIKMIN2_TUTORIAL_STAGE_TABLE_ROW.md` - this doc.

## Pinned row (from the #534 P1 import contract, read-only)

| Field | Pinned value |
|---|---|
| cave_id / table_order / ui_index | ch_ABEM_tutorial / 0 / 0 |
| source | user/Mukki/mapunits/caveinfo/ch_ABEM_tutorial.txt |
| source_sha256 | e21f31f7fa5621a5922d9ee54ffb211a8e4f0e797866d70cc1edb98389ab097d |
| floors / floor_seconds | 2 / [100.0, 100.0] |
| starting roster 7x3 | color 1 maturity 0 x50, rest 0 |
| bitter / spicy sprays | 2 / 2 |
| legacy_time | 0.0 |
| treasure_count_field | 0 |

Native color/maturity indices are carried as indices, never guessed into
species names. The row mirrors the `P2ChallengeStageRow` field layout
read-only; shared tables are never modified here.

## What the fixture proves (and only this)

The engine parses `--experimental-challenge-stage ch_ABEM_tutorial`
(`P2_CHALLENGE_STAGE_FLAG`), the run directory carries the staged
`P2_TUTORIAL_STAGE_SELECT_1` record, the engine's own table does NOT
resolve the key (selected stays null: the serialized boundary), and the
lane-owned pinned row DOES resolve it with field-by-field agreement. The
real engine then boots privately under the room-preview path with a
guarded captain (960x540 centred window). All six gameplay gates stay
UNTESTED (`P2_TUTORIAL_STAGE_GATES all=UNTESTED content_wired=0`); content
wiring is the downstream consumer's job (#534). No PASS without observed
evidence. Unguarded runs are refused: the #632 guard is unconditional
(no flag disables it) and a missing room-preview flag or record refuses
before boot.

## Captain safety (#632)

Vendored verbatim from `scripts/p2_fixture_captain_guard.h` (sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`);
runs first after engine idle, before movie/pause/UI returns, readiness or
PASS; orimaDead/NaviDead/HP<=1 -> `P2_FIXTURE_CAPTAIN_DOWN` + BLOCKED (86);
captain parked outside attack reach; no blanket invincibility. Guard
self-test 7/7 plus a negative captain-down test (exit 86, no PASS) run
before every headed boot and recorded in the provenance.

## Verification

- `py -3.12 -m unittest tests.test_pikmin2_tutorial_stage_table_row`
- `py -3.12 scripts/build_p2_tutorial_stage_table.py --native <native>
  --build <private-build> --output <new-private-dir> --expected-native-head
  <commit> --assets <legal-assets> --converted <room105>` -> status built,
  guarded run passed with all markers, provenance with executable/log
  hashes, ninja no-work dry run.

## SERIALIZED integration (follow-on, NOT done here)

Appending this row to `pc_bbft.cpp` kP2ChallengeStages and wiring the
CMake target needs owner #186 review first (shared pc_bbft.cpp /
CMakeLists.txt are owned by the #736 line; untouched here). The #186
decision is recorded in the handoff; landing waits on it. No ADMIT.

## Native commits and compiled evidence

Recorded in the lane handoff: native base `93603dc2` (contains consumer
pin `b805d9c6`), lane native commit(s), private build directory,
`fixture.exe` SHA-256, `runtime.log` SHA-256, ninja `-n pikmin_pc`
no-work output, guard self-test/negative logs, staged record hash.
