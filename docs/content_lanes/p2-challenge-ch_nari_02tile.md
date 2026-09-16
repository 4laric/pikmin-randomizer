# P0 source audit: P2 Challenge 05 ch_NARI_02tile (lane p2-challenge-ch_nari_02tile, #537)

Implementation owner: Codex through shared account 4laric. P0 only: source
audit and additive import contract. No playability claim; full content issue
stays open for P1/P2. Runtime dependencies #136, #137, #129, #130, #131.

## Source identity (verified)

- Cave ID `ch_NARI_02tile`, table order 19, UI index 4.
- Disc path `user/Mukki/mapunits/caveinfo/ch_NARI_02tile.txt`, 2104 bytes,
  sha256 `d047060c7965e501d23b23e2850b5f58e327d40b452d70710149ea4b41479ea6`
  (matches `docs/PIKMIN_CONTENT_IMPORT_LANES.json` source_sha256).
- Local evidence bytes:
  `output/workflow/content-expansion/p2-challenge-ch_nari_02tile/ch_NARI_02tile.txt`.
- Decoder: `experimental/content_lanes/p2-challenge-ch_nari_02tile.py`
  reuses shared `experimental.pikmin2_cave` (`tree`, `parameters`,
  `safe_name`) and `experimental.pikmin2_cave_catalog` (`integer`, `rows`,
  `parse`); no shared file was modified.

## Decoded floor coverage (actual definitions)

Two individually authored floors, contiguous coverage 1-2:

| Floor | Range | Unit pool | Light | Enemies | Treasures | Gates | Caps |
|---|---|---|---|---|---|---|---|
| 1 | 1-1 | 2_units_northF_pool_tile.txt | normal_light_cha.ini | 5 rows | 5 rows | 0 | 1 (Egg) |
| 2 | 2-2 | 1_MIYA_bunki_tile.txt | normal_light_cha.ini | 1 row | 3 rows | 0 | 1 (WhitePom) |

Floor 1 enemies (token, weight, type): UmiMushiBlind_key 10/8,
Jigumo_toy_ring_a_blue 10/1, Jigumo_toy_ring_b_green 10/1,
Demon_diamond_blue_l 1/6, OniKurage_diamond_red 1/6.
Floor 1 treasures: ahiru, toy_dog, bell, diamond_red_l, diamond_green_l
(all weight 10). Floor 2 enemies: UmiMushi_key 1/6. Floor 2 treasures:
ahiru_head, diamond_blue, toy_ring_a_red (all weight 10).
Caps: Egg 11/1 (floor 1), WhitePom 20/1 (floor 2). No gates either floor.
Floor 1 maxima: enemies 3, items 5, caps 50, rooms 3. Floor 2 maxima:
enemies 0, items 3, caps 0, rooms 1, geyser exit present (f007=1).

Weights are definition inputs (packed minimum/weight or plant target
counts per shared semantics), not spawn instances; no coordinates exist in
this file and none are emitted.

## Inventory baseline (not re-derived)

Floor timers [200.0s, 150.0s], starting roster 50 flower reds (native
color 0, maturity 2), spicy x5, bitter x0, treasure_count_field 0,
legacy_time 0.0. These come from the lane plan/inventory stage table and
are carried as labeled baseline by `import_contract()`; the caveinfo bytes
do not contain them.

## Resource closure status

- Internal: header count matches, floor ranges contiguous, type tags and
  the shared floor-key discipline enforced, roster framing exact, asset
  names pass `safe_name`. Malformed/missing-input tests fail closed.
- Referenced assets: `user/Mukki/mapunits/units/2_units_northF_pool_tile.txt`,
  `user/Mukki/mapunits/units/1_MIYA_bunki_tile.txt`,
  `user/Mukki/mapunits/normal_light_cha.ini` (VRBOX `none` needs no asset).
  Disc presence is UNVERIFIED here: `asset_closure(scan, None)` reports
  `unverified`; P1 supplies an explicit disc catalog.
- Semantic resolution OPEN: 5 enemy tokens + 8 treasure tokens + Egg/WhitePom
  cap payloads await enemy/pellet catalog owners.

## Exact blockers for P1/runtime

#136 Challenge framework (timing/keys/scoring/retry/result semantics),
#137 content completion + pellet table + stage-table verification, #129 +
lanes 34-51 unit instantiation, #128/#130/#131 actor and treasure admission.
No ADMIT, no shared-checkout change, no full-issue closure proposed.

## Tests and evidence

`tests/content_lanes/test_p2_challenge_ch_nari_02tile.py`: 12 tests +
13 subtests pass (hash pin, coverage, golden rosters, malformed/missing
fail-closed on synthetic and real bytes, shared-parser wiring, closure and
no-placement contract). Log:
`output/workflow/content-expansion/p2-challenge-ch_nari_02tile/checks-p0.log`.
