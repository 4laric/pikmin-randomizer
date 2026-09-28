# P0 source audit + import contract — p2-cave-yakushima_3 (#160)

Lane `p2-cave-yakushima_3`, issue #160, yakushima_3 (7 floors).
Implementation owner: Codex through shared account `4laric`; executing
contributor Muse Spark 1.3 (lane generation 2, session
`ses_f588f5ecbffewB4l1dbImg41Ak`).

## Source identity

- Retail source (bytes UNAVAILABLE): `user/Mukki/mapunits/caveinfo/yakushima_3.txt`.
- Searched: decomp repo (loader only), staged BBFT assets, private outputs,
  local ISO paths. No checkout on this host carries it; no story-cave hash
  exists in `docs/PIKMIN2_CONTENT_INVENTORY.json` `source_sha256` (that map
  covers only `ch_*`/`vs_*` caveinfo files); lane `source_sha256` is null.
- Decoder contract (read-only, never edited):
  `native/pikmin2-research/include/Game/Cave/Info.h` — `CaveInfo::load`,
  `mFloorMax` (`c000`, 1..128), `FloorInfo` parms `f000`-`f017` (indices,
  teki/item/gate/cap maxima, room count, route ratio, escape-fountain flag,
  unit file `f008`, lighting `f009`, vrbox, hole-clogged flag,
  alpha/beta/hidden types, version, Waterwraith timer `f016`, seesaw),
  `TekiInfo` (enemy ID/weight/spawn type/drop mode/held-treasure code),
  `ItemInfo`, `GateInfo`, `CapInfo`, `BaseGen` spawn types 0-8.

## Catalogued floor roster (P0 baseline, not fresh retail bytes)

Decoded from the pinned lane plan and inventory, verified byte-identical
between `docs/PIKMIN_CONTENT_IMPORT_LANES.json` and
`docs/PIKMIN2_CONTENT_INVENTORY.json` `story_caves` (`lane_vs_inventory`
equal; enforced by test):

| Floor | Unit pool | Enemy tokens | Treasure tokens |
|---|---|---|---|
| 1 | 3_units_a_d_north_tile.txt | MaroFrog, Wtank, Rock, $1Tadpole ×2, ElecHiba | otama |
| 2 | 2_units_ud_dry_tile.txt | Kurage, BlueChappy, Rock, BlueKochappy ×2, GasHiba ×2 | toy_dog, denchi_2_black |
| 3 | 4_units_a_d_f_l_tile.txt | OniKurage_compact_make, Kurage, Jigumo, Catfish, $1Catfish | futa_a_gold, hotate |
| 4 | 1_unit_16x17r_conc.txt | RandPom, ShijimiChou, Clover ×3, KareOoinu_s ×3, Zenmai, Ooinu_s | momiji_normal |
| 5 | 3_units_d_f_ujikou_tile.txt | Hanachirashi, MaroFrog, Tank, BlueKochappy ×2, Hiba ×2 | toy_lady, kan_iwate, g_futa_kitaama |
| 6 | 3_units_a_l_yuko_tile.txt | ElecOtakara, GasOtakara, BombOtakara, MaroFrog, Demon, BlueChappy, BlueKochappy ×2 | ahiru, dia_a_blue, milk_cap |
| 7 | 1_units_a_tile.txt | UmiMushi_fue_wide | — |

Coverage: floors 1..7 contiguous, no gaps, no duplicates
(`floor_coverage` contiguous; enforced by test).

## Token inventory (adapter-generated, syntactic classes only)

`$N` prefix = generator variant (roster alias rules); anything else with an
underscore = compound (passed through opaquely, never split into a species
claim); plain names = exact. No spawn semantics invented; admission status
is roster-ledger owned, not stated here.

- generator_variant (2): `$1Tadpole` [1], `$1Catfish` [3].
- compound (4): `OniKurage_compact_make` [3], `KareOoinu_s` [4],
  `Ooinu_s` [4], `UmiMushi_fue_wide` [7].
- exact (20): BlueChappy [2,6], BlueKochappy [2,5,6], BombOtakara [6],
  Catfish [3], Clover [4], Demon [6], ElecHiba [1], ElecOtakara [6],
  GasHiba [2], GasOtakara [6], Hanachirashi [5], Hiba [5], Jigumo [3],
  Kurage [2,3], MaroFrog [1,5,6], RandPom [4], Rock [1,2], ShijimiChou [4],
  Tank [5], Wtank [1], Zenmai [4].
- treasure tokens, unresolved (no treasure catalog in the inventory; 12):
  ahiru [6], denchi_2_black [2], dia_a_blue [6], futa_a_gold [3],
  g_futa_kitaama [5], hotate [3], kan_iwate [5], milk_cap [6],
  momiji_normal [4], otama [1], toy_dog [2], toy_lady [5].

## Reserved changes

- `experimental/content_lanes/p2-cave-yakushima_3.py` — isolated
  metadata/import adapter (decomp-derived cave contract, strict floor
  decoder, token classes, lane-vs-inventory check, resource closure, exact
  prerequisites, packet builder).
- `tests/content_lanes/test_p2_cave_yakushima_3.py` — 16 tests +
  15 subtests, all passing; pinned-catalog plus synthetic fixtures only.
- `docs/content_lanes/p2-cave-yakushima_3.md` — this spec.

No shared parser/schema, species, native, admission or other-lane edits.

## Evidence

- Focused test log: `output/workflow/content-expansion/p2-cave-yakushima_3/pytest.log`
  (SHA-256 recorded in the inbox packet).
- Source bytes unavailable (see Source identity); lane `source_sha256` null.
- Blockers: disc bytes + unit-file hashes; validated P1 publications
  #129/#128/#131/#132/#140/#144/#145/#146; sibling caves #158/#159/#161;
  treasure catalog absent from inventory.

## Status

P0 implementation packet reviewed and tested. Full content acceptance and
dependencies stay OPEN. No claim of playability. No ADMIT.
