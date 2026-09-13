# Cannon Stone projectile lifecycle contract (#406)

Implementation owner: opencode projectiles-lane session using shared account
`4laric`. Parent: [#169](https://github.com/4laric/pikmin-randomizer/issues/169)
(Cannon larvae, Groinks and projectiles). Integration contract:
[#186](https://github.com/4laric/pikmin-randomizer/issues/186). Source contract
for the same entries: [#350](https://github.com/4laric/pikmin-randomizer/issues/350) /
[PIKMIN2_CANNON_PROJECTILE_ASSETS.md](PIKMIN2_CANNON_PROJECTILE_ASSETS.md).
Cross-references: [PIKMIN2_BOMBSARAI_PROJECTILE_CONTRACT.md](PIKMIN2_BOMBSARAI_PROJECTILE_CONTRACT.md)
(#244) and [PIKMIN2_GROINK_PROTOTYPE.md](PIKMIN2_GROINK_PROTOTYPE.md) (#169).

This is the projectiles-lane "one birth -> motion/homing -> collision -> damage
-> destruction, including interruption and teardown" slice. It implements the
**Stone (EnemyID 74)** fired by Armored/Decorated Cannon Beetle Larvae (Kabuto
75 / Rkabuto 95), which is `Game::Rock::Obj` with `mRockType == EnemyID_Stone`.
It is an **isolated policy milestone**: lane-owned files, no shared hooks, no
converter/build changes, no native actor registration. The falling/rolling Rock
hazard variant's `Wait`/`Appear`/`Fall`/`DropWait` states are a separate bounded
slice and are not implemented here.

Source reference is projectPiki/pikmin2 revision
`632af93787b9c95b63f0c13be32b161375ce3a96` (US GPVE01 rev 0); line numbers
follow `native/pikmin2-research`.

## Lane-owned files

Native branch `opencode/p2-projectiles-stone` at base native `356e9c08`:

- `pc_port/pc_p2_cannon_stone.h` / `.cpp` — isolated Stone lifecycle policy.
- `tools/p2_cannon_stone_test.cpp` — standalone fixture executable.
- `docs/PIKMIN2_CANNON_STONE_PROJECTILE.md` — this contract.

No edit to the Groink modules (`pc_p2_groink_*`, owned by #169/#198/#204-#210),
the BombSarai modules (`pc_p2_bombsarai_*`, #244) or any Man-at-Legs/Long Legs
file. Groink ownership and parked status are preserved.

## 1. Identity, registration and scope

| Field | Value | Source |
|---|---|---|
| Stone ID | `EnemyID_Stone` 74 | `enemyInfo.h:133` |
| Rock ID | `EnemyID_Rock` 19 | `enemyInfo.h:78` |
| Obj / Mgr | `Game::Rock::Obj` / `Game::Rock::Mgr`, type selected by `mRockType` | `Rock.h:58,116,120-135` |
| Registration row | `enemyInfo.cpp:37` (no `EFlag_UseOwnID`; parent Rock) | `RockMgr.cpp:101-115` builds one object array over `{Rock, Stone}` |
| Firing species | Kabuto 75 / Rkabuto 95 / Fkabuto 96 resolve the Kabuto manager and fire `createStoneAttack` | `Kabuto.cpp:268-290` |
| Flags | `EFlag_HasNoInfo` projectile entry (no Piklopedia) | `enemyInfo.cpp:36-37` |

The Stone is a projectile, not a creature: it has no Piklopedia entry, no
carcass (`EB_LeaveCarcass` disabled, `Rock.cpp:59`), no death effect
(`EB_DeathEffectEnabled`, `:60`), no lifegauge (`:61`) and is invulnerable
(`EB_Invulnerable`, `:57`).

## 2. State machine

Only the fired Stone's two states are modeled; the Rock-only states are out of
scope (see the header comment).

| Phase | Source state | Behavior |
|---|---|---|
| `Move` | `ROCK_Move` | Stone `onInit` starts directly here (`Rock.cpp:88-93`): `initMoveVelocity`, `ROCK_Move`, animation culling off. `StateMove::exec` runs `updateMoveVelocity` + `moveRockScaleUp` + timer, then gates on health/timeout (`RockState.cpp:229-241`). |
| `Dead` | `ROCK_Dead` | Target velocity zeroed, dead motion started (`RockState.cpp:261-269`); first exec disables atari and hard-constrains (`:275-281`). |
| `Killed` | `kill(nullptr)` | After the dead animation's `KEYEVENT_END` (`RockState.cpp:283-285`). Slot reusable. |

## 3. Birth — `createStoneAttack`

`Obj::createStoneAttack` (`Kabuto.cpp:268-290`):

- Obtains the `Rock::Mgr` (`:270`), sets `birthArg.mTypeID = EnemyID_Stone` (`:273`).
- Spawn position from the `mouth` joint world matrix: `(mouth.x, 25.0f + mPosition.y, mouth.z)` (`:276`). `P2CannonStone::mouthBirthPosition` applies the fixed `+25 y`.
- `birthArg.mFaceDir = mFaceDir` (`:279`), then `rockMgr->birth(birthArg)` (`:281`), `rock->init(nullptr)` (`:283`), `rock->mSourceEnemy = this` (`:284`).
- Homing is enabled **only** when the firing species is Rkabuto: `if (getEnemyTypeID() == EnemyID_Rkabuto) rock->mIsHoming = true` (`:285-287`).
- A failed birth is silently tolerated (`:282-288`); the policy models this as `P2CannonStonePool::spawn` returning `nullptr` with no partial state.

`initMoveVelocity` (`Rock.cpp:356-362`) sets
`mTargetVelocity = mVelocity = getDirection(mFaceDir) * mMoveSpeed`
(`getDirection(a) = (sin a, 0, cos a)`, `trig.h:182-186`). `onInit` for the
drop-group-none case starts the visual scale at `0.0001` (`Rock.cpp:51-55`).

## 4. Motion and homing — `updateMoveVelocity`

`StateMove::exec` (`RockState.cpp:229-241`) each tick: `updateMoveVelocity`,
`moveRockScaleUp`, `mTimer += mDeltaTime`, water-effect update and roll sound,
then transit to `Dead` when `mHealth <= 0` or `mTimer > 15.0f`.

- **Homing branch** (`Rock.cpp:370-389`): target the active Navi, else the
  nearest Pikmin/Navi within `mSightRadius` and a `180.0f`-degree search angle
  (`EnemyFunc::getNearestPikminOrNavi`, `:376`; `searchAngle` is converted with
  `TORADIANS` and tested as `|angDist| <= searchAngle`, `enemyAction.cpp:21,45`,
  so 180 degrees is unrestricted), using the 2D x/z distance
  (`enemyAction.cpp:47-53`). `turnToTarget(targetPos,
  mTurnSpeed, mMaxTurnAngle)` (`:386`) then `setTargetSpeed(
  C_PROPERPARMS.mSearchRumbleSpeed())` (`:388`). Without a target,
  `targetPos = mPosition + mTargetVelocity` (keep heading, `:382-384`).
- **Non-homing branch** (`Rock.cpp:391-397`): `mTargetVelocity = 0.01 *
  mCurrentVelocity + 0.99 * mTargetVelocity`, then `turnToTarget(mPosition +
  mTargetVelocity, ...)`.
- `turnToTarget` (`EnemyBase.h:462-471`) is
  `faceDir = roundAng(faceDir + clamp(angDist * turnSpeed, TORADIANS(maxTurnAngle)))`.
- `moveRockScaleUp` (`Rock.cpp:333-350`) scales `0.0001 -> 1.0` at a fixed
  `5.0/s`, independent of parms.

The policy takes the host homing snapshot as `P2CannonStoneTarget` and the
post-physics result through `P2CannonStoneTraceFn`; a trace `wall` result maps
to `wallCallback`. With no trace the policy integrates the command directly.

## 5. Collision, damage and interruption

`Obj::collisionCallback` (`Rock.cpp:204-238`):

- `other->isNavi() || other->isPiki()`: if the target has a floor triangle, emit
  `InteractPress(target, C_GENERALPARMS.mAttackDamage, nullptr)` where `target`
  is `mSourceEnemy` when set, else the Stone itself (`:210-220`). Airborne
  Navi/Piki receive nothing.
- `other->isTeki()`: emit `InteractAttack(this, 250.0f, collisionObj)` (`:221-223`);
  if this is a Rock and the other is a Rock, suppress mutual collision
  (`notRock = false`, `:225-227`).
- Any non-Navi/Piki contact forces `mHealth = 0.0f` (`:230-232`), consumed by the
  next `StateMove::exec` gate.

Interruptions:

- `wallCallback` (`Rock.cpp:244-249`): `ROCK_Move -> ROCK_Dead`.
- `hipdropCallBack` (`Rock.cpp:190-198`): alive, not bittered, `ROCK_Move ->
  ROCK_Dead`.
- `ignoreAtari` (`Rock.cpp:298-304`): ignore the source enemy while
  `mTimer < 1.0f`, preventing the firing Kabuto from immediately self-killing
  its own Stone.

## 6. Destruction and teardown

- `StateDead::init` (`RockState.cpp:261-269`): zero target velocity, start the
  dead motion, remove the shadow, create the dead effect, play the break sound.
- `StateDead::exec` (`RockState.cpp:275-286`): disable atari + hard-constrain on
  the first exec; on the dead animation's `KEYEVENT_END`, `kill(nullptr)`.
- `Obj::onKill` (`Rock.cpp:100-106`): finish fall/rolling effects, then
  `EnemyBase::onKill`.

The policy exposes `finishDeath()` for the host's animation-end kill request and
`P2CannonStonePool` slot reuse.

## 7. Fixed constants vs host/config inputs

Fixed by the source (compile-time constants on `P2CannonStone`):

| Constant | Value | Source |
|---|---|---|
| `kSourceDelta` | 1/30 s | source-rate clock |
| `kMoveTimeoutSeconds` | 15.0 | `RockState.cpp:238` |
| `kRollScaleUpPerSecond` | 5.0 | `Rock.cpp:336-337` |
| `kInitialScale` | 0.0001 | `Rock.cpp:53` |
| `kAtariGraceSeconds` | 1.0 | `Rock.cpp:300` |
| `kHomingSearchAngleDegrees` | 180.0 (degrees, unrestricted) | `Rock.cpp:376` |
| `kTekiAttackDamage` | 250.0 | `Rock.cpp:222` |
| `kNonHomingCurrentWeight` / `TargetWeight` | 0.01 / 0.99 | `Rock.cpp:391-393` |

Host/converter inputs (parm-explicit, never invented): `moveSpeed` (general
fp06, disc 250), `searchRumbleSpeed` (proper fp01, disc 100), `turnSpeed`,
`maxTurnAngle`, `attackDamage` (general fp24, disc 10), `sightRadius` (general
fp12, disc 350), `collisionRadius` (Rock root 40 / child 27), `health` (general
fp00, disc 99999) and `variant`. Disc values come from
[PIKMIN2_CANNON_PROJECTILE_ASSETS.md](PIKMIN2_CANNON_PROJECTILE_ASSETS.md) §5.

## 8. Host contract

The policy never dereferences creatures, the map or the effect system:

- `P2CannonStoneTarget` — the host selects the active Navi / nearest Pikmin or
  Navi inside `mSightRadius` and the 180-degree search angle; no target
  selection is invented here.
- `P2CannonStoneTraceFn` — the host applies `targetVelocity()` with the engine
  creature physics and returns the resulting position/velocity, plus `wall` for
  `wallCallback`.
- `contact(kind, targetOnFloor, targetIsRock, targetToken)` — the host classifies
  the colliding creature and supplies a stable token; it routes the returned
  `P2CannonStoneStrike` to the receiver. Press attribution uses the source-enemy
  token when present, else the Stone's own token.
- `notifyWallContact` / `notifyHipdrop` — host-detected interruptions.
- `finishDeath` — host reports the dead animation's `KEYEVENT_END`; the host
  owns pellet/actor teardown and slot free.
- `P2CannonStonePool` — the host configures the real shared Rock manager limit
  (shared with falling Rock objects); exhaustion returns `nullptr` with no
  partial state, matching failed manager births.

## 9. Fixture evidence

Standalone MinGW build, no engine objects (same convention as the Groink and
BombSarai lanes):

```powershell
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
g++ -std=gnu++17 -Wall -Wextra -Werror `
    -I output/native-projectiles/pc_port `
    output/native-projectiles/tools/p2_cannon_stone_test.cpp `
    output/native-projectiles/pc_port/pc_p2_cannon_stone.cpp `
    -o output/p2-projectiles-stone/p2_cannon_stone_test.exe
```

Compiled warning-clean with local MinGW GCC 16.2.0; private run directory
`output/p2-projectiles-stone/` (`build.log` 0 bytes = no diagnostics,
`run.log` empty/stdout, exit 0). Executable SHA-256
`84678E5AC3A96C3B61E2BF4DDFDF877970132C1BC4E7FBBAF9D640DBEE8B7D05`.
Native base commit `356e9c08`, dirty state = the three new untracked lane files
only.

Coverage: mouth `+25 y` birth and `getDirection*moveSpeed`; live birth refusal
and invalid-config refusal; non-homing straight roll, trace radius and 0.01/0.99
smoothing; scale ramp to 1.0 after six ticks; homing face snap and target-speed
switch, max-turn clamp, target loss and NaN-target fallback; grounded Press
attribution (source vs self), airborne no-op, Teki 250 Attack, non-Navi/Piki
health-zero, Rock-vs-Rock suppression; 1 s source-enemy atari grace at the
boundary; trace-wall, explicit wall and hipdrop interruption (bittered no-op);
contact-driven health-zero consumed next tick; 15 s timeout; `finishDeath`
exactly once and terminal `Killed`; invalid-delta immutability; pool
supply/exhaustion/invalid-config/slot reuse.

This is a standalone policy test, not a native arena or gameplay test. Host
trace, target enumeration, receiver stimulation, effects, sound, the firing
Kabuto FSM and save/resume are unimplemented.

## 10. Arena gate status (policy slice)

| Gate | Status | Evidence / limitation |
|---|---|---|
| 1. Exact identity and spawn | source-backed + fixture PASS; native UNTESTED | `createStoneAttack` birth reproduced in fixture; no native actor registered. |
| 2. Autonomous movement and animation | fixture PASS; native UNTESTED | Motion/homing/scale in fixture; no animation bank or draw. |
| 3. Attacks and receivers | fixture PASS; receiver UNTESTED | Strike classification/attribution; host receiver routing not wired. |
| 4. Death and corpse | fixture PASS; corpse source-backed N/A | `finishDeath`/`Killed`; `EB_LeaveCarcass` disabled (`Rock.cpp:59`). |
| 5. Transport and reward | source-backed N/A | Projectile/hazard: no carry or reward. |
| 6. Cleanup and re-entry | fixture PASS (slot reuse); native UNTESTED | Pool slot reuse after `Killed`; no native reset/teardown. |

## 11. Fixture baseline adoption

No runtime acceptance run was performed in this slice, so the mandatory
starting-Pikmin overlay and 960x540 centred-window adoption
([PIKMIN2_IMPLEMENTATION_FANOUT.md](PIKMIN2_IMPLEMENTATION_FANOUT.md)) is **not**
claimed here. It remains required before this lane's next native/runtime
acceptance run. No executable, arena or save was launched.

## 12. Open items for later slices

- Host MapMgr/creature-physics trace adapter with the `wall`/ground contract.
- Receiver routing for `InteractPress`/`InteractAttack` and the source-enemy
  attribution; separate acceptance evidence.
- Firing Kabuto/Rkabuto/Fkabuto attack FSM and mouth-joint alignment; the
  buried `FixKabuto` attack shares the same Stone birth.
- Falling/rolling **Rock (19)** `Wait`/`Appear`/`Fall`/`DropWait` and the
  drop-group collision/bounce path (separate bounded slice).
- Save/resume of in-flight Stones; native registration and arena gates.
- Numeric parm values bound to converted assets (#128/#350).
