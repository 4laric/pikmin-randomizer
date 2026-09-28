# forest_1 P1 gen-12: legal assets + REAL floor-1 geometry boot

Attempt c70048f32624b6deed69d515910c66b48c5144ec4e609cb573e2af92bc1fa466,
generation 12. Consumed forest1-legal-asset-staging (#681) and closed both
remaining geometry/asset gaps for the floor-1 boot.

## Consumed + staged

- Cherry-picked bdc07f7c (411ab0b6) into the private root tree: helper +
  tests + doc, 59 lane tests pass (log 4d55a116...).
- Staged the 23 present legal members from the local disc
  (C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso) into
  out/legal-assets: caveinfo forest_1.txt + floor-1 unit pool + 7 unit
  arc/texts archives + Kando/forest course archives + Abe/forest route.
- Decoded REAL floor-1 unit geometry from the staged pool with the shared
  `unit_definition` parser: item_cap_tsuchi [1,1] k0, way3/4/l/2_tsuchi
  [1,1] k2, way2x2 [1,2] k2, room_cent3_4_tsuchi [5,5] k1 + real doors.

## Observed boot (real geometry, canonical runner)

run-forest1-realgeom: exit 0 in 2.406s. P2_CAVE_READY floor=1 survivors=20;
POOL units=7; GENERATE_LINKS total=36 symmetric=36 (real door links all
resolve); SPAWN UjiA 6 + UjiB 4 (roster minima); GENERATE_PASS rooms=7
spawns=2 links=36 anchor=hole; BOOT_PASS squad_alive=20; PASS
CAVE_GUARDED_BOOT; no CAPTAIN_DOWN; 960x540 centred.

Negative (forced captain-down, same inputs): exit 86 in 1.594s,
P2_FIXTURE_CAPTAIN_DOWN, no PASS.

## Honest limits / remaining

- Room topology (one room per unit, +x spaced, turn=i%4) and anchor kind
  (hole) remain STAGED harness shaping; unit cells/kind/doors are now real.
- No actor births, combat, collision-contact or route traversal observed:
  all six arena gates remain UNTESTED. No playability claim; no ADMIT.
- Handoff out/handoff-gen12.json validates green except the no-work Ninja
  dry run: the private build tree is stale and a fresh leased rebuild is
  queued behind live heavy builds. One lease+rebuild+re-run from submission.
