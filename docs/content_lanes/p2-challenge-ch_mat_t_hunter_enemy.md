# P0 import contract — ch_MAT_t_hunter_enemy challenge (lane p2-challenge-ch_mat_t_hunter_enemy, issue #543)

Generation-2 P0 slice. Concrete source-import preparation only: no native
build, no runtime, no ADMIT, no playability claim. The full-content issue
#543 stays open for P1/P2. Reserved implementation:
`experimental/content_lanes/p2-challenge-ch_mat_t_hunter_enemy.py`
(adapter, stdlib only, dependency-free pure functions) plus
`tests/content_lanes/test_p2_challenge_ch_mat_t_hunter_enemy.py`
(17 focused tests).

## Source identity

- Source ID `ch_MAT_t_hunter_enemy` (P2 Challenge 11); retail definition
  `user/Mukki/mapunits/caveinfo/ch_MAT_t_hunter_enemy.txt` (US GPVE01
  revision 0, shift_jis caveinfo text). English title unresolved; source
  ID, table_order 10 and ui_index 10 are authoritative.
- The definition file is NOT available in this worktree. Exact missing
  prerequisite: stage a retail US GPVE01 rev-0 disc (or its extracted
  `user/Mukki` tree) and decode with
  `experimental.pikmin2_cave_catalog.parse` against the inventory enemy
  universe and pellet-catalog treasure universe. No values are invented
  in its place.

## Catalogued baseline (validated, not reimplemented)

From `docs/PIKMIN2_CONTENT_INVENTORY.json` challenge entry plus the
lane-plan entry in `docs/PIKMIN_CONTENT_IMPORT_LANES.json`:

- Floors: 5. Per-floor timers: 50.0, 75.0, 65.0, 40.0, 70.0 (sum 300.0).
- Pikmin roster (7x3 native color/maturity matrix, preserved exactly):
  rows 1 and 4 hold `[0, 0, 5]`, all other rows `[0, 0, 0]` — 10 total.
  The matrix is preserved, never reinterpreted or renormalized.
- legacy_time 400.0 against the 300.0 floor-timer sum: observed
  discrepancy +100.0, reported as a finding with both values preserved.
  P1 reconciles against the source; nothing is "fixed" here.
- bitter_sprays 2, spicy_sprays 3, treasure_count_field 0.
- Unlike story caves, the catalogued challenge baseline is stage-level
  metadata only: no per-floor enemy/treasure rosters are catalogued, so
  the adapter emits no placements, weights, topology or schedules.

## Hash record

- Lane-plan `source_sha256` pin
  `dc3734362430697c2a4dbce67b447efe876c60934cb282bc10051a3cdb2f5a82`
  is carried as the P1 acceptance hash: when the source lands,
  `source_prerequisite()` hashes the observed bytes and compares them to
  this pin (match required before decode counts as source evidence).
- The pin itself is format-checked (64-hex) and equality-checked against
  the P0 record; it is quoted, not re-observed, until P1.

## Exact native/framework blockers

1. Missing retail source (above) — blocks weighted-definition decode,
   unit pool asset closure and any placement/runtime work.
2. Timer discrepancy (+100.0) unresolved pending source decode; the
   legacy total and the floor timers may measure different things.
3. Full-content dependencies stay OPEN on issue #543 (#136, #137, #129,
   #130, #131; existing content owner #137).
4. No shared-file changes in this slice: global parsers/schema, species
   or other levels untouched. Any future shared need goes through scoped
   review with the owning lanes.

## Implementation packet for P1

Consume `audit_stage()` output (schema
`p2-challenge-ch_mat_t_hunter_enemy-p0/1`, `generated: False` with stated
limitations) plus `source_prerequisite()`. When the source lands,
`decode_source_text()` wraps the shared `pikmin2_cave_catalog.parse`;
per-floor `f008` unit pools then resolve under
`user/Mukki/mapunits/units/` with `arc`/`texts.szs` closure per unit.
P1 then needs a private root/native pair, leased build, starting squad,
centred 960x540 startup and natural acceptance per the lane phases —
none of which is claimed here. All runtime gates UNTESTED; fixture
adoption N/A (kind=tooling handoff).

## Verification

`py -3.12 -m pytest tests/content_lanes/test_p2_challenge_ch_mat_t_hunter_enemy.py -q`
? 17 passed (positive pins on the real catalogued entry; identity/shape/
timer negatives; missing-source prerequisite and malformed-source
decode boundaries).
