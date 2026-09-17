# tutorial_3 P1 runtime import (#153, shard #593)

Bounded first playable-floor/runtime slice for the caves-tutorial partition. Consumes the
landed shared infrastructure: source locator (tutorial_3.txt sha256
`adcc816653957fbf00919c313291142cb110b5479c7790d997399e380c9b1abb`), guarded
cave boot fixture (#642, native pin `ab81cf5d`), arena overlay provider (#654) and
its content-line integration (#655). No new generator/save/scoring semantics; no
playability claim beyond observations; #153 stays OPEN.

## Owned files (NEW, disjoint from the P0 lane)

- `experimental/content_lanes/p2-cave-tutorial_3_p1.py` - floor-1 staging-plan adapter.
- `tests/content_lanes/test_p2_cave_tutorial_3_p1.py` - focused tests.
- `docs/content_lanes/p2-cave-tutorial_3-p1.md` - this doc.
- `native/tools/p2_tutorial3_p1_fixture.cpp` - guarded replacement-main fixture variant.

## What it does

The adapter consumes the DONE tutorial_3 P0 packet (schema
`p2-cave-import-p0-1`, 8 floors, read-only) and the hash-pinned source
locator, and emits a deterministic, placement-free floor-1 staging plan
(`p2-tutorial3-floor1.json` + `p2-tutorial3-floor1.txt`). With `--runtime-inputs` it also
emits the shared #642 guarded-boot input package (`p2-cave-entry.txt`,
`p2-cave-generate.txt`, `p2-cave-runtime-inputs.json`) by calling the shared
`experimental.pikmin2_cave_runtime_inputs` renderers (no forked parser). The fixture is the
lane variant of `p2_cave_guarded_boot_fixture.cpp`: same replacement-main loop, same
vendored captain guard (#632, sha256 `d2f678c9...`) and fail-closed markers, specialised to
`P2_TUTORIAL3_P1_*`.

## Boundaries and honest status

- P0 packet pins: `user/Mukki/mapunits/caveinfo/tutorial_3.txt` sha256
  `adcc816653957fbf00919c313291142cb110b5479c7790d997399e380c9b1abb`; floor 1 pool
  `3_MAT_nor4_hit2_blk1_snow.txt`, 13 exact tokens (KareOoinu_l 4, KareOoinu_s 3,
  YellowKochappy 2, Fart 2, YellowChappy 1, Wakame_l 1), treasure count 2
  (Xmas_item, teala_dia_a recorded but no transport claimed), 2 cap slots.
- Weighted rows remain definitions; no seeded topology, holes or placements are generated.
- Floor 2-8, persistence and gameplay sign-off remain out of scope.
- All six runtime gates UNTESTED until the guarded floor-1 run is observed with the live
  squad and captain guard active; no playability claim is made here.

## Verification

`py -3.12 -m unittest tests.content_lanes.test_p2_cave_tutorial_3_p1` -> 8 passed.
