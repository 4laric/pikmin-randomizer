# P2 cave tutorial_3 — P0 source decode and import contract (#153)

Lane `cave-tutorial3-p0-source-decode`; work class expansion; phase P0 only.
Implementation owner: Codex through shared account 4laric; executing
contributor Muse Spark 1.3 (worker muse-l60, generation 2). Full content issue
#153 stays OPEN; no playability is claimed anywhere in this packet.

## Completion note (supersedes the blocked first slice)

The first P0 slice (`p2-cave-tutorial_3`, commit `cc47fa8a`) delivered the
isolated import contract but recorded the actual definition bytes as
unavailable ("`output/pikmin2-runtime/` empty", exact retail-ISO prerequisite).
This slice completes that decode: the local retail ISO
`C:\Users\alari\Downloads\PIKMIN2 for GAMECUBE.iso` (995,557,376 bytes) is a
US GPVE01 revision 0 disc (validated by the shared `disc_files` reader; 2768
members) exposing `user/Mukki/mapunits/caveinfo/tutorial_3.txt`. The recorded
prerequisite is satisfied; the decode now runs against real bytes.

## Source identity (observed, not catalogued)

- Cave: `tutorial_3`, definition file
  `user/Mukki/mapunits/caveinfo/tutorial_3.txt`.
- Observed sha256: `adcc816653957fbf00919c313291142cb110b5479c7790d997399e380c9b1abb`
  (9701 bytes on disc).
- The lane entry keeps `source_sha256: null`; this observed hash pins the local
  ISO copy only and is not a plan pin (see `limitations` in the packet).
- Reference sets (read-only): decomp
  `native/pikmin2-research/src/plugProjectYamashitaU/enemyInfo.cpp` → 100
  enemy ids; on-disc `user/Abe/Pellet/us/pelletlist_us.szs` (`otakara_config.txt`
  + `item_config.txt`) → 201 treasure ids via the shared `pellet_catalog`.

## Decoded floor manifest (verified against real bytes)

All 8 floors decoded with the shared `pikmin2_cave_catalog.parse`; the
catalogued baseline below was transcribed from the lane entry and the decoded
bytes AGREE with it exactly (`baseline_agrees: true`), including the raw
`source_token` multisets.

| Floor | Unit pool | Pool sha256 (prefix) | Pool bytes | Units | Enemies | Treasures | Gates | Caps |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 3_MAT_nor4_hit2_blk1_snow.txt | bd8c27d6649296be | 4853 | 9 | 13 | 2 | 0 | 2 |
| 2 | 3_MAT_ike3_mid2_sak1_snow.txt | 731b5549c5878935 | 3902 | 9 | 7 | 2 | 0 | 0 |
| 3 | 3_MAT_d_g_m_renga.txt | 7d82ebcd4c911ee5 | 5855 | 9 | 10 | 2 | 0 | 4 |
| 4 | 3_MAT_a_h_m_renga.txt | 3cdbd943519fcc3e | 5347 | 9 | 11 | 2 | 0 | 6 |
| 5 | 1_MAT_cent2_tsuchi.txt | d68f5b83c1b298ad | 3676 | 7 | 11 | 0 | 0 | 4 |
| 6 | 3_MAT_nor4_ike1_ike2_tsuchi.txt | 13c34e983fbe94ee | 4249 | 9 | 8 | 2 | 0 | 1 |
| 7 | 3_MAT_cent_mid1_mid2_tsuchi.txt | fdf02363499278e2 | 6055 | 9 | 9 | 2 | 0 | 2 |
| 8 | 1_units_queen_b_tsuchi.txt | 548e67b000205411 | 222 | 1 | 3 | 0 | 0 | 0 |

72 enemy definition rows, 12 treasure definition rows. Full pool hashes are in
the packet artifact. Weights/counts are definition inputs, never spawn
instances or placements.

## Unit arc/texts closure (verified)

For every unit in every referenced pool, both
`<BASE>/arc/<unit>/arc.szs` and `<BASE>/arc/<unit>/texts.szs` were resolved on
the disc index. Closure is complete: 0 missing members across all 8 pools
(`unit_closure_complete: true`). Any future missing member is reported as an
explicit blocker by `unit_asset_closure`, never inferred.

## Adapter contract (`experimental/content_lanes/p2-cave-tutorial_3.py`)

Schema `p2-cave-import-p0-1`. Reuses shared
`pikmin2_cave_catalog.parse`, `pikmin2_cave.unit_definition`,
`pikmin2_pod.pellet_catalog` and `pikmin2_assets.disc_files` unedited. The
adapter emits no placements (`placement: None`, `runtime_status: 'unsupported'`
on every row, `playable: False`, `retail_generation: False`).

- `decode_source(text, enemy_ids, treasure_ids)` — fail-closed decode.
- `validate_floor_coverage` / `occupied_floors` — exactly floors 1..8.
- `baseline_agreement` / `baseline_matches_lane_entry` — drift guard.
- `unsupported_references` / `resource_closure_manifest`.
- `read_source_file` / `read_iso_entry` / `read_member` — exact
  missing-prerequisite errors.
- `read_reference_sets(decomp_root, iso)` — authoritative enemy/treasure sets.
- `unit_asset_closure(index, units)` — explicit arc/texts missing list.
- `decode_live(iso, decomp_root)` — full source decode with observed hashes.
- `live_packet(iso, decomp_root)` — metadata packet including hashes/closure.
- `native_framework_blockers()` / `summarize(...)`.

Tests (`tests/content_lanes/test_p2_cave_tutorial_3.py`): **28 passed, 8
subtests passed** — decode boundaries, malformed battery, coverage gaps,
baseline drift guard, unsupported detection, source/ISO boundaries (including
non-retail ISO rejection), reference-set and closure boundaries, and four
live-decode tests that skip cleanly when the local ISO/decomp is absent.

## Exact native/framework blockers (P1/P2 activation)

- #129 cave generation/seams/navigation (active #468, lanes 34–51): accepted
  generator pin required; nothing forked here.
- #128/#130/#131/#140–#146 actor/assets/species/hazards: roster admission
  (notably Sarai, Demon, WaterOtakara, Queen_dashboots, Baby) blocks promotion,
  not P0 preparation.
- #132 surface days/saves/progression: stable course/floor identity and source
  schedules preserved, not redefined.
- Unit pool arc/texts closure: now verified against the local retail ISO for
  all 8 pools (was the blocking prerequisite).

## Evidence artifacts (this worktree's ignored `output/`)

- `output/p0-decode/packet.json` (61588 bytes, sha256
  `48a8cb719d789951d903b3bfeba1cab6b7c75845ef6f32227f9fcb560db231d6`) —
  full metadata packet.
- `output/p0-decode/checks.log` — focused pytest + shared plan checker output.
- `output/p0-decode/explore.json` — first-pass decode cross-check.

## Existing evidence preserved

Emergence/Hole of Beasts partial engineering and runtime work, P1 preview
startup, and all existing issue evidence are untouched; this lane consumes the
shared parsers and inventory as read-only references and duplicates no existing
surface/cave work.