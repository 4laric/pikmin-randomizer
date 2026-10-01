# P0 source audit: P2 Challenge 21 ch_NARI_07whitepurple (#553)

Implementation owner: Codex through shared account 4laric. P0 only: source
audit and additive import contract. No playability claim; full content issue
#553 stays open for P1/P2. Runtime dependencies #136, #137, #129, #130, #131.
Parent #569; integration owner #437.

## Source identity (verified)

- Cave ID `ch_NARI_07whitepurple`, table order 1, UI index 20.
- Disc path `user/Mukki/mapunits/caveinfo/ch_NARI_07whitepurple.txt`, 2634
  bytes, sha256 `478fee6f70236ed8d51ad47cf8a08809309dc25bc763a54e484ff12693e0ad92`
  (matches `docs/PIKMIN_CONTENT_IMPORT_LANES.json` source_sha256).
- Local evidence bytes:
  `output/workflow/autofill/p2-challenge-ch_nari_07whitepurple/ch_NARI_07whitepurple.txt`.
- Decoder: `experimental/content_lanes/p2-challenge-ch_nari_07whitepurple.py`
  reuses shared `experimental.pikmin2_cave` (`tree`, `parameters`, `safe_name`)
  and `experimental.pikmin2_cave_catalog` (`integer`, `rows`, `parse`,
  `enemy_token`); no shared file was modified.

## Decoded floor coverage (actual definitions)

Two individually authored floors, contiguous coverage 1-2:

| Floor | Range | Unit pool | Light | Enemies | Treasures | Gates | Caps |
|---|---|---|---|---|---|---|---|
| 1 | 1-1 | 2_units_cent_north_tsuchi.txt | normal_light_cha.ini | 10 rows | 6 rows | 0 | 0 |
| 2 | 2-2 | 2_units_mid2_north_tsuchi.txt | normal_light_cha.ini | 10 rows | 5 rows | 0 | 1 (TamagoMushi) |

Authored maxima (definition limits, not observed counts): floor 1 enemies 13,
items 6, caps 100, rooms 3, no geyser; floor 2 enemies 10, items 5, caps 100,
rooms 3, geyser exit present (f007=1). VRBOX `none` on both floors.

Floor 1 enemies (token, weight, type): Wealthy_gold_medal 10/1,
Fart_silver_medal 10/1, Kogane_wadou_kaichin 10/1, BlackPom 30/1, Egg 20/1,
GasHiba 50/5, Magaret 4/6, Clover 4/6, Ooinu_s 4/6, KareOoinu_s 4/6.
Floor 1 treasures: key, apple, leaf_normal, leaf_kare, dia_a_red, ichigo_l
(all weight 10). Floor 2 enemies: Mar_key 10/1, Wealthy_gold_medal 10/1,
Fart_silver_medal 10/1, Kogane_wadou_kaichin 10/1, TamagoMushi 10/1,
GasHiba 50/5, Magaret 4/6, Clover 4/6, Ooinu_s 4/6, KareOoinu_s 4/6.
Floor 2 treasures: leaf_yellow, momiji_kare, dia_a_green, donutswhite_s,
bane_yellow. Floor 2 cap: TamagoMushi 10/1. No gates on either floor.

Weights are definition inputs (packed minimum/weight, or plant target counts
for type 6); type 5 is carried verbatim and not rewritten. No coordinates
exist in this file and none are emitted.

## Inventory baseline (not re-derived)

Floor timers [170.0s, 170.0s], starting roster 30 leaf purple Pikmin (native
color index 4, maturity 0), spicy x3, bitter x0, treasure_count_field 0,
legacy_time 0.0. These come from the lane plan/inventory stage table and are
carried as labeled baseline by `import_contract()`; the caveinfo bytes do not
contain them.

## Resource closure (fresh, read-only disc enumeration)

All four referenced assets were verified present on the local GPVE01 image:

- `user/Mukki/mapunits/units/2_units_cent_north_tsuchi.txt` present
- `user/Mukki/mapunits/units/2_units_mid2_north_tsuchi.txt` present
- `user/Abe/cave/normal_light_cha.ini` present (both floors)

The light directory `user/Abe/cave/` is a disc-observed convention; shared
code only `safe_name`s `f009` and does not resolve the light path, so this
adapter records the mapping explicitly. Full strict decode against the real
`enemyInfo.cpp` IDs and the disc pellet catalog is ACCEPTED (2 floors). All
13 unique enemy tokens resolve, and all 11 treasure tokens resolve. Four
enemy tokens are `Enemy_treasure` carries, not missing entries:
Wealthy_gold_medal -> gold_medal, Fart_silver_medal -> silver_medal,
Kogane_wadou_kaichin -> wadou_kaichin, Mar_key -> key. The other eight
(BlackPom, Clover, Egg, GasHiba, KareOoinu_s, Magaret, Ooinu_s, TamagoMushi)
resolve as plain enemies.

## Exact blockers for P1/runtime

- #136 Challenge framework: starting color/maturity intake, per-floor timing,
  keys/exits, scoring, retry and ordinary/deathless result semantics.
- #137: stage completion, stage-table verification of the 170 s timers, the
  30-purple roster and 3 spicy sprays, and the unresolved English title.
- #129 / lanes 34-51: unit-pool instantiation for both `*_tsuchi.txt` pools.
- #128 / #130 / #131: real actor admission and behavior for the resolved
  enemy tokens plus the floor-2 TamagoMushi cap payload.
- No ADMIT, no shared-checkout change, no full-issue closure proposed.

## Tests and evidence

`tests/content_lanes/test_p2_challenge_ch_nari_07whitepurple.py`: 13 tests +
13 subtests pass (hash pin, coverage/pools, golden rosters, authored maxima
recorded without spawns, malformed/missing fail-closed on synthetic and real
bytes, shared-parser wiring, closure and no-placement contract). Log:
`output/workflow/autofill/p2-challenge-ch_nari_07whitepurple/checks-p0.log`.
Reviewed packet: `.../contract-p0.json`.
## P1 import path (lane p2-challenge-ch-nari-07whitepurple-p1; no re-implementation)

`validate_p1_manifest()` checks a P0 manifest carries everything the P1
runtime import needs (2 decoded floors with unit pools + enemy/treasure
rosters, 7-row starting roster totalling 30 purples at [4][0], timers
[170.0, 170.0], sprays bitter 0 / spicy 3, ui_index 20) and normalizes a
staging dict; anything else raises fail-closed via `UnsupportedDefinition`.
`stage_run_layout()` writes a private run layout: `stage-manifest.json`
(validated copy), `p1-input-package.json` (stage key, floors, squad total 30,
timers, sprays, ui 20) and `run-plan.json` (ordered observation plan: fresh
arena + starting-Pikmin overlay + centred 960x540 boot, captain guard FIRST
with orimaDead/NaviDead/HP<=1 and CAPTAIN_DOWN + BLOCKED, live-squad check,
collision/routes/actors markers, honest six-gate evidence). `p1_main()` drives
it from a manifest file; `main()` is a thin CLI. All decode helpers are the
P0 ones in this same file; no parser was forked.

P1 validation evidence: `P1ImportTests`, 14 focused tests (valid manifest,
wrong cave, floor count, empty enemies, missing unit pool, wrong squad total,
missing pinned cell, bad timer, wrong sprays, wrong ui, three-file layout
write + package schema/squad assertions, bad-manifest and missing-file
rejections, end-to-end `p1_main`), all green alongside the 13 P0 tests
(27 passed total). No runtime run, no build, no shared edits; all six gates
UNTESTED. The runtime boot (leased build, fresh arena, guard adoption, live
observation) remains explicitly future work once the host toolchain recovers.
