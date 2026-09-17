# Challenge persistence engine membership (issue #725)

Lane `challenge-persistence-engine-membership-native`. Owner: Codex through
shared account 4laric. Adds the #713 persistence recorder module to the
`pikmin_pc` target and proves the production engine emits the 7 probe markers.

## Why

`p2-challenge-ch_mat_route_rover-p1` (#561, blocked gen 14) adopted the #718
callsite chain and booted run-19: base P1 passes but 0/7 markers. Cause: the
#718 callsite in `pc_port/pc_bbft.cpp` references the recorders WEAKLY, and the
#713 module `pc_port/pc_p2_challenge_persistence.cpp` was not in
`PC_PORT_SOURCES`, so the weak references resolved null and the engine never
emitted markers. Membership was explicitly left to #186.

## Change (owned files; #713/#718/#710 read-only)

- `native/CMakeLists.txt`: added `pc_port/pc_p2_challenge_persistence.cpp` to
  `PC_PORT_SOURCES` next to the other challenge TUs (shared CMake change;
  **#186 owner review required before any shared-line landing**).
- `native/tools/p2_challenge_persistence_membership_fixture.cpp`: new guarded
  replacement-main fixture. It does NOT compile the module in; it only includes
  the header and calls the recorders, so the link requires the CMake
  membership (strong references). It then drives the real `pc_bbft_update()`
  callsite for `ch_MAT_route_rover`.
- `scripts/build_p2_challenge_persistence_membership.py`: private leased
  build/run helper (builds `pikmin_pc`, compiles the fixture, links through a
  rewritten Ninja response file, runs the guarded marker observation).
- `docs/PIKMIN2_CHALLENGE_PERSISTENCE_ENGINE_MEMBERSHIP.md`,
  `experimental/pikmin2_challenge_persistence_engine_membership.py`,
  `tests/test_pikmin2_challenge_persistence_engine_membership.py`.

## Membership proof (two independent facts)

1. Link-time: the fixture references `p2challengepersist::selectStage` and
   `compute_score` strongly and does not compile the module, so a successful
   link is only possible when `pc_p2_challenge_persistence.cpp` is a real
   `pikmin_pc` member. The build log shows
   `[396/571] Building CXX object CMakeFiles/pikmin_pc.dir/pc_port/pc_p2_challenge_persistence.cpp.obj`
   and `pikmin_pc` links (`bin/nectar.exe`).
2. Run-time: the production `pc_bbft_update()` callsite emits the exact 7 probe
   markers for the selected stage.

## Compiled evidence (leased private build)

Lease token `828e00c6...` on `build:...\output\challenge-persistence-membership-build`
(private dir; cap read live). Native commit `22785c69` on
`codex/autofill-challenge-persistence-engine-membership-native` at base
`93603dc2`.

- `ninja -n pikmin_pc` -> "no work to do." (`fixture-build/ninja-dry-run.log`).
- Fixture executable sha256
  `8bf00dc64364a87c27573a0fd0fbf5acfca9f90a8f5816d6ccd9594d99cb1297`.
- Run: exit 0, `PASS P2_CHALLENGE_PERSISTENCE_MEMBERSHIP_RUN markers=7`, exact
  7/7 lines `P2_CHALLENGE_{SAVE_KEY,LOAD_KEY,CLEAR,HIGHSCORE,UNLOCK,RECEIPT_DEDUP,REENTRY} stage=ch_MAT_route_rover`,
  no `P2_FIXTURE_CAPTAIN_DOWN`, no refusal. Log sha256
  `908d68285b12d90c628c35faa433aeef0f0755942748e213bcf701dac94cbb66`.
- Captain safety #632: guard `scripts/p2_fixture_captain_guard.h` sha256
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`
  (vendored read-only; `--guard-self-test` and `--guard-negative-test` modes;
  a guard trip exits BLOCKED/86). No guard provider created.

## Downstream / gates

Consumer `p2-challenge-ch_mat_route_rover-p1` (#561) observes 7/7 markers, then
save/reload acceptance. All six runtime gates UNTESTED. No ADMIT, no consumer
edits, no #710 edits, no shared-line landing.
