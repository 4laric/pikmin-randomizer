# Swooping Snitchbug (Sarai) source audit — enemy ID 23 (#166, lane 30)

Audited against US GPVE01 rev 0 read-only checkout
`native/pikmin2-research` (no engine edits). This is the first source slice for
the Swooping Snitchbug; the Bumbling Snitchbug (`Demon`, ID 32) candidates are
tracked separately on #242.

## Identity

| Field | Value |
|---|---|
| Name | `Sarai` — Swooping Snitchbug |
| Enemy ID | 23 |
| Animator/mgr | `SaraiAnimator`, `SaraiMgr`, `SaraiState` (`plugProjectNishimuraU`) |
| Headers | `include/Game/Entities/Sarai.h` |
| Derived class | `Demon` (Bumbling Snitchbug, ID 32) |
| Mouth slots | 2 (`rkamujnt`, `lkamujnt`), radius 15.0f |

## FSM (Sarai.h)

States: `Dead`, `Fall`, `Damage`, `TakeOff`, `Flick`, `Wait`, `Move`, `Attack`,
`Fail`, `CatchFly`, `FallMeck` (11). Animations: `wait1`, `move1`, `attack1`,
`waitact2` (CatchFly), `waitact1` (FallMeck), `flick`, `type1` (Fall), `type2`
(Damage), `type3` (TakeOff), `type4` (Fail), `type5` (Carry), `dead`.

Key transitions (SaraiState.cpp):

- **Attack** dives at a Pikmin target; `catchTarget()`
  (`EnemyFunc::eatPikmin`) is called only once `getMotionFrame() > 16.0f`.
  `KEYEVENT_4` with no catch -> `Fail`; `KEYEVENT_END` with a catch ->
  `CatchFly`, without -> `Move`. `disableEvent(EB_NoInterrupt)` at `KEYEVENT_3`.
- **Fail** decays target velocity by `fp32` and re-checks on `KEYEVENT_END`.
- **CatchFly** climbs (`setHeightVelocity`) and walks to a random target with
  `fp05`; drops to the height decision when altitude > `fp03` or general timer
  > 3.0 s; `KEYEVENT_END` -> `FallMeck`. If the catch is lost at any point ->
  `Move`.
- **FallMeck** drops the captives at `KEYEVENT_3` via `fallMeckGround()` and
  returns to `Move` at `KEYEVENT_END`.

## Distinctive mechanics (Sarai.cpp)

- **Climb velocity** (`setHeightVelocity`): weight = clamp(body-latched Pikmin,
  0..5); `velFactor = lerp(fp11, fp12, weight/5)`; target height = mapY +
  (`fp02` if carrying else `fp01`); `velocity.y = velFactor * (target - y)`.
- **Escape/drop decision** (`getNextStateOnHeight`): death -> `Fall`; any
  Purple among body-latched Pikmin -> `Fall`; otherwise `index =
  clamp(bodyLatched - 1, 0, 4)` and `fallChance = lerp(fp21, fp22, index/4)`;
  `randWeightFloat(1.0f) < fallChance` -> `Flick` (flick off attackers), else
  `Fall` (drop the captives).
- **Flick** (`flickStickTarget`): `InteractFlick(this, 10.0f, 0.0f,
  FLICK_BACKWARD_ANGLE)` on every mouth-stuck creature.
- **Drop** (`fallMeckGround`): `InteractFallMeck(this, mAttackDamage)` plus
  downward velocity `-fp41`.
- **Target selection** (`getAttackableTarget`): inside `mTerritoryRadius`,
  living, `isPikmin`, not `isStickToMouth`, not already stuck to this, with a
  floor triangle, within the view angle and `mSightRadius`.
- **Random patrol target** (`setRandTarget`): home radius when carrying, a
  `50 + rand(50)` cave radius underground, else home..territory on the surface.

## Parms (Sarai.h ProperParms; retail overrides via converted assets)

`fp01` normal flight height 100, `fp02` grab flight height 80, `fp03` state
transition height 50, `fp04` normal speed 100, `fp05` grab speed 75, `fp06` wait
3.0, `fp11` climbing factor 1.5, `fp12` climbing factor 1.0, `fp21` payoff
probability (1) 0.1, `fp22` payoff probability (5) 0.7, `fp23` struggling time
3.0, `fp31` hunt descent factor 0.3, `fp32` post-hunt decay 0.95, `fp41`
FallMeck speed 200.

## Not yet implemented

No native `Sarai` actor/module, mouth attachment, animation playback, assets,
receiver wiring, arena placement or eligible encounter exists. This lane slice
delivers the isolated policy contract (`pc_p2_sarai_policy.h`) and its fixtures
only. The next slices are: (1) capture/attachment receiver against a real mouth
slot, (2) flight lifecycle (Attack -> CatchFly -> decision -> FallMeck -> Move)
on an ordinary spawned actor, (3) source animation/event playback (#431 clock),
and (4) arena placement under #186.
