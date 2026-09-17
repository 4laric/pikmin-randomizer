# NARI 02tile + 03toy stage rows (#769, consumers #537 + #746)

Implementation owner: Codex through shared account 4laric. Disjoint new
module following the accepted MUKI rows #748 pattern; no shared-file edits.

## Provenance (live decode, never invented)

- ch_NARI_02tile: #705 landing adapter record (ui 4, order 19, 2 floors
  200.0 + 150.0 s, bitter 0 / spicy 5, row 0 = 50 leaf red).
- ch_NARI_03toy: #743 gap record (ui 5, order 2, 2 floors 100.0 + 150.0 s,
  bitter 2 / spicy 2, row 2 = 100 flower blue).
- Cross-checked against the P0 catalogue pins before commit.

## Owned files (this slice only)

- native/pc_port/pc_p2_challenge_nari_stages.h / .cpp (self-contained rows;
  this base predates the shared #651 host-mode module, so nothing is
  borrowed or duplicated; lookup by ui_index; boot pops = roster sums).
- native/tools/p2_nari_stage_table_fixture.cpp (argv select, guard ticks,
  self-test + negative test, fail-closed unknown/unguarded).
- scripts/build_p2_nari_stage_table.py (leased-build + fixture-build driver).
- experimental/pikmin2_nari_stage_table_rows.py (pin checker + log observer).
- tests/test_pikmin2_nari_stage_table_rows.py (6 tests).
- docs/PIKMIN2_NARI_STAGE_TABLE_ROWS.md (this file).

## Proof

Leased private build (pikmin_pc + ninja no-work, exe hash), fixture
provenance built, guarded fixture boots: both rows resolve with exact pops
(02tile 50, 03toy 100), guard self-test + negative green, unknown refused,
no abort/captain-down. Captain safety #632 vendored semantics.

## Serialized follow-on (NOT this slice)

pc_bbft.cpp / CMakeLists.txt integration lands only via #186 review +
integrator; this slice changes no shared target. Consumers #537 (02tile)
and #746 (03toy) adopt after that landing. No ADMIT.
