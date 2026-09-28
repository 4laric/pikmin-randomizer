# P0 import contract — tutorial_2 story cave (lane p2-cave-tutorial_2, issue #152)

Generation-2 P0 slice. Concrete source-import preparation only: no native
build, no runtime, no ADMIT, no playability claim. The full-content issue
#152 stays open for P1/P2. Reserved implementation:
`experimental/content_lanes/p2-cave-tutorial_2.py` (adapter, stdlib only,
dependency-free pure functions) plus
`tests/content_lanes/test_p2_cave_tutorial_2.py` (26 focused tests).

## Source identity

- Source ID `tutorial_2`; retail definition
  `user/Mukki/mapunits/caveinfo/tutorial_2.txt` (US GPVE01 revision 0,
  shift_jis caveinfo text).
- The definition file is NOT available in this worktree. Exact missing
  prerequisite: stage a retail US GPVE01 rev-0 disc (or its extracted
  `user/Mukki` tree) and decode with
  `experimental.pikmin2_cave_catalog.inventory(iso, source, output)`.
  No values are invented in its place.

## Catalogued baseline (validated, not reimplemented)

From `docs/PIKMIN2_CONTENT_INVENTORY.json` story_caves entry `tutorial_2`
(also mirrored in `docs/PIKMIN_CONTENT_IMPORT_LANES.json` lane
`p2-cave-tutorial_2`): 9 floors, contiguous coverage 1..9, one unit pool
per floor.

| Floor | Unit pool | Enemies | Treasures |
|---|---|---|---|
| 1 | 3_MAT_mid1_mid2_uzu1_snow.txt | 10 | gum_tape_s, tel_dial |
| 2 | 2_MAT_h335_h447_metal.txt | 8 | sinkukan_c, gear_silver |
| 3 | 2_MAT_h224_h443_tekiF_metal.txt | 8 | gear, bane |
| 4 | 1_units_hit224_metal.txt | 3 | — |
| 5 | 1_units_nobo2_metal.txt | 18 | mojiban, nut |
| 6 | 5_units_mid2_cent_hit4_hit5_nor2_metal.txt | 10 | sinkukan, channel, bolt_l |
| 7 | 3_MAT_ari_h446_h443_tower_metal.txt | 13 | denchi_1_black, tape_red |
| 8 | 1_units_hit224_metal.txt | 6 | — |
| 9 | 1_units_houdai_metal.txt | 3 | — |

Resource closure: 8 distinct unit pools (floors 4 and 8 share
`1_units_hit224_metal.txt` — reported, not an error); 79 enemy tokens, 25
distinct; 13 distinct treasure tokens, every one present in the
`us/runtime/otakara` pellet catalog (188 entries).

## Token classification (TekiInfo::read rule)

79 tokens: 68 exact, 8 generator-variant (`$Bomb` ×7 floor 5,
`$BombOtakara` ×1 floor 5), 2 resolved carriers (`Fkabuto_bolt` floor 3 →
Fkabuto + `bolt`; `FminiHoudai_sinkukan_b` floor 7 → FminiHoudai +
`sinkukan_b`, both cargo pellets catalogued), 1 unknown-cargo
(`Houdai_light_a` floor 9 → Houdai + `light_a`, which is NOT in the pellet
catalog). The unknown cargo is a finding, not a failure: carried-cargo and
`$` drop modes on flat roster summaries need the actual retail definition
to confirm. No weights, placements, topology or schedules are derived from
flat rosters.

## Hash record

- Lane-plan pin `inventory_sha256` (`2d87ad05...`) MATCHES the raw bytes of
  `docs/PIKMIN2_CONTENT_INVENTORY.json` as staged (CRLF preserved;
  `adapter.inventory_hashes()` reads bytes, not text). Any future drift
  fails the `test_inventory_hash_matches_pin` regression test and forces a
  re-audit — a mismatch is never asserted equal.
- Retail definition hash: unavailable (source absent); the lane entry's
  `source_sha256` stays null until the P1 decode.

## Exact native/framework blockers

1. Missing retail source (above) — blocks weighted-definition decode, unit
   pool asset closure (`arc`/`texts.szs` per unit), and any placement work.
2. Unresolved carrier `light_a` (floor 9) — needs source decode; do not
   guess a pellet mapping.
3. Cap/ambush/helper rosters for floors with `$` variants and carriers
   (issue #152 dependencies #129, #132, #148, #140, #144, #145; actor
   dependencies #173, #120, #170, #171, #166, #165, #169) — P1 scope.
4. No shared-file changes in this slice: global parsers/schema, species or
   other levels untouched. Any future shared need goes through scoped
   review with the owning lanes.

## Implementation packet for P1

Consume `audit_entry()` output (schema `p2-cave-tutorial_2-p0/1`,
`generated: False` with stated limitations) plus `source_prerequisite()`.
When the source lands: `decode_source_text()` wraps the shared
`pikmin2_cave_catalog.parse` with the inventory enemy/treasure universes,
then per-floor `f008` unit pools resolve under `user/Mukki/mapunits/units/`
with `arc`/`texts.szs` closure per referenced unit. P1 then needs a
private root/native pair, leased build, starting squad, centred 960×540
startup and natural acceptance per the lane phases — none of which is
claimed here. All runtime gates UNTESTED; fixture adoption N/A
(kind=tooling handoff).

## Verification

`py -3.12 -m pytest tests/content_lanes/test_p2_cave_tutorial_2.py -q`
→ 26 passed (positive pins on the real catalogued entry; malformed,
missing-entry, gap/overlap, empty-pool, unknown/malformed-token and
missing-source-boundary negatives).
