# P0 import contract — P2 Challenge 03: ch_MAT_conc_cave (issue #536)

Lane `p2-challenge-ch_mat_conc_cave`, generation 2. Concrete source-import
preparation only: no native build, no runtime, no ADMIT, no playability
claim. Parent issue #137 owns the Challenge content; the full issue #536
stays open for P1/P2. Existing work has priority: cherry-pick ONLY the
three reserved files below into the chosen integration branch.

- `experimental/content_lanes/p2-challenge-ch_mat_conc_cave.py` — stdlib
  metadata/import-contract adapter (pure functions, no I/O except the
  explicit source-root probe).
- `tests/content_lanes/test_p2_challenge_ch_mat_conc_cave.py` — 38 focused
  tests (catalogued pins, malformed/missing negatives, missing-source
  boundary, synthetic parser-path exercises).
- `docs/content_lanes/p2-challenge-ch_mat_conc_cave.md` — this file.

## Catalogued baseline (observed, never invented)

Source `user/Mukki/mapunits/caveinfo/ch_MAT_conc_cave.txt`, sha256 pin
`b3ae2c41e4719e1c34a86e887847650d9da293b992b7899c5559f60f35b1d5fe`
(identical in the lane plan and the content inventory). English title
unresolved; source ID and UI index are authoritative.

| Field | Value |
|---|---|
| Floors | 3, contiguous 1..3 on decode |
| Floor timers (s) | 70.0, 100.0, 50.0 |
| Starting Pikmin | 2 total, cell [4][2] only (7 colors x 3 maturities, rest 0) |
| Sprays bitter/spicy | 0 / 0 |
| Treasure count field | 0 |
| Legacy time | 500.0 |
| UI index / table order | 2 / 11 |

Enemy universe: 102 inventory `internal` names. Treasure universe: 188
`us/runtime/otakara` entries. Challenge stages catalogue no per-floor
enemy/treasure rosters; rosters arrive only with the decoded retail
definition.

## Adapter contract

- `find_lane_entry` / `find_stage_entry`: fail closed on missing entries.
- `audit_metadata`: validates floor count, timer list (positive finite),
  7x3 population matrix (nonnegative ints, bools rejected), sprays,
  treasure field, legacy time, ui/table indices. Reports totals only.
- `verify_source_bytes`: sha256 pin check; drift fails loudly.
- `source_prerequisite`: exact missing prerequisite while unstaged
  (GPVE01 rev-0 disc + `catalog.inventory(iso, source, output)`); reports
  observed hash when a source root is supplied.
- `decode_source_text`: shared `pikmin2_cave_catalog.parse`, imported and
  never edited; fail-closed on malformed/unknown input.
- `summarize_decoded`: requires contiguous 1..3 coverage; per-floor unit
  pool (`f008`) plus enemy/treasure/gate/cap token counts and distinct
  enemy base ids. Counts and pools are definition inputs, never spawn
  instances, weights-as-counts, placements or topology.
- `resource_closure_contract`: `units/<pool>` plus per-unit
  `arc/<unit>/{arc,texts}.szs` against a caller-supplied disc file set;
  every missing file reported, no silent pass.
- `audit_packet`: machine-readable P0 packet, `generated: False`.

## What was proven (P0 only)

- Catalogued pins match: 3 floors, timers, total 2 Pikmin at [4][2],
  sprays/treasure/ui/order fields, lane sha == inventory sha map.
- Retail source absent in this worktree (no ISO staged): the decode,
  coverage and closure paths are tested through synthetic inputs and
  the real shared parser, labeled synthetic, never presented as source
  evidence.
- 38/38 focused tests pass; `check_content_import_lanes.py` still passes
  (plan/inventory untouched).

## Exact blockers for P1

1. Retail `user/Mukki/mapunits/caveinfo/ch_MAT_conc_cave.txt` absent —
   stage the GPVE01 rev-0 disc, verify the `b3ae2c41...` pin, then run
   `experimental.pikmin2_cave_catalog.inventory(iso, source, output)`.
2. Decoded per-floor rosters, unit pools and asset closure unknown until
   (1); unadmitted species among referenced enemies will block promotion,
   not preparatory work.
3. Runtime dependencies stay OPEN on issue #536: framework #136, content
   #137, generator #129, actors #130/#131.
4. P1/P2 require validated dependency publications and updated scoped
   ownership; the host `chal0` fixture is not Challenge-mode evidence.

## One exact reproduction command

```
cd C:/Users/alari/pikmin-randomizer/output/content-p0-536
py -3.12 -m pytest tests/content_lanes/test_p2_challenge_ch_mat_conc_cave.py -q   # 38 passed
py -3.12 scripts/check_content_import_lanes.py   # plan still valid
```
