# Naturally scheduled Snow chase observation (#120)

The private fixture in `experimental/pikmin2_snow_natural_chase.py` observes 200 ordinary engine updates with Snow AI, animation, acceleration, collision and rotation enabled. It makes no direct chase, turning or acceleration calls and writes no enemy state, motion, direction or target. The captain is placed 70 units west of the existing enemy, then moved 80 units north of its current position after 20 observed active chase ticks. Unrelated Pikmin are initially moved away; their AI is not frozen either.

## Source expectations

Native `src/plugPikiNakata/taichappy.cpp` constructs the reused P1 proxy FSM. State 15 (initial wait) and state 6 check `TaiTargetVisibleNaviPikiAction`, transitioning to state 10. State 10 advances to state 11. State 11 includes `TaiTracingAction(TekiMotion::Move1, TPF_RunVelocity)`, then combat/territory/visibility/lost-target checks. State 8 is attack and state 12 is the homeward path. `taijudgementactions.cpp` acquires a target through `getClosestNaviPiki(TekiVisibleCondition(...))` and writes its target pointer internally. Those are the paths being observed, not fixture-assigned states.

The optional `p2-snow-chase.txt` profile only changes the registered Snow's tracing steering. Normal P1 target selection, state ordering and animation still schedule the action. Therefore a successful natural chase demonstrates integration into this proxy FSM, not native Pikmin 2 AI parity.

## Acceptance and use

The log records state, target-is-captain, animation index/frame, facing, desired/current velocity, position, ground, delta time and stimulus phase. Evidence requires at least 30 state-11/Move1/captain-target chase observations (20 before and 10 after the stimulus change), actual movement, animation advancement, turning and grounded finite values. All 200 observations must show an unfrozen enemy. The opt-in mode additionally checks the observed horizontal desired speed of 50. State transitions are reported rather than rewritten to satisfy a test.

Use `python -m experimental.pikmin2_snow_natural_chase instrument --source <immutable-native>/tools/preview_p2_room.cpp --output <private-fixture>/preview_p2_room.cpp`, compile/link against matching privately snapshotted native objects, then `run` with `--assets`, `--converted`, `--pod`, `--snow`, `--exe` and a fresh `--output` directory. Pass `--policy` for the opt-in run; omit for baseline. The binary SHA256 is recorded with evidence. This fixture does not alter live playtest bundles or production native sources.

Uneven terrain, campaign balance and P2 FSM parity remain outside this test.

## Recorded native validation

Native `d1efd5ac`, privately copied 45 link inputs with before/copy/after hash checks and matching archived source/headers. The current Ninja production object list was compared with the recipe: the only intentionally omitted object was the production `pc_main`, replaced by the fixture. Snapshot manifest and recipe: `output/p2-natural-chase/snapshot/`. Private executable SHA256: `63d0c9efae8f948275a7c5ca09c932cfa962bb8d1ea9d309886f02f2681c373f`.

Both `output/p2-natural-chase/opted/evidence.json` and `baseline/evidence.json` passed with exit 0. Both began in naturally selected state 6, acquired the captain into state 10 at the first observed tick, and entered state 11 with advancing Move1 animation. Both produced 39 active captain-target chase observations: 20 before and 19 after the captain stimulus moved. All 200 observations in each run showed unfrozen AI and zero ground-height error.

| Observation | Opt-in | Absent profile |
|---|---:|---:|
| Observed simulation delta-time sum | 6.3290 s | 6.2737 s |
| Maximum displacement from first observation | 63.6334 | 48.0248 |
| First moving chase tick | 62 | 60 |
| States observed | 4, 8, 9, 10, 11 | 8, 10, 11 |

Immediately after the northward stimulus move, opt-in desired horizontal velocity remained on a turning arc: approximately `(-49.2979, 8.3497)` and facing advanced by 10 degrees. Baseline desired velocity changed directly to `(0, 50)` while ordinary native facing caught up. Subsequent actual positions and current velocities advanced in both modes. Desired horizontal speed was 50 throughout the opt-in chase samples.

Initial positions, facing, animation phase and delta times differ because the AI had already run naturally before observation. These runs establish integration and behavior, not a controlled timing or distance comparison. The native FSM continued into attack/recovery-related states instead of being held artificially in chase. The 33 focused natural-observer/chase-policy tests pass.
