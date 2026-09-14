# Fuefuki FSM bridge policy (#245)

Successor of the #245 source audit (P2_FUEFUKI_AUDIT.md) and squad-control
interference contract (P2_FUEFUKI_INTERFERENCE_POLICY.md).
pc_p2_fuefuki_fsm.h expresses the nine source states and their transitions
as commands for a future native bridge, driving
pc_p2_fuefuki_interference_policy.h for squad ownership. It calls no
captain, Pikmin FSM, map or actor API and implements no shared hook.
Source revision: projectPiki/pikmin2 632af93787b9c95b63f0c13be32b161375ce3a96
(US GPVE01 rev 0), read-only under native/pikmin2-research.

## Host contract

- Fixed 30 Hz simulation ticks (delta = 1/30) with no wall clock; paused
  ticks are omitted, never zero-delta replayed. All randomness (Land
  teleport target/facing, fp31 landing choice), map facts (arrival,
  private-radius intruders, wall triangles, water), animation facts
  (playing flag, KEYEVENT_2/3/END of the emitting motion, isFinishMotion,
  turnToTargetPos result) and combat facts (health, stuck-attacker count,
  press/hipdrop callbacks, bittered) arrive as per-tick inputs. A rejected
  tick (nonfinite/negative delta, nonfinite health, unbound epoch) makes
  no mutation.
- State entry/exit mirrors the source init/cleanup exactly: spawn enters
  Land (teleport-to-target, NoInterrupt window until KEYEVENT_2,
  lifegauge at KEYEVENT_2, struggle arming at KEYEVENT_3); Whisle cleanup
  runs on ANY exit and ends the cast while claims persist (the new
  endCast path on the interference policy — source finishWhisle); Stay
  entry suspends followers (source ActTeki isFlying Success/emote exit;
  the releasedSuspend output carries the resolved brain
  destination -- **Free, not Formation**, via
  P2FuefukiFsmOut::suspendFallback: ActTeki::getNextAIType() returns
  ACT_Free, PikiAI.h:1254; Brain::exec routes to start(ACT_Free),
  aiAction.cpp:108-110; the stored piki->mNavi is not consulted and is
  cleared by ActFree::init, aiFree.cpp:33);
  Dead entry commits the owner-death Panic release before any host death
  callback; Dead kills at dead-anim END and the carcass uses
  FUEFUKIANIM_Carry.
- Transition precedence inside each state follows source field order:
  later checks overwrite mNextState, so Dead > Jump > Whisle > the
  state's normal next. Land and Stay have no health check in source and
  this policy does not invent one.
- Whistle cadence: whistleTimer initializes to fp12 - fp11 at Land entry
  and accumulates per tick in Wait/Turn/Walk/Struggle. isWhisleTimeMax
  uses fp12 without a squad, fp13 with a squad and no stuck attackers,
  fp12 with a squad and stuck attackers. The cast lasts the fixed source
  3.0 s (parms.castDuration; fixtures shorten it), the ring grows to
  mAttackRadius over the first second, and the post-cast next state is
  Turn with a squad, Wait without.
- Jump-away: appearTimer above fp01 always triggers; Navi/Pikmin
  intrusion into mPrivateRadius triggers only while no squad is active
  and pins appearTimer to fp01. Jump KEYEVENT_3 emits the escape burst
  (target velocity 1500 * facing, flick nearby Navi, nearby Pikmin and
  stuck attackers); Jump END enters Stay, which releases followers
  through the suspend (non-Panic) path — a landed beetle can re-cast and
  re-claim the same Pikmin.
- Struggle: press/hipdrop while canStruggle and not bittered transits
  immediately; exits are health<=0 -> Dead, no stuck attackers after the
  hard-coded 3.0 s -> Jump, or fp21 struggle time -> Jump. Cleanup
  re-arms canStruggle.
- Event-flag commands (eventSet/eventClear masks) describe source
  EB_NoInterrupt/Untargetable/Lifegauge/BitterImmune/Cullable writes;
  the host maps them to engine events and must not infer extra flags.

## Root-owned hook request specs (integration, not implemented here)

Update 2026-09-13: per the #128 ownership reassignment these specs are now
lane-owned and IMPLEMENTED by the Fuefuki binding seam — see
P2_FUEFUKI_BINDING.md (pc_p2_fuefuki_binding.h). Item 6 (motion bank)
remains with the engine lane's converter/material work (#128). The
original spec text is kept for reference:

1. Squad-whistle stimulation routing (P1 whistle -> Fuefuki candidate
   scan): a root-owned adapter that, each cast tick, enumerates P1 squad
   Pikmin inside whistleRadius (XZ, no height gate, matching source
   sqrDistanceXZ) and feeds P2FuefukiCandidate rows (living, callable
   state, mouth-stuck, already-Teki-owned). Request: read-only squad
   enumeration + candidate classification; the policy performs admission.
2. Follower action slot: root-owned binding from an accepted claim to
   starting the host's ACT_Teki-equivalent follow action on that Pikmin,
   and routing each follower's per-tick ping back as followerPings.
   Request must guarantee one controller per Pikmin (the ownership table
   enforces it) and no captain-ownership write on claim.
3. Captain whistle reclaim: root-owned interception of the P1 whistle
   receiver for Panic-released followers only, performing the source
   ownership write (clear action, assign whistling captain, LookAt
   equivalent) exactly once per reclaim. Captain switch and party combine
   must NOT be routed to beetle-held or Panic-released Pikmin.
4. Death/kill hook: root-owned delivery of health<=0 and the kill command
   at dead-anim END, plus carcass spawn with the Carry motion. Release
   ordering (ownerDied before host death callbacks) is contract-critical.
5. Intrusion/arrival probes: root-owned per-tick computation of
   private-radius intruders, wall-triangle contact and target arrival
   (XZ dist^2 < 625) as plain inputs; no geometry in the policy.
6. Motion/animation bank: converter handoff (#128 dependency) for the 10
   FUEFUKIANIM slots and key-event wiring; the policy consumes events,
   it does not schedule them.

## Fixtures and evidence

tools/p2_fuefuki_fsm_test.cpp (MinGW64 g++ -std=c++17 -Wall -Wextra
-Werror, warning-clean) covers: full spawn -> Land -> patrol -> cast ->
claim -> squad-cadence Turn -> jump-away -> Jump escape burst -> Stay
suspend -> re-Land -> re-claim cycle; ring growth to exactly
attackRadius; claims persisting past cast end; jump-away by fp01 ground
time, by intrusion without a squad, and intrusion suppression with a
squad; whistle cadence fp12 vs fp13 by squad presence and fp12 when
attackers are stuck; struggle entry, the 3.0 s stuck-empty exit to Jump,
bittered press rejection and fatal struggle exit to Dead; death routing
from Wait/Turn/Walk/Whisle and the Jump struggle window, death while
casting with Panic release and captain-whistle reclaim, dead-anim kill
plus Carry carcass, and the absence of death routing in Land/Stay;
malformed delta/health rejection without mutation. Result:
p2_fuefuki_fsm_test PASS. The interference fixtures were re-run after
the endCast addition: p2_fuefuki_interference_policy_test PASS.

    g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_fuefuki_fsm_test.cpp -o ../fuefuki-fsm-test.exe
    ../fuefuki-fsm-test.exe   # prints PASS

No live captain, native hook, map geometry, animation runtime or gameplay
acceptance follows from these fixtures. Root retains shared integration.

## Remaining open items

- Retail parm-asset values (fp01-fp31, mAttackRadius, mPrivateRadius)
  still gate fixture-realistic timing; fixtures use shortened parms.
- Land-init whistleTimer adds one delta in source; the policy starts at
  fp12 - fp11 and lets the first patrol tick supply the delta.
- Stay/Jump airborne duration, escape trajectory and landing position
  validity are host/map responsibilities with no fixture coverage.
- Brain fallback after suspend is resolved to **Free** (this lane slice;
  see tools/p2_fuefuki_suspend_fallback_test.cpp). Claim persistence
  across day/cave transitions remains open from the earlier slices.

## Test evidence (this slice)

    g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_fuefuki_suspend_fallback_test.cpp -o <out>
    <out>   # p2_fuefuki_suspend_fallback_test PASS (exit 0)

Tools/p2_fuefuki_interference_policy_test re-verified PASS; tools/
p2_fuefuki_fsm_test re-verified PASS; tools/p2_fuefuki_binding_test
re-verified PASS after the P2FuefukiSuspendOut / suspendFallback
propagation.
