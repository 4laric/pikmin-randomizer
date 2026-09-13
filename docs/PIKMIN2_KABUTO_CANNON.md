# Cannon Beetle attack-FSM / Stone-birth contract (#424)

Implementation owner: opencode projectiles-lane session via shared account
`4laric`. Parent: [#169](https://github.com/4laric/pikmin-randomizer/issues/169).
Integration contract: [#186](https://github.com/4laric/pikmin-randomizer/issues/186).
Projectile slices: [#406](https://github.com/4laric/pikmin-randomizer/issues/406)
(Stone), [#410](https://github.com/4laric/pikmin-randomizer/issues/410) (Egg),
[#411](https://github.com/4laric/pikmin-randomizer/issues/411) (Rock),
[#412](https://github.com/4laric/pikmin-randomizer/issues/412) (host adapter),
[#413](https://github.com/4laric/pikmin-randomizer/issues/413) (native seam).
Source contract: [#350](https://github.com/4laric/pikmin-randomizer/issues/350).

This slice implements the **consumer** side of the Cannon projectile path: the
Armored/Decorated/Buried Cannon Beetle attack FSM that births the Stone. It is
an isolated policy milestone: lane-owned files, no shared hooks, no converter or
build changes, no native actor registration.

Source reference is projectPiki/pikmin2 revision
`632af93787b9c95b63f0c13be32b161375ce3a96` (US GPVE01 rev 0); line numbers
follow `native/pikmin2-research`.

## Lane-owned files

Native branch `opencode/p2-projectiles-cannon` at base native `3c30aa39`
(the lane integration candidate):

- `pc_port/pc_p2_kabuto_cannon.h` / `.cpp` — isolated fire-decision policy.
- `tools/p2_kabuto_cannon_test.cpp` — standalone fixture executable.
- `docs/PIKMIN2_KABUTO_CANNON.md` — this contract.

No edit to the Stone/Egg/Rock/host/seam modules or their CMake wiring.

## 1. Identity and states

| Field | Value | Source |
|---|---|---|
| Surfaced species | Kabuto 75 (Green), Rkabuto 95 (Red) | `enemyInfo.h:134,154` |
| Buried species | Fkabuto 96 | `enemyInfo.h:155` |
| Attack states | `KABUTO_Attack` (5), `KABUTO_FixAttack` (11) | `Kabuto.h:28-44` |
| Attack clips | `attack` (`KEYEVENT_2` at frame 50), `K_attack` (`KEYEVENT_2` at frame 55) | PIKMIN2_CANNON_PROJECTILE_ASSETS.md §3 |

Phases modeled: `Wait`, `Turn`, `Attack`, `FixAttack`, `Flick`, `FixWait`,
`FixTurn`, `FixHide`, `FixStay`, `FixAppear`, `Dead`, `Killed`. Surface `Move`
locomotion and buried emergence animation/effects/shake are host-owned; the
emergence transition graph is modeled. Fkabuto `onInit` starts in `FixStay`
(`Kabuto.cpp:48-54`).

## 2. Firing — `createStoneAttack`

`StateAttack::exec` / `StateFixAttack::exec` fire on the attack animation's
`KEYEVENT_2` (`KabutoState.cpp:355-359`, `:720-724`) by calling
`Obj::createStoneAttack` (`Kabuto.cpp:268-290`):

- Birth position from the `mouth` joint world matrix with `+25.0f` y
  (`Kabuto.cpp:274-277`); `P2KabutoCannon::takeBirth` reuses
  `P2CannonStone::mouthBirthPosition`.
- `birthArg.mFaceDir = mFaceDir` (`:279`).
- Homing is enabled only when `getEnemyTypeID() == EnemyID_Rkabuto`
  (`:285-287`); Kabuto and Fkabuto are non-homing.
- A failed birth is silently tolerated (`:281-288`); the host applies that to
  the Stone pool.

The policy raises a pending birth on `KEYEVENT_2` and reports
`P2KabutoAction::FireStone`. `takeBirth(mouthJointWorldPos, faceDir, out)`
consumes it exactly once and fills `P2KabutoStoneBirth`.

## 3. Attack END transitions

Surfaced `StateAttack::exec` (`KabutoState.cpp:360-372`), on `KEYEVENT_END`:

1. `EnemyFunc::isStartFlick(kabuto, false)` -> `Flick`.
2. `getSearchedTarget()` -> `Turn`.
3. otherwise -> `Wait`.

Buried `StateFixAttack::exec` (`:725-748`):

1. flick -> `FixFlick` (modeled as `Flick`; the host picks the `K_flick` clip
   for Fkabuto).
2. `isAttackableTarget()` -> `FixAttack`.
3. `getSearchedTarget()` present: `|angDist| <= mMaxAttackAngle` -> `FixWait`,
   otherwise -> `FixTurn`.
4. no target -> `FixHide`.

The policy returns the matching `P2KabutoAction::To*` and moves its own phase.

## 4. Wait / Turn / Flick / Dead

- `Wait` END (`:89-110`): flick -> `Flick`; searched target -> `Turn`; else keep
  waiting.
- `Turn` END (`:139-174`): flick -> `Flick`; attackable target -> `Attack`;
  otherwise keep turning (the no-target random-move branch is host-owned and
  folded to a continued search here).
- `Flick` END: searched target -> `Turn`, else `Wait`.
- Death gate (`:350-353`, `:92-95`, `:142-145`, `:715-718`): `health <= 0` in
  any live state -> `Dead`. `Dead` END -> `kill(nullptr)` -> `Killed`
  (`:55-59`); the host owns the corpse/carry path.

## 4a. Buried emergence (Fkabuto)

Modeled from `KabutoState.cpp:391-690`. `FixStay` is invulnerable, hidden and
consumes no animation events: a searched target transits to `FixAppear`
(`:411-421`). `FixAppear` END checks health first (-> `Dead`), then flick
(-> `Flick`), attackable (-> `FixAttack`), a target within `mMaxAttackAngle`
(-> `FixWait`, else `FixTurn`), otherwise `FixHide` (`:473-506`). `FixHide` END
returns to `FixStay` (`:545-553`). `FixWait` END (`:584-616`) and `FixTurn` END
(`:644-681`) select `FixAttack` / `FixWait` / `FixTurn` / `FixHide`; `FixTurn`
with an out-of-angle target keeps turning. The policy adds
`P2KabutoAction::ToFixStay` / `ToFixAppear` and the species-aware `start()`.

## 5. Host contract

The policy never dereferences the animation, model, map or creatures:

- `P2KabutoCannonConfig` — general `mMaxAttackAngle` (degrees) and `mHealth`.
- `P2KabutoHostState` — per-event target presence/attackability
  (`getSearchedTarget` / `isAttackableTarget`), signed horizontal target angle,
  flick request (`EnemyFunc::isStartFlick`) and current health.
- `P2KabutoEvent` — the animation event (`None`/`Key2`/`End`) mapped from
  `EnemyAnimKeyEvent::mType`.
- `P2KabutoAction` — the host starts the matching motion (`To*`), or births the
  Stone from the pending `P2KabutoStoneBirth` (`FireStone`).
- Mouth joint world position and facing are host-supplied; the `+25 y` offset is
  source-fixed in the command.

## 6. Fixture evidence

Standalone MinGW build, no engine objects:

```powershell
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
g++ -std=gnu++17 -Wall -Wextra -Werror `
    -I output/native-projectiles-cannon/pc_port `
    output/native-projectiles-cannon/tools/p2_kabuto_cannon_test.cpp `
    output/native-projectiles-cannon/pc_port/pc_p2_kabuto_cannon.cpp `
    output/native-projectiles-cannon/pc_port/pc_p2_cannon_stone.cpp `
    -o output/p2-projectiles-cannon/p2_kabuto_cannon_test.exe
```

Compiled warning-clean with local MinGW GCC 16.2.0; test exit 0. Executable
SHA-256 `D13044928270635008C4E12216E7925439DFB514EA093B5311EE23903C15DF36`.
Native base commit `3c30aa39`.

Coverage: single-fire per `KEYEVENT_2` and consumed-birth idempotence; the
`+25 y` mouth birth and face dir; Rkabuto-only homing (Kabuto/Fkabuto
non-homing); Wait/Turn/Flick END decisions; Attack END flick/target/idle table;
FixAttack END flick/attackable/angle-boundary/no-target table; `FixWait`
re-entry firing; health -> Dead -> kill terminal; explicit `beginDead`; invalid
config and non-finite host input immutability.

## 7. Arena gate status (policy slice)

| Gate | Status |
|---|---|
| 1. Exact identity and spawn | policy-level birth PASS; natural spawn native UNTESTED |
| 2. Autonomous movement and animation | source-backed N/A (animation host-owned) |
| 3. Attacks and receivers | fire decision PASS; Stone receiver UNTESTED (#186) |
| 4. Death and corpse | Dead->kill PASS; corpse host-owned |
| 5. Transport and reward | source-backed N/A |
| 6. Cleanup and re-entry | FSM terminal PASS; native reset UNTESTED |

## 8. Fixture baseline adoption

No runtime acceptance run was performed in this slice, so the mandatory
starting-Pikmin overlay and 960x540 centred-window adoption is **not** claimed.
No executable, arena or save was launched.

## 9. Open items

- Wire `P2KabutoCannon` into the #413 seam so the host spawns the Stone from
  the FSM event stream and a real mouth joint (gate 1).
- Host target enumeration matching `getViewAngle`/`isAttackableTarget`.
- Surface `Move` locomotion and buried emergence animation/effects/shake.
- Receiver routing / target-health mutation (#186 shared-semantics review).
