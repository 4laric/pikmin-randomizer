# P0 source audit on real bytes: P2 overworld course last (Wistful Wild)
 
Lane p2-overworld-last-p0-real-source, issue 151. P0 ONLY. No claim of
playability; full content acceptance and all runtime dependencies stay OPEN.
 
## Source identity (observed, not assumed)
 
- Retail file user/Abe/stages.txt extracted read-only from the verified local ISO
  C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso (disc offset 770327488,
  size 3275) via experimental.pikmin2_assets.disc_files. Staged lane copy:
  prepared/last-p0-output/stages.txt.
 - Observed sha256 4de9008c99e799b99b2746c0156846eeb7ad50895ad110fc7f2070db6de1fff8,
  3275 bytes. Recorded in manifest-real.json and asserted by the real-bytes test.
 - Course last (Wistful Wild) at index 3 of 5 courses
(tutorial, forest, yakushima, last, test_map).
 
## Corrections to the synthetic-only revision
 
The prior adapter encoded three wrong assumptions, all corrected here against
the observed bytes: course count is 5 not 4; there is no farm keyword
(keyword order is name, folder, abe_folder, model, collision, waterbox,
mapcode, route, start, startangle, literal end trailer); each course sits in
brace blocks; # starts an end-of-line comment; cave ids are brace-wrapped
({l_01}); the startangle trailer token is the literal word end.
 
## Decoded last summary (real bytes)
 
- Start position -3300, 0, -850; start angle -130 degrees.
- Resource closure: model user/Kando/map/last/last.bmd,
  collision user/Kando/map/last/collision.bin,
  waterbox user/Kando/map/last/waterbox.txt,
  mapcode user/Kando/map/last/mapcode.bin,
  route user/Abe/map/last/route.txt.
- LimitGenInfo: 1 row (0-1.txt, days 0 to 1, limit 1). LoopGenInfo: 0 rows.
- CaveOtakaraInfo: 3 rows: l_01 with 17 from last_1.txt,
  l_02 with 13 from last_2.txt, l_03 with 21 from last_3.txt.
- Ground-otakara max: 5. No placements emitted, ever.
 
## Adapter and contract
 
experimental/content_lanes/p2-overworld-last.py implements the isolated P0
adapter against the observed grammar: comment stripping, brace blocks,
strict order-dependent decode, last-at-index-3 selection, brace-wrapped cave
ids, defect validation (empty paths, inverted or negative schedules,
duplicate cave ids, negative counts), byte-exact sha256, metadata-only
manifest with placements_emitted always False.
 
CLI reproduction (from the prepared root):
 
    py -3.12 experimental/content_lanes/p2-overworld-last.py --source <stages.txt> --manifest-out <manifest.json>
 
Real-source manifest: prepared/last-p0-output/manifest-real.json.
 
## Required-inventory coverage (metadata only)
 
- terrain/collision/water: collision, waterbox, mapcode, model.
- generator day schedules and regrowth: limit_gen, loop_gen (definitions only).
- buried/enemy-held treasure: caves otakara counts, ground_otakara_max.
- Onions/ship/bridges/gates: route (no farm field exists in retail bytes).
- all cave entrances and return anchors: cave ids and filenames.

## Exact blockers (P1 prerequisites)
 
Runtime import waits on validated publications: 128, 130, 131 (actors),
132 (surface days, saves, progression), 140, 144, 145, 146. Per the
launch brief, 129 cave-generate-provider and 132 cave-multifloor-identity
are now done and integrated; surface save/progression and receipt
publications remain the P1 gate. P1 remains gated on validated surface
save/progression and receipt publications. No shared edits made here.
 
## Tests and evidence
 
tests/content_lanes/test_p2_overworld_last.py: 23 focused tests (synthetic
happy path plus closure joins, malformed and missing-input boundary cases,
plus the recorded real-bytes decode of course last). Run from the prepared root:
 
    py -3.12 -m unittest tests.content_lanes.test_p2_overworld_last -v
 
Test log: prepared/last-p0-output/test-real.log. No runtime or admission claim.
