# Snow angular response profile (#120)

This experimental profile applies the retail Snow proportional angular response
inside the existing P1 turn path. It does not port full P2 locomotion, change
forward movement speed or retime bite/capture events.

Single opt-in field:

```text
P2_SNOW_TURN_1
turn_profile source_snow
```

The profile is fixed to audited source values; this is not a general tuning file.
Extraction: `py -3.12 -m experimental.pikmin2_snow_turn --iso PATH --output NEW_DIR`.
`install(imported,run)` requires an existing Snow visual/actor bank. Health and
attack-entry policies are independent.

## Source mapping and deliberate boundary

Retail enemy/parm/enemyParms.szs / yellowkochappy/enemyparm.txt general fp08 is
0.4 (turn gain) and fp28 is10 (maximum angular step in degrees). EnemyParmsBase.h
names these mTurnSpeed and mMaxTurnAngle. General fp06 is50 world units of movement
speed, matching P1 Chappy's constructor chase/home speed; installed P1 assets may
override that default.

KochappyBase.h maps proper fp03 to rotation-end angle: retail Snow is180 degrees.
Proper fp01=2 is absent-minded duration, not completion tolerance. This distinction
is enforced by extractor tests. The source StateTurn can complete after one
proportional update and continue steering while walking. The P1 walking/action
path is different, so this increment records the source180 but does not apply it.

P2 EnemyBase::turnToTarget uses the signed shortest angle, multiplies by0.4,
clamps the result to +/-10 degrees, then updates direction. sysMath::angDist
chooses the negative direction at an exact180-degree tie. The native
profile preserves P1's existing turnSpeed*dt strict arrival threshold and snap;
otherwise it applies this source angular step. Thus it changes angular response,
while retaining P1 state-entry, animation gates and arrival behavior.

The source angular response is per update, not dt-normalized. At a normal30-Hz
simulation it can turn up to300 degrees per second; do not describe that as a
constant speed. At small errors it turns proportionally. Different update rates
change its response per wall-clock second. P1's arrival threshold remains dt-based.

Source paths under native/pikmin2-research: include/Game/EnemyBase.h,
include/Game/EnemyParmsBase.h, include/Game/Entities/KochappyBase.h,
src/sysCommonU/sysMath.cpp and src/plugProjectYamashitaU/kochappyState.cpp.
P1 receiver references: BTeki::turnToward in tekibteki.cpp and
TaiTurningToTargetPositionAction::act in taimoveactions.cpp. P1 prechecks may
finish a turn before the receiver is called; those remain unchanged.

## Validation status

Real retail extraction records source hashes and the correctly mapped180-degree
completion value. Eighteen focused tests cover signed/capped/proportional
steps, exact180 tie, wraparound, strict P1 arrival/snap, convergence, invalid input
installer prerequisites, compiled C++ registry behavior and native receiver wiring. Both modified native .cpp files compile in isolated output using production flags. The combined turn/attack/health suites pass48 tests. Full integration build and actual native turning runtime evidence remain pending.


The native implementation owns no family parameters: pc_p2_enemy registers the
turn policy only for configured Snow actors and the existing reset/forget hooks
clear its registry. Nonliving actors use the original path, preserving corpse
behavior. Invalid finite-state inputs leave a registered actor's direction
unchanged and report not arrived; unregistered actors retain the P1 receiver.
The setup log explicitly records source_rotation_end_180=not_applied.
