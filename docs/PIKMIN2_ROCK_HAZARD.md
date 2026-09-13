# Rock falling/rolling hazard contract (#411)

Implementation owner: opencode projectiles-lane session using shared account
`4laric`. Parent: [#169](https://github.com/4laric/pikmin-randomizer/issues/169)
(Cannon larvae, Groinks and projectiles). Integration contract:
[#186](https://github.com/4laric/pikmin-randomizer/issues/186). Source contract
for the same entries: [#350](https://github.com/4laric/pikmin-randomizer/issues/350) /
[PIKMIN2_CANNON_PROJECTILE_ASSETS.md](PIKMIN2_CANNON_PROJECTILE_ASSETS.md).
Sibling slices: [#406](https://github.com/4laric/pikmin-randomizer/issues/406) /
[PIKMIN2_CANNON_STONE_PROJECTILE.md](PIKMIN2_CANNON_STONE_PROJECTILE.md) (Stone)
and [#410](https://github.com/4laric/pikmin-randomizer/issues/410) /
[PIKMIN2_EGG_HAZARD.md](PIKMIN2_EGG_HAZARD.md) (Egg).

This is the **falling Rock (EnemyID 19) hazard** slice: the Rock-only states
`ROCK_Wait`, `ROCK_Appear`, `ROCK_DropWait`, `ROCK_Fall` plus the drop-group
collision path, implemented as an isolated, source-faithful FSM group. The Rock
is the other identity managed by the same `Game::Rock::Obj` / `Rock::Mgr` as
the fired Stone (74, #406). The Stone's rolling `ROCK_Move` projectile path is a
separate FSM group and is **not** implemented or modified here. It is an
isolated policy milestone: lane-owned files, no shared hooks, no converter/build
changes, no native actor registration.

Source reference is projectPiki/pikmin2 revision
`632af93787b9c95b63f0c13be32b161375ce3a96` (US GPVE01 rev 0); line numbers
follow `native/pikmin2-research`.

## Lane-owned files

Native branch `opencode/p2-projectiles-rock` at base native `1e649cdd`:

- `pc_port/pc_p2_rock_hazard.h` / `.cpp` — isolated falling-Rock FSM policy.
- `tools/p2_rock_hazard_test.cpp` — standalone fixture executable.
- `docs/PIKMIN2_ROCK_HAZARD.md` — this contract.

No edit to `pc_port/pc_p2_cannon_stone.*` (#406), `pc_port/pc_p2_egg_hazard.*`
(#410), the Groink modules (#169/#198/#204-#210) or the BombSarai modules
(#244).

## 1. Identity, registration and scope

| Field | Value | Source |
|---|---|---|
| Rock ID | `EnemyID_Rock` 19 | `enemyInfo.cpp:36` |
| Stone ID | `EnemyID_Stone` 74 | `enemyInfo.cpp:37` |
| Obj / Mgr | `Game::Rock::Obj` / `Game::Rock::Mgr`, type selected by `mRockType` | `Rock.h:58,116,120-135` |
| Shared array | `Mgr::createObj` fills one object array over `{Rock, Stone}` | `RockMgr.cpp:101-115` |
| Generator | `Game::Rock::Generator` "落石ジェネレータ" (falling-rock generator) | `RockMgr.cpp:13-19`, `genEnemy.cpp:506-508` |
| Natural spawns | Queen drops (`Queen.cpp:395-401`), DangoMushi drops (`DangoMushi.cpp:651,710`) | `EnemyID_Rock` births |

The Rock is a hazard, not a creature: no carcass (`EB_LeaveCarcass` disabled,
`Rock.cpp:59`), no death effect (`EB_DeathEffectEnabled`, `:60`), no lifegauge
(`:61`), invulnerable (`EB_Invulnerable`, `:57`) and bitter-immune (`:62`).

`mDropGroup` (`EnemyBase.h:102-108`) is the birth drop group: `EDG_None` = not
dropping; `EDG_Normal/Pikmin/Navi/Carry/Earthquake` drop on a trigger. A
`mDropGroup == EDG_None` Rock hides at scale 0.0001 and starts `ROCK_Wait`; any
other group starts `ROCK_DropWait` (`Rock.cpp:51-55,78-84`).

## 2. State machine

Only the Rock-only falling states are modeled. `ROCK_Move` is not reachable for
`EnemyID_Rock` (Rock.cpp:71-93 starts Move only for `EnemyID_Stone`) and belongs
to the Stone policy (#406).

| Phase | Source state | Behavior |
|---|---|---|
| `Wait` | `ROCK_Wait` | atari off, untargetable, hard-constrained, model hidden, stopped Run motion (`RockState.cpp:30-42`). Timer or Olimar/Pikmin detection -> `Appear` (`:48-71`). Cleanup restores constraint/animation/model (`:77-83`). |
| `Appear` | `ROCK_Appear` | `position.y += mFallOffset`, hidden/cull-sound flags, Run motion, shadow add + force visible, fall sound (`RockState.cpp:89-107`). `fallRockScaleUp` clamp -> `Fall` (`Rock.cpp:310-327`). Cleanup enables atari, clears untargetable/model-hidden (`:125-131`). |
| `DropWait` | `ROCK_DropWait` | Run motion (`:137-141`); exec -> `Fall` immediately (`:147-150`). Cleanup disables cullable/cull-sound, adds the shadow (`:156-164`). |
| `Fall` | `ROCK_Fall` | velocity `(0, -mFallSpeed, 0)` and fall effect (`:170-176`); a floor triangle or `EB_Colliding` -> `Dead` (`:182-189`). Cleanup releases force-visible shadow + effect (`:195-204`). |
| `Dead` | `ROCK_Dead` | target velocity zeroed, dead motion, shadow removed, dead effect (`:261-269`); first exec disables atari + hard-constrains, `KEYEVENT_END` -> `kill(nullptr)` (`:275-286`). |
| `Killed` | `kill(nullptr)` | `onKill` finishes fall/rolling effects (`Rock.cpp:100-106`); slot reusable. |

## 3. onInit — falling-Rock branch

`Obj::onInit` (`Rock.cpp:47-94`), `getEnemyTypeID() == EnemyID_Rock`:

- `mDropGroup == EDG_None` sets `mScaleModifier = mScale = collTree scale =
  0.0001` (`:51-55`) and starts `ROCK_Wait` with `doAnimationCullingOff()`
  (`:78-80`); otherwise it starts `ROCK_DropWait` (`:82-84`).
- `mExistDuration != 0` disables `EB_Cullable` and seeds `mTimer` with
  `randWeightFloat(1.5)` (`:73-76`; `rand.h:26-29`).
- `shadowMgr->delShadow(this)` (`:86`).
- `setInitialSetting` (`Rock.cpp:36-41`) maps the fall parms:
  `mFallSpeed = mSearchDistance`, `mFallOffset = mSearchHeight`,
  `mScaleUpRate = mSearchAngle`.

The policy takes the `randWeightFloat(1.5)` result as `initialTimer` so no RNG
is embedded; `dropGroupNone` and `timedAppear` mirror `mDropGroup == EDG_None`
and `mExistDuration != 0`.

## 4. Motion, scale-up and fall

- `fallRockScaleUp` (`Rock.cpp:310-327`): while `mScaleModifier < 1.0`,
  `scale = mScaleUpRate * mDeltaTime + mScaleModifier`, clamped to 1.0; returns
  true on the tick it reaches 1.0, transiting `Appear -> Fall`. `mScaleUpRate`
  is a host parm (general `mSearchAngle`), never invented.
- `StateFall::init` (`RockState.cpp:170-176`) sets
  `velocity = (0, -mFallSpeed, 0)` and starts the fall effect. There is no
  gravity in this state.
- `StateFall::exec` (`:182-189`) transits to `Dead` on `mFloorTriangle` or
  `EB_Colliding`. `EB_Colliding` is set by `setCollEvent`
  (`enemyBase.cpp:2928-2932`) and reset each source frame
  (`enemyBase.cpp:1657-1665`), so a recorded contact is consumed by the next
  Fall update.

## 5. Collision, damage and death

`Obj::collisionCallback` (`Rock.cpp:204-238`), identical semantics to the Stone
slice:

- `other->isNavi() || other->isPiki()`: if the target has a floor triangle,
  emit `InteractPress(target, C_GENERALPARMS.mAttackDamage, nullptr)` where
  `target` is `mSourceEnemy` when set, else the Rock (`:210-220`). Airborne
  Navi/Piki receive nothing.
- `other->isTeki()`: emit `InteractAttack(this, 250.0f, collisionObj)`
  (`:221-223`); a Rock colliding with another Rock suppresses `setCollEvent`
  (`notRock = false`, `:225-227`), so no mutual death event.
- Any non-Navi/Piki contact forces `mHealth = 0.0f` (`:230-232`).
- `setCollEvent` (unless suppressed) enables `EB_Colliding`, which the next
  `Fall` update turns into `Dead`.

`ignoreAtari` (`Rock.cpp:298-304`) ignores `mSourceEnemy` while `mTimer < 1.0`,
so the dropping enemy is not immediately hit. `collisionCallback` only runs
while atari is enabled: the falling Rock enables atari in
`StateAppear::cleanup` (`RockState.cpp:128`) and `StateDropWait` leaves it on
from `onInit`.

Interruptions:

- `wallCallback` (`Rock.cpp:244-249`) and `hipdropCallBack` (`Rock.cpp:190-198`)
  transit to `Dead` **only from `ROCK_Move`**. The falling Rock never reaches
  `ROCK_Move`, so both are faithful no-ops for this FSM; the API is exposed so a
  host sharing the `Obj` callbacks can route them without branching on identity.

## 6. Destruction and teardown

- `StateDead::init` (`RockState.cpp:261-269`): zero target velocity, start the
  dead motion, remove the shadow, create the dead effect, play the break sound.
- `StateDead::exec` (`:275-286`): disable atari + hard-constrain on the first
  exec; on the dead animation's `KEYEVENT_END`, `kill(nullptr)`.
- `Obj::onKill` (`Rock.cpp:100-106`): finish fall/rolling effects, then
  `EnemyBase::onKill`.

The policy exposes `finishDeath()` for the host's animation-end kill request and
`P2RockHazardPool` slot reuse.

## 7. Fixed constants vs host/config inputs

Fixed by the source (compile-time constants on `P2RockHazard`):

| Constant | Value | Source |
|---|---|---|
| `kSourceDelta` | 1/30 s | source-rate clock |
| `kAppearTimerSeconds` | 1.5 | `RockState.cpp:53` |
| `kInitialHiddenScale` | 0.0001 | `Rock.cpp:51-55` |
| `kAtariGraceSeconds` | 1.0 | `Rock.cpp:300` |
| `kTekiAttackDamage` | 250.0 | `Rock.cpp:222` |
| `kCullTimerRange` | 1.5 | `Rock.cpp:75` |

Host/converter inputs (parm-explicit, never invented): `fallSpeed` (general
`mSearchDistance`), `fallOffset` (general `mSearchHeight`), `scaleUpRate`
(general `mSearchAngle`), `sightRadius` (general `mSightRadius`), `attackDamage`
(general `mAttackDamage`), `collisionRadius` (host fall-trace radius), `health`
(general `mHealth`), plus the birth inputs `dropGroupNone`, `timedAppear`,
`initialTimer`, `sourceToken` and `selfToken`. Disc values are bound later from
[PIKMIN2_CANNON_PROJECTILE_ASSETS.md](PIKMIN2_CANNON_PROJECTILE_ASSETS.md) §5.

## 8. Host contract

The policy never dereferences creatures, the map, the effect system or the RNG:

- `P2RockHazardInit` — birth inputs: position, `dropGroupNone`, `timedAppear`,
  the host `randWeightFloat(1.5)` `initialTimer`, `sourceToken` (`mSourceEnemy`,
  0 = none) and `selfToken`.
- `P2RockHazardDetection` — the host runs `isThereOlimar` then `isTherePikmin`
  at `mSightRadius` (`RockState.cpp:59-65`) and reports the two booleans.
- `P2RockHazardTraceFn` — the host applies map/creature physics during `Fall`
  and returns position/velocity plus `floorTriangle`/`colliding`; with no trace
  the policy integrates the source velocity.
- `contact(kind, targetOnFloor, targetIsRock, targetToken)` — the host
  classifies the colliding creature and supplies a stable token; it routes the
  returned `P2RockHazardStrike` to the receiver. Press attribution uses the
  source-enemy token when present, else the Rock's own token.
- Source event flags (`atari`, `untargetable`, `hardConstrained`, `animating`,
  `modelHidden`, `cullable`, `cullSound`, `shadow`, `shadowForcedVisible`,
  `fallEffectActive`, `deadEffectCreated`, `animationCullingOff`, `motion`) are
  read by the host, which owns the real shadow/effect/sound/animation bank.
- `notifyWallContact` / `notifyHipdrop` — host-detected interruptions; faithful
  no-ops for the falling Rock.
- `finishDeath` — host reports the dead animation's `KEYEVENT_END`; the host
  owns actor teardown and slot free.
- `P2RockHazardPool` — the host configures the real shared Rock manager limit
  (shared with Stone objects); exhaustion returns `nullptr` with no partial
  state, matching failed manager births.

## 9. Fixture evidence

Standalone MinGW build, no engine objects (same convention as the Stone, Egg,
Groink and BombSarai lanes):

```powershell
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
g++ -std=gnu++17 -Wall -Wextra -Werror `
    -I output/native-projectiles-rock/pc_port `
    output/native-projectiles-rock/tools/p2_rock_hazard_test.cpp `
    output/native-projectiles-rock/pc_port/pc_p2_rock_hazard.cpp `
    -o output/p2-projectiles-rock/p2_rock_hazard_test.exe
```

Compiled warning-clean with local MinGW GCC 16.2.0; private run directory
`output/p2-projectiles-rock/` (`build.log` 0 bytes = no diagnostics, `run.log`
0 bytes, exit code 0). Executable SHA-256
`38F547E6719A6350C0029A831E261EC7E6D08BBC8D1D4F6E31FAB58F6D4B6C74`.
Native base commit `1e649cdd`.

Coverage: both `onInit` branches (drop-group-none hidden `0.0001` + Wait flags;
drop-group DropWait + default scale; timed-appear cull disable + seeded timer);
invalid position/scale-up/timer rejection and second-init refusal; Wait
Olimar/Pikmin detection and the 1.5 s timed path; Appear fall-offset, hidden
flags and the `mScaleUpRate` ramp to `Fall`; DropWait immediate fall, fall
velocity and fall effect; no-trace fall integration and trace-driven floor /
`EB_Colliding` death; grounded Press attribution (source vs self), airborne
no-op, Teki 250 Attack, non-Navi/Piki health-zero, Rock-vs-Rock suppression,
contact-driven `EB_Colliding` consumed next tick; atari gate in Wait/Appear and
the 1 s source grace on the drop path; wall/hipdrop Move-gated no-ops;
`finishDeath` exactly once and terminal `Killed`; invalid-delta immutability;
pool supply/exhaustion/invalid-config/slot reuse.

This is a standalone policy test, not a native arena or gameplay test. Host map
/ creature physics, Olimar/Pikmin enumeration, receiver stimulation, shadow,
effects, sound, the animation bank and save/resume are unimplemented.

## 10. Arena gate status (policy slice)

| Gate | Status | Evidence / limitation |
|---|---|---|
| 1. Exact identity and spawn | source-backed + fixture PASS; native UNTESTED | Rock onInit/drop-group branches in fixture; no native actor registered. |
| 2. Autonomous movement and animation | fixture PASS; native UNTESTED | Fall velocity/scale-up in fixture; no animation bank or draw. |
| 3. Attacks and receivers | fixture PASS; receiver UNTESTED | Strike classification/attribution; host receiver routing not wired. |
| 4. Death and corpse | fixture PASS; corpse source-backed N/A | `finishDeath`/`Killed`; `EB_LeaveCarcass` disabled (`Rock.cpp:59`). |
| 5. Transport and reward | source-backed N/A | Falling hazard: no carry or reward. |
| 6. Cleanup and re-entry | fixture PASS (slot reuse); native UNTESTED | Pool slot reuse after `Killed`; no native reset/teardown. |

The Stone rolling `ROCK_Move` gates are covered by #406 and are **not** claimed
here.

## 11. Fixture baseline adoption

No runtime acceptance run was performed in this slice, so the mandatory
starting-Pikmin overlay and 960x540 centred-window adoption
([PIKMIN2_IMPLEMENTATION_FANOUT.md](PIKMIN2_IMPLEMENTATION_FANOUT.md)) is **not**
claimed here. It remains required before this lane's next native/runtime
acceptance run. No executable, arena or save was launched.

## 12. Open items for later slices

- Host MapMgr/creature-physics fall-trace adapter with the
  `floorTriangle`/`colliding` contract, and the real `mFallSpeed`/`mFallOffset`/
  `mScaleUpRate` parm values bound to converted assets (#128/#350).
- Host Olimar/Pikmin sight enumeration for the Wait detection branch.
- Receiver routing for `InteractPress`/`InteractAttack` and source-enemy
  attribution; separate acceptance evidence.
- Shadow add/remove/force-visible, fall/dead effects, fall/break sounds and the
  Run/Dead animation bank.
- Native registration and the Rock arena gates; drop-group collision/bounce
  behaviour against a live map.
- Save/resume of in-flight falling rocks, and joint manager budgeting with the
  Stone (#406).
