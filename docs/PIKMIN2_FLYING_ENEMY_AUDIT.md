# Flying enemies, captors and ambient fliers source audit (#166)

Source behavior audit for enemy IDs 16 `Qurione`, 23 `Sarai`, 29 `Mar`, 32 `Demon`,
41 `Fuefuki`, 55 `Hanachirashi`, 57 `Kurage`, 58 `BombSarai`, 72 `OniKurage` and
77 `ShijimiChou`. Paths are relative to `native/pikmin2-research` unless they name
a disc file. Numbers marked *disc* come from `enemy/parm/enemyParms.szs` on the US
GPVE01 revision 0 disc and override the header defaults quoted next to them. This
is an audit, not an implementation: no actor, save or animation interface changes.

## Identity, placement and carcass

| ID | Internal | Piklopedia | Drop table | Health *disc* | Carcass | Story caves (floors) | Surface generators |
|---:|---|---:|---|---:|---|---|---|
| 16 | `Qurione` Honeywisp | 56 | `BDT_Empty` | 99999 | none | forest_2:3, forest_3:4, last_2:5 | Valley, Awakening Wood initgen; Perplexing Pool defaultgen |
| 23 | `Sarai` Swooping Snitchbug | 31 | `BDT_Strong` | 1500 | 4 pokos, 3 to 6 | forest_4:3, last_1:2, last_2:2, tutorial_2:2, tutorial_3:4, yakushima_1:3 | Wistful Wild, Perplexing Pool initgen |
| 29 | `Mar` Puffy Blowhog | 17 | `BDT_Strong` | 3000 | none | last_1:7, last_2:3, last_3:7, yakushima_2:3 | none |
| 32 | `Demon` Bumbling Snitchbug | 32 | `BDT_Strong` | 1500 | 4 pokos, 3 to 6 | last_1:9, last_2:2, last_3:7 and 11, tutorial_2:1, tutorial_3:4, yakushima_3:6 | none |
| 41 | `Fuefuki` Antenna Beetle | 34 | `BDT_Strong` | 700 | 5 pokos, 3 to 6 | forest_4:5 and 6, last_2:2, last_3:8 and 12 | none |
| 55 | `Hanachirashi` Withering Blowhog | 18 | `BDT_Strong` | 1800 | none | forest_3:3, last_1:7, last_2:3, last_3:5, yakushima_3:5, yakushima_4:3 | Valley, Perplexing Pool, Wistful Wild initgen |
| 57 | `Kurage` Lesser Spotted Jellyfloat | 45 | `BDT_Normal` | 2500 | none | last_2:15, last_3:1, 6 and 10, yakushima_3:2, 3 and 5 | none |
| 58 | `BombSarai` Careening Dirigibug | 33 | `BDT_Strong` | 1500 | 4 pokos, 3 to 6 | 11 floors across tutorial_2, yakushima_4, last_1 to last_3 | none |
| 72 | `OniKurage` Greater Spotted Jellyfloat | 44 | `BDT_Strong` | 4500 | none | last_2:15, last_3:6, yakushima_3:3 | none |
| 77 | `ShijimiChou` Unmarked Spectralids | 55 | `BDT_Empty` | 200 | 1 poko, 1 | last_2:5, tutorial_3:5, yakushima_3:4 (plus plant, Mamuta and Beady Long Legs births) | none |

Held treasures in story caves: the Antenna Beetle carries the Whistle in
`forest_4`, the Puffy Blowhog carries cookies and diamonds in `last_1` and
`last_3`, the Withering Blowhog a dairy lid in `yakushima_4`, the Jellyfloats a
diamond, compact and flask in `last_3` and `yakushima_3`. Battle mode injects four
Swooping Snitchbugs and four Withering Blowhogs into every random layout
(`baseGameSection.cpp:2266-2270`). Bitter kills roll one nectar at 90 percent
(`BDT_Normal`/`BDT_Strong`) yellow; `BDT_Empty` drops nothing. None of the ten is a
day-end spawner. Assets: `enemy/data/<Internal>/model.szs` and `anim.szs`; the two
Blowhogs also have BRK/BTK material animations (`fuusen_model`, `hanachirashi_model`).

## Shared flight idiom

Every flier uses `EB_Untargetable` as "is flying" (`EnemyBase.h:167`), which keeps
ground Pikmin from targeting the body; only thrown Pikmin connect. Height control
is a proportional spring toward `mapMgr->getMinY + flight height` with the rise
factor reduced as up to five Pikmin latch on. Fall-when-laden is polled, not
callback driven: a stuck Purple forces a fall at once, otherwise after a shake-off
timer or a minimum stuck count the enemy rolls between shaking (`Flick`) and
falling; grounded it struggles for a fixed time before taking off again. All ten
stub the water callbacks, so water boxes have no effect. Quakes skip flying
enemies (`enemyBase.cpp:2860`). There is no shared flying base class in source;
only the Bumbling Snitchbug inherits (from the Swooping Snitchbug).

## Snitchbugs (`Sarai`, `Demon`)

Files: `include/Game/Entities/{Sarai,Demon}.h`, `src/plugProjectNishimuraU/Sarai*.cpp`,
`Demon*.cpp`. States (`Sarai.h:164`): Dead, Fall, Damage, TakeOff, Flick, Wait,
Move, Attack, Fail, CatchFly, FallMeck. Two mouth slots on `rkamujnt`/`lkamujnt`
(radius 15). Flight height `mNormalFlightHeight` (100 header, 85 *disc*) drops to
`mGrabFlightHeight` (80 header, 70 *disc*) while carrying.

- **Swooping** targets grounded Pikmin inside `mTerritoryRadius` (300 *disc*),
  `mViewAngle` (90) and `mSightRadius` (200). The attack dives between frames 10
  and 30 at `mHuntDescentFactor`, grabs with `eatPikmin` from frame 16, then
  `CatchFly` carries at `mGrabMovementSpeed` (75 header, 70 *disc*) and `FallMeck`
  key 3 plants the captives (`InteractFallMeck`, `mFallMeckSpeed` 200, 330 *disc*).
  Captives are released with a zero-damage flick whenever it falls, is petrified or
  dies (`flickStickTarget`). Captives do not count toward the shake threshold.
- **Bumbling** overrides only target and catch: after a 3 s cooldown it grabs any
  captain (no grounded check) inside the same ranges with `InteractSarai`, up to
  two at once; the captain drops the squad, wiggles free after six inputs with a
  random roll (`naviState.cpp:3914-3960`), or is dropped by `FallMeck`.
- Fall chance lerps from `mPayoffProbability1` (0.1, 0.3 *disc*) to
  `mPayoffProbability5` (0.7, 0.8 *disc* Swooping, 0.85 Bumbling) over one to five
  stuck Pikmin; struggle `mStrugglingTime` (3.0, 4.0 *disc* Swooping, 1.5 Bumbling).
  Normal enemy-base damage; carcass `type5`; `BDT_Strong`.
- **Animation keys** (`sarai`/`demon`): `wait1` 10:0 49:1; `move1` 0:0 19:1;
  `attack1` 10:2 13:3 30:4; `waitact1` (fall meck) 8:2 19:3 25:4; `waitact2` 0:0
  39:1; `flick` 13:2; `type1` (fall) 11:0 12:1 13:2; `type2` 0:0 19:1; `type3` 7:0
  29:1; `type5` 10:0 29:1.

## Careening Dirigibug (`BombSarai`)

Files: `include/Game/Entities/BombSarai.h`, `src/plugProjectNishimuraU/BombSarai*.cpp`.
States (`BombSarai.h:24`): Dead, Damage, Wait, BombWait, Move, BombMove, Supply,
Release, Fall, TakeOff1, TakeOff2, Flick, BombFlick.

- **Bombs.** Seeing a Pikmin sends it to Supply, which births a `Bomb` enemy (ID 36)
  from the general manager and captures it on `kamu_jnt1` (`BombSarai.cpp:263-279`;
  the registry reserves two per Dirigibug). It carries for at most 15 s
  (`mBombCarryTimer`), releasing when a target is inside `mMaxAttackRange`
  (100 *disc*) or `mAttackRadius` (50): Release key 2 lobs it forward at velocity
  (50, 100, 50); a fall throws it harder (100, 300, 100); death drops it in place.
  A queued bitter spray while armed forces a fall. Fuse and explosion belong to the
  `Bomb` object (its source file is absent from the decomp). Blasts only hurt it
  while it has a floor triangle, so it is immune to explosions in the air.
- **Flight** at `mFlightHeight` (90, 70 *disc*) with a bob of `mPitchAmp` (20)
  at `mPitchRate` (2.5); rise factors 1.5 to 1.0, or 6.0 for the fast
  `TakeOff2` used below half health. Fall chance `mFreeFlickChance`/`mLadenFlickChance`
  (0.1 / 0.7, 0.2 / 0.8 *disc*), struggle 3 s (1.5 *disc*). Normal damage; carcass
  `type5`; `BDT_Strong`; five balloons pop on death.
- **Animation keys**: `run1` 10:0 49:1; `run2` 5:0 44:1; `wait1` 10:0 49:1; `wait2`
  5:0 44:1; `release1` 21:2; `fall1` 2:2 3:3 4:4 5:5 6:6 7:7 9:0 10:1 11:8;
  `dead1` 10:2 17:6 24:4 30:3 36:5 65:2 66:3 67:4 68:5 69:6 83:7; `flick1`/`bflick1`
  15:2; `mogaki1` 0:0 1:2 13:3 17:2 22:3 24:1 26:2 39:3; `takeoff1` 65:0 104:1;
  `takeoff2` 32:0 34:1; `type5` 10:0 29:1.

## Honeywisp (`Qurione`)

Files: `include/Game/Entities/Qurione.h`, `src/plugProjectNishimuraU/Qurione*.cpp`.
States (`Qurione.h:201`): Stay, Appear, Disappear, Move, Drop, Dead.

- It shuttles between two waypoints `mFlyDist` (200) apart at `mFlightHeight`
  (60, 90 *disc*) with a bob, appearing when a Pikmin or captain is within
  `mSightRadius` (100 *disc*) and fading out at each end. It is invulnerable,
  bitter-immune and untargetable; the only reaction is a thrown Pikmin colliding
  in flight (`flyCollisionCallBack`, `Qurione.cpp:136`), which enters Drop: key 2 of
  `damage` releases the `Egg` it carries on joint `water` (`attachItem`), and the
  Egg's own drop table yields the nectar. Dead floats up at `mDeathRate` (100,
  400 *disc*) and kills after `mDeathTime` (1.0, 0.5 *disc*) or once off screen.
- No carcass (`EB_LeaveCarcass` cleared), `BDT_Empty`, custom generator with fly
  and slide distances (`QurioneMgr.cpp:45-62`).
- **Animation keys**: `waitl` 0:0 99:1; `damage` 5:2; `run` 0:0 9:1; `appear1`,
  `hide1` end only.

## Blowhogs (`Mar`, `Hanachirashi`)

Files: `include/Game/Entities/{Mar,Hanachirashi}.h`, `src/plugProjectNishimuraU/Mar*.cpp`,
`Hanachirashi*.cpp`. States (`Mar.h:20`): Dead, Wait, Move, Chase, ChaseInside,
Attack, Fall, Land, Ground, TakeOff, FlyFlick, GroundFlick; the Withering Blowhog
adds Laugh. Structurally clones; the Withering one is smaller.

- **Flight** at `mStandardFlightHeight` (90, 80 / 70 *disc*) with a bob; Wait
  holds `mAirWaitTime` (3 s) then wanders; Chase keeps a standoff ring of
  `mMaxAttackRange` (200 *disc*) and retreats toward home when outside
  `mTerritoryRadius` (400 / 250 *disc*).
- **Blast.** Attack key 2 starts a downward-forward cone from the nose joint that
  grows to `mAttackRadius` (300 *disc*) within `mAttackHitAngle` (20 *disc*)
  (`Mar.cpp:1006-1085`). The Puffy Blowhog applies `InteractWind` with strong
  horizontal and upward force on Pikmin and a weaker push on captains; wind is
  ignored by Purples and by a captain wearing the Repugnant Appendage. The
  Withering Blowhog applies `InteractHanaChirashi`, a weaker wind whose blow state
  wilts flowers and buds to leaves; Purples are not blown but still lose their
  flower, and a successful wilt makes it Laugh. Attack damage is 0 *disc*.
- **Fall.** Stuck Purple, `mShakeOffTime` (3 s) of any attachment, or
  `mFallingMinPikiNumber` (10 header, 6 / 4 *disc*) Pikmin drop it; Ground lasts
  `mGroundWaitTime` (3 s) then it shakes and takes off. Normal damage; no carcass
  (`EB_LeaveCarcass` disabled); the held treasure is spawned 500 units up with zero
  velocity at the end of the death animation (`Mar.cpp:233-255`). `BDT_Strong`.
- **Animation keys** (`mar`/`hanachirashi`): `move1` (fly wait) 0:0 39:1;
  `wait2` (ground) 0:0 39:1; `attack` 50:2; `damage` (fly flick) 15:2; `flick`
  30:2 / 25:2; `type1` (takeoff) 30:2; `type2` (fall) 5:0 19:1; `dead`, `dead2`,
  `move2`, `laugh` end only.

## Antenna Beetle (`Fuefuki`)

Files: `include/Game/Entities/Fuefuki.h`, `src/plugProjectNishimuraU/Fuefuki*.cpp`.
States (`Fuefuki.h:20`): Dead, Stay (away), Land, Jump, Wait, Turn, Walk, Whisle,
Struggle.

- **Cycle.** It lands at a random spot (radius 50 to 75 in caves) with a
  `mNormalLandingChance` (0.5) of the clean landing, whistles almost immediately,
  then wanders. The whistle ring grows to `mAttackRadius` (130 *disc*) and lures
  every Pikmin of any colour not already its own with `InteractFueFuki`
  (`Fuefuki.cpp:362-390`); lured Pikmin follow its footprints (`aiTeki.cpp`) and
  cannot be whistled back until it leaves or dies, when they panic. Whistles repeat
  every `mMaxWhistleTimeNoSquad` (5 s, 3 *disc*) or `mMaxWhistleTimeWithSquad`
  (10 s) with the branch inverted against the field names.
- **Flee.** After `mMaxGroundTime` (30 s, 20 *disc*) or, without a squad, when a
  captain or foreign Pikmin enters `mPrivateRadius` (60 *disc*), Jump key 3 makes
  it untargetable and launches it at 1500 units per second; Stay lasts
  `mAirborneTime` (3 s) before the next landing. Speed 250 *disc*.
- **Damage.** Normal while landed; a press or purple pound knocks it into Struggle
  (`mStruggleTime` 3 s, 2.5 *disc*) instead of applying press damage. Carcass
  `carry`; `BDT_Strong`; the radar tracks live beetles. The held Whistle treasure
  is thrown by the enemy base.
- **Animation keys**: `landing` 21:2 45:3; `landfail` 21:2 60:3; `move` 4:0 14:1;
  `pivot` 4:0 13:1; `wait` 0:0 29:1; `whisle` 14:0 23:1; `struggle` 20:0 39:1;
  `jump` 3:0 8:1 13:2 15:3; `carry` 10:0 29:1; `dead` end only.

## Jellyfloats (`Kurage`, `OniKurage`)

Files: `include/Game/Entities/{Kurage,OniKurage}.h`, `src/plugProjectNishimuraU/Kurage*.cpp`,
`OniKurage*.cpp`. States (`Kurage.h:19`): Dead, Wait, Move, Chase, Attack, Fall,
Land, Ground, TakeOff, FlyFlick, GroundFlick; the Greater adds Drop.

- **Ingestion.** Targets below the body inside `mTerritoryRadius` (300 / 500
  *disc*) and `mSightRadius`; the Lesser only takes Pikmin, the Greater also
  captains. Attack sucks for `mSuckTime` (5 s, 2 *disc*) with per-frame chance
  `mSuckChance` (0.025, 0.1 *disc*) per Pikmin inside `mAttackRadius` (40 / 60
  *disc*) up to `mMaxSuckPiki` (10 header; 10 / 20 *disc*). Swallowed Pikmin climb
  into the stomach and die after `mKurageKillTime` (16 s, `PikiParms`); the timer
  pauses while it is petrified or at zero health, and they are released alive if
  it dies first (`pikiState.cpp:2091-2226`). The Greater holds up to two captains
  on joint `Proom` via `InteractSarai`; captains wiggle free as with the
  Snitchbug and are vomited out, or expelled with a bomb interaction on a ground
  flick.
- **Fall.** Stuck Purple, `mShakeTime` (3 s, 1 *disc* Lesser / 5 Greater) or
  `mMinFallPiki` (10, 6 *disc*) drop it; Ground lasts `mGroundTime` (3 s, 0.5
  *disc*). Damage counts only with a collision part. Stickable `bod1`/`bod2`, the
  `suck` part is the intake. No carcass, no death effect; the death animation's
  key 2 releases stuck Pikmin, key 3 bursts. `BDT_Normal` / `BDT_Strong`.
- **Animation keys** (both): `wait` 0:0 34:1; `move1` 0:0 59:1; `attack` 37:2 60:0
  67:1; `flick1` 16:2; `flick2` 20:2 30:3; `type1` 32:2; `type2` 0:0 19:1; `dead1`,
  `dead2` 33:2 93:3; `move2` end only.

## Unmarked Spectralids (`ShijimiChou`)

Files: `include/Game/Entities/ShijimiChou.h`, `src/plugProjectMorimuraU/shijimiChou*.cpp`.

- **Groups.** Every group has an invisible, intangible leader (no collision,
  bitter-immune outside the Piklopedia) with `mGroupCount` followers on a ring;
  followers inherit the spawn source. Sources: generator birth (25 per parms), a
  plant touched for the first time (5, all yellow), a Mamuta at birth (5, resting
  on it), Beady Long Legs with no treasure (25) and Piklopedia Bulborbs with many
  kills. Manager limit 10 above ground and 25 in caves. Colours roll
  `mRedSpawnChance` / `mPurpleSpawnChance` (0.1 each); the leader is always red or
  purple and never drops.
- **Flight.** Followers wait until a Pikmin is within 150 units, then fly for
  `mMaxFlyTime` (300 ticks, 250 *disc*; 100 for plant groups; 60 for enemy
  groups) around home at `mFlightHeight` (100, 70 *disc*) with a bob, then Leave
  behind the active captain and despawn once far from home; the leader self-kills
  when the group is down to one.
- **Kill and drop.** All damage callbacks return false; a Pikmin sticking to one
  is the only kill, spiralling it down (`shijimiChou.cpp:275-310`). On death it
  re-enables its 1 poko carcass and drops by `genItem`: yellow gives nectar, red a
  spicy spray drop once the first spicy spray exists, purple a bitter spray drop
  once the first bitter spray exists (`:507-537`). A bittered Spectralid near the
  ground drops and dies. Its death effect is keyed to the Female Sheargrub ID, a
  known source bug.
- **Animation keys**: `move` 0:0 7:1; `carry` 10:0 29:1; `dead` end only.

## Dependencies a reimplementation must provide

- `Bomb`, `Egg` and `ItemHoney` births with capture matrices; `InteractSarai`,
  `InteractFallMeck`, `InteractSuikomi_Test`, `InteractWind`,
  `InteractHanaChirashi`, `InteractFueFuki` and the captain `NSID_Sarai` and
  `NSID_FallMeck` states; Pikmin blow, panic, fall-meck and suikomi states with
  the digestion timer.
- Mouth slots, stickers, footprint trails and the teki follow action; plant and
  Mamuta spawn hooks and the Spectralid cluster sound; radar counters for the
  Antenna Beetle.
- BRK/BTK material animation for the Blowhogs; shadows scaled by flight height.

## Unknowns and decomp caveats

- The Blowhog wind, target-loss and chase functions, and six Spectralid flight
  functions keep retained assembly; the Snitchbug, Dirigibug, Honeywisp,
  Jellyfloat and Antenna Beetle units are fully matching.
- The `Bomb` implementation file is absent from the decomp, so the fuse length and
  explosion are not cited here.
- Source oddities: the Antenna Beetle whistle branch inversion, squad memory
  decremented per frame, `catchTarget` without a return value, the Spectralid
  death effect ID and `sin` used for both goal axes.
- Natural runtime evidence, Battle-mode injections and captain capture flows stay
  with the enemy, captain and mode lanes.
