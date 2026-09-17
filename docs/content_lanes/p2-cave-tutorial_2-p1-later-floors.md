# tutorial_2 P1 later-floor runtime acceptance (#747)

Follow-on to the DONE tutorial_2 P1 floor-1 lane (implementation-ready),
extending the runtime import to floors 2-9 plus a persistence round-trip.
Consumes the accepted tutorial_2 source locator and the DONE floor-1 lane
outputs read-only. No ADMIT; #747 stays OPEN.

## Owned files (NEW, disjoint from floor-1 lane)

- `experimental/content_lanes/p2-cave-tutorial_2_p1_later_floors.py` - floor
  2-9 staging-plan adapter (refuses floor 1: duplicate scope).
- `tests/content_lanes/test_p2_cave_tutorial_2_p1_later_floors.py` - focused tests.
- `docs/content_lanes/p2-cave-tutorial_2-p1-later-floors.md` - this doc.
- `native/tools/p2_tutorial2_p1_later_floors_fixture.cpp` - guarded
  replacement-main fixture variant (floor-parameterised).

## What it does

The adapter consumes the DONE tutorial_2 P0 packet (schema
`p2-cave-tutorial_2-p0/1`, 9 floors) and emits deterministic,
placement-free staging plans per later floor plus the shared #642
guarded-boot input package for directly entry-bootable floors. Only floor 2
is directly entry-bootable (`P2_CAVE_ENTRY_1`, floors 1-2 policy); floors 3-9
use the engine descend chain or stay blocked with the exact policy reason.
The open P0 light_a cargo blocker is floor 9 and recorded unresolved.

The fixture mirrors the floor-1 guarded replacement-main with
`P2_TUTORIAL2_LATER_*` markers, the vendored #632 guard and fail-closed
markers, floor-parameterised for floors 2-9.

## Boundaries and honest status

- Source pin: `user/Mukki/mapunits/caveinfo/tutorial_2.txt` sha256
  `05a38ab1e37c4ad11b5f48425bec3c2101ff199a4ea0b926fc9f35fde5620049`.
- Weighted rows remain definitions; no seeded topology, holes or placements.
- Floor 1 belongs to the DONE floor-1 lane; persistence providers route to
  provider shards.
- All six gates start UNTESTED; only genuinely observed facts flip a gate.

## Verification

`py -3.12 -m unittest tests.content_lanes.test_p2_cave_tutorial_2_p1_later_floors` -> 9 passed.
