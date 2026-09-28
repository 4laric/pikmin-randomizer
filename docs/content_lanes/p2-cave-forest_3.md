# forest_3 P0 source audit and import contract (lane p2-cave-forest_3, #156)

Implementation owner: Codex through shared GitHub account `4laric`.
Executing worker: muse-l60 (paid pool session retained), generation 2.
Phase P0 only. Full content issue #156 stays OPEN; no playability,
admission, or promotion claim is made here.

## Source identity

- Cave `forest_3`, source `user/Mukki/mapunits/caveinfo/forest_3.txt`
  (US GPVE01 revision 0).
- Canonical baseline: `docs/PIKMIN_CONTENT_IMPORT_LANES.json` lane
  `p2-cave-forest_3` (issue 156, `source_sha256: null`) cross-checked
  against `docs/PIKMIN2_CONTENT_INVENTORY.json` story-caves entry
  `forest_3` by `experimental/content_lanes/p2-cave-forest_3.py`
  (`baseline_floors` fails closed on any plan/inventory drift).
- 7 singleton floors, contiguous 1..7.

## Floor coverage (canonical baseline, not a new audit claim)

| Floor | Unit pool | Enemy tokens | Treasure tokens |
|---|---|---|---|
| 1 | 3_MAT_cnt2_nor3_uzu1_tsuchi.txt | BlueChappy_diamond_green_l, BlueKochappy, WhitePom | — |
| 2 | 2_MAT_sak2_nor1_tsuchi.txt | FireOtakara, Hiba ×3, HikariKinoko | diamond_blue_l |
| 3 | 2_MAT_mid1_nor2_tsuchi.txt | Hanachirashi ×2, UjiA ×3, WhitePom, HikariKinoko | makigai |
| 4 | 3_MAT_hit2_blk1_nor3_tsuchi.txt | Wealthy_kouseki_suisyou, $MaroFrog_wadou_kaichin, ElecBug ×2, ElecHiba, HikariKinoko | — |
| 5 | 2_MAT_hit4_nor2_tsuchi.txt | BlueChappy, BlueKochappy ×2, $Egg, $Bomb, $Egg | dia_a_green |
| 6 | 2_MAT_cent_mid2_tsuchi.txt | BlueChappy_diamond_red_l, BlueChappy, Hiba, FireOtakara ×3, BlueKochappy ×2, Hiba | saru_head |
| 7 | 2_MAT_kingA_kingB_tsuchi.txt | KingChappy_suit_fire, Hiba, Zenmai, KareOoinu_s | haniwa |

## Resource closure (adapter-computed, `resource_closure`)

- 7 unit pools, 5 treasure tokens
  (`diamond_blue_l`, `makigai`, `dia_a_green`, `saru_head`, `haniwa`).
- Enemy tokens split structurally: exact identities
  (`BlueKochappy`, `FireOtakara`, `Hiba`, `HikariKinoko`, `Hanachirashi`,
  `UjiA`, `WhitePom`, `ElecBug`, `ElecHiba`, `BlueChappy`);
  generator variants (`$MaroFrog_wadou_kaichin`, `$Egg`, `$Bomb`);
  suffixed-unresolved carrier candidates
  (`BlueChappy_diamond_green_l`, `Wealthy_kouseki_suisyou`,
  `BlueChappy_diamond_red_l`, `KingChappy_suit_fire`, `KareOoinu_s`,
  `Zenmai`).
- No counts are emitted as placements: weighted definitions stay
  definitions. `validate_manifest` refuses `placements`/`actors`/
  `spawn_layout` keys outright.

## Exact missing prerequisite

The disc source is not available locally: no `caveinfo` tree exists
under any inspected asset root and the documented
`output/pikmin2-runtime/pikmin2-source-test.iso` is absent
(`locate_source` raises `MissingPrerequisite` naming the expected
relative path, the searched root, and issue #156). The inventory
records no hash for `forest_3.txt` (`source_sha256: null`, correctly
kept unknown per the plan checker). Byte decoding and hash validation
are therefore P1 work gated on a US GPVE01 rev 0 disc or an existing
import tree — no values are invented here.

## Native/framework blockers (exact owners, no duplicates)

- Cave generation/seams/navigation: #129; active #468 and lanes 34–51
  own the accepted generator pin. This lane forks nothing.
- Actor/species/hazard semantics: #128, #130, #131, #140–146 and family
  owners (#167, #172, #120, #170, #171, #166, #165, #169, #168 for the
  main-roster actors above, plus cap/ambush/helper roster resolution in
  the floor audit).
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
   dependency publications; keep #156 open.

## Verification

- `py -3.12 -m pytest tests/content_lanes/test_p2_cave_forest_3.py -q`
  → 15 passed, 13 subtests passed (baseline agreement, closure,
  classifier, 10 malformed-manifest rejections, fabricated-placement
  refusal, missing-source prerequisite, synthetic presence/hash
  boundary, summarize packet).
- Shared plan checker untouched and still green
  (`tests/test_content_import_lanes.py` → 15 passed).
- No native build, no runtime, no assets staged, no shared files edited.
