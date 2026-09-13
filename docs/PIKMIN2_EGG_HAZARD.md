# Egg hazard destruction and drop-table contract (#410)

Implementation owner: opencode projectiles-lane session using shared account
`4laric`. Parent: [#169](https://github.com/4laric/pikmin-randomizer/issues/169)
(Cannon larvae, Groinks and projectiles). Integration contract:
[#186](https://github.com/4laric/pikmin-randomizer/issues/186). Source contract
for the same entries: [#350](https://github.com/4laric/pikmin-randomizer/issues/350) /
[PIKMIN2_CANNON_PROJECTILE_ASSETS.md](PIKMIN2_CANNON_PROJECTILE_ASSETS.md).
Sibling slice: [#406](https://github.com/4laric/pikmin-randomizer/issues/406) /
[PIKMIN2_CANNON_STONE_PROJECTILE.md](PIKMIN2_CANNON_STONE_PROJECTILE.md).

This is the #169 "stationary variants ... eggs" slice: the **Egg (EnemyID 37)**
destruction and `genItem` reward drop table, implemented as an isolated policy.
It is a separate `Egg::Obj` resource group from Rock/Stone and Bomb. It is an
isolated policy milestone: lane-owned files, no shared hooks, no converter/build
changes, no native actor registration.

Source reference is projectPiki/pikmin2 revision
`632af93787b9c95b63f0c13be32b161375ce3a96` (US GPVE01 rev 0); line numbers
follow `native/pikmin2-research`.

## Lane-owned files

Native branch `opencode/p2-projectiles-stone` (continues #406) at base native
`356e9c08`:

- `pc_port/pc_p2_egg_hazard.h` / `.cpp` — isolated Egg policy.
- `tools/p2_egg_hazard_test.cpp` — standalone fixture executable.
- `docs/PIKMIN2_EGG_HAZARD.md` — this contract.

No edit to the Stone module (`pc_p2_cannon_stone.*`), the Groink modules
(#169/#198/#204-#210) or the BombSarai modules (#244).

## 1. Identity and state machine

| Field | Value | Source |
|---|---|---|
| ID | `EnemyID_Egg` 37 | `enemyInfo.h:96` |
| Obj / Mgr | `Game::Egg::Obj` / `Mgr`; `EFlag_HasNoInfo` projectile/hazard (child Mitite x10) | `Egg.h:35,79`; `enemyInfo.cpp:65` |
| States | `EGG_Wait` only | `Egg.h:159-162`, `eggState.cpp:14-18` |
| Animation | `damage1` only | `Egg.h:141-144` |

Phases modeled: `Inactive`, `Wait`, `Broken`. `Broken` is the same-tick
`genItem` + `kill(nullptr)` path (`eggState.cpp:45-65`); the host frees the slot.

`onInit` (`egg.cpp:35-62`): disables `EB_LeaveCarcass`, `EB_DamageAnimEnabled`,
`EB_DeathEffectEnabled`; sets `EB_BitterImmune`; clears `mIsFalling`; starts
`EGG_Wait`. A non-drop-group Egg enables `EB_Constrained` and the host snaps its
Y to `mapMgr->getMinY(position + 20)`; the policy records `constrained` and
leaves the map query to the host.

## 2. Destruction triggers

- `Obj::doUpdate` (`egg.cpp:79-88`): target velocity is zero on a floor triangle,
  otherwise it tracks the current velocity. Host physics.
- `bounceCallback` (`egg.cpp:166-172`): a falling (`mIsFalling`) or drop-group Egg
  that touches a floor sets the lifegauge visible and `mHealth = 0`.
- `collisionCallback` (`egg.cpp:178-186`): a drop-group Egg in `EGG_Wait` touched
  by a **non-null, non-Teki** creature sets the lifegauge visible and
  `mHealth = 0`.
- `pressCallBack` returns `false` (`egg.cpp:157-160`): ordinary Pikmin press does
  not damage an Egg. Host-injected attacks use `damage()`.
- `StateWait::exec` (`eggState.cpp:45-65`): when `mHealth <= 0`, `genItem()`
  runs, break effects/sound play and `enemy->kill(nullptr)` removes the Egg. The
  `mFlickTimer`/key-event motion restart (`:67-75`) is host animation.

## 3. Capture lifecycle

`onStartCapture` (`egg.cpp:215-226`): constrained, invulnerable, not cullable;
the host moves it with the capture matrix. `onEndCapture` (`egg.cpp:232-237`):
constraint off, `mIsFalling = true`, cullable. The policy records the source
event flags; the host owns the matrix and position.

## 4. Drop table — `genItem`

`Obj::genItem` (`egg.cpp:243-383`). The policy returns the selected type and the
per-item spawn commands; the host births the items and applies the spawn
velocity at `mPosition + (0, 2, 0)` (`:248-249`).

Selection (`:251-275`): one `randFloat()` is compared against cumulative
`fp01..fp05`; the source default (no band matched) is `EGGDROP_SingleNectar`.

| Band | Type | Spawn (`switch`, `:293-382`) |
|---|---|---|
| fp01 `singleNectarChance` (disc 0.5) | SingleNectar | one `ItemHoney` `HONEY_Y`, velocity `(0,250,0)` |
| +fp02 `doubleNectarChance` (0.35) | DoubleNectar | two `HONEY_Y`: `angle = TAU*randFloat()`, item i velocity `(50 sin(PI*i+angle), 250, 50 cos(PI*i+angle))` (`:320-336`) |
| +fp03 `mititesChance` (0.05) | Mitites | `TamagoMushi` group of 10, `velocity.y = 200`, `faceDir = TAU*randFloat()`; on `createGroup` failure a `HONEY_Y` nectar fallback (`:340-362`) |
| +fp04 `spicyChance` (0.05) | Spicy | `ItemHoney` `HONEY_R` (`:364-379`) |
| +fp05 `bitterChance` (0.05) | Bitter | `ItemHoney` `HONEY_B` (`:364-379`) |

Overrides:

- `mForcedDropType != 0` sets `dropType = mForcedDropType - 1` (1-based parm;
  `:277-279`).
- `mDoCheckHasSpray != 0` downgrades Spicy/Bitter to SingleNectar until
  `DEMO_First_Spicy_Spray_Made` / `DEMO_First_Bitter_Spray_Made` is set
  (`:281-289`).

`1Pellets`/`5Pellets` (`:294-306`) spawn a `PelletNumber` of 1 or 5 with
`randInt(3)` colour and velocity `(0,250,0)`. The retail Egg drop chances
(fp01 0.5, fp02 0.35, fp03-05 0.05) come from
[PIKMIN2_CANNON_PROJECTILE_ASSETS.md](PIKMIN2_CANNON_PROJECTILE_ASSETS.md) §5.

## 5. Host contract

The policy never dereferences map, creatures, items, effects or sound:

- `P2EggConfig` — disc proper parms, forced type, spary-demo flags and general
  health (disc 50). Values are converter/host inputs, never invented.
- `P2EggRandFloatFn` / `P2EggRandIntFn` — scripted host RNG; the policy consumes
  them in the exact source order (`randFloat` roll, then the branch's
  `randFloat`/`randInt`).
- `damage()` / `bounce()` / `contact()` — host-detected damage and contacts.
- `onStartCapture()` / `onEndCapture()` — source event flags.
- `update()` — when health is zero, computes `P2EggDrop` once and transits to
  `Broken`; the host births the items then frees the Egg.
- `P2EggDrop` — item kinds, pellet colour, velocities, Mitite count and the
  nectar-fallback flag. Pellet/Mitite/Honey births and their null checks are
  host-owned.

## 6. Fixture evidence

Standalone MinGW build, no engine objects (same convention as the Stone,
Groink and BombSarai lanes):

```powershell
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
g++ -std=gnu++17 -Wall -Wextra -Werror `
    -I output/native-projectiles/pc_port `
    output/native-projectiles/tools/p2_egg_hazard_test.cpp `
    output/native-projectiles/pc_port/pc_p2_egg_hazard.cpp `
    -o output/p2-projectiles-stone/p2_egg_hazard_test.exe
```

Compiled warning-clean with local MinGW GCC 16.2.0; private run directory
`output/p2-projectiles-stone/` (`egg-build.log` 0 bytes, exit 0). Executable
SHA-256 `79F8E4BD1F62C8E4F119778E5070F7282F5116D78E978AA6C41934E0A442A69C`.
Native base commit `356e9c08`.

Coverage: every cumulative drop band and the sub-1.0 fallthrough; forced
override; Spicy/Bitter first-spray gate; spawn commands for 1/5 pellets
(colour + velocity), single/double nectar (two-item angle math), Mitites
(count/velocity/fallback) and spicy/bitter sprays; bounce trigger and
non-trigger; drop-group/non-drop-group/null/Teki contact classification;
capture flags; exactly-once break and drop; invalid-config refusal
(health, forced range, non-finite chance).

This is a standalone policy test, not a native arena or gameplay test. Host
physics, map snap, item births, effects, sound, the animation and save/resume
are unimplemented.

## 7. Arena gate status (policy slice)

| Gate | Status | Evidence / limitation |
|---|---|---|
| 1. Exact identity and spawn | source-backed + fixture PASS; native UNTESTED | Egg birth/phase in fixture; no native actor registered. |
| 2. Autonomous movement and animation | source-backed N/A (stationary); native UNTESTED | No motion or animation bank. |
| 3. Attacks and receivers | fixture PASS; receiver UNTESTED | Bounce/contact/damage triggers; host receiver routing not wired. |
| 4. Death and corpse | fixture PASS; corpse source-backed N/A | Break/kill path; `EB_LeaveCarcass` disabled (`egg.cpp:38`). |
| 5. Transport and reward | fixture PASS (drop selection); birth UNTESTED | Drop table/commands; item/pellet/Mitite births not wired. |
| 6. Cleanup and re-entry | source-backed (same-tick kill); native UNTESTED | No separate cleanup state; native slot reuse not tested. |

## 8. Fixture baseline adoption

No runtime acceptance run was performed in this slice, so the mandatory
starting-Pikmin overlay and 960x540 centred-window adoption
([PIKMIN2_IMPLEMENTATION_FANOUT.md](PIKMIN2_IMPLEMENTATION_FANOUT.md)) is **not**
claimed. It remains required before this lane's next native/runtime acceptance
run. No executable, arena or save was launched.

## 9. Open items

- Host item/pellet/Mitite births, null-check fallbacks and spawn positioning.
- Host capture/fall physics, map Y snap and floor/collision detection feeding
  `bounce`/`contact`.
- Break effects/sound and the `damage1` animation restart.
- Native registration and arena gates alongside the Stone/other projectiles.
- Numeric drop parms bound to converted assets (#128/#350) and save/resume.
