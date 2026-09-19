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


## Runtime evidence (floor 2 boot PASS; floors 3-9 blocked)

- Private leased build of native pin plus accepted #129 consumer landing
  (cherry-pick 21caef9a): exe `output/tutorial2-later-floors-build/p2_tutorial2_p1_later_floors.exe`;
  guard self-test 7/7 exit 0; negative exit 86 `P2_FIXTURE_CAPTAIN_DOWN`.
- Floor-2 headed guarded boot PASS: 960x540 centred window,
  `P2_CAVE_READY floor=2 survivors=20`, engine-consumed unit staging
  (`P2_CAVE_GENERATE_POOL pool=2_MAT_h335_h447_metal.txt`, real spawn ids
  BombSarai/Sarai/Bomb/Daiodo, `P2_CAVE_GENERATE_PASS rooms=1 spawns=5`),
  `P2_TUTORIAL2_LATER_PASS floor=2 squad_alive=20`, `PASS TUTORIAL2_LATER`.
- Floors 3-8 BLOCKED (mechanism, not data): the native entry policy admits
  floors 1-2 only, and `pc_p2_cave.cpp` descends solely from floor 1
  (`floorId==1?"Descend":"Leave cave"`), so no engine path reaches floors
  3+. Their staging plans validate clean and are committed for the future
  path.
- Floor 9 BLOCKED (same mechanism plus the open P0 light_a cargo
  `Houdai_light_a unknown_cargo`, which this slice refuses to invent).
- Persistence round-trip BLOCKED: needs the floor-1 lane descend handoff
  (descend originates on floor 1, owned by the DONE floor-1 lane); recorded
  here as an exact cross-lane dependency, not duplicated.


## Runtime evidence (floors 2-8 boot PASS; floor 9 + persistence blocked)

- Private leased build with the adapted #757 descend policy (ENTRY_4 floors
  3-8): guard self-test 7/7 exit 0; negative exit 86 `P2_FIXTURE_CAPTAIN_DOWN`.
- Headed guarded boots, one fresh arena per floor (20-squad baseline,
  single pr05, canonical runner): floors 2-8 ALL PASS with `P2_CAVE_READY
  floor=N survivors=20`, engine-consumed unit staging with real spawn ids,
  and `P2_TUTORIAL2_LATER_PASS squad_alive=20` + `PASS TUTORIAL2_LATER`.
  Spawn counts: f2=5, f3=6, f4=3, f5=4, f6=7, f7=6, f8=4.
- Floor 9 BLOCKED: `Houdai_light_a unknown_cargo` refused by the adapter
  (open P0 light_a blocker, not invented).
- Persistence round-trip BLOCKED: needs the floor-1 lane descend handoff
  (descend originates on floor 1); recorded as an exact cross-lane
  dependency, not duplicated.


## Generation 12: #690 walk-inside traversal integrated and observed

Integrated the accepted `yakushima4-collision-traversal-native` (#690)
prerequisite (native walk-inside grid sampling + guarded fixture; root leased
build/run harness with guard fixes). Leased configure/build/fixture/guardcheck
all green with built provenance; guard self-test and negcap(86) pass.

Real walk-inside collision traversal samples on the decoded floor-1 geometry:
`P2_YAKUSHIMA4_TRAVERSAL_PASS rooms=8 links=36 interior_contacts=39
link_contacts=58` (119 samples, 44 link steps, 0 links blocked; chain pass,
exit 0). Consumer verification accepted passed=true/prerequisite_resolved=true.

Combined floor-1 record: real guarded boot (960x540, live 20, unit staging),
authored route topology (36 NAV rows), walk-inside collision samples.
Residual: floor 9 (light_a), higher floors beyond the tutorial_2 scope,
persistence and admission.
