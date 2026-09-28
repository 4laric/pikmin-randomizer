# Demon real-captain forced-drop fixture (#238)

Private executable built from frozen native756515d57088f7ea7241c451e2e5b968bf9c7c6d
production objects plus this lineage's one-TU fixture and captured dependencies.
No shared native source, CMake, captain registry or hook patch was applied.
Build manifest: output/demon-drop-fixture-01/provenance.json.
Executable SHA256: def21e1ce5738c413f3061321d56ec6df0c5b8881bc735b938e831eade9c264b.
Private session: output/demon-drop-sessions/534310e951484514ad9061a24eb3e5be.

Observed runtime gates:
- Real Navi starts at an injected position120 above room terrain, with actual
  Y=-400 and target Y=-200. Normal Creature movement produces descent and bounce.
- Real bounce dispatch reaches the actor-local fixture state. Health remains100
  at impact. Native JKoke animation KEY_Finished drives the damage command.
- Normal P1 InteractAttack receiver accepts10 damage at that event: health100->90.
  No direct HP write, fabricated successful animation event or bounce injection.
- Normal timer and GetUp animation completion return the captain to Walk.
- A second drop reaches terrain; explicit Walk interruption cancels its pending
  knockdown damage. After90 native updates health remains90 and damage count1.
- A deliberately stale policy END probe is rejected after cancellation. This is
  a policy rejection test, not an injected native animation success.

Limits and fixture interventions:
The entry point injects a drop and temporarily installs an actor-local NaviState
with the Flick ID. It does not replace the registered production Flick state.
This is a receiver experiment, not a Bumbling Snitchbug actor or real capture.
The state uses production AI message dispatch, physics, terrain and animations.
It omits P2 impact addDamage(0,true) and water effects. P1 InteractAttack may change
animation/damage cooldown and is not equivalent to P2 KokeDamage. Generation and
phase guards are narrow fixture safeguards; full actor/scene lifetime remains open.
No screenshot/visual-fidelity gate is claimed. Fixed assets remain private.

Build from this worktree (MinGW bin on PATH):
py -3.12 ../p2-groink-prototype/scripts/build_pikmin2_fixture.py --build ../native-groink-policy/build-groink-runtime --source ../native-groink-policy --fixture tools/p2_demon_drop_runtime.cpp --output ../NEW-BUILD --expected-native-head 756515d57088f7ea7241c451e2e5b968bf9c7c6d

Run into a fresh session:
py -3.12 tools/p2_demon_drop_run.py --root ../p2-groink-prototype --assets C:/Users/alari/pikmin-local/game/assets --room ../pikmin2-room105 --fixture ../NEW-BUILD --output ../demon-drop-sessions

## Separate integration hook request

Do not install this fixture state as production Flick or silently apply the
existing escape-only landing patch to forced drops. Root owns the production
adapter. The minimal eventual hook boundary is: accepted owner-qualified drop
request -> dedicated receiver state; existing MsgBounce and MsgAnim delivery ->
that state; cleanup -> cancel; scene teardown -> invalidate callback generation.
Navi's existing message dispatch already provides bounce and animation callbacks,
so this experiment needs no shared update/draw patch. A production registration
patch depends on root's choice of dedicated state ID/adapter and is not fabricated
here. Existing #226/#231 hook patch remains separate and escape-only. Capture
slot revocation must occur before this receiver is entered, without zeroing the
final actual/target velocity afterward. Map P2 damage semantics before fidelity
acceptance; this P1 attack-receiver experiment is insufficient for that claim.

Final runner adds its own and preview-helper hashes. Fresh provenance-complete session output/demon-drop-sessions/a1efddf098464c1db2e389af050f4de3 also passes the same scoped native gates; first session is preserved.

Independent review confirmed the native dispatch and observed log, with no fixture blocker. Production must use a dedicated state ID: Flick ID can misclassify the actor in other callers. InteractAttack reenters state resume through startDamage; after MsgAnim returns, Navi's KEY_Finished path calls finishDamage and state restart. This fixture inherits no-op resume/restart. A production receiver must explicitly preserve the committed Lay phase through both callbacks and the Damage motion change. Source references: navi.cpp1129-1135 and2609-2632, StateMachine.h61-96, creatureMove.cpp151 and278-284.
