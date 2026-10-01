# Demon production receiver plan — #241

Source-only review of current native `2c08d6b8d6d085318f239c07297be0bb5c33dbdf`, frozen #238 worktree `output/native-demon-drop-fixture` (71f69b48), and #240 `output/native-demon-drop-interruption` (10739e96). No native or fixture edits/builds. Paths below are relative to `C:/Users/alari/pikmin-randomizer/native`, unless marked frozen.

## Decision: dedicated registered state, narrow compatibility receiver

Append PC-only `NAVISTATE_DemonDrop = 36` immediately before Count in `include/NaviState.h:55`; keep existing IDs0–35 unchanged and non-PC Count36. Register exactly one `NaviDemonDropState` from `NaviStateMachine::init` (`src/plugPikiKando/naviState.cpp:79`) after `create(NAVISTATE_Count)`. Do not override Flick8, manually install a stack-owned current-state pointer, or touch state-machine indexing generically. `include/StateMachine.h:75` calls cleanup before assigning/initializing the next state; its index lookup precedes effective validation, so admission must never transit to an unregistered ID.

A new isolated `pc_port/pc_p2_demon_drop_state.{h,cpp}` owns the policy, captain-lifetime generation and receiver-delivery guard. Registration/factory and bridge admission are the only entry route. Validate live captain/current allowed state/no rope/no stick, finite release position and nonnegative configured damage, then detach capture ownership before transiting. Maintain generation across cancellation; do not recycle generation1 on every reset or rely on raw pointer equality. `P2DemonDropPolicy::begin` permits negative damage as a no-damage drop; production admission should reject negative payloads explicitly. Do not interpret the compatibility receiver as retail P2 damage fidelity.

## Same-frame reentrancy is part of the normal route

`src/plugPikiKando/navi.cpp:2609` InteractAttack rejects `isDamaged`, calls `startDamage`, then subtracts health, updates gauge, and starts Damage motion. `startDamage:364` calls current-state `invincible`, starts effects, sets damaged, then synchronously invokes state `resume`. `handleAnim` at1128 sends the event to the state **first**, then on the same KEY_Finished calls `finishDamage` if damage is now set. `finishDamage:424` clears damaged and invokes current-state `restart` before possibly transiting to Dead for health<=1. Consequently a Knockdown END that calls InteractAttack can receive both resume and restart before its outer animation handler returns.

Minimal state contract:

1. Check current state, owner/captain generation, expected policy phase and originating animation identity. Commit Knockdown→Lay and consume pending damage before stimulating the receiver, as frozen policy already does.
2. Set an RAII delivery guard; stimulate the real InteractAttack once. `resume`/`restart` during this owned delivery must preserve committed Lay, pending=0, recovery clock and generation. They must not call init, clear the policy, restart Knockdown or transit Walk. Do not globally override Navi damage handling.
3. After receiver returns, re-read captain liveness/current state/generation. If callbacks already changed ownership, return without touching animation/state/physics. A rejected receiver is still a consumed delivery attempt; record rejection and never retry the damage. Respect existing invincibility/recent-damage behavior.
4. A later Damage END outside the delivery guard also must not reset Lay/GetUp. `restart` should be phase-preserving while the registered drop state owns the current generation. Distinguish external damage in `resume`: cancel the pending drop before allowing the ordinary interrupt route, rather than preserving an uncommitted future impact. Exact external-damage fallback needs a small state-local decision, not global receiver replacement.
5. Match END to animation serial/token, not only motion enum: a stale event for the same motion in a newer generation must fail. The P1 event itself has no policy generation; derive/capture an animation issuance token in the adapter. Do not claim the fixture's manually passed old-generation policy calls prove native event tagging.

Frozen #238 `tools/p2_demon_drop_runtime.cpp` installs an actor-local state with Flick ID, no resume/restart overrides, real terrain bounce and actual InteractAttack. #240 tests cancellation during fall/Knockdown/Lay and Navi::reset, then90 normal updates. These establish no duplicate HP event in that fixture, not registered-state integration or physics quiescence.

## Physics ownership: do not zero everything in generic cleanup

`Creature::resetPosition` (`src/plugPikiKando/creature.cpp:479`) assigns position and last position only. `Navi::reset:579` transits Walk at607 without clearing actual/target/volatile velocity, ground/previous contact or position. `NaviWalkState::init:557` starts Walk animation, not a physics reset. `Navi::doKill:1836` is empty. Therefore neither reset, Walk nor doKill alone establishes safe removal of drop-owned physics.

Actual movement details:

- `Creature::update:645` performs animation/AI before movement. Around760 it saves `originalVel`, runs `moveNew` using volatile velocity, restores saved actual velocity at773, then runs normal `moveNew`. A bounce callback in the first pass cannot permanently clear actual velocity: the saved value is restored afterward. Volatile is finally cleared at818. `Navi::update:1056` calls this whole routine; a narrowly gated post-call adapter can clear residual owned velocity after both passes, but cannot undo already applied displacement.
- `creatureMove.cpp:151` clears current ground before tracing;213 clears platform for trace. At278 a bounce requires current ground and **no previous triangle**;314 saves current into previous. `Navi::bounceCallback:1709` emits MsgBounce with a fixed up normal. Dynamic platform bounce is filtered unless its owner is a WorkObject. Thus a test on dry static floor is not moving-platform or water acceptance.
- `Creature::moveAttach` at `creatureMove.cpp:84` can dereference/apply the previous `mCollPlatform` before a later trace rebuilds contacts. This is a separate function, not the start of moveNew. `mGroundTriangle`, `mPreviousTriangle`, `mCollPlatform` and position-fixed flags have distinct ownership; clearing only current ground is insufficient after teleport/scene disposal.
- `Creature::calcVelocity` around1259 projects target velocity using ground normal/slip code and includes `_B0` before acceleration. Position fixing around779 can pull toward `mFixedPosition`. Do not claim writing targetY alone defines physical falling or that zero actualY means stable contact.

Use explicit disposition, not a universal cleanup reset:

| Boundary | Required ownership action |
|---|---|
| Capture release into drop | Revoke mouth binding first; reject rope/stick. Assign drop velocities once, zero inherited volatile, invalidate current+previous ground and stale platform; clear on-ground/position-fixed status, establish current position as fixed reference if fixing will be restored. Retain normal gravity/collision. Verify actual trace behavior. |
| Real bounce into Knockdown | Consume bounce once; retain fresh terrain contact. Request post-physics quiescence for the owned generation so first-pass saved velocity cannot survive. Do not null floor every frame or create repeated bounce. |
| Lay/GetUp | State controls locomotion commands; post-Creature-update hook removes residual drop velocity only while same state/generation still owns it. Preserve collision system's valid ground; slopes/externally applied impulses remain explicit test cases. |
| Completed grounded recovery | Cancel policy/binding before Walk; clear remaining drop-owned commands while preserving valid current contact. No global contact reset. |
| External Flick/Press/Bury/Geyser/death transition | Cleanup cancels policy and callbacks first. Do not indiscriminately zero incoming state's impulse: some interactions write data before transit and next init owns new motion. Explicit handoff reason or pre-transition adapter decides whether inherited drop velocity is preserved, replaced or quenched. |
| Reset/teleport/scene exit | Explicit adapter invalidates token before reset; clear drop-owned velocities and map contact references while captain/map are still valid, before scene resources disappear. Scene owner provides safe destination; zero velocity alone does not stop gravity at altitude. No teleport fabricated by the receiver. |
| Captain/owner teardown | Invalidate registry before pointer reuse. Owner loss synchronously revokes capture; captain teardown clears receiver handle. No dereference after manager destruction. Navi::reset is not destruction and NaviMgr pool removal is not complete scene teardown. |

## Exact minimal shared hook surface

1. `include/NaviState.h`: PC-only appended state ID; factory/class declaration may live isolated.
2. `src/plugPikiKando/naviState.cpp:79`: registration only. Preserve every existing state.
3. New state module + CMake source entry: generation, policy, real receiver, expected animation token, state-local interruption guard and explicit physics disposition.
4. Existing optional Demon bridge release/admission (`pc_p2_demon_bridge.cpp` in frozen240): replace Walk/Fall side channel only after validating dedicated registered state; detach old binding before transit. Do not enable owner destruction side effects globally.
5. `src/plugPikiKando/navi.cpp:1056`: narrowly gated post-Creature-update quiescence hook, conditional on same owner generation; no behavior for ordinary captains. Needed because state callback writes can be overwritten inside the two-pass routine. Initial implementation may omit this hook only if actual runtime proves an equally safe state-owned alternative; do not assume exec zero suffices.
6. `Navi::reset:579`: cancel/invalidate and apply explicit reset disposition before Walk transition, only if drop owns captain. Audit actual captain manager teardown/scene cleanup callsite before adding the separate lifetime revocation hook; do not treat empty doKill as proof every teardown passes through it.

No required edits to generic StateMachine, InteractAttack, Creature physics or unrelated enemy receivers. If tests reveal generic interruption ordering cannot be expressed by the dedicated state, stop and propose the exact additional hook instead of changing all damage behavior.

## Required regression gates before enabling production

- PC registry unique ID36/Count37; non-PC IDs/count unchanged; real ordinary Flick/Bomb controls remain correct.
- Real registered state performs fall→one terrain bounce→Knockdown END→one accepted InteractAttack→Lay→GetUp→Walk, including same-stack resume and outer restart. Record phase/generation/HP at each nested callback.
- Invincible/recent-damage rejection consumes one attempt without retry; fatal damage reaches Dead without later Walk revival; unrelated incoming attack before and after commit cancels/interrupts as specified.
- Duplicate bounce, stale END, same-motion older-generation END, reset during each phase, owner loss, captain manager reuse, scene unload: no callback/HP delivery or stale handle after revocation.
- Measure actual/target/volatile velocity, position, ground/previous triangle, platform and fixed flags before each physics pass and after Navi update. Cover bounce in volatile pass and normal pass; reset while high above floor; grounded reset; no repeated landing damage or stale platform dereference.
- Slippery slope, ledge, moving platform and water are separate gates. First release can remain explicitly dry-static-floor only; never inherit a broad success claim from238/240.

This audit enables a narrowly scoped implementation review. It does not enable production Demon behavior or claim P2 receiver fidelity.
