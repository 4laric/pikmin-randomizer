# Pikmin 2 Careening Dirigibug (BombSarai) source audit (#244)

## Scope and provenance

This is a source audit of the native `pikmin2-research` checkout at revision `632af93787b9c95b63f0c13be32b161375ce3a96` (remote `projectPiki/pikmin2`, US GPVE01 rev 0). Paths below are source-relative to that checkout; numbers in parentheses are function-start lines at that revision. No runtime implementation, native build or gameplay test is implied. This document extends the one-paragraph BombSarai summary in [PIKMIN2_FLYING_ENEMY_AUDIT.md](PIKMIN2_FLYING_ENEMY_AUDIT.md) (#166) and the shared Bomb coverage in [PIKMIN2_CANNON_GROINK_AUDIT.md](PIKMIN2_CANNON_GROINK_AUDIT.md) into the full lane checklist required by #244.

## Registration and classification

`EnemyID_BombSarai = 58` ("Careening Dirigibug") is declared in `include/Game/enemyInfo.h:117`. The roster row at `src/plugProjectYamashitaU/enemyInfo.cpp:46` sets `mParentID = -1`, `mMembers = 1`, flags `EFlag_CanBeSpawned | 2 | EFlag_UseOwnID` (the unnamed `2` bit is noted as inert in `enemyInfo.h:28-32`), `mChildID = EnemyID_Bomb` with `mChildNum = 2` (payload bomb-rock preallocation), and `mBitterDrops = BDT_Strong` (enum at `enemyInfo.h:44-52`). All asset-name fields (`mModelName` through `mStoneName`) are empty strings, so model/motion/parameter assets are resolved by the standard name-derived path, not by this table; the concrete asset filenames are an open item for the converter handoff (#128 dependency).

Manager creation is a dedicated switch case: `src/plugProjectYamashitaU/generalEnemyMgr.cpp:406-407` constructs `BombSarai::Mgr(limit, viewNum)`. `Mgr::doAlloc` allocates only `Parms` (`src/plugProjectNishimuraU/BombSaraiMgr.cpp:22-25`), `createObj` is a plain `Obj[count]` array (31-34), and `loadModelData` additionally forces `setTexMtxLoadType(0x2000)` on every shape (49-57). The generator name is `バクダンサライ` at `src/plugProjectYamashitaU/genEnemy.cpp:558`. The payload `Bomb` (`EnemyID_Bomb`, `enemyInfo.h`/`enemyInfo.cpp:64`, `BDT_Empty`, `EFlag_HasNoInfo`) has its own manager case at `generalEnemyMgr.cpp:322`.

The static name string is `"246-BombSarai"` (`src/plugProjectNishimuraU/BombSarai.cpp:8`); 246 is the family slot used across the Nishimura sources.

## FSM: states and transitions

`include/Game/Entities/BombSarai.h:24-40` enumerates 13 states; `FSM::init` (`src/plugProjectNishimuraU/BombSaraiState.cpp:19-35`) registers Dead (0), Damage (1), Wait (2), BombWait (3), Move (4), BombMove (5), Supply (6), Release (7), Fall (8), TakeOff1 (9), TakeOff2 (10), Flick (11), BombFlick (12). The "Bomb*" variants are the carrying counterparts of Wait/Move/Flick. Initial state is Wait (`BombSarai.cpp:50`).

Core loop:

- **Wait** (`BombSaraiState.cpp:164-216`): untargetable, hovers. On an attackable target it selects Supply; after 3 s idle it selects Move; transitions at animation END (178-207).
- **Move** (303-364): hovers and walks toward a random target via `EnemyFunc::walkToTarget` with move/turn/max-turn general parms (337-338). On a target it selects Supply; after 5 s or within 25 units of the waypoint it selects Wait (318-354).
- **Supply** (460-501): untargetable + NoInterrupt, calls `supplyBomb()` in init (466) — allocation is a state-entry side effect, not an animation event. At END, re-evaluates `getNextStateOnHeight` and otherwise enters BombMove (477-489). Cleanup resets `mBombCarryTimer` to 0 (495-501).
- **BombWait** (221-297): untargetable + NoInterrupt. Release triggers, in priority order: `mBombCarryTimer > 15 s` (forced drop, 242-244); target attackable by `isTargetAttackable` (max attack range/angle, 247-250); target within `mAttackRadius` in XZ (255-257); otherwise re-approach via BombMove (259-261) or after 3 s with no target (263-266). Bitter queue transits directly to Fall (268-271).
- **BombMove** (369-454): like BombWait but actively walks toward the target or waypoint; same 15 s carry cap and attack gates (386-444). Bitter queue → Fall (425-428).
- **Release** (507-555): at KEYEVENT_2 throws the bomb with velocity `(50·sin(face), 100, 50·cos(face))` — a fixed lob, no homing or target lead — and clears NoInterrupt (528-534). At END, height-dependent transition or Wait (535-543).
- **Flick** (740-781) / **BombFlick** (787-835): at KEYEVENT_2 call `EnemyFunc::flickStickPikmin` with shake chance/knockback/damage general parms and `FLICK_BACKWARD_ANGLE` (757-760, 810-813). END returns to Move or BombMove respectively. BombFlick also falls if bittered mid-swing (804-807).
- **Fall** (561-636): interruptible crash. Motion is force-finished when within 35 units of the floor or after 1 s (585-587). At KEYEVENT_2 the carried bomb is thrown with velocity `(100·sin(face), 300, 100·cos(face))` — a higher pop-up than Release (592-596); KEYEVENT_3..7 pop the five balloon effects; END goes to Dead if health ≤ 0, else Damage (618-624).
- **Damage** (98-158): struggle on the ground. Finishes early if health ≤ 0, no Pikmin remain stuck, or the struggle timer exceeds `fp40` (119-121). END transits to Dead (health ≤ 0), TakeOff1 (health > 50% max) or TakeOff2 (137-145).
- **TakeOff1** (642-685) / **TakeOff2** (691-734): untargetable only after motion frames 45/21 respectively, then climb via `setHeightVelocity` (658-661, 707-710); TakeOff2 uses the fast-takeoff rise factor. On death or crossing the transition height they re-evaluate `getNextStateOnHeight`, else finish to Move (663-675, 712-724). `doFinishStoneState` uses the same 50%-health split between TakeOff1/2 (`BombSarai.cpp:141-149`).
- **Dead** (41-92): `deathProcedure`, targetable and non-cullable; KEYEVENT_2..6 pop the five balloon effects, KEYEVENT_7 adds camera/rumble/down-effect, END kills (55-83). Corpse motion is `BOMBSARAIANIM_Carry` (`BombSarai.cpp:175-178`).

Shared gate: `getNextStateOnHeight` (`BombSarai.cpp:314-340`) returns Fall when health ≤ 0 or when any stuck Pikmin is Purple (`EnemyFunc::getStickPikminColorNum(this, Purple) > 0`, 322-324); otherwise with 1–5 stuck Pikmin it rolls an interpolated flick probability between `fp31` (free) and `fp32` (laden) and returns Flick or BombFlick (selected by `mHeldBomb != nullptr`, 326-334), defaulting to Fall when the roll fails (336). Wait/BombWait/Move/BombMove only consult this gate once altitude exceeds `fp03` (transition height) or the state timer exceeds 5 s. `bombCallBack` (`BombSarai.cpp:127-135`) takes explosion damage only while grounded (`mFloorTriangle != 0`) — the flying dirigibug is immune to its own and other bombs' blasts.

## Bomb supply, carry and throw

`supplyBomb` (`BombSarai.cpp:263-279`) runs once per Supply entry: it resolves the shared `Bomb::Mgr` through `generalEnemyMgr->getEnemyMgr(EnemyID_Bomb)`, births one bomb with the carrier's facing, and only on a non-null birth initializes it, `startCapture`s it at the `kamu_jnt1` joint world matrix and assigns `mCarrier = this`. A missing manager or exhausted bomb pool silently leaves `mHeldBomb = nullptr`; the FSM still proceeds through the Bomb* states, and `throwBomb` (285-294) is a no-op on null — so pool exhaustion degrades the lane to a harmless flyer without crashing. `throwBomb` ends capture, applies the given velocity, matches the carrier's facing and clears the pointer; `mCarrier` on the bomb is intentionally *not* cleared, which is what attributes the later blast to the dirigibug. `onKill` (`BombSarai.cpp:57-61`) calls `throwBomb(Vector3f::zero)`, so any death while carrying drops the payload in place with no velocity — the bomb-drop-on-death exit.

The Bomb half of the contract (audited in the cannon/Groink doc, re-verified here):

- Capture (`src/plugProjectMorimuraU/bomb.cpp:23-44`): `onStartCapture` restarts `BOMB_Wait`, snaps to the capture matrix, constrains the bomb and makes it invulnerable outside versus mode. `onEndCapture` (46-53) un-constrains, drops invulnerability and sets `mHasEscapedCapture`.
- Fuse arming: an escaped bomb with a floor triangle passes `isAnimStart` (`bomb.cpp:468-476`), so a thrown bomb ignites its hit-loop animation on landing; `StateWait::exec` then ticks damage and transits to `BOMB_Bomb` at animation END (`src/plugProjectMorimuraU/bombState.cpp:50-81`). Non-drop spawns arm after `mFlickTimer` reaches the `ip01` damage-limit parameter; `BOMB_Wait` bombs that stay uncaptured and escaped for over 200 ticks are killed silently (bombState.cpp:53-58). Bomb-on-bomb induction uses the `ip02` trigger-limit countdown (`bomb.cpp:348-368, 426-440`). Drop-group births arm on floor bounce or non-Teki collision (`bomb.cpp:383-408`); neither path applies to dirigibug lobs, which are ordinary births, so arc termination is floor-contact driven.
- Detonation (`bombState.cpp:109-198`): `StateBomb` drains health each frame, then waits 10 ticks, spawns `TBombrock` effects, and applies a height-gated spherical blast — radius `mAttackRadius` (general), vertical half-height `fp02` ±50 default (`include/Game/Entities/Bomb.h:138-141`) — before `kill(nullptr)`.
- Friendly-fire policy (bombState.cpp:159-190): Teki in the volume receive `InteractBomb` for `fp01` damage-to-enemies (250 default) with the bomb as source — explosions unconditionally damage other enemies, including (if grounded) the carrier itself via `bombCallBack`. Navi/Pikmin receive `InteractBomb` for the general attack damage with directional knockback (100 captain / 200 Pikmin separation force), attributed to `mCarrier` when set, else to the bomb. There is no faction check: the policy is "hurt everything in the volume, with carrier attribution only for scoring".
- `bomb.cpp:296-297` shows `mCarrier` is also consumed by `BombOtakara` (Titan Dweevil clears its target when its bomb dies); nothing in the BombSarai sources reads `mCarrier` back, so carrier reuse after a lob leaves a stale-but-harmless pointer. Durable serialization of that link is not established (shared persistence caveat below).

## Flight and locomotion

There is no ground-walk mode: every living state hovers. `setHeightVelocity` (`BombSarai.cpp:202-224`) drives vertical velocity toward `minY + fp01` flight height (default 90), blending the rise factor between `fp21` (free, 1.5) and `fp22` (laden, 1.0) over 0–5 stuck Pikmin — carrying Pikmin weigh the bug down; the fast-takeoff variant forces factor 6. Above the nominal height it oscillates with `fp10`/`fp11` (pitch rate/amplitude, defaults 2.5/20, 214-219). Horizontal motion in Move/BombMove is `EnemyFunc::walkToTarget` against waypoints from `setRandTarget` (230-245): inside caves a 50–100 unit ring around home, otherwise home-radius plus a weighted share of territory radius, biased outward from home. Targets are only considered inside the territory radius (`getAttackablePikmin`, 300-308). Flight sound `PSSE_EN_BOMBSARAI_AIR` plays while `isFlying()` (67-73). Water callbacks are empty overrides (`include/Game/Entities/BombSarai.h:49-50`), so the dirigibug ignores water volumes; terrain interaction relevant to the #169 adapter is floor-height sampling via `mapMgr->getMinY` (204, 584) and the shadow volume sized by flight height (107-121).

## Interruption and death exits

- Bitter spray: BombWait/BombMove/BombFlick check `EB_BitterQueued` and transit to Fall (`BombSaraiState.cpp:268-271, 425-428, 804-807`); Fall throws the bomb skyward at KEYEVENT_2, so a bittered carrier ejects its payload rather than keeping it.
- Purple Pikmin: any stuck Purple forces Fall through `getNextStateOnHeight` (`BombSarai.cpp:322-324`).
- Stone state: `doFinishStoneState` re-flies with the 50%-health TakeOff1/TakeOff2 split (`BombSarai.cpp:141-149`).
- Death while carrying: `onKill` throws with zero velocity (`BombSarai.cpp:57-61`) — the bomb detaches at the corpse position and then follows its own escaped-capture lifecycle (arms on landing).
- Death/blast while flying: because `bombCallBack` requires a floor triangle, only a grounded (Fall/Damage/carcass) dirigibug takes bomb damage; other hostile explosions cannot kill it mid-air.
- Piklopedia mode init makes the object invulnerable (`BombSarai.cpp:38-40`). Movie start/end only toggle the supply effect draw (184-196); birth-type drop start/finish do the same (155-169).

## Animation and motion bank

`include/Game/Entities/BombSarai.h:161-177` enumerates 14 clips: Dead (`dead1`), Fall (`fall1`), Flick (`flick1`), BombFlick (`bflick1`), Struggle (`mogaki1`), Release (`release1`), Run (`run1`), BombRun (`run2`), Supply (`supli1`), TakeOff1/2, Carry (`type5`, the carcass motion), Wait (`wait1`), BombWait (`wait2`). `ProperAnimator` is a single-`SysShape::Animator` wrapper (`src/plugProjectNishimuraU/BombSaraiAnimator.cpp:9-21`). Joints referenced by gameplay code: `kamu_jnt1` (bomb capture), `kuti_joint1` (supply effect), `balloon1`–`balloon5` (pop effects), `body_joint1` (shadow). Effects: `efx::TBsaraiSupli` (`PID_BSaraiSupli`, chase-matrix) and `efx::TBsaraiDead` (`PID_BSaraiDead_1/2`) in `include/efx/TBsarai.h:10-26`. Sounds: `PSSE_EN_BOMBSARAI_AIR`, `PSSE_EN_BOMBSARAI_DEAD`, and the bomb's own `PSSE_EN_BOMB_LOOP`/`PSSE_PK_SE_BOMB`.

## Parameters

Family-specific (`include/Game/Entities/BombSarai.h:121-146`, defaults/ranges): `fp01` flight height 90 (0–150), `fp03` transition height 50 (0–300), `fp10` pitch rate 2.5 (0–10), `fp11` pitch amplitude 20 (0–50), `fp21` free rise factor 1.5 (0–5), `fp22` laden rise factor 1.0 (0–5), `fp31` free flick chance 0.1 (0–1), `fp32` laden flick chance 0.7 (0–1), `fp40` struggle time 3.0 s (0–10). Hardcoded timers: Wait idle 3 s, state-timer gate 5 s, Move waypoint timeout 5 s / arrival radius 25 (625 squared), bomb carry cap 15 s, Fall finish distance 35 / timeout 1 s, Release lob (50, 100), Fall lob (100, 300). Consumed general parms: health, move speed, turn speed, max turn angle, view angle, sight radius, home/territory radius, max attack range/angle, attack radius, shake chance/knockback/damage, attack damage. Bomb-specific (`include/Game/Entities/Bomb.h:134-149`): `fp01` damage to enemies 250, `fp02` blast half-height ±50, `ip01` damage limit 2, `ip02` trigger limit 50. Shipped per-enemy `.txt` parm overrides live in game assets, not this checkout; defaults above are the header values.

## Save/persistence caveat

As established in the cannon/Groink audit, `Creature::save` writes position only and `doSave` is an empty default (`include/Game/Creature.h:254`, `src/plugProjectKandoU/creature.cpp:262-275`); no BombSarai- or Bomb-local serialization of `mHeldBomb`/`mCarrier`, carry timer, FSM state or fuse state was found. Save/resume and cave-transition behavior for a carrying dirigibug or in-flight bomb is therefore unresolved and must be covered by native acceptance tests, not inferred.

## Native acceptance checklist for the lane

1. Exhaust the shared Bomb manager pool, then trigger Supply: confirm null birth leaves a harmless carrier and later births recover.
2. Lob arcs: Release (50/100) and Fall (100/300) throws against floor, walls, water and targets; confirm landing-armed fuse, 10-tick detonation delay, radius + vertical gate, 250 Teki damage, carrier attribution, and mid-air bomb-immunity of the flyer.
3. Bomb drop on death from each exit (bitter Fall, Purple-forced Fall, direct kill while carrying): confirm zero-velocity detach and independent fuse.
4. Interruption: bitter queue in BombWait/BombMove/BombFlick, stone finish at both health bands, Purple stick at each altitude gate.
5. Multi-projectile: two or more dirigibugs lobbing concurrently plus bomb-on-bomb induction (`ip02`); confirm per-bomb timers and no shared-state bleed.
6. Save/reload and cave/day transitions with a carried bomb, an in-flight bomb and an armed landed bomb.

## Open questions / dependencies

- **#169 (Groink terrain adapter / host clock)**: BombSarai's floor interaction is `mapMgr->getMinY` height sampling plus the Bomb's floor-triangle landing test; the projectile-lifecycle slice should reuse the Groink lane's host terrain adapter and fixed-step clock rather than adding a second pattern.
- **#128 (converter handoff)**: asset names are absent from the enemy-info row (empty strings); the exact BMD/BCK/BRK/BTP and collision asset filenames for BombSarai and Bomb must come from the converter pass. Material fidelity is validated separately from hitboxes per #244.
- **#186 (shared P1 arena contract)**: arena staging and opt-in install profile follow the root-owned contract; this audit makes no placement decision.
- **Bomb pool sizing**: `mChildNum = 2` preallocates two bomb-rocks per dirigibug record; whether that is per-generator or per-manager (and how it interacts with the shared Bomb manager limit under concurrent carriers, including BombOtakara lanes) needs runtime confirmation.
- **Stale `mCarrier` link**: thrown bombs keep pointing at the carrier; carrier death/reuse while a lob is in flight is untested territory for attribution (native acceptance item 2/5).
- **Persistence**: no family-local serialization exists (caveat above); resume semantics for carried/in-flight/armed bombs must be decided with the lifecycle contract before the fixtures slice.
