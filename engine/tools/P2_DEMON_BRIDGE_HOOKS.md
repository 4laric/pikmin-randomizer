# P1 captain bridge review contract (#226)

Prototype only, based on dad7449f. New pc_p2_demon_bridge.cpp/h compile against
frozen native756515d5. This is NOT a linked/live-tested capture implementation.
Root owns shared edits and must test the hooks before enabling the bridge.

The record supports one native captain, exclusive owner-generation token and
slot0/1. Acquire accepts only living Walk with no existing stick/rope; releases
the squad and starts P1 FALL. It uses explicit registration, not a fake rope
or P1 generic mouth branch. Caller must reflect accepted bind into its own
slot occupancy and clear it when pc_demon_bound becomes false. A true bind is
bridge registration, not evidence of a complete source InteractSarai receiver.

Owner token must be globally unique across owner lifetimes. Invalidate it with
owner_lost BEFORE destruction; this never dereferences stored owner memory.
Owner loss immediately revokes the binding without calling captain methods;
normal captain hooks resume fallback. For explicit release animation cleanup,
call release with a known-live captain before owner_lost. Call forget BEFORE captain
destruction/scene teardown, before its address can be reused. Only callbacks
for a known-live current Navi may call functions that dereference it.

Interruption/death detection revokes registration without overwriting the
new state's velocity/animation. Explicit release while still Walk clears
capture velocity and re-enters Walk. This is P1 fallback, not source SaraiExit:
source airborne exit, collision gating and escape input are still pending.

Precise proposed hook changes in src/plugPikiKando/navi.cpp (serial root review):

```cpp
// include pc_p2_demon_bridge.h under PIKI_PC_PORT.
// Navi::update: guard updateWalkAnimation so it cannot replace FALL.
if (!pc_demon_bound(this)) updateWalkAnimation();
// Keep mNaviAnimMgr.updateAnimation and controller update running.
// At the existing Creature::update call (after controller update):
if (!pc_demon_apply(this)) Creature::update();
// Keep mapMgr->updatePos after this branch. Audit cell/collision bookkeeping
// normally performed inside Creature::update before accepting this bypass.

// Navi::doAI: before ordinary state-machine execution:
if (pc_demon_bound(this)) return;

// Navi::draw: before the existing mRope / makeSRT matrix selection:
if (pc_demon_draw_matrix(this, mWorldMtx)) {
    // Full source mouth orientation/scale already supplied.
} else if (mRope) {
    // existing rope branch
} else {
    // existing SRT branch
}
```

Do not paste a broad return at the start of Navi::update: it would skip
controller and animation work. Publish fresh owner world-mouth pose before
captain apply/draw. Pause/movie boundaries require release or consistent
update suspension; callback hooks must not revive stale scene registrations.
The bridge does not yet schedule escape/RNG or source SaraiExit atari changes.

Required runtime tests: normal unbound fallback, accepted capture pose across
multiple frames, competing owners/slots refused, explicit release, owner-loss,
Flick/Dead interruption preserving their state, captain address reuse/reset,
and animation/controller/collision consistency. Existing display copies are
not substitutes. No shared source or game binaries are modified by this slice.
