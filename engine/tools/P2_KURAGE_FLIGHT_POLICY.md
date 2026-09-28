# Lesser Jellyfloat (Kurage) flight/suction policy contract (#243)

`pc_port/pc_p2_kurage_flight_policy.h` transcribes the retrieved source flight
and suction numerics for the Lesser Spotted Jellyfloat, complementing the lane's
existing bounded receiver/digestion host. It is dependency-free; hosts supply
per-tick facts.

Source anchors: `include/Game/Entities/Kurage.h`,
`src/plugProjectNishimuraU/Kurage.cpp`, `.../KurageState.cpp`.

## Contract

- `heightVelocity` / `altitude` (`setHeightVelocity`): vertical velocity is
  `(speedFactor + fp02) * ((yOffset + fp01 + mapY) - positionY)`.
- `movePitchOffset`: free-running `50 * sin(timer)` with `timer += dt*PI`,
  wrapped at `TAU`.
- `attackPitchOffset` / `flickPitchOffset` / `takeOffPitchOffset` /
  `fallPitchOffset`: linear keyframe sampling. `fallPitchOffset` scales the
  state timer by 30 and samples only the first four of eight segments, matching
  the decomp.
- `updateFallTimer` (`updateFallTimer`): accumulates only while Pikmin are
  latched to the body, otherwise resets.
- `flyingNextState` (`getFlyingNextState`): death -> `Dead`; Purple latch ->
  `Fall`; `fallTimer > fp04` or `stuck >= ip01` -> `FlyFlick` (below `ip01`) or
  `Fall`; otherwise `Null`.
- `inSuctionWindow` / `searchAdmit` / `inAttackRange`
  (`getSearchedTarget`, `isSuck`): vertical window `currY - offset - 50 < y <
  currY`, alive/Pikmin/not-self-stuck, view half-angle
  `PI * (DEG2RAD * mViewAngle)` and `mSightRadius` / `mMaxAttackRange`.
- `suckAdmit` (`suckPikmin`): below `ip11`, passing the `fp12` chance roll,
  inside the `mAttackRadius` and vertical window.

## Exclusions

No state machine, animation/event playback (#431), receiver/attachment
ownership, moving suction joint, assets, spawn, arena placement or rendering.
`fill()` order/candidate iteration order and the per-candidate RNG stream remain
host responsibilities (the lane's existing admission gate is deterministic).

## Evidence

`tools/p2_kurage_flight_policy_test.cpp` — 35 assertions across the climb
velocity, pitch keyframes, fall timer, flying next-state, scan/suction geometry
and suction admission. MinGW-w64 g++ 16.2.0, warning-clean under
`-std=gnu++17 -Wall -Wextra -Werror`.
