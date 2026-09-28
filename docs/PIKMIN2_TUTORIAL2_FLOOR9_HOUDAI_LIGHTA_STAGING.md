# tutorial_2 floor-9 Houdai_light_a staging contract (#805)

Root-only staging contract binding two DONE handoffs to the consumer closure
for `p2-cave-tutorial_2-p1-later-floors` (#747). Recovery request `8e9f4d22`.
No native/shared edits, no builds, no launches, no ADMIT.

## Inputs (read-only, hash-pinned; fail-closed)

- `houdai-light-a-pin-discovery` (#782) handoff sha256
  `7fa6df04dc8a28b380844582494aa4937818a6bebb32b32b3e6ab36c0cc993df`:
  `Houdai_light_a` = enemy `Houdai` id 66 carrying item `light_a`
  (`light_a.szs` / `eq_flashlight.bmd`), on floor 9, pool
  `1_units_houdai_metal.txt`.
- `tutorial2-descend-policy-native` (#757) handoff sha256
  `3cacd9ac4cb778db1147e37ad71d257cd797d37f23bc6154b6bdebe2739f0128`:
  entry `P2_CAVE_ENTRY_4` admits floors 3-8; descend runs 1-7 with floor 8
  terminal (`native/pc_port/pc_p2_cave.cpp`).

## Consumer and re-run check (#747)

Pins root `94c0261fd81a245f357bac5e7f8414a45d608cf9`, native
`8c66708af77b9f44c8e7493ab626c7a19f0bee79`.

1. `py -3.12 -m unittest tests.content_lanes.test_p2_cave_tutorial_2_p1_later_floors`
2. `py -3.12 experimental/content_lanes/p2-cave-tutorial_2_p1_later_floors.py --packet <tutorial_2-p0-packet.json> --output <private_dir> --floors 9 --runtime-inputs`
3. guarded headed run of `native/tools/p2_tutorial2_p1_later_floors_fixture.cpp`
   floor 9 via `scripts/run_pikmin2_fixture.py`.

Expected: the floor-9 plan resolves the `Houdai_light_a` cargo (no
`unknown_cargo` refusal) and the guarded boot reaches
`P2_TUTORIAL2_LATER_PASS`.

## Recorded remaining prerequisite (not invented, not staged here)

The accepted descend policy is terminal at floor 8, so floor 9 is not yet
reachable by the engine descend chain. Closing #747 floor 9 needs a bounded
engine follow-on extending `native/pc_port/pc_p2_cave.cpp` entry/descend to
floor 9 under the canonical lease CLI, private build dir under `output/`, and
#632 captain-safety guard, before the floor-9 guarded run can be observed.
All six runtime gates stay UNTESTED; no gameplay claim.

## Verification

`py -3.12 -m pytest tests/test_pikmin2_tutorial2_floor9_houdai_lighta_staging.py -q`
-> 7 passed, including a live-handoff binding test.
