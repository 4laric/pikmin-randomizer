# Swooping Snitchbug (Sarai) isolated FSM bridge (#166, lane 30)

`pc_port/pc_p2_sarai_fsm.h` is a fixed-step transcription of all eleven Sarai
states in `src/plugProjectNishimuraU/SaraiState.cpp`, composing
`pc_p2_sarai_policy.h` for the numeric decisions. It owns
`mGeneralTimer`/`finishing`, the current `State`, `Motion` and event `Flags`
(`untargetable`, `noInterrupt`, `cullable`); it creates no engine objects.

Build/test:

```
g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_sarai_fsm_test.cpp -o p2_sarai_fsm_test.exe
p2_sarai_fsm_test.exe   # p2_sarai_fsm_test PASS checks=37
```

## States and motions

`Dead, Fall, Damage, TakeOff, Flick, Wait, Move, Attack, Fail, CatchFly,
FallMeck`, with motions `wait1/move1/attack1/waitact2/waitact1/flick/type1..5/dead`.
Entry sets the source's flag/motion changes (for example Attack clears
`Cullable` and sets `NoInterrupt`; FallMeck starts targetable with
`NoInterrupt` off).

## Transition logic (source-faithful)

- `Wait`: target or `fp06` timer finishes the motion; altitude > `fp03` or timer
  > 3 routes through `getNextStateOnHeight`; END -> `Attack` with a target else
  `Move`.
- `Move`: target, 10 s timer or arrival within 25 units finishes the motion;
  altitude/timer routes through the decision; END -> `Attack` (target) else
  `Wait`.
- `Attack`: with no target creature -> `Move`; frames `16..30` emit
  `attemptCatch`; `KEY3` clears `NoInterrupt`; `KEY4` without a catch -> `Fail`;
  END -> `CatchFly` (caught) else `Move`.
- `Fail`: END -> `CatchFly` (caught) else `Move`.
- `TakeOff`: death or altitude > `fp03` finishes; END -> decision, else
  `CatchFly`/`Move`.
- `Flick`: `KEY2` emits `flickAttackers`; END -> `Fall` (death), `CatchFly`
  (caught) else `Move`.
- `CatchFly`: 10 s / arrival finishes the follow; losing the catch -> `Move`;
  altitude > `fp03` or timer > 3 routes through the decision; END ->
  `FallMeck`.
- `FallMeck`: `KEY3` emits `drop`; END -> `Move`.
- `Fall`: below 10 units altitude or 1 s finishes; `KEY2` emits `downEffect`;
  END -> `Dead` (death) else `Damage`.
- `Damage`: death, `fp23` timer or no body attackers finishes; END -> `Dead`
  (death) else `TakeOff`.
- `Dead`: END emits `kill`.

## Host responsibilities (explicitly out of scope)

The host supplies `KeyEvent`, `motionFinished`, `targetPresent`,
`hasTargetCreature`, `targetFrame`, positions/altitude, latch counts and the
random unit, and consumes `In`/`Out`. Still owned elsewhere: the source
animation/event clock (#431), `getAttackableTarget` geometry, the
catch/flick/drop receivers, movement, the Attack hunt-descent velocity and the
post-hunt `mTargetVelocity` decay, assets, rendering, arena placement and
manager registration.

## Evidence

`tools/p2_sarai_fsm_test.cpp` — 37 assertions covering spawn idle choice,
Wait/Move routing, the Attack catch window and `KEY3/KEY4/END` branches,
CatchFly decision vs keep-flying and catch loss, FallMeck drop, TakeOff routing,
Fall/Damage/Dead lifecycles, Flick, and Move arrival. MinGW-w64 g++ 16.2.0,
warning-clean under `-std=gnu++17 -Wall -Wextra -Werror`.
