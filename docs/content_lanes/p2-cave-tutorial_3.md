# P2 cave tutorial_3 — P0 source audit and import contract (#153)

Lane `p2-cave-tutorial_3`; work class expansion; phase P0 only. Implementation
owner: Codex through shared account 4laric; executing contributor Muse Spark
1.3 (worker muse-l58). Full content issue #153 stays OPEN; no playability is
claimed anywhere in this packet.

## Source identity

- Cave: `tutorial_3` (8 floors), definition file
  `user/Mukki/mapunits/caveinfo/tutorial_3.txt`.
- Recorded hash: none. The lane entry (`docs/PIKMIN_CONTENT_IMPORT_LANES.json`
  lane `p2-cave-tutorial_3`) has `source_sha256: null`, and the inventory
  baseline (`docs/PIKMIN2_CONTENT_INVENTORY.json` `source_sha256`) records
  only `user/Mukki/mapunits/caveinfo/ch_ABEM_tutorial.txt`, not this file.
- Local bytes: unavailable. No retail ISO is present in this workspace
  (`output/pikmin2-runtime/` is empty; the supported source-test image is
  not a retail disc), and no `caveinfo/` tree exists in the repo, native
  research checkout, or local asset staging. Exact prerequisite: a US GPVE01
  revision 0 disc image exposing the member above (see adapter
  `read_iso_entry`), plus decomp `enemyInfo.cpp` and pellet configs for the
  authoritative reference sets.

## Catalogued floor manifest (baseline, not decoded bytes)

From the lane entry `details.floors`, agreeing with the inventory
`story_caves` tutorial_3 entry:

| Floor | Unit pool | Enemies | Treasures |
|---|---|---|---|
| 1 | 3_MAT_nor4_hit2_blk1_snow.txt | YellowChappy, YellowKochappy×2, Fart×2, KareOoinu_s, KareOoinu_l×2, KareOoinu_s, KareOoinu_l, KareOoinu_s, KareOoinu_l, Wakame_l (13) | Xmas_item, teala_dia_a |
| 2 | 3_MAT_ike3_mid2_sak1_snow.txt | RKabuto, YellowChappy, YellowKochappy×2, KareOoinu_s×2, KareOoinu_l (7) | chess_king_black, toy_ring_c_blue |
| 3 | 3_MAT_d_g_m_renga.txt | LeafChappy, KumaChappy_bell_red, KumaKochappy×3, GasHiba, Hiba, ElecHiba, KareOoinu_s×2 (10) | toy_ring_a_green, toy_ring_c_red |
| 4 | 3_MAT_a_h_m_renga.txt | Sarai×2, Demon×2, ElecBug×3, ElecHiba, KareOoinu_s×2, KareOoinu_l (11) | toy_ring_c_green, be_dama_red |
| 5 | 1_MAT_cent2_tsuchi.txt | Miulin_fue_a, ShijimiChou, Miulin, WaterOtakara×2, Clover, Wakame_s, Wakame_l, Ooinu_l, Magaret, Ooinu_s (11) | — |
| 6 | 3_MAT_nor4_ike1_ike2_tsuchi.txt | RKabuto, LeafChappy, Catfish×3, Hiba, HikariKinoko×2 (8) | chess_king_white, chess_queen_black |
| 7 | 3_MAT_cent_mid1_mid2_tsuchi.txt | BlueChappy, Rock×3, BlueKochappy×3, HikariKinoko×2 (9) | yoyo_red, bell_yellow |
| 8 | 1_units_queen_b_tsuchi.txt | Queen_dashboots, Baby×2 (3) | — |

72 enemy definition rows, 12 treasure definition rows. Weights/counts are
definition inputs, never spawn instances or placements.

## Adapter contract (`experimental/content_lanes/p2_cave_tutorial_3.py`)

Schema `p2-cave-import-p0-1`. Reuses shared `pikmin2_cave_catalog.parse`
unedited. Test-only synthetic fixtures exercise the real parser; the adapter
emits no placements (`placement: None`, `runtime_status: 'unsupported'` on
every row, `playable: False`, `retail_generation: False`).

- `decode_source(text, enemy_ids, treasure_ids)` — fail-closed decode.
- `validate_floor_coverage(parsed)` — exactly floors 1..8 contiguous.
- `baseline_agreement(parsed)` — per-floor unit pool + raw `source_token`
  multiset + treasure multiset vs the table above; mismatches reported, never
  corrected (raw tokens compared so no TekiInfo split/case assumption is
  baked in — e.g. `Miulin_fue_a` needs the authoritative sets to resolve).
- `baseline_matches_lane_entry(path)` — embedded table guarded against lane
  entry drift.
- `unsupported_references(parsed, enemy_ids, treasure_ids)` — explicit
  unknown-token blockers.
- `resource_closure_manifest(parsed)` — unit pools referenced per floor.
- `read_source_file` / `read_iso_entry` — exact missing-prerequisite errors.
- `native_framework_blockers()` — exact owners below.
- `summarize(...)` — reviewed P0 packet dict for integrator review.

Tests (`tests/content_lanes/test_p2_cave_tutorial_3.py`): 19 passed, 8
subtests passed — decode boundaries, malformed battery, coverage gaps,
baseline drift guard, unsupported detection, source/ISO boundaries
(including non-retail ISO rejection), metadata-only packet shape.

## Exact native/framework blockers (P1/P2 activation)

- #129 cave generation/seams/navigation (active #468, lanes 34–51):
  accepted generator pin required; nothing forked here.
- #128/#130/#131/#140–#146 actor/assets/species/hazards: roster admission
  (notably Sarai, Demon, WaterOtakara, Queen_dashboots, Baby) blocks
  promotion, not P0 preparation.
- #132 surface days/saves/progression: stable course/floor identity and
  source schedules preserved, not redefined.
- Unit pool arc/texts closure per floor: unverified until retail ISO bytes
  are available (prerequisite above).

## Existing evidence preserved

Emergence/Hole of Beasts partial engineering and runtime work, P1 preview
startup, and all existing issue evidence are untouched; this lane consumes
the shared parsers and inventory as read-only references and duplicates no
existing surface/cave work.
