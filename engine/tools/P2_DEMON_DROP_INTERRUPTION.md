# Demon interruption/reset native fixture (#240)

Isolated successor of238. The238 worktree, build and evidence remain unchanged.
New fixture includes the existing actor-local drop state; the only change to its
source is a main-function guard so it can be reused in this private executable.
No shared game source, registry, state ID or production hook was changed.

Frozen production base756515d57088f7ea7241c451e2e5b968bf9c7c6d.
Build02: output/demon-interruption-fixture-02/provenance.json.
EXE SHA256 e7405ee2e1fb6f21a826e1f60cf5eec7b040046291352467690995c2c15e73a6.
Session: output/demon-interruption-sessions/05c75a17f8614c3f915284d2cad8295b.
Build01 failed duplicate main compilation; retained privately, never run.

Observed sequence on the real captain, with normal production updates:
1. Drop generation1: interrupt during falling via Walk transition. Health100.
2. Generation2: real terrain bounce, interrupt JKoke before damage. Health100.
3. Generation3: real terrain/JKoke END, P1 damage100->90, interrupt Lay recovery.
4. Generation4: call production Navi::reset during falling. Cleanup cancels the
   pending drop; health90. This is the reset used by GameCoreSection at line1063.
5. Generation5: after reset and rejected prior-generation probes, complete real
   terrain/JKoke damage90->80 and GetUp to Walk. Exactly two damage events total.

Each interruption waits90 native updates, asserting stable health and that the
old fixture-state pointer is not restored. New drops increment the same persistent
policy generation. Synthetic calls to old-generation bounce and animationEnd are
rejected both after cancellation and while the subsequent generation is active.
These are explicit policy probes, not events emitted by destroyed actors.

Teardown boundary:
Navi::reset is an actual production reset, NOT object destruction/rebirth or scene
unload. NaviMgr inherits MonoObjectMgr::kill/birth, which marks pool entries and
may defer removal while referenced. The active stage/camera retain captain links;
this fixture does not bypass them or pretend pool removal is full safe teardown.
There is no enemy owner actor here, so actual owner destruction/replacement and
captain allocator reuse remain untested. Fresh generation means receiver-policy
identity on the SAME real Navi, not a newly constructed captain/owner pair.

Production implications retain238 limits: dedicated state ID instead of Flick ID;
resume/restart must preserve committed Lay across P1 damage receiver reentrancy;
external interruption must cancel before callbacks; full actor lifetime teardown
needs an explicit hook before pointer reuse. P1 InteractAttack is a compatibility
receiver, not P2 damage fidelity. Drop entry is injected, capture absent, water
and ledges excluded. No synthetic successful animation or direct HP write.

Build (MinGW bin on PATH):
py -3.12 ../p2-groink-prototype/scripts/build_pikmin2_fixture.py --build ../native-groink-policy/build-groink-runtime --source ../native-groink-policy --fixture tools/p2_demon_drop_interruption.cpp --output ../NEW-BUILD --expected-native-head 756515d57088f7ea7241c451e2e5b968bf9c7c6d

Run:
py -3.12 tools/p2_demon_interruption_run.py --root ../p2-groink-prototype --assets C:/Users/alari/pikmin-local/game/assets --room ../pikmin2-room105 --fixture ../NEW-BUILD --output ../demon-interruption-sessions

Independent review found a reset boundary worth preserving: Navi::reset does not clear actual/target/volatile velocity, ground contact or position. Scenario4 cancels pending policy damage but can continue falling under Walk during the90updates. This PASS does NOT establish physical quiescence after reset. The next injected drop overwrites position/velocities explicitly. A production adapter must assign velocity/contact cleanup to the appropriate stage/state owner; this fixture does not silently clear those values or add that behavior to Navi::reset.
