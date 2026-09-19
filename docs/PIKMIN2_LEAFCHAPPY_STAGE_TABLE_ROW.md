# P2 leafchappy stage-table row provider (issue #774)

Lane `challenge-2-leafchappy-bridge-row`, cross-partition provider scope for
the challenge-2 recovery; downstream blocked consumer
`p2-challenge-ch-abem-leafchappy-p1` (#550), whose first dependency is bridge
stage-table registration for ch_ABEM_LeafChappy (the bridge table holds only
ch_NARI_01kusachi). No bridge-row provider exists anywhere; this lane is it.
Implementation owner: Codex through shared account `4laric`.

## Owned files (NEW, disjoint)

- `native/pc_port/pc_p2_challenge_leafchappy_stage.h` / `.cpp` - pinned
  leafchappy row + fail-closed lookup (engine-free, `-Ipc_port` only).
- `native/tools/p2_leafchappy_stage_table_fixture.cpp` - guarded
  standalone replacement fixture (compiled directly with g++, never CMake).
- `scripts/build_p2_leafchappy_stage_table.py` - standalone build/run
  driver with marker validation.
- `experimental/pikmin2_leafchappy_stage_table_row.py` - pinned row,
  log validator, contract.
- `tests/test_pikmin2_leafchappy_stage_table_row.py` - focused tests.
- `docs/PIKMIN2_LEAFCHAPPY_STAGE_TABLE_ROW.md` - this doc.

## Pinned row (from the lane-plan source contract, read-only)

| Field | Pinned value |
|---|---|
| cave_id / table_order / ui_index | ch_ABEM_LeafChappy / 4 / 17 |
| source | user/Mukki/mapunits/caveinfo/ch_ABEM_LeafChappy.txt |
| source_sha256 | 49cc9076cede949786025b3bcd08ce60362096d8fe8f8b5330c725de4acd2baf |
| floors / floor_seconds | 2 / [85.0, 100.0] |
| starting roster 7x3 | colors 0-2 maturity 0 x10 each, rest 0 |
| bitter / spicy sprays | 1 / 1 |
| legacy_time | 400.0 |
| treasure_count_field | 11 |

Native color/maturity indices are carried as indices, never guessed into
species names. The row mirrors the `P2ChallengeStageRow` field layout
read-only; shared tables are never modified here.

## What the fixture proves (and only this)

The pinned row resolves by cave_id with field-by-field agreement, and
unknown/malformed keys refuse fail-closed. Markers
(`P2_LEAFCHAPPY_STAGE_RESOLVED` + `P2_LEAFCHAPPY_STAGE_REFUSED`) plus a
checks summary; exit 0 only when every check passes. A printed row alone
cannot pass: every claim executes the provider lookup and asserts it.
All six gameplay gates stay UNTESTED; content wiring is the downstream
consumer job (#550). No PASS without observed evidence.

## Captain safety (#632)

Vendored verbatim from `scripts/p2_fixture_captain_guard.h` (sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`);
this fixture boots no game world, so the guard truth table is proven via
`--guard-self-test` (7/7) and the interruption via `--guard-negative-test`
(exit 86 `P2_FIXTURE_CAPTAIN_DOWN`, no PASS, no resolution). The canonical
header is adopted by reference for any future game-world run; no blanket
invincibility anywhere. Guard self-test/negative logs recorded in the
lane provenance.

## Verification

- `py -3.12 -m unittest tests.test_pikmin2_leafchappy_stage_table_row`
- `py -3.12 scripts/build_p2_leafchappy_stage_table.py --native <native>
  --output <new-private-dir>` -> status built, fixture markers verified,
  guard self-test + negative verified, provenance with executable/log
  hashes.

## Diagnosis + verification scope (producer contract)

The engine boot-table integration itself stays serialized: the named
integration callsites (`pc_p2_challenge_mode.cpp:selectByUiIndex`,
`pc_bbft.cpp:pc_p2_challenge_stage_lookup`) were verified ABSENT at the
pinned native base `ab81cf5d` (git grep, no hits), as is the standalone
build-membership fixture (NOT CMake). The consumer command (fixture run
emitting `P2_LEAFCHAPPY_STAGE_RESOLVED`, expecting ui-17 resolution with
unknown-key refusal) is proven against the lane row. Serialized
`pc_bbft.cpp`/CMake integration specified as follow-on with #186 review.

## SERIALIZED integration (follow-on, NOT done here)

Appending this row to `pc_bbft.cpp kP2ChallengeStages` and wiring the
CMake target needs owner #186 review first (shared pc_bbft.cpp /
CMakeLists.txt untouched here). The #186 decision is recorded in the
handoff; landing waits on it. No ADMIT.

## Native commits and compiled evidence

Recorded in the lane handoff: native base `ab81cf5d`, lane native
commit(s), private build directory, `fixture.exe` SHA-256, marker log
SHA-256, guard self-test/negative logs. Standalone fixture: no CMake
membership, so ninja no-work is N/A by construction (same as accepted
#734).
