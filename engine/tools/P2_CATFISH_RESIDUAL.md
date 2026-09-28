# Catfish (Water Dumple, EnemyID 26) residual fidelity: two-slot mouth, attackNavi, fp02 poison, banked flick

Issue #407 / #167. Source: `Catfish.cpp`, `KochappyBase.cpp`,
`kochappyState.cpp` and `enemyAction.cpp` at research revision
`632af93787b9c95b63f0c13be32b161375ce3a96` (`native/pikmin2-research`).

## Source rule (retail)

`Catfish::Obj::initMouthSlots` (`Catfish.cpp:83-92`) allocates **two** mouth
slots, `kamu1` and `kamu2`, each radius 20. The shared `KochappyBase` FSM drives
them (`kochappyState.cpp:1398-1415`):

```
StateAttack KEYEVENT_2 (attack frame 17):
    EnemyFunc::attackNavi(enemy, mAttackRadius(), mAttackHitAngle(), mAttackDamage(), ...)
    if (!EnemyFunc::eatPikmin(enemy, nullptr)) startMotion(Eat)
    EnemyFunc::flickStickPikmin(enemy, mShakeChance, mShakeKnockback, mShakeDamage, faceDir)
StateAttack KEYEVENT_3 (attack frame 75):
    EnemyFunc::swallowPikmin(enemy, CG_PROPERPARMS(enemy).mPoisonDamage(), ...)
```

`EnemyFunc::eatPikmin` (`enemyAction.cpp:1107-1140`) fills each free mouth slot
with the nearest Pikmin inside its radius (`InteractSwallow`); a Pikmin is taken
by at most one slot. `EnemyFunc::swallowPikmin` (`enemyAction.cpp:1148-1175`)
kills every sticker with `isStickToMouth()` and, only when the Pikmin is
`White`, runs `eatWhitePikminCallBack(piki, poisonDamage)`, which calls
`addDamage(poisonDamage)` on the eater (`enemyBase.cpp:3293`).

`StateFlick::exec` (`kochappyState.cpp:1764-1795`) uses the banked events:
`KEYEVENT_2` (flick frame 25) runs `flickStickPikmin` + `flickNearbyPikmin` +
`flickNearbyNavi`; `KEYEVENT_3` (frame 47) runs `resetEnemyNonStone`.

Catfish parms (`experimental/pikmin2_aquatic_assets.py`, GPVE01 rev 0): general
`fp22=50` attack hit radius, `fp24=10` attack damage; `fp17/fp18/fp19` fall back
to the header defaults 300/0/120; proper `fp02=300` poison
(`KochappyBase.h:106`). `fp23` (hit angle) falls back to the 15 deg default.

## P1 host facts

* `TEKI_Namazu` (the P1 Water Dumple ancestor) has no source mouth geometry and
  the Catfish rides a visual-only pose bank (`pc_p2_batch3.cpp`).
* `InteractSwallow` with a null mouth part kills immediately
  (`interactBattle.cpp:419-433`), so the port cannot hold a Pikmin in a real
  slot; the captured pointer is the stand-in.
* `Piki` has no `getKind()==White`; the port uses
  `pc_p2_is_white()` (`pc_p2_white.cpp`).
* `BTeki` has no `addDamage`; the poison is applied directly to `mHealth` so the
  normal health/death path is preserved.

## Port implementation

`pc_port/pc_p2_catfish_residual_policy.h` (pure, engine-free) encodes:

```
kMouthSlots = 2                 // Catfish.cpp:85
kAttackHitRadius = 50, kAttackHitAngle = 15 deg, kAttackDamage = 10
kPoisonDamage = 300             // proper fp02
kFlickRange = 120, kFlickKnockback = 300, kFlickDamage = 0

attackEvent(code):  2 -> Bite, 3 -> Swallow
flickEvent(code):   2 -> Knockback, 3 -> RestoreNonStone
attackNaviHits(distance, absAngle) == distance < 50 && absAngle < 15 deg
inFlickRange(distance)             == distance < 120
selectMouthCaptures(candidates)    // nearest-first, at most 2, never twice
swallowResult(isWhite, consumed)   // kill; White -> +300 poison; consumed -> no-op
```

`pc_port/pc_p2_catfish.cpp` wires it:

* At the banked attack bite event (frame 17) `biteEvent` runs `attackNavi`
  against the active Navi (fp22/fp23/fp24) and captures up to two eligible
  Pikmin nearest-first (marked `held` if already in a slot, so never twice),
  logging `P2_CATFISH_BITE ... pikmin=1 slot=N` and
  `P2_CATFISH_ATTACK_NAVI ... damage=10.0`.
* At the banked swallow event (frame 75) `swallowEvent` kills each slot once
  logging `P2_CATFISH_EAT ... slot=N`; a consumed White also logs
  `P2_CATFISH_POISON ... damage=300.0 health=...` and subtracts fp02 from the
  Catfish, leaving the normal death/corpse untouched.
* `fireFlickEvents` maps the banked codes: frame 25 `flickEvent -> Knockback`
  runs `doFlick` (stick-to-mouth/captured Pikmin + nearby Pikmin + nearby Navi
  with fp17/fp18/fp19 defaults and `FLICK_BACKWARDS_ANGLE`); frame 47
  `flickEvent -> RestoreNonStone` logs `P2_CATFISH_FLICK ... event=restore`.
* Setup logs the wiring contract
  `P2_CATFISH_RESIDUAL generator=... slots=2 attack_damage=10.0 poison_damage=300.0 flick_events=25,47`.

## Tests

```
g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port \
    tools/p2_catfish_residual_policy_test.cpp -o ../p2_catfish_residual_policy_test.exe
../p2_catfish_residual_policy_test.exe   # p2_catfish_residual_policy_test PASS
```

The matrix covers both banked event dispatches, the `attackNavi` radius/angle
gate, the flick range, two-slot nearest-first selection (ineligible / held /
fewer-than-two / never-twice) and the swallow outcome (non-White kill, White
kill+300 poison, already-consumed no-op). The compiler used is
`C:/msys64/mingw64/bin/g++.exe`. The fixture validator and unit tests live in
`experimental/pikmin2_catfish_residual_behavior.py` and
`tests/test_pikmin2_catfish_residual_behavior.py`.

## Honest limits

* The two-slot mouth is an explicit nearest-first capture inside the source
  attack sweep; the P1 host has no `kamu1`/`kamu2` joints, so there is no mouth
  attachment visual.
* Runtime White Pikmin poison is not staged by the batch-3 aquatic arena (it
  spawns the 20-red starting squad); the fp02 policy is covered by the
  standalone test. A run with no swallowed White never emits
  `P2_CATFISH_POISON`.
* `attackNavi` only fires when the active Navi is inside the fp22=50 / fp23=15
  deg sweep at the bite frame.
* Live fixture execution is owned by the runtime slot and is not run here.
