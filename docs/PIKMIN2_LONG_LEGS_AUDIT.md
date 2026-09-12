# Beady Long Legs, Man-at-Legs and Raging Long Legs source audit (#173)

Source behavior audit for enemy IDs 56 `Damagumo`, 66 `Houdai` and 69 `BigFoot`.
Paths are relative to `native/pikmin2-research` unless they name a disc file.
Numbers marked *disc* come from `enemy/parm/enemyParms.szs` on the US GPVE01
revision 0 disc and override the header defaults quoted next to them. This is an
audit, not an implementation: no actor, save or animation interface changes.

## Identity and placement

| ID | Internal | Piklopedia | Drop table | Registry (`src/plugProjectYamashitaU/enemyInfo.cpp`) |
|---:|---|---:|---|---|
| 56 | `Damagumo` | 72 | `BDT_Boss` | line 92 (retail, `BUGFIX` off): no child; line 90 (`BUGFIX`): `ShijimiChou` × 25 |
| 66 | `Houdai` | 74 | `BDT_Boss` | line 95: no child |
| 69 | `BigFoot` | 73 | `BDT_Boss` | line 94: child `TamagoMushi` × 30 |

All three are in `IS_ENEMY_BOSS` (`include/Game/enemyInfo.h:214`) and share the
"long legs" attack rule: attacking Pikmin aim at the nearest collision part instead of
the body centre (`src/plugProjectKandoU/aiAttack.cpp:158-180`). None leaves a carcass
(`EB_LeaveCarcass` disabled at init) and none has a `carcass_config.txt` entry.

Retail rosters (caveinfo; type 8 means the special-enemy slot):

| Cave | Floor | Entry | Held treasure |
|---|---:|---|---|
| `tutorial_2` (Subterranean Complex) | 9 | `Houdai_light_a` | Stellar Orb |
| `yakushima_1` (Citadel of Spiders) | 5 | `Damagumo_key` | The Key |
| `last_2` (Hole of Heroes) | 13 | `Houdai_j_block_yellow` | yellow block |
| `last_2` (Hole of Heroes) | 14 | `Damagumo_j_block_red` | red block |
| `last_2` (Hole of Heroes) | 15 | `BigFoot_robot_head` (type 8) | robot head |
| `ch_MUKI_damagumo` | 1 | `Damagumo_key` (type 0) | The Key |
| `ch_MUKI_bigfoot` | 1 | `BigFoot_key` (type 8) | The Key |
| `ch_MUKI_houdai` | 2 | `Houdai_key` | The Key |
| `vs_8_kakukaku` (Battle) | 1 | `BigFoot` (type 8) | none |

Surface: `Damagumo` appears in the Perplexing Pool `loop/30-39`, `40-49` and
`50-59` day-window generators (days 30 onward). No other surface placements.
Assets: `enemy/data/{Damagumo,Houdai,BigFoot}` model and animation archives;
`Damagumo` also has `damagumo.btk`, `damagumo_model.btk` and `damagumo_model.brk`,
`BigFoot` has `ooashi_model.brk`.

## Shared skeleton: IK legs, foot crush, joint shadows

All three are driven by `IKSystemMgr` (`src/plugProjectNishimuraU/IKSystemMgr.cpp`)
with four legs of three joints (`rhand`, `lhand`, `rfoot`, `lfoot` 1 to 3). There is
**no walk animation**: the Walk state runs the IK motion and the body position and
facing are copied from the IK centre each frame. The animation set is only
`dead`, `landing`, `wait`, `flick` (plus `attack` for Man-at-Legs).

- **Foot crush.** Beady and Raging Long Legs press any captain or Pikmin touched by a
  foot sphere `lfsp`/`lhsp`/`rfsp`/`rhsp` with `InteractPress(mAttackDamage)` and hit
  other enemies for 500, but only while that leg is descending or planting with a
  move ratio above 1 (`IKSystemMgr::isCollisionCheck`, `:263-280`). A resting foot is
  harmless. Man-at-Legs has no press code at all; its legs never damage.
- **Leg tubes** `lft1`/`lht1`/`rft1`/`rht1` are built with `makeTubeTree` and only
  push creatures aside. The disc collision files mark `tama` as the stickable body
  sphere (radius 32.5 Beady, 70 Raging, 30 Man-at-Legs); Raging Long Legs also marks
  `lht1` stickable.
- **Damage** (`Damagumo.cpp:206`, `BigFoot.cpp:202`, `Houdai.cpp:223`): only a Pikmin
  that is stuck to a collision part damages them in the US build (the JP build drops
  the stuck requirement). Captains and bombs do nothing. Petrified damage coefficient
  is 0.25 for all three; leaving stone shakes every Pikmin off with no damage.
  They are bitter-immune while dormant and while landing (until the landing key 2).
- **Shadows** are joint-shadow trees (`*Shadow.cpp`) that also write the leg joint
  world positions used by every foot effect.
- **Start.** All three sit in Stay, model hidden, until a captain or Pikmin enters
  `mPrivateRadius` (75 *disc* for all three), then Land plays `landing` and the boss
  music starts when the landing ends.

## Beady Long Legs (`Damagumo`)

Files: `include/Game/Entities/Damagumo.h`, `src/plugProjectNishimuraU/Damagumo.cpp`,
`DamagumoState.cpp`, `DamagumoShadow.cpp`, `DamagumoMgr.cpp`.

**States** (`Damagumo.h:31`): Dead 0, Stay 1, Land 2, Wait 3, Flick 4, Walk 5.
Wait lasts 1.75 to 3.5 s, Walk 3.25 to 6.5 s (`DamagumoState.cpp:214`, `:312`);
Pikmin accumulating on it (`isStartFlick`) interrupts either with Flick, whose key 2
shakes with `mShakeChance`/`mShakeKnockback`/`mShakeDamage` in all directions. Walk
targets the nearest non-stuck Pikmin inside `mTerritoryRadius` (400 *disc*), else a
random point between `mHomeRadius` (75 *disc*) and the territory, else home
(`Damagumo.cpp:310-337`). Health 1300 *disc*, speed 100 *disc*, press damage 10.

**IK parameters** (`Damagumo.h:176`, header = *disc*): base factor fp01 3.0, raise
decel fp02 −0.2, downward accel fp03 0.5, min/max decel fp04 −2.0 / fp05 10, leg
swing fp06 120; bend factor 0.67 hardcoded.

**Pinch and death.** Below 35 percent health three random leg joints smoke
(`PSSE_EN_DAMAGUMO_SMOKE`); leg-raise sounds tier at 35 and 17.5 percent. The Dead
state's key 2 throws the held treasure straight down from the `kosi` joint and,
**only when it holds no treasure**, births 25 Shijimi butterflies
(`createItemAndEnemy`, `Damagumo.cpp:616-627`). Key 3 starts the dissolve material
animation and shadow fade; end kills. Retail registry does not declare the butterfly
child, which is what the `BUGFIX` row corrects.

**Animation keys** (`damagumo/enemyanimmgr.txt`): `landing` 18:2 54:3 56:4 60:5
64:6 (key 2 removes bitter immunity and fires all four feet); `wait` 0:0 75:1;
`flick` 35:2; `dead` 95:2 150:3.

## Man-at-Legs (`Houdai`)

Files: `include/Game/Entities/Houdai.h`, `src/plugProjectNishimuraU/Houdai.cpp`,
`HoudaiState.cpp`, `HoudaiShotGun.cpp`, `HoudaiShadow.cpp`, `HoudaiMgr.cpp`.
It shares no code with the Groinks (`MiniHoudai`).

**States** (`Houdai.h:28`): Dead 0, Stay 1, Land 2, Wait 3, Flick 4, Walk 5,
Shot 6. Stay also wakes when damaged. Land pauses its animation until something is
within `mPrivateRadius`. Wait lasts 1.5 to 3 s, Walk 3.5 to 7 s. Shot is entered
from Wait when the burst cooldown `mShotGunBurstTimer` exceeds `mSearchHeight`
(50 *disc*, a general parameter reused as seconds) and **always** after a Flick
(`HoudaiState.cpp:315-321`). Taking damage resets the cooldown
(`Houdai.cpp:612-619`), so sustained attacks postpone the gun. Health 2800 *disc*.

**Gun** (`HoudaiShotGun.cpp`). Target: nearest non-stuck Pikmin or captain within
`mSearchDistance` (500 *disc*) over a full circle, no line-of-sight test; in Hole of
Heroes a 50 percent roll switches to targeting the captain's party instead
(`Houdai.cpp:313-327`). With no target after 1 s it fires at a random point. Head
joint `tamajnt` yaws and `gun` pitches at up to 0.05 rad per frame. The Attack
animation's key 2 stops the motion for aiming; key 3 emits one shell per loop from
45 units ahead of the muzzle at speed 600, direction jittered by `mAttackHitAngle`
(0.004 *disc*); key 4 pauses the burst, key 5 ends rotation. Bursts last about
`mMaxShootingOn` (2.0 header, 2.5 *disc*) and pause about `mMaxShootingOff` (1.0
*disc*); only the difference to the `Min` parameters is used. Aiming and firing run
for at most `mSearchAngle` seconds (120 *disc*, another reused parameter). Shells: a
pool of 10, radius 10, no gravity, swept-capsule hit test with `mAttackRadius`
(10 *disc*), `InteractBomb(mAttackDamage)` (10 *disc*) on Pikmin and captains and
500 on other enemies, laser sight and `PSSE_EN_HOUDAI_BEAM` while locked.

**Legs.** Only `rht1` gets a tube tree (`Houdai.cpp:761`); no press damage. IK
parameters (`Houdai.h:200`, header / *disc*): fp01 5.0 / 9.0, fp02 −0.4 / −0.1,
fp03 0.5, fp04 −3.0 / −2.0, fp05 10, fp06 90 / 40. `mLastToTerritory` fp20 (380
header, 130 *disc*) replaces the territory radius in Hole of Heroes. Speed 250
*disc*, territory 800, home 75, sight 600.

**Death.** Steam and chimney effects run while awake; the dead animation's end
throws the held treasure straight down from `kosi`, explodes and kills. In-flight
shells are faded on kill.

**Animation keys** (`houdai/enemyanimmgr.txt`): `landing` 54:2 84:3 100:4 130:5
150:6; `wait` 0:0 39:1; `flick` 40:2 45:3 68:4; `attack` 33:2 34:0 35:3 37:4 38:1
39:5 (the 34:0 / 38:1 pair loops the firing frames); `dead` has no keys.

## Raging Long Legs (`BigFoot`)

Files: `include/Game/Entities/BigFoot.h`, `src/plugProjectNishimuraU/BigFoot.cpp`,
`BigFootState.cpp`, `BigFootShadow.cpp`, `BigFootMgr.cpp`.

**States** (`BigFoot.h:29`): Dead 0, Stay 1, Land 2, Wait 3, Flick 4, Walk 5.
Wait is a fixed 5 s; Walk lasts `mNormalTravelTime` (fp20, 10 s) or, in the walk
cycle right after a Flick, `mPostShakeTravelTime` (fp21, 3 header, 5 *disc*).

**Rage is a one-cycle flag.** `mIsEnraged` is set when Flick ends and cleared when
the next Walk ends (`BigFootState.cpp:294`, `:350`). That one cycle uses the second
IK set (fp11 to fp17), the fast raise sound and the attack-loop music, and ignores
Pikmin: it stomps at a point `mMovementOffset` (fp17, 50) ahead at ±30° instead of
chasing (`BigFoot.cpp:336-372`). It is not health based.

**IK parameters** (`BigFoot.h:187`, header / *disc*): normal fp01 3.0 / 1.4, fp02
−0.2 / −0.1, fp03 0.5 / 2.0, fp04 −2.5 / −0.7, fp05 10, fp06 120 / 80; enraged fp11
3.0 / 4.0, fp12 −0.2 / −0.3, fp13 0.5 / 2.0, fp14 −2.0 / −1.7, fp15 10, fp16
120 / 110, fp17 50. Foot sample radius 40, bend factor 0.5. Health 10000 *disc*,
speed 70, territory 310, home 75, press damage 10.

**Shake-off thresholds** *disc* are 70/80/90/100 blows at under 50/60/70/more stuck
Pikmin, versus 30/35/45/50 for the Empress, which is why it tolerates so many
attackers. Below 35 percent health three legs smoke.

**Death.** Key 2 throws the held treasure straight down from `kosi` and, only when it
holds nothing, births 30 Mitites in ball form with fall speeds spread by ±100
(`BigFoot.cpp:662-675`); the registry declares that child so slots are reserved.
Key 3 starts the dissolve; end kills. There is no Versus-specific code: in
`vs_8_kakukaku` it behaves as in story, and having no held treasure it bursts into
Mitites on death.

**Animation keys** (`bigfoot/enemyanimmgr.txt`): `landing` 18:2; `wait` 0:0 75:1;
`flick` 35:2; `dead` 85:2 150:3.

## Dependencies a reimplementation must provide

- `IKSystemMgr`/`IKSystemBase` with leg states, move ratio and ground callbacks;
  joint-shadow trees that publish joint positions; tube collision trees.
- `ShijimiChou::Mgr::createGroupByBigFoot` and `TamagoMushi::Mgr::createGroupByBigFoot`
  for the no-treasure death bursts; cave ID checks for Hole of Heroes.
- For Man-at-Legs: joint rotation callbacks on `tamajnt` and `gun`, `traceMove`
  shells, map attribute lookup for impact effects, laser sight ground march.
- `PSM::EnemyBoss` music requests, camera vibration and rumble tables, BTK/BRK
  material animations for the damage colour and dissolve.

## Unknowns and decomp caveats

- `HoudaiShotGunNode::update`, `emitShotGun` and `returnShotGunRotation` keep
  retained assembly; the Damagumo and BigFoot units are fully matching.
- Raging Long Legs' random wander uses `sin` for both axes (`BigFoot.cpp:361-364`),
  and `Houdai::onInit` is marked unfinished in the decomp.
- Man-at-Legs' `Min` shooting parameters only widen the random range; they are never
  added as offsets.
- Natural runtime evidence, IK stability on generated floors and the Battle
  placement of Raging Long Legs remain runtime work for the enemy and mode lanes.
