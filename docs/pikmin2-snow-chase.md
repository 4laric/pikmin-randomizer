# Snow walk steering and chase slice (#120)

The implemented bounded bridge from angular-only turning to source-style chasing
is a heading-aligned chase target velocity. It is intentionally separate from
full P2 locomotion, physics, animation and state selection.

## Source update path

Retail YellowKochappy general fp06/fp08/fp28 are50 world units of forward speed,
0.4 turn gain and10 degrees maximum angular change per update.

KochappyBase StateWalk first handles flick, target search and whether to enter
attack/turn/home states. In the remaining chase branch it calls
EnemyFunc::walkToTarget. That function:

1. Calls EnemyBase::turnToTarget with source proportional yaw and cap.
2. Reads the updated facing.
3. Writes target velocity X/Z as50*sin(facing),50*cos(facing).
4. Preserves the existing target velocity Y.

There is no arrival snap in this chase overload. The0.4 response and10-degree
cap are per call, without dt multiplication. Actual ground movement is separate:
EnemyBase::doSimulationGround replaces desired Y with current vertical velocity,
applies acceleration dt/mAccel and gravity, then engine collision/movement
integrates velocity. A target-velocity test alone cannot prove ground speed or
collision parity.

StateWalk::init sets movement animation speed40*(moveSpeed/50), then starts the
Move clip. Transitions can finish motion and use60 animation speed. None of these
animation signals are applied by the bounded steering implementation. Current Snow
visuals still sample source poses from native motion progress.

Source paths under native/pikmin2-research:

- src/plugProjectYamashitaU/kochappyState.cpp: StateWalk init/exec
- src/plugProjectYamashitaU/enemyAction.cpp: both walkToTarget overloads
- include/Game/EnemyBase.h: turnToTarget/getAccelerationScale
- src/plugProjectYamashitaU/enemyBase.cpp: doSimulationGround
- include/Game/EnemyParmsBase.h and retail yellowkochappy/enemyparm.txt

## Native receiver differences

P1 TaiTracingAction waits for its continuous motion to start, requires a target,
then calls BTeki::moveToward with the action's stored trace speed. moveTowardStatic
zeros both Y positions, normalizes the direct target displacement and writes
that vector times speed to mTargetVelocity. It does not first turn toward the
heading and writes desired Y as zero.

The native Creature update runs animation/AI before movement. Creature::moveRotation
later turns facing toward target velocity using an adjustment factor and dt.
Creature::moveVelocity applies its own acceleration, slopes and gravity behavior.
In the native Chappy chase state, tracing precedes the attackable/flick/target
conditions. This ordering differs from P2 StateWalk and remains out of scope.

P1 references: taimoveactions.cpp::TaiTracingAction::act,
tekibteki.cpp::moveToward/Static, taichappy.cpp chase state action order,
creature.cpp::update/moveVelocity and creatureMove.cpp::moveRotation.

## Optional native contract

```text
P2_SNOW_CHASE_1
chase_profile source_snow
```

One optional fixed profile, independent of health, attack-entry and turning
profiles. Apply only to registered living Snow actors within TaiTracingAction,
after motionStarted and nonnull-target guards. Use source yaw gain/cap without
P1 arrival snapping, then target velocity50 along the new heading with Y retained.
Existing generic auto-facing then sees a target velocity already aligned with
facing, apart from numerical rounding. No persistent rotation flags or shared
family parameters need to change.

The native interface is implemented in pc_p2_enemy.cpp/h with a new isolated
policy header and a guarded TaiTracingAction receiver. Existing reset/forget
hooks supply registry cleanup. Homeward movement, wandering, knockback, corpse
transport, animation rates, target selection and state ordering remain unchanged.
Missing policy and ordinary actors keep the existing moveToward path.

A90-degree target from facing0 gives heading10 degrees and desired X/Z about
8.6824/49.2404. P1's current direct-to-target vector is50/0. This is a measurable
steering increment even though source forward speed50 matches the P1 constructor
chase-speed default. Physical acceleration remains native.

## Current artifacts and validation

experimental.pikmin2_snow_chase extracts source parameters/hashes and exposes a
reference steer function. Use `--iso PATH --output NEW_DIRECTORY`; install into
an existing private Snow bank using install(imported,run).
Sixteen tests cover source values, turn-before-velocity ordering, preserved Y,
constant horizontal speed, signed/wrapped turns, no arrival snap, update sequence,
invalid values and installation prerequisites. Retail extraction passed locally
at output/p2-snow-chase/import. Native policy and receiver wiring are implemented; reference vectors are not runtime gameplay evidence.


The native policy uses the existing source turn-step helper with arrivalStep0,
so it never applies the separate P1 turn-arrival snap while chasing. Per-actor
registration is independent of the other Snow policies; reset and forget clear
it through existing scene/slot lifecycle calls. A nonliving actor falls back to
P1. Malformed configuration is rejected before pose resources load. Nonfinite
inputs leave registered actor state unchanged rather than writing invalid
velocity/facing values.

Sixteen focused chase tests include a compiled C++ probe for actual policy
vectors, preserved Y, horizontal speed50, negative180 tie, invalid values,
unregistered/ordinary fallback, individual forget, reset and reload. Receiver
wiring checks retain motion-started and target guards before the override.
The combined chase/turn/attack/health policy suites pass64 tests. Both modified
native .cpp files compile in private output using current production flags.
Full integration build and a native chase-action runtime fixture remain pending.
No physical-speed, animation or full P2 AI parity claim follows from these tests.
