# Forest_1 headed-run legal assets (issue #681)

Bounded verification and staging of the legal assets the forest_1 headed run
needs. Owner: Codex through shared account 4laric. Tooling only: no runtime,
no source/shared edits, no ADMIT. All six runtime gates UNTESTED.

## Why

Consumer shard-caves-forest-forest1-p1 (#154) listed gap 1 as missing legal
assets (courses/pikmin2room model data) for the headed run, with no producer
lane and no recorded failed reads. This slice resolves that gap directly
against output/workflow/asset-inputs.json and the locally owned disc.

## Verified closure (exact reads)

Source disc C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso (2768 members).
Header source:

- user/Mukki/mapunits/caveinfo/forest_1.txt offset 770562536 size 4664
  sha256 c0dccd032e576bdc9234ad04fc44b7081c6f36b52e50cb66ed48fe9e6f54cf88
  (matches asset-inputs.json verified_members exactly).

Per-floor unit pools live under user/Mukki/mapunits/units/ (present):

- 1_units_cent3_tsuchi.txt (floor 1) - enumerates item_cap_tsuchi,
  way3_tsuchi, way4_tsuchi, wayl_tsuchi, way2_tsuchi, way2x2_tsuchi,
  room_cent3_4_tsuchi (names only; geometry decode is #154 owner scope).
- 1_units_cent2_tsuchi.txt, 2_ABE_norhiba_blkhiba_tsuchi.txt,
  2_ABE_mid1_nor3_tsuchi.txt, 1_units_boss_tsuchi.txt.

Floor-1 unit archives (7 units x arc.szs/texts.szs = 14) all present under
user/Mukki/mapunits/arc/<unit>/. Course data is archived, not loose:

- user/Kando/map/forest/arc.szs and texts.szs (model/collision/waterbox/mapcode).
- user/Abe/map/forest/route.txt.

Result: 23 assets PRESENT and staged, 5 candidates ABSENT with exact failed
reads. No invented assets.

## Recorded ABSENT (exact failed reads)

Each of these is a documented wrong-path probe. The failed read is exact:
member not present in the disc index.

- user/Mukki/mapunits/1_units_cent3_tsuchi.txt
- user/Kando/map/forest/forest.bmd
- user/Kando/map/forest/collision.bin
- user/Kando/map/forest/waterbox.txt
- user/Kando/map/forest/mapcode.bin

The loose .bmd/.col/.wbx/.mpc names from the course header are entries INSIDE
user/Kando/map/forest/arc.szs, and the pools are under mapunits/units/, not
mapunits/ - so nothing is missing at the real retail locations.

## Adapter and tests

experimental/pikmin2_forest1_legal_assets.py: exact-read member verification
with sha256, light pool name enumeration via the shared parser (geometry
decode deliberately NOT performed), a documented ABSENT-probe set, fail-closed
packet validation and an exact-read staging copy plus staged manifest.

tests/test_pikmin2_forest1_legal_assets.py: 12 focused tests (present/absent/
short read, packet validation rejections, staging exactness and drift refusal,
closure membership, no-invention invariant).

## Staging output

out/staged/ holds the 23 present members in their retail relative layout plus
staged-manifest.json (paths, sizes, sha256). Consumable by the forest_1 headed
run as the asset root; the run itself stays with the #154 owner and the
controller lease.

## Boundary and next scope

Unit-blob geometry decode (gap 2) and the leased headed run (gap 3) are NOT
duplicated here. Downstream consumer: #154 gap 1. Next bounded scope: #154
owner decodes the pinned floor-1 unit geometry onto these staged assets, then
the controller grants the heavy-build lease for the real floor-1 boot.

