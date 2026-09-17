# tutorial_1 (Emergence Cave) P1 runtime import (#114, shard #593)

Bounded first playable-floor/runtime slice for the caves-tutorial partition. Consumes the
landed shared infrastructure: guarded cave boot fixture (#642, native pin `78e8ce9b`),
arena overlay provider (#654) and its content-line integration (#655). No new
generator/save/scoring semantics; no playability claim beyond observations; #114 stays OPEN.

## Owned files (NEW, disjoint from the P0 lane)

- `experimental/content_lanes/p2-cave-tutorial_1_p1.py` - floor-1 staging-plan adapter.
- `tests/content_lanes/test_p2_cave_tutorial_1_p1.py` - focused tests.
- `docs/content_lanes/p2-cave-tutorial_1-p1.md` - this doc.
- `native/tools/p2_tutorial1_p1_fixture.cpp` - guarded replacement-main fixture variant.

## What it does

The adapter consumes the DONE tutorial_1 P0 packet (`cave-tutorial1-p0-source-decode`,
read-only) and emits a deterministic, placement-free floor-1 staging plan
(`p2-tutorial1-floor1.json` + `p2-tutorial1-floor1.txt`). With `--runtime-inputs` it also
emits the shared #642 guarded-boot input package (`p2-cave-entry.txt`,
`p2-cave-generate.txt`, `p2-cave-runtime-inputs.json`) by calling the shared
`experimental.pikmin2_cave_runtime_inputs` renderers (no forked parser). The fixture is the
lane variant of `p2_cave_guarded_boot_fixture.cpp`: same replacement-main loop, same
vendored captain guard (#632, sha256 `d2f678c9...`) and fail-closed markers, specialised to
`P2_TUTORIAL1_P1_*`.

## Boundaries and honest status

- P0 packet pins: `user/Mukki/mapunits/caveinfo/tutorial_1.txt` sha256
  `5dae39d831ec5b68f16176cc4a54bb828aaed4a4bda10d05aef409c54987a84d`; floor 1 pool
  `1_units_north_tutorial_snow.txt`, 7 unit names, one YellowKochappy row (min 4).
- Weighted rows remain definitions; no seeded topology, holes or placements are generated.
- Floor 2, persistence and gameplay sign-off remain out of scope.
- All six runtime gates UNTESTED until the guarded floor-1 run is observed with the live
  squad and captain guard active; no playability claim is made here.

## Verification

`py -3.12 -m pytest tests/content_lanes/test_p2_cave_tutorial_1_p1.py -q` -> 8 passed.