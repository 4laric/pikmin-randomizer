# Groink private live-target fixture (#208)

Base 77f63eac. Ordered implementation c39fde6f, bb8b0413. The new fixture
reads current Navi position/alive state and passes it through the corridor
and END policies. It starts Attack on acquisition, repeats only after a
successful fresh END query, and selects WalkPath after a controlled loss.

Private build groink-target-runtime-fixture-02 passed source/input freshness
checks against stable native-groink-policy 756515d5. Reproduce from this
worktree with MinGW bin on PATH:

```
py -3.12 ../p2-groink-prototype/scripts/build_pikmin2_fixture.py --build ../native-groink-policy/build-groink-runtime --source ../native-groink-policy --fixture tools/p2_groink_target_runtime.cpp --output ../NEW_FIXTURE --expected-native-head 756515d57088f7ea7241c451e2e5b968bf9c7c6d
py -3.12 tools/p2_groink_volley_run.py --root-worktree ../p2-groink-prototype --assets C:/Users/alari/pikmin-local/game/assets --room ../pikmin2-room105 --stage ../groink-arena-stage-02 --fixture ../NEW_FIXTURE --output ../groink-target-runtime-sessions --expected-contact floor
```

Passed session on 2026-09-13:
groink-target-runtime-sessions/353fb2136cda410e899acf06f12aa7a8.
verification.json records hashes for the executable, provenance, model,
profile, room, logs and captures. Generic runner checks six distinct terminal
slots, two primary shells, reset and captures. Additional stdout markers were
checked separately:

- Query tick 0: living Navi (0,0,100), found.
- Fires tick 42 and 156, both source cursor frame 26.
- END tick 115: target still found, state Attack.
- After second fire: injected relocation to (100,0,100).
- END tick 229: target absent, state WalkPath.
- Six floor impacts, 96 traces, two acquisitions; LIVE_TARGET_PASS.

First fixture run 7f5df94292734e6f89d1cd40ea642d7a failed its repeat assertion:
the unpinned captain had moved to (42.943,0,132.845) and correctly failed the
strict lateral corridor test. bb8b0413 pins test placement every idle call;
the original failed run remains preserved and is not acceptance evidence.

Limits: only one Navi candidate, point-sphere broadphase approximation,
stationary zero-yaw owner, pinned placement and injected relocation. There
is no searched-target success branch in this fixture. WalkPath is selected
but not executed. The model is still baked frame 25; inspected flight capture
shows the actor and captain but does not resolve the debug shells. Materials,
animated muzzle alignment and full projectile visibility remain unvalidated.
This is live actor snapshot evidence, not natural pursuit or combat.

Independent source review confirmed phase order and decision wiring. No
shared hooks/build/export were changed. Next receiver work must account for
P1/P2 interaction differences documented in P2_GROINK_RECEIVER_AUDIT.md;
do not treat similarly named Bomb/Wind classes as equivalent. Death/corpse/
revival and scene lifecycle remain open.
