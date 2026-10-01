# Swooping Snitchbug (Sarai) isolated policy contract (#166, lane 30)

`pc_port/pc_p2_sarai_policy.h` is a dependency-free transcription of the
Swooping Snitchbug's numeric behavior. It owns no engine state; a host supplies
per-tick facts and consumes the returned decisions. Build/test:

```
g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_sarai_policy_test.cpp -o p2_sarai_policy_test.exe
p2_sarai_policy_test.exe   # p2_sarai_policy_test PASS checks=38
```

## Host inputs

| Input | Source meaning |
|---|---|
| `bodyStuckCount` | `mStuckPikminCount` (all body-latched Pikmin, including mouth-carried) |
| `mouthCarried` | `getCatchTargetNum()` (occupied mouth slots) |
| `purpleLatched` | any body-latched Pikmin is Purple |
| `mapY`, `positionY` | map ground height and Sarai position (for climb velocity) |
| `randomUnit` | a fresh `randWeightFloat(1.0f)` in `[0, 1)` |
| symbolic key events | engine `KEYEVENT_*` mapped by the host, not hard-coded here |

## Contract

- `climbingFactor` / `heightVelocity`: weight clamps body-latched Pikmin to
  0..5; the factor lerps `fp11 -> fp12`; the target height is `mapY + fp01`
  (`fp02` while carrying). Positive velocity means rising.
- `nextStateOnHeight`: death -> `Fall`; Purple latch -> `Fall`; no body
  attackers -> `None`; otherwise `fallChance = lerp(fp21, fp22,
  clamp(bodyLatched-1, 0, 4) / 4)` and `randomUnit < fallChance` -> `Flick`,
  else `Fall`.
- `stickPikminNum`: body-latched count minus mouth-carried count.
- `randTargetRadius`: carrying -> `fp`-driven home radius; cave -> `50 +
  rand(50)`; surface -> home..territory.
- `fallMeckVelocity`: `-fp41` applied to a released captive.
- `attackMayCatch`: `motionFrame > 16.0f` (the only frame window where
  `catchTarget()` runs).
- `attackExit`: symbolic Attack transitions (`Fail` / `CatchFly` / `Move`).
- `catchFlyReadyForHeightDecision`: altitude > `fp03`, general timer > 3.0 s,
  or motion `END`.
- `targetable` (`getAttackableTarget`): only inside `mTerritoryRadius`; candidate
  must be alive, a Pikmin, not mouth-stuck, not stuck to this Sarai, on a floor
  triangle, within the view half-angle and within `mSightRadius`. `viewHalfAngle`
  transcribes the source expression `PI * (DEG2RAD * mViewAngle)` verbatim.

## Deliberate exclusions

The policy does not decide target acquisition geometry
(`getAttackableTarget` raycast/sight), mouth-slot attachment, animation/event
playback, flick/drop receiver semantics, rendering or spawn. Those are host or
shared-semantics concerns and stay on their owning lanes/contracts.

## Evidence

- `tools/p2_sarai_policy_test.cpp` — 49 assertions across the climb factor,
  height velocity, latch accounting, escape/drop probability (including
  monotonicity), random-target radius branches, FallMeck velocity, Attack catch
  frame window and transitions, the CatchFly decision trigger, and
  `getAttackableTarget` geometry.
- Compiler: MinGW-w64 g++ 16.2.0, warning-clean under
  `-std=gnu++17 -Wall -Wextra -Werror`.
