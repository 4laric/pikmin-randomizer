# Fuefuki (Antenna Beetle) source audit (#245)

Source revision: projectPiki/pikmin2 632af93787b9c95b63f0c13be32b161375ce3a96
(US GPVE01 rev 0 config), inspected read-only under native/pikmin2-research.
This is a source contract only; no P1 translation, runtime fixture or gameplay
acceptance is claimed. Parent family audit: docs/PIKMIN2_FLYING_ENEMY_AUDIT.md
(#166, "Antenna Beetle: Fuefuki (41)"). Closest contract analogue for
exclusive single-controller ownership: native/tools/P2_DEMON_FORCED_DROP.md
(#236) and native/tools/P2_DEMON_DROP_POLICY.md (#237).

## Registration and classification

- EnemyID_Fuefuki = 41, "Antenna Beetle" (include/Game/enemyInfo.h:100).
- enemyInfo table row: name "Fuefuki", ID 41, flags
  EFlag_CanBeSpawned | 2 | EFlag_UseOwnID, no linked child species, class
  BDT_Strong (src/plugProjectYamashitaU/enemyInfo.cpp:69).
- Manager dispatch: EnemyID_Fuefuki -> new Fuefuki::Mgr(limit, viewNum)
  (src/plugProjectYamashitaU/generalEnemyMgr.cpp:337-338). Mgr allocates
  Fuefuki::Parms and a plain Obj array
  (src/plugProjectNishimuraU/FuefukiMgr.cpp:12-43); manager debug name
  "246-FuefukiMgr" (FuefukiMgr.cpp:6).
- Obj::getEnemyTypeID returns EnemyID_Fuefuki
  (include/Game/Entities/Fuefuki.h:44). Obj derives directly from EnemyBase;
  no shared base with other species.

## FSM

Registration (src/plugProjectNishimuraU/FuefukiState.cpp:13-26), IDs in
include/Game/Entities/Fuefuki.h:20-32:

- 0 Dead: init runs deathProcedure, zeroes velocity, starts Dead anim
  (FuefukiState.cpp:32-38); exec kills at KEYEVENT_END (44-49).
- 1 Stay: hidden airborne state — untargetable, bitter-immune, no lifegauge,
  Landing motion stopped (63-77); exec transits Land after fp03 airborne
  interval (83-90).
- 2 Land: spawn entry; teleports to a fresh target position, random facing,
  NoInterrupt until KEYEVENT_2 (lifegauge on, down-effect, water ripple);
  KEYEVENT_3 sets mCanStruggle and cullable; END transits mNextState
  (default Wait) (104-161). fp31 normal-vs-failed landing anim chance
  (124-128). Cleanup clears bitter-immunity/NoInterrupt and retargets
  (167-174).
- 3 Jump: escape hop. While mCanStruggle velocity is zero and health<=0
  transits Dead; at KEYEVENT_2 bitter-immune on; KEYEVENT_3 untargetable,
  cullable off, sets horizontal escape velocity 1500 * facing and flicks
  nearby Navi, nearby Pikmin and stuck Pikmin (shake range/knockback/damage,
  FLICK_BACKWARD_ANGLE); END transits Stay (180-259). fp22 jump-time gate
  finishes the motion early (215-217).
- 4 Wait: idle; exec picks Turn once mStateTimer>0, Whisle on
  isWhisleTimeMax, Jump on isJumpAway, Dead on health<=0 (274-317).
- 5 Turn: turnToTargetPos toward mTargetPosition (turn speed/max turn angle
  parms, 30.0 frame arg) then Walk; same Whisle/Jump/Dead overrides
  (332-377).
- 6 Walk: EnemyFunc::walkToTarget with move/turn parms; arrival
  (isArriveTarget: wall triangle or XZ distance squared < 625,
  Fuefuki.cpp:486-493) or 5 s state timer ends Walk into Turn when
  mSquadTimer>0 else Wait; same overrides (392-455).
- 7 Whisle (dev spelling): init startWhisle (cullable off, timers reset,
  effect on, Fuefuki.cpp:350-356); exec updateWhisle every frame, after
  3.0 s picks Turn (squad) or Wait (no squad), with Jump/Dead overrides
  (FuefukiState.cpp:472-516). Cleanup finishWhisle and plays
  PSSE_EN_FUEFUKI_WHISTLE_ECHO (522-528).
- 8 Struggle: entered from pressCallBack/hipdropCallBack when mCanStruggle
  and not bittered (Fuefuki.cpp:163-185); exec finishes motion on health<=0,
  no stuck Pikmin after 3 s, or fp21 struggle time; END transits Dead or
  Jump (FuefukiState.cpp:534-569). Cleanup re-arms mCanStruggle (575-580).

Initial state is FUEFUKI_Land from onInit (Fuefuki.cpp:66-79). Every
ground state checks isJumpAway and isWhisleTimeMax each frame, so whistle
and escape take precedence over locomotion.

## Whistle interference mechanic

Emission (Fuefuki.cpp::updateWhisle, 362-390):

- Radius grows linearly: mWhistleRadiusModifier += deltaTime, clamped at
  1.0 after 1 s; effective radius = modifier * C_GENERALPARMS.mAttackRadius.
  The ring is XZ-only (sqrDistanceXZ, squared radius compare) — no height
  check in the source.
- Each frame it iterates all living Pikmin and stimulates InteractFueFuki
  on any Pikmin that isAlive, isPikmin(), is not mouth-stuck
  (isStickToMouth) and is not already this beetle's follower
  (isMyPikmin(this), Piki::isMyPikmin resolves the ActTeki owner's pointer,
  src/plugProjectKandoU/piki.cpp:1229-1239).
- Radar hooks bornFuefuki/dieFuefuki/fuefuki (Fuefuki.cpp:54-60, 85-93,
  387-389; src/plugProjectKandoU/radarInfo.cpp:69-91, 185-187) drive the
  treble-clef HUD indicator; they are bookkeeping only.

Duration and cadence:

- Whisle state lasts a fixed 3.0 s minimum per cast
  (FuefukiState.cpp:491).
- Cast interval is governed by mWhistleTimer against fp12/fp13 in
  isWhisleTimeMax (Fuefuki.cpp:329-344): with an active squad timer and
  stuck Pikmin -> fp12 (max whistle interval, no-squad); with squad timer
  and no stuck Pikmin -> fp13 (with-squad); without squad timer -> fp12.
- mSquadTimer is set to 5.0 by InteractFuefukiTimerReset::actEnemy
  (Fuefuki.cpp:18-26), which each ActTeki follower stimulates on its owner
  every exec tick (aiTeki.cpp:96-99). Note doUpdate decrements mSquadTimer
  by 1 per frame (Fuefuki.cpp:103-105), not by deltaTime — the 5.0 value
  behaves as a frame count, effectively refreshed to ~5 frames while any
  follower is active. A squad therefore keeps the beetle on the
  squad-cadence branch (Turn after Walk/Whisle instead of Wait).
- While whistling the beetle is non-cullable; finishWhisle restores
  culling (Fuefuki.cpp:350-356, 396-402).

Attraction receiver (src/plugProjectKandoU/interactPiki.cpp,
InteractFueFuki::actPiki, 34-49):

- Rejects invincible-state Pikmin, non-Pikmin, and Pikmin already in
  ACT_Teki (any Teki owner — one beetle cannot steal another owner's
  followers through this path).
- Requires mCurrentState->callable() before starting PikiAI::ACT_Teki with
  the beetle as CreatureActionArg. State callability is the real admission
  gate; busy/attack/transport states decide individually.

Follow behavior (src/plugProjectKandoU/aiTeki.cpp, ActTeki):

- init stores mFollowingTeki and starts WALK motion (27-56).
- exec: owner not alive -> transit Pikmin to PIKISTATE_Panic and continue
  (62-81); owner flying (isFlying) -> ACTEXEC_Success with mToEmote
  (83-87); owner bittered and Fuefuki -> ACTEXEC_Success with mToEmote
  (89-94); otherwise stimulate InteractFuefukiTimerReset and run the
  follow test (96-100).
- emotion_success transits to PIKISTATE_Emotion(EMOTE_Excitement) when
  mToEmote (107-113).
- Following is footprint-based: the beetle records up to 10 Footmarks
  every ~2.5 frame-timer ticks (Fuefuki.cpp:499-520); ActTeki picks the
  closest footmark within FOLLOW_DISTANCE 100 of the owner, runs at speed
  1.0 beyond 100 units, 0.5-1.0 within, and re-targets through
  makeTarget/test_0/setTimer (aiTeki.cpp:8, 119-269).

Control restoration:

- Captain whistle (Navi::callPikis, src/plugProjectKandoU/navi.cpp:3260-3285)
  broadcasts InteractFue(this, doCombineParties=false, isNewToParty=true)
  to creatures inside the NaviWhistle sphere; receiver
  InteractFue::actPiki (interactPiki.cpp:68-...) has an explicit ACT_Teki
  branch (172-185): an ACT_Teki Pikmin is callable ONLY when its current
  state is PIKISTATE_Panic. A live beetle's followers therefore ignore both
  captains' whistles; a dead beetle's followers are in Panic and can be
  reclaimed by a normal whistle. The reclaim path also clears the current
  action, reassigns piki->mNavi to the whistling captain and transits
  LookAt (190-206) — this is the source's ownership-handoff write.
- Beetle defeat mid-effect: ActTeki::exec owner-death branch (aiTeki.cpp
  65-81) is the only release; there is no timer expiry while the owner is
  alive and grounded. Release is per-Pikmin via Panic, not a squad-wide
  broadcast.
- Interruption of the effect on the beetle side: onKill finishes the
  whistle effect and updates radar (Fuefuki.cpp:85-93); stone state
  (doStart/FinishStoneState) and earthquake-fit state finish and restart
  the whistle effect around the interruption (Fuefuki.cpp:191-233).
  Bittering a whistling beetle makes followers exit with Success next
  tick (aiTeki.cpp:89-94).
- Captain switch: Y-button captain swap (naviState.cpp:483-505) whistles
  the other captain with InteractFue(otherNavi, false, false);
  InteractFue::actNavi (interactNavi.cpp:233-276) moves the idle captain
  to NSID_Follow and re-broadcasts InteractFue(otherNavi, /*combine*/ true,
  true) to that captain's cell occupants, which reassigns Formation Pikmin
  ownership (piki->mNavi write). Neither path touches ACT_Teki Pikmin
  unless they are in Panic — beetle-held Pikmin are invisible to captain
  switch and party combine.

## Locomotion and death exits

- Ground locomotion is Turn/Walk toward randomized home-radius/territory
  target positions; in caves targets are 50-75 units from home at random
  angle (setTargetPosition, Fuefuki.cpp:408-434).
- Escape: isJumpAway (Fuefuki.cpp:440-480) triggers Jump when the appear
  timer exceeds fp01 max ground time, or (when no squad timer is running)
  when a Navi or non-owned, non-stuck Pikmin enters mPrivateRadius — and
  the intrusion pins mAppearTimer to max, forcing relocation.
- Death exits: health<=0 checks in Wait/Turn/Walk/Whisle/Struggle and the
  struggle-window of Jump all route to Dead; Dead kills the creature at
  Dead-anim KEYEVENT_END (FuefukiState.cpp:44-49). startCarcassMotion
  starts FUEFUKIANIM_Carry (Fuefuki.cpp:259-262), so the corpse is a
  normal carryable carcass.
- Movie boundaries only toggle effect drawing (Fuefuki.cpp:268-280);
  WaitingBirthTypeDrop hides/shows effects (239-253).

## Animation / motion bank

10 animation slots (include/Game/Entities/Fuefuki.h:160-172):
0 Dead, 1 Landing, 2 LandFail, 3 Move, 4 Pivot, 5 Wait, 6 Whisle,
7 Struggle, 8 Jump, 9 Carry. ProperAnimator is a single-animator wrapper
(FuefukiAnimator.cpp:9-21). Whistle visuals are efx::TCursor ring +
efx::TFuebugOnpa sound-wave effect (Fuefuki.cpp:526-608); whistle echo
sound PSSE_EN_FUEFUKI_WHISTLE_ECHO at cleanup (FuefukiState.cpp:527).
Model/motion conversion for the P1 host remains a converter-handoff item
(dependency #128).

## Parameters

ProperParms defaults (include/Game/Entities/Fuefuki.h:121-145);
authoritative retail values live in the enemy parm asset, not here:

- fp01 出現時間(Max) 30.0 — max ground time before jump-away
- fp02 出現時間(Min) 20.0 — min ground time (appear-timer random base)
- fp03 出現間隔 3.0 — airborne Stay interval
- fp11 フエ間隔(1) 0.0 — min whistle interval (used only in reset math)
- fp12 フエ間隔(2～:隊列ナシ) 5.0 — whistle interval without squad
- fp13 フエ間隔(2～:隊列アリ) 10.0 — whistle interval with squad
- fp21 もがき時間 3.0 — struggle time
- fp22 逃げジャンプ時間 0.0 — escape jump time
- fp31 通常出現率 0.5 — normal (vs failed) landing chance

General parms consumed: mAttackRadius (whistle radius base), mPrivateRadius
(intrusion trigger), mHomeRadius/mTerritoryRadius (target selection),
mMoveSpeed/mTurnSpeed/mMaxTurnAngle (Walk/Turn), mShakeChance/mShakeRange/
mShakeKnockback/mShakeDamage (Jump flicks), mAttackHitAngle (ring effect
spin, Fuefuki.cpp:554). Hard-coded constants: whistle grow time 1.0 s,
cast length 3.0 s, Walk cap 5.0 s, squad timer 5.0 (per-frame decrement),
arrival radius^2 625, escape speed 1500, shadow radius 50/75
(Fuefuki.cpp:142-157).

## Overlap with Snitchbug captain-ownership contracts (#226/#231/#236/#237)

- Both lanes implement exclusive single-controller ownership of creatures:
  Sarai/Demon hold creatures in mouth slots; Fuefuki holds Pikmin as
  ACT_Teki followers keyed on the owner pointer (Piki::isMyPikmin,
  piki.cpp:1229-1239). The #237 generation/admission discipline (strictly
  increasing owner epochs, admission validation before mutation,
  cancellation before teardown) maps directly onto Fuefuki owner lifetime:
  ActTeki stores a raw EnemyBase* with no generation, so a native bridge
  must invalidate followers before manager-slot reuse, matching the
  "invalidate the entire callback domain" rule in P2_DEMON_DROP_POLICY.md.
- Ownership write: the source's only captain-ownership mutation is the
  InteractFue receiver (piki->mNavi reassignment, interactPiki.cpp:205).
  Fuefuki adds a second controller (the beetle) that never writes mNavi —
  it borrows the squad through the AI-action slot instead. A faithful port
  must keep these two ownership domains distinct and must not let the
  whistle-interference path write captain ownership.
- Release-on-interruption mirrors the Demon drop contract: owner death,
  owner flying/bittered, and state interruption are separate exits and
  must not be merged; delayed/queued effects (here the timer-reset
  stimulus) must not survive cancellation.
- Captain switch (#130): source evidence shows captain switching and party
  combine deliberately cannot reclaim beetle-held Pikmin
  (interactPiki.cpp:172-185 gate on PIKISTATE_Panic). Any #245 contract
  must preserve that exclusivity — no shared writes, no whistle override
  while the beetle lives.

## Open questions / unknowns

1. ActTeki::exec returns ACTEXEC_Success for a flying or bittered owner,
   but the follow-up brain action chosen after Success is not traced here;
   whether the Pikmin rejoins the previous captain's formation or Free
   depends on PikiAI brain fallback and the stored piki->mNavi. Needs
   tracing before any release contract is written (touches #130).
2. mSquadTimer decrements per frame, not per second (Fuefuki.cpp:103-105);
   confirm intended retail cadence at 60 fps vs the decomp's deltaTime
   assumption before encoding durations in a native fixture.
3. Whistle radius uses mAttackRadius and the XZ-squared test with no
   vertical gate; verify against retail parm values (enemy parm asset,
   not the header defaults above) and decide how the P1 host expresses
   the ring (#113/#131 species/receiver fidelity).
4. InteractFueFuki admission depends on per-state callable(); the exact
   callable-state set (which P1-side squad/work states the beetle may
   steal) must be enumerated from PikiState before fixtures — stealing a
   carrier or sprout state incorrectly would violate the ownership
   contract.
5. Owner-slot reuse: ActTeki holds a raw owner pointer; death is checked
   via isAlive() only. Manager slot reuse of a dead beetle by a new
   Fuefuki instance (or by another enemy in the host) is a stale-owner
   hazard the #237 generation pattern must cover.
6. Two-beetle and beetle-vs-captain competition: ACT_Teki admission
   rejects any existing Teki follower (interactPiki.cpp:40), but
   simultaneous first-contact by two whistling beetles in one frame is
   untraced; claim ordering must be defined for the native contract.
7. Persistence: nothing in Creature::save covers ACT_Teki ownership or
   the beetle's whistle state; behavior across day/cave transitions
   (release vs preserved follow) is undefined by this audit (see family
   audit "Shared persistence").
8. Struggle/press exits (Fuefuki.cpp:163-185) and Jump flicks affect
   stuck attackers; interaction between a flicked stuck Pikmin and an
   ACT_Teki follower in the same crowd is untraced.
9. Versus-mode color gating in InteractFue::actPiki (interactPiki.cpp
   194-200) applies to captain reclaim; versus-mode Fuefuki behavior is
   out of scope for the campaign lane but noted for completeness.

No executable tests, native builds or gameplay runs were performed for
this audit.
