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

## Generation-2 proof (this turn)

- Native c2f30c31 (clean): module + fixture committed, no shared edits.
- Leased production build passed (ninja pikmin_pc exit 0, source identity
  unchanged); nectar.exe `8ea76b31...`; dry-run `ninja: no work to do.`
- Fixture provenance built; fixture.exe
  `12b65bd5cd49dbe0783361e4942ac0ccba528e3a0d2869d00a2ba4ea91adfd57`.
- Guarded boots: 02tile RESOLVED pops 50, 03toy RESOLVED pops 100
  (both-log `3807c6cd...`); self-test exit 0; negative exit 86; unknown ui
  exit 2; --no-guard exit 2; zero captain-down. Root checker VERDICT PASS
  (observer-verdict `8eff30e5...`).
- Guard: vendored #632 semantics (canonical header sha256 d2f678c9...).
- Serialized follow-on unchanged: pc_bbft.cpp/CMakeLists.txt via #186 +
  integrator; consumers #537 + #746 adopt after landing. No ADMIT.
