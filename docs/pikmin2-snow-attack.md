# Snow source attack-entry gate (#120)

The optional `p2-snow-attack.txt` changes when a registered Snow actor may enter
its attack state. It does not change bite hit detection, mouth slots, capture,
swallowing, damage, animation speed, or death/corpse behavior.

```text
P2_SNOW_ATTACK_1
range 30
half_angle 20
```

Extract from the local retail ISO with
`py -3.12 -m experimental.pikmin2_snow_attack --iso PATH --output NEW_DIRECTORY`.
Install into a private Snow bank with `pikmin2_snow_attack.install(imported,run)`.
The existing health policy is independent: neither requires the other. Existing
launchers do not opt in automatically. Missing files preserve P1 behavior;
malformed or unsupported values abort setup before loading pose resources.

## Why an entry gate

Retail `enemy/parm/enemyParms.szs` / `yellowkochappy/enemyparm.txt` general
parameters fp20 and fp21 are 30 and 20. EnemyParmsBase.h identifies these as
maximum attack range and angle. KochappyBase StateWalk, StateTurn and StateAttack
use EnemyBase::isTargetAttackable. That routine tests strict squared **3D center
separation** below 900 and absolute yaw difference at most 20 degrees.
Creature.h includes Y in separation; trig.h treats the angle as a half-angle.

P1 BTeki::attackableCreature instead calls contactCreature, using collision
surface distance, then divides its full-angle parameter by two. Assigning the
source values directly to those P1 parameters would produce different geometry.
The new PC-only branch replaces this geometry only for registered opted-in Snow,
after the existing stuck-to-self rejection. It retains TekiRecognitionCondition
eligibility. All ordinary and unregistered actors continue down the original
contactCreature path. No family parameters are mutated.

The policy keeps an actor registry reset/forget through the existing Snow scene
setup, manager lifecycle and pre-init slot-reuse calls. Corpse identity remains
registered through death; no corpse carrying or delivery behavior is changed.
The geometry helper rejects NaN/infinity and negative squared distances and wraps
yaw before its inclusive angle comparison.

## Why not retime the bite yet

The audited retail kochappy/enemyanimmgr.txt has attack events type2 at frame8 and
type3 at frame88. KochappyBase StateAttack consumes type2 by attacking captains,
capturing Pikmin, switching to the separate Eat animation when no Pikmin are
captured, and flicking attached Pikmin. Type3 swallows captured Pikmin.

P1 TaiAnimationSwallowingAction similarly has capture and swallow actions, but
its ACTION_0/ACTION_1 events, mouth-slot handling and state branches are tied to
P1 motion progress. Replacing the visual frame mapping alone would not implement
source timing. This increment retains the P1 action events and documents the
remaining state-machine work explicitly.

Source references are under native/pikmin2-research:

- include/Game/EnemyParmsBase.h
- include/Game/EnemyBase.h and include/Game/Creature.h
- include/trig.h
- src/plugProjectYamashitaU/kochappyState.cpp

Native receiver references:

- src/plugPikiNakata/tekibteki.cpp: attackableCreature/contactCreature
- src/plugPikiNakata/taiattackactions.cpp: attack selection and swallowing
- src/plugPikiNakata/taichappy.cpp: shared native action graph

## Validation

Sixteen focused tests cover retail profile validation, strict distance boundary,
vertical separation, inclusive signed half-angle, wraparound, NaN/infinity,
unrecognized targets, absent policy, ordinary actors, reset/reload/reused address,
installer prerequisites, and source receiver ordering. The native policy probe
is compiled and executed. Both modified production .cpp files compile isolated
with current production flags. Real local retail extraction confirmed parameters
and capture/swallow event frames; the report includes source hashes.

A full integrated native build and actual attack-entry fixture remain pending.
These tests prove geometry and receiver wiring, not that a bite hits at 30 units
or that source P2 combat behavior is complete. The prior health/corpse runtime
runs do not validate this new attack-entry policy.
