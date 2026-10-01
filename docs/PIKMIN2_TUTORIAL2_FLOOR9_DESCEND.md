# tutorial_2 floor-9 descend admission (#807)

Bounded engine change admitting tutorial_2 floor 9 in `native/pc_port/pc_p2_cave.cpp`
entry/descend, downstream `p2-cave-tutorial_2-p1-later-floors` (#747, blocked gen 4).

## Change (owned callsite, #186 review required for landing)

Ports the accepted #757 policy pattern (TU-local mapping, shared
`pc_p2_cave_entry_policy.h` untouched) and extends it to floor 9:

- `p2_tutorial2_entry_profile`: `P2_CAVE_ENTRY_4` admits tutorial staged
  floors 3-9 under the 32-hex token contract (was 3-8).
- `p2_tutorial_descends`: floors 1-8 transition downward (was 1-7); floor 9
  exits terminal (no floor 10).
- Engine-emitted `P2_TUTORIAL2_DESCEND_POLICY floor=N descend=0/1` on every
  tutorial entry, proving the decision in-band.
- `pc_p2_tutorial2_entry_check`: non-aborting header validator for the
  fixture `--check-entry` battery.
- Descend confirmation + Bulbmin-exit logic now consult the helper instead of
  the hardcoded `floorId==1` rule; Beasts arms untouched.

## Fixture

`native/tools/p2_tutorial2_floor9_descend_fixture.cpp` (adapted from the #757
pattern read-only): replacement-main harness booting `--floor 9`, guarded by
#632 (vendored guard, self-test + negative test), passing on READY + live
squad with no abort and no captain-down.

## Guard #632

`scripts/p2_fixture_captain_guard.h` sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`
(orimaDead/NaviDead/HP<=1 -> CAPTAIN_DOWN + BLOCKED), vendored into the
fixture; self-test and negative test recorded.

## Tests and build

`tests/test_pikmin2_tutorial2_floor9_descend.py` (8 fail-closed policy tests,
green). `scripts/build_p2_tutorial2_floor9_descend.py` (adapted from #757)
configures a private Ninja/MinGW build, builds `pikmin_pc`, links the
fixture, and records executable hashes.

No ADMIT. No gameplay claim beyond the observed floor-9 boot. Shared-file
landing (`pc_p2_cave.cpp`) requires #186 review before integration.
