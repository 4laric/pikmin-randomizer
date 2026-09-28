# tutorial_2 P1 runtime import (#152, shard #593)

Bounded first playable-floor/runtime slice for the caves-tutorial partition. Consumes the
landed shared infrastructure: source locator (tutorial_2.txt sha256
`05a38ab1e37c4ad11b5f48425bec3c2101ff199a4ea0b926fc9f35fde5620049`), guarded
cave boot fixture (#642, native pin `ab81cf5d`), arena overlay provider (#654) and
its content-line integration (#655). No new generator/save/scoring semantics; no
playability claim beyond observations; #152 stays OPEN.

## Owned files (NEW, disjoint from the P0 lane)

- `experimental/content_lanes/p2-cave-tutorial_2_p1.py` - floor-1 staging-plan adapter.
- `tests/content_lanes/test_p2_cave_tutorial_2_p1.py` - focused tests.
- `docs/content_lanes/p2-cave-tutorial_2-p1.md` - this doc.
- `native/tools/p2_tutorial2_p1_fixture.cpp` - guarded replacement-main fixture variant.

## What it does

The adapter consumes the DONE tutorial_2 P0 packet (schema
`p2-cave-tutorial_2-p0/1`, 9 floors, read-only) and the hash-pinned source
locator, and emits a deterministic, placement-free floor-1 staging plan
(`p2-tutorial2-floor1.json` + `p2-tutorial2-floor1.txt`). With `--runtime-inputs` it also
emits the shared #642 guarded-boot input package (`p2-cave-entry.txt`,
`p2-cave-generate.txt`, `p2-cave-runtime-inputs.json`) by calling the shared
`experimental.pikmin2_cave_runtime_inputs` renderers (no forked parser). The fixture is the
lane variant of `p2_cave_guarded_boot_fixture.cpp`: same replacement-main loop, same
vendored captain guard (#632, sha256 `d2f678c9...`) and fail-closed markers, specialised to
`P2_TUTORIAL2_P1_*`.

## Boundaries and honest status

- P0 packet pins: `user/Mukki/mapunits/caveinfo/tutorial_2.txt` sha256
  `05a38ab1e37c4ad11b5f48425bec3c2101ff199a4ea0b926fc9f35fde5620049`; floor 1 pool
  `3_MAT_mid1_mid2_uzu1_snow.txt`, 10 exact tokens (YellowKochappy 4, YellowChappy 2,
  Demon 2, GasHiba 2), treasure count 2 (per-floor ids unresolved in the packet).
- Weighted rows remain definitions; no seeded topology, holes or placements are generated.
- Floor 2-9, persistence and gameplay sign-off remain out of scope. The floor-9 light_a
  cargo blocker is recorded open and untouched.
- All six runtime gates UNTESTED until the guarded floor-1 run is observed with the live
  squad and captain guard active; no playability claim is made here.

## Verification

`py -3.12 -m unittest tests.content_lanes.test_p2_cave_tutorial_2_p1` -> 7 passed.
