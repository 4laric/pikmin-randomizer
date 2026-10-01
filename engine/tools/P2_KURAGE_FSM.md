# Lesser Jellyfloat (Kurage) flight-lifecycle FSM bridge (#243)

`pc_port/pc_p2_kurage_fsm.h` is a fixed-step transcription of all eleven Kurage
states in `src/plugProjectNishimuraU/KurageState.cpp`, composing
`pc_p2_kurage_flight_policy.h`. It owns `mStateTimer`, `mMovePitchTimer`,
`mFallTimer`, the current state/motion/flags and `mIsSucking`; it creates no
engine objects.

Build/test:

```
g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_kurage_fsm_test.cpp -o p2_kurage_fsm_test.exe
p2_kurage_fsm_test.exe   # p2_kurage_fsm_test PASS checks=35
```

## States and motions

`Dead, Wait, Move, Chase, Attack, Fall, Land, Ground, TakeOff, FlyFlick,
GroundFlick` with motions `dead1/dead2/flick1/flick2/wait1/move1/move2/type1/type2/attack1`.
Entry sets the source flag/motion transitions (for example Attack clears
`Cullable`; Land/Ground/TakeOff start targetable; Dead picks `DeadFly` vs
`DeadGround` from `isFlying()`).

## Transition logic (source-faithful)

- `Wait`: searched target + suckable -> `Attack`, otherwise -> `Chase`; no
  target for 3 s -> `Move`; END commits the pending state.
- `Move`: searched target -> `Attack`/`Chase`; no target within 10 s or 25 units
  -> `Wait`; otherwise walks to the random patrol target (host).
- `Chase`: searched target + suckable -> `Attack`; target lost -> `Move`; no
  state-timer increment.
- `Attack`: death, `fp11` timer or `fp04` shake finishes the motion; `KEY2`
  starts suction, event `1` stops it once finishing; END routes through
  `getFlyingNextState`, else re-`Attack` (`isSuck`) or `Wait`.
- `Fall`: while flying, `getFallPitchOffset`, and past frame 65 loses
  `Untargetable` and finishes; END -> `Dead`/`Land`.
- `Land`: END -> `Dead`/`Ground`; enters with a down effect.
- `Ground`: no stuck Pikmin or `fp10` finishes; END -> `Dead`/`GroundFlick`
  (stuck)/`TakeOff`.
- `TakeOff`: while flying, `getTakeOffPitchOffset`; `KEY2` becomes untargetable;
  END -> `Dead`/`Wait`.
- `FlyFlick`: `getFlickPitchOffset`; `KEY2` flicks stuck Pikmin; END routes
  through `getFlyingNextState`, else `Attack`/`Wait`.
- `GroundFlick`: `KEY3` flicks nearby captains and Pikmin and stuck Pikmin; END
  -> `Dead`/`TakeOff`.
- `Dead`: `KEY2` flicks, `KEY3` runs the death procedure/body bomb, END kills.
- `getFlyingNextState` (per tick): death -> Dead, Purple -> Fall,
  `fp04`/`ip01` -> FlyFlick or Fall; the FSM owns `mFallTimer` via
  `updateFallTimer`.

## Host responsibilities

`getSearchedTarget`/`isSuck` geometry (`targetFound`/`suckTarget`/`suckAny`),
`walkToTarget` movement, the animation/`KeyEvent` clock (#431), suck/flick
receivers, effects and rendering. The moving suction joint and Animated
collision tree are separate lane work.

## Evidence

`tools/p2_kurage_fsm_test.cpp` — 35 assertions covering spawn, Wait/Move/Chase
routing, Attack suction and END re-attack, Fall/Land/Ground/TakeOff lifecycles,
FlyFlick/GroundFlick, Dead events, and immediate `getFlyingNextState` routing.
MinGW-w64 g++ 16.2.0, warning-clean under `-std=gnu++17 -Wall -Wextra -Werror`.
