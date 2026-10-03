# Original Withering Blowhog (source 55), issue 1255

Implementation owner: Codex through shared GitHub account `4laric`.

`enemyInfo.h` gives Hanachirashi 55. `genEnemy.cpp` creates the ordinary
EnemyGeneratorBase; `gameGenerator.h` gives it `????`, no tail and null initArg.
The provider accepts literal source 55 rows only. It retains complete common
fields, authored sourceKey/UID, survivor counts, ordinal attempts and original
registry tokens. It never resolves an AP pool ID. Neutral TEKI_Mar allocation
provides the native Creature/animation/pellet infrastructure; the Hanachirashi
module drives its own hover/chase/wind/laugh/death behavior and P2 pose bank.

Resources require actual chassis model/animation, number drop resources, converted P2 animation clips including authored attack
KEYEVENT_2 at frame 50, deformable sampled meshes and private actor geometry.
The family opts its drawn source mesh into the native fitted body collider.
Retail onInit disables EB_LeaveCarcass; death END throws authored items then
kills the actor directly. Corpse transport is N/A for source55.
The original registry owns durable course/UID/ordinal/epoch/activation identity.
Native cleanup handles the actor and any partially constructed ownership, and its forget funnel retires
provider ownership before address reuse. Failed and null births consume attempts.

Authored wind starts on the frame after KEYEVENT_2 and remains active until
attack END, with retail radius ramp `min(1,scale+3*dt)*300`. Accepted ordinary
Pikmin lose maturity; Purple loses maturity without a blow or Laugh success.
The native InteractFlick receiver preserves no-HP-loss wind. These remain port
boundaries: wind uses actor center instead of the source emitter joint, flattened
heading/knockback instead of the source 3D impulse, and captain wind is absent.
Fall/Land/Ground/TakeOff/FlyFlick/GroundFlick and ChaseInside source fidelity remain
open. This provider adds original admission; it does not claim full species parity.

## Human gameplay qualification

Use a fresh private original-course session with source 55 at its authored
position and configuration, a living captain, the current 20-Pikmin overlay,
and centered 960x540 window (`PIKMIN_P2_ROOM_WINDOW=960x540`). Preserve the
session's legal assets and prior saves/logs. Never use a synthetic AP replacement.

1. Confirm the real source mesh, flight height and authored facing/position.
   Approach with the squad and observe Wait/Chase/Attack at ordinary game speed.
2. Bring flower/bud Pikmin into the wind cone after the inhale. Confirm maturity
   loss and blow without HP damage. Enter the cone late during the active attack
   to verify the receiver is not limited to its first key event.
3. Test Purple separately: maturity falls, no blow occurs, and Purple stripping
   alone must not select Laugh. Compare captain wind against retail; it is an
   explicitly open gate.
4. Throw four Pikmin onto the body and separately throw one Purple. Record the
   expected retail fall/land/flick response as a current missing-mechanic gate;
   fitted collision alone is not acceptance of grounding behavior.
5. Defeat through ordinary attacks, watch the complete dead animation, and
   record authored number pellets and actual reception. Retail source55 disables
   EB_LeaveCarcass: a carryable corpse is N/A; no borrowed Mar corpse may appear.
6. Save at the normal day boundary, exit, resume, and revisit at the literal
   original respawn interval. Confirm surviving/dead counts and no extra actor,
   borrowed corpse or duplicate number drop across unload/reentry.

Portable provider tests and syntax checks cover contracts only. Production
build, physical combat, number-drop delivery and save/resume need separately
recorded runner/gameplay evidence. Bounded cleanup may stop only this test's PID.
