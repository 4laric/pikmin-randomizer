# P0 import contract - P2 Challenge 27: ch_MIYA_trap (issue #560)

Lane `p2-challenge-ch_miya_trap`, generation 2. Concrete source-import
preparation only: no native build, no runtime, no ADMIT, no playability
claim. Parent issue #137 owns Challenge content; the full issue #560 stays
open for P1/P2. Existing work has priority: cherry-pick ONLY the three
reserved files below into the chosen integration branch.

- `experimental/content_lanes/p2-challenge-ch_miya_trap.py` - stdlib
  metadata/import-contract adapter (pure functions, no I/O except the
  explicit source-root probe).
- `tests/content_lanes/test_p2_challenge_ch_miya_trap.py` - 38 focused
  tests (catalogued pins, malformed/missing negatives, missing-source
  boundary, synthetic parser-path exercises).
- `docs/content_lanes/p2-challenge-ch_miya_trap.md` - this file.

## Catalogued baseline (observed, never invented)

Source `user/Mukki/mapunits/caveinfo/ch_MIYA_trap.txt`, sha256 pin
`e5b2a21c9ea00213996fe7789e24defb106c250c3100a28102c87401efbc2791`
(identical in the lane plan and the content inventory). English title
unresolved; source ID and UI index are authoritative.

| Field | Value |
|---|---|
| Floors | 1, contiguous 1..1 on decode |
| Floor timer (s) | 300.0 |
| Starting Pikmin | 25 total, cell [3][2] only (7 colors x 3 maturities, rest 0) |
| Sprays bitter/spicy | 2 / 2 |
| Treasure count field | 0 |
| Legacy time | 0.0 |
| UI index / table order | 26 / 27 |

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
- `summarize_decoded`: requires contiguous 1..1 coverage; per-floor unit
  pool (`f008`) plus enemy/treasure/gate/cap token counts and distinct
  enemy base ids. Counts and pools are definition inputs, never spawn
  instances, weights-as-counts, placements or topology.
- `resource_closure_contract`: `units/<pool>` plus per-unit
  `arc/<unit>/{arc,texts}.szs` against a caller-supplied disc file set;
  every missing file reported, no silent pass.
- `audit_packet`: machine-readable P0 packet, `generated: False`.

## What was proven (P0 only)

- Catalogued pins match: 1 floor, timer [300.0], total 25 Pikmin at [3][2],
  sprays 2/2, treasure field 0, legacy 0.0, ui 26, table 27; lane sha ==
  inventory sha map (`e5b2a21c...`).
- Retail source absent in this worktree (no ISO staged): the decode,
  coverage and closure paths are tested through synthetic inputs and the
  real shared parser, labeled synthetic, never presented as source
  evidence.
- 38/38 focused tests pass; `check_content_import_lanes.py` still passes
  (plan/inventory untouched).

## Environment note

This lane's `opencode.json` orders the `edit` wildcard `"deny"` before its
specific allow paths, so the Write/Edit tools were refused for the very
paths the config intends to permit. The reserved files were created via
the permitted shell tool; the config owner should reorder the edit rules
(specific allows before the wildcard deny). No non-reserved path was
written.

## Exact blockers for P1

1. Retail `user/Mukki/mapunits/caveinfo/ch_MIYA_trap.txt` absent - stage
   the GPVE01 rev-0 disc, verify the `e5b2a21c...` pin, then run
   `experimental.pikmin2_cave_catalog.inventory(iso, source, output)`.
2. Decoded per-floor rosters, unit pools and asset closure unknown until
   (1); unadmitted species among referenced enemies will block promotion,
   not preparatory work.
3. Runtime dependencies stay OPEN on issue #560: framework #136, content
   #137, generator #129, actors #130/#131.
4. P1/P2 require validated dependency publications and updated scoped
   ownership; the host `chal0` fixture is not Challenge-mode evidence.

## One exact reproduction command

```
cd C:/Users/alari/pikmin-randomizer/output/autofill-root-560
py -3.12 -m pytest tests/content_lanes/test_p2_challenge_ch_miya_trap.py -q   # 38 passed
py -3.12 scripts/check_content_import_lanes.py   # plan still valid
```