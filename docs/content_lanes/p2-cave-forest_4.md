# forest_4 P0 source audit and import contract (lane p2-cave-forest_4, #157)

Implementation owner: Codex through shared GitHub account `4laric`.
Executing worker: muse-l61 (paid pool session retained), generation 3.
Phase P0 only. Full content issue #157 stays OPEN; no playability,
admission, or promotion claim is made here.

## Source identity

- Cave `forest_4`, source `user/Mukki/mapunits/caveinfo/forest_4.txt`
  (US GPVE01 revision 0).
- Canonical baseline: `docs/PIKMIN_CONTENT_IMPORT_LANES.json` lane
  `p2-cave-forest_4` (issue 157, `source_sha256: null`) cross-checked
  against `docs/PIKMIN2_CONTENT_INVENTORY.json` story-caves entry
  `forest_4` by `experimental/content_lanes/p2-cave-forest_4.py`
  (`baseline_floors` fails closed on any plan/inventory drift).
- 7 singleton floors, contiguous 1..7.

## Floor coverage (canonical baseline, not a new audit claim)

| Floor | Unit pool | Enemy tokens | Treasure tokens |
|---|---|---|---|
| 1 | 1_units_torigoya_kusachi.txt | BlueChappy_be_dama_yellow_l, UjiB | bird_hane |
| 2 | 3_ABE_5X5a_ike_big_kusachi.txt | Hana, Armor, UjiB, Tobi, Tanpopo, Magaret, Clover, Ooinu_s | ichigo_l, futa_a_silver |
| 3 | 1_ABE_mid1_boss_tsuchi.txt | SnakeCrow_apple_blue, SnakeCrow, Sarai, Ooinu_s, Ooinu_l | — |
| 4 | 3_ABE_mid2_hit446_hit344.txt | Kabuto, $1Kabuto_uji_jisyaku, Wtank x2, BlueKochappy, ElecHiba, DaiodoRed, DaiodoGreen | flower_red, be_dama_red_l |
| 5 | 3_ABE_cent_4x4_mid1_metal.txt | Fuefuki_whistle, $2BlueKochappy_be_dama_blue_l, $1BlueKochappy, DaiodoRed, DaiodoGreen | — |
| 6 | 3_ABE_b_f_g_conc.txt | SnakeCrow_chess_queen_white, $1BlueKochappy_bey_goma, SnakeCrow, Fuefuki, GasHiba, Clover x2 | flower_blue, g_futa_kyodo |
| 7 | 1_ABE_manp_boss_conc.txt | SnakeWhole_suit_powerup | — |

## Resource closure (adapter-computed, `resource_closure`)

- 7 unit pools, 7 treasure tokens
  (`be_dama_red_l`, `bird_hane`, `flower_blue`, `flower_red`,
  `futa_a_silver`, `g_futa_kyodo`, `ichigo_l`).
- 28 enemy tokens split structurally: exact identities
  (`Armor`, `BlueKochappy`, `Clover`, `DaiodoGreen`, `DaiodoRed`,
  `ElecHiba`, `Fuefuki`, `GasHiba`, `Hana`, `Kabuto`, `Magaret`,
  `Sarai`, `SnakeCrow`, `Tanpopo`, `Tobi`, `UjiB`, `Wtank`);
  generator variants (`$1BlueKochappy`, `$1BlueKochappy_bey_goma`,
  `$1Kabuto_uji_jisyaku`, `$2BlueKochappy_be_dama_blue_l`);
  suffixed-unresolved carrier candidates
  (`BlueChappy_be_dama_yellow_l`, `Fuefuki_whistle`, `Ooinu_l`,
  `Ooinu_s`, `SnakeCrow_apple_blue`, `SnakeCrow_chess_queen_white`,
  `SnakeWhole_suit_powerup`).
- No counts are emitted as placements: weighted definitions stay
  definitions. `validate_manifest` refuses `placements`/`actors`/
  `spawn_layout` keys outright.

## Exact missing prerequisite

The disc source is not available locally: no `caveinfo` tree exists
under the documented asset root and the documented
`output/pikmin2-runtime/pikmin2-source-test.iso` is absent
(`locate_source` raises `MissingPrerequisite` naming the expected
relative path, the searched root, and issue #157). The inventory
records no hash for `forest_4.txt` (`source_sha256: null`, correctly
kept unknown per the plan checker). Byte decoding and hash validation
are therefore P1 work gated on a US GPVE01 rev 0 disc or an existing
import tree — no values are invented here.

## Native/framework blockers (exact owners, no duplicates)

- Cave generation/seams/navigation: #129; active #468 and lanes 34–51
  own the accepted generator pin. This lane forks nothing.
- Actor/species/hazard semantics: registered runtime dependencies
  #128, #140–146 and the roster/family owners resolve the 7
  suffixed carrier candidates and 4 `$` generator variants above;
  no fallback behavior is fabricated here.
- Surface days/saves/progression: #132 (stable floor/instance identity).
- Treasure hauling/rewards and natural completion: family lanes plus the
  P1 importer; unresolved enemy admission blocks promotion, not this
  preparatory work.

## P1 implementation packet (for the integrator)

1. Supply the disc/import tree; `locate_source` returns
   `{path, sha256, bytes}` and the recorded hash becomes the lane's
   source pin (plan update owned by the integrator, not this lane).
2. Decode with the existing `experimental.pikmin2_cave.cave_definition`
   brace parser (read-only reuse); shape each floor as
   `{number, unit_pool, enemy_ids, treasure_ids}`.
3. Gate the decode with `validate_manifest` (this lane): exact 7-floor
   coverage, exact pools, exact token sets, no fabricated placements.
4. Resolve `unresolved` tokens with the roster/family owners above;
   `$`-variants need generator integration (cf. `pikmin2_content`
   weighted-population refusal precedent).
5. Runtime activation needs P1 acceptance from the lane plan plus
   dependency publications; keep #157 open.

## Verification

- `py -3.12 -m pytest tests/content_lanes/test_p2_cave_forest_4.py -q`
  → 17 passed, 9 subtests passed (baseline agreement, closure,
  classifier, good-manifest validation, 10 malformed-manifest
  rejections, fabricated-placement refusal, missing-source
  prerequisite, synthetic presence/hash boundary, summarize packet).
- Shared plan checker untouched and still green
  (`tests/test_content_import_lanes.py`).
- No native build, no runtime, no assets staged, no shared files edited.
