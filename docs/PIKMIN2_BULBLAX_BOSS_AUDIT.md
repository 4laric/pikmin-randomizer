# Empress Bulblax, Bulborb Larva and Emperor Bulblax source audit (#172)

Source behavior audit for enemy IDs 30 `Queen`, 31 `Baby` and 53 `KingChappy`.
Paths are relative to `native/pikmin2-research` unless they name a disc file.
Numbers marked *disc* come from `enemy/parm/enemyParms.szs` on the US GPVE01
revision 0 disc and override the header defaults quoted next to them. This is an
audit, not an implementation: no actor, save or animation interface changes.

## Identity and placement

| ID | Internal | Piklopedia | Drop table | Registry (`src/plugProjectYamashitaU/enemyInfo.cpp`) |
|---:|---|---:|---|---|
| 30 | `Queen` | 71 | `BDT_Boss` | line 56: spawnable, own ID, child `EnemyID_Baby` × 50 |
| 31 | `Baby` | 9 | `BDT_Weak` | line 57: spawnable, own ID, no child, not a day-end spawn |
| 53 | `KingChappy` | 70 | `BDT_Boss` | line 87: spawnable, own ID |

`Queen` and `KingChappy` are in `IS_ENEMY_BOSS` (`include/Game/enemyInfo.h:214`),
which gives them `PSM::EnemyMidBoss` music, squad-adjusted treasure weight when
they throw up their held treasure on a cave's last floor in story mode
(`enemyBase.cpp:2605`), and 5 nectar rolls at 85 percent yellow when killed while
petrified (`enemyBase.cpp:1346`). `Baby` gets 1 roll at 99 percent.
Registering a `Queen` also reserves 10 `Rock` objects (`generalEnemyMgr.cpp:851`).

Retail rosters that list them (caveinfo, story unless prefixed):

| Cave | Floor | Entry | Held treasure |
|---|---:|---|---|
| `tutorial_3` (Subterranean Complex) | 8 | `Queen_dashboots`, `Baby` × 2 rows (weight 9, type 0) | Repugnant Appendage |
| `forest_1` (Hole of Beasts) | 5 | `Queen_radar_a` | Prototype Detector |
| `forest_3` (Bulblax Kingdom) | 7 | `KingChappy_suit_fire` | Forged Courage |
| `last_1` (Cavern of Chaos) | 4 | `KingChappy_g_futa_koiwai`, `KingChappy` | dairy lid |
| `last_2` (Hole of Heroes) | 10 | `KingChappy_j_block_white`, `KingChappy` | white block |
| `last_2` (Hole of Heroes) | 11 | `Queen_j_block_blue` | blue block |
| `ch_MUKI_king` (Challenge) | 4 | `Queen_key` (type 8) | The Key |
| `ch_MUKI_king` (Challenge) | 5 | `KingChappy_key`, `_gold_medal`, `_silver_medal` | |

No surface generator and no Battle definition spawns any of the three. Assets:
`enemy/data/{Queen,Baby,KingChappy}/model.szs` (`enemy.bmd`) and `anim.szs`;
the Empress also has `queenchappy_model.btk` (texture animation, `QueenMgr.cpp:12`).
Carcasses: `Queen` and `KingChappy` are 15 pokos, carry 20 to 30
(`carcass_config.txt`); `Baby` has no carcass entry and leaves no corpse.

## Empress Bulblax (`Queen`)

Files: `include/Game/Entities/Queen.h`, `src/plugProjectNishimuraU/Queen.cpp`,
`QueenState.cpp`, `QueenShadow.cpp`, `QueenMgr.cpp`.

**States** (`Queen.h:26`, FSM `QueenState.cpp:14`): Dead 0, Sleep 1, Wait 2,
Damage 3, Flick 4, Rolling 5, Born 6. Every state except Rolling turns the hard
constraint on; Rolling is the only mobile state. Transitions are deferred into
`mNextState` and taken on `KEYEVENT_END`. Entry state is Wait when larvae are
allowed, otherwise Sleep (`Queen.cpp:62`).

- Sleep: ends the motion when health is gone, the hit counter rose or a larva is
  due; then Dead, Flick (`EnemyFunc::isStartFlick`), Damage (Pikmin stuck) or Wait
  (`QueenState.cpp:89-103`). Key 2 wakes the sleep flower effect and sets the
  mid-boss appear music.
- Wait: Sleep after 30 s idle with no larva due, Damage on hit-counter rise,
  Born when a larva is due, Flick, Dead, evaluated in that order with later checks
  overriding (`QueenState.cpp:153-173`).
- Damage: Born, Wait when nothing is stuck, Flick, Dead (`:219-237`).
- Flick: key 2 flicks stuck Pikmin (`flickPikmin(faceDir)`), end goes to Dead or
  Rolling with the side chosen by `isRollingAttackLeft` (`:281-293`).
- Rolling: rolls sideways along ±90° of the facing direction, bounded by
  `mTerritoryRadius`; each frame presses everything in reach and flicks stuck
  Pikmin; camera shake `VIBTYPE_MidFastShort`. Key 2 near the territory edge
  (`dot > territory - 50`) ends the pass with a crash (`PSSE_EN_QUEEN_CRUSH`,
  `RUMBLETYPE_Fixed15`) and queues another Rolling pass; otherwise once
  `mWaitTimer > mRollingTime` and she is near home the pass ends in Wait
  (`:409-433`). The next pass is "left" when the current animation is
  `rolling_r`, so direction alternates (`:441-447`).
- Born: key 2 spawns one larva and the birth effect; end goes to Wait or Dead.
- Dead: key 2 rumble; end releases joint shadows and calls `kill`.

**Attacks and collision.** `rollingAttack` (`Queen.cpp:287`) presses every alive
creature within a 250 unit cell sphere whose height difference is under 50 and
that lies inside `mAttackRadius` (150 *disc*) and `mAttackHitAngle` (25 *disc*)
using `InteractPress(mAttackDamage)` (10 *disc*). `flickPikmin` (`:324`) applies
`mShakeKnockback` (300) and `mShakeDamage` (1) to Pikmin stuck to `nose`, `head`,
`bod1` (and `bod5` with reversed angle); anything else is shaken off without
damage. While rolling and not petrified she ignores collision with captains and
enemies (`ignoreAtari`, `:247`). Collision tree (`queen/enemycoll.txt`): 275 unit
root, children `bod3` 90, `bod4` 85, `bod5` 75, `bod2` 80, `bod1` 60, `head` 25,
`nose` 10, all stickable (`st__`). Six joint shadows (`neck1`, `neck3`, `neck5`,
`head`, `body3`, `body4`) replace the normal shadow while alive
(`QueenShadow.cpp:64-192`).

**Larvae.** `updateCreateBaby` (`Queen.cpp:469`) counts alive larvae in the global
`Baby::Mgr` (a shared pool, not per Empress): at `mMaxBirths` (50) the room flag
clears, at `mMinBirths` (25) it sets again; between them it keeps its value.
A birth is due when larvae are allowed, there is room and `mBirthTimer` exceeds
`mBirthInterval` (0 in the header, 2.0 s *disc*). `createBabyChappy` (`:423`)
spawns one larva at joint `body_end` facing away from her, launched at
`mSearchDistance` (50 *disc*) units per second. Nothing kills larvae when she dies.

**Special cases** (`Queen.cpp:85-105`): Piklopedia disables larvae. Hole of Beasts
(`getCaveID() == 'f_01'`) disables larvae, replaces health with `mHoBHealth`
(2500 header, 3300 *disc*; normal health 5000 *disc*) and sets `mDoEasyRoll`, so
the first roll goes away from the active captain (`:357`). Hole of Heroes
(`'l_02'`) makes each crash spawn 7 `Rock` enemies with a 30 s lifetime, laid out
across the facing line (`createCrashFallRock`, `:384`).

**Damage.** Only Pikmin hitting a collision part count (`:185`): ×0.1 asleep,
×0.2 while flicking, ×1 otherwise. Captain punches do nothing. Immune to purple
quakes (`earthquakeCallBack` returns false). Petrified damage coefficient 0.25.
`mFlickTimer` accumulates Pikmin attacks; a rise since the last Sleep/Wait entry
(`isHitCounterUp`) forces the Damage state. Shake-off thresholds *disc*:
blows 30/35/45/50, sticking 5/10/15.

**Animation keys** (`queen/enemyanimmgr.txt`, frame:type): `sleep` 59:0 118:1
120:2; `wait1` 0:0 29:1; `damage` 10:0 29:1; `flick` 40:2; `rolling_l`/`_r` 20:0
67:2 69:1; `born` 24:2; `dead` 60/73/86/99:2; `carry` 10:0 29:1. Type 0/1 pairs
bracket loop ranges; the Empress also treats type 0 in `sleep` and `rolling_*`
as the effect and roll start.

**Parameters** (`QueenParms`, *disc*): rolling time 3.5 s, birth interval 2.0 s,
Forest 1 life 3300, births max 50 / min 25. General *disc*: speed 125, territory
200, home 25, sight 200, LOD 300, damage scale 0/0.05.

## Bulborb Larva (`Baby`)

Files: `include/Game/Entities/Baby.h`, `src/plugProjectNishimuraU/Baby.cpp`,
`BabyState.cpp`, `BabyMgr.cpp`.

**States** (`Baby.h:140`): Dead 0, Press 1, Born 2, Move 3, Attack 4. Starts in
Born (Move in the Piklopedia). Born damps velocity until landed, then Move
(`BabyState.cpp:107-127`). Move targets the nearest Pikmin or captain within
`mSightRadius` (800 *disc*) and `mViewAngle` (180 *disc*), walks at `mMoveSpeed`
(40 *disc*) when facing it (quarter speed while turning) and enters Attack inside
`mMaxAttackRange` (30) and `mMaxAttackAngle` (45); with no target it wanders
(`:153-186`). Attack: key 2 hits captains with `mAttackDamage` (2 *disc*) and
tries to eat; with an empty mouth the motion switches to `attackfail`. Key 3
swallows with poison damage `mPoisonDamage` (300 *disc*, White Pikmin). End goes
back to Move (`:516-540`). Dead plays `dead` and kills at the end; Press sets
health to 0, plays `deadpress` and a squash effect (`:57-71`).

**Mouth.** One slot on joint `kamu`, radius 20 (`Baby.cpp:202`); at most one
Pikmin per bite. Collision (`baby/enemycoll.txt`): root 25, one stickable child
of radius 15.

**Crush.** `pressCallBack` and `hipdropCallBack` are identical: any press or
purple pound while in Move or Attack and not petrified is an instant kill
(`Baby.cpp:114-137`); the damage value is ignored. Health 5 *disc*.

**Lifetime and ownership.** No timer and no parent link: `mExistenceLength` stays
0 for larvae born from the Empress (`enemyMgrBase.cpp:214`, `enemyBase.cpp:521`),
so they persist until killed. The 50-object budget comes from the Empress's child
count. `EB_Cullable` and `EB_LeaveCarcass` are disabled at init (`Baby.cpp:40`),
so larvae update off camera and never become carcasses. Death and crush roll one
yellow nectar at `mNectarChance` (0.2 *disc*).

**Animation keys** (`baby/enemyanimmgr.txt`): `move` 0:0 11:1; `attack` 10:2
30:3; `born` 7:0 8:1; `dead`, `deadpress`, `attackfail` end only.

## Emperor Bulblax (`KingChappy`)

Files: `include/Game/Entities/KingChappy.h`, `src/plugProjectMorimuraU/kingChappy.cpp`,
`kingChappyState.cpp`, `kingChappyMgr.cpp`.

**States** (`KingChappy.h:22`, FSM `kingChappyState.cpp:20`): Walk 0, Attack 1,
Dead 2, Flick 3, WarCry 4, Damage 5, Turn 6, Eat 7, Hide 8, HideWait 9,
Appear 10, Caution 11, Swallow 12. Starts buried in HideWait with the hard
constraint on, life gauge hidden and bitter immunity (`kingChappy.cpp:107`).

- HideWait → Appear when a captain or any Pikmin is within
  `mDistanceToSpawn` × scale (150 header, 60 *disc*) after
  `mTimeToAppearance` frames (200 header, 0 *disc*), or at animation end
  (`kingChappyState.cpp:1954-2016`).
- Appear: key 3 shakes off Pikmin and captains within
  `mAppearanceShakeOffRange` (100) with power `mAppearanceShakeOffPower` (200);
  end → Caution → Walk.
- Walk: walks to its goal, turns via Turn when the goal is more than
  `mRequiredTurningAngleDeg` (60 *disc*) off, finishing the turn within `mTurningEndAngle` (40 *disc*); loses interest after
  `mPeriodOfIncubation` frames without a target (500) or when out of territory,
  returns home and enters Hide (`:53-117`). `checkFlick` accumulates
  `mFlickTimer` and, once `isStartFlick` fires, roars (WarCry) with probability
  `mFlickShoutRate` (0.5) when under half health, otherwise Flick
  (`kingChappy.cpp:2457-2474`). `checkDead` goes to Dead (or WarCry with
  `mDeathRate`, 0 by default).
- Attack: the tongue. Key 3 arms eating, key 6 allows bomb eating; each armed
  frame tries `eatBomb` and `EnemyFunc::eatPikmin`. The tongue tip (joint
  `bero6`, radius 5) aborts the lick when it hits floor or wall. Captains within
  any of the 9 mouth slots (`kamu1`..`kamu9`, radius 25 × scale) take
  `mAttackDamage` (5 *disc*). End → Eat (bombs) → Damage, Swallow (Pikmin,
  300 poison damage) → Walk, or Walk (`:133-743`).
- Flick: key 3 presses every Pikmin and captain within `mTramplingRange`
  (45) × scale of the foot position in a 30 unit height band,
  then the standard flick triple with `mShakeRange` (60 *disc*); captains are
  only flicked if none was pressed (`:823-1574`).
- WarCry: key 4 astonishes Pikmin within `mRoarEffectiveRange` (300 *disc*) and
  `mRoarEffectiveAngleDeg` (180 *disc*) and flicks; key 3 also asks the manager to
  wake one buried Emperor and make one walking Emperor roar
  (`Mgr::requestState`, `kingChappyMgr.cpp:53`; `forceTransit`,
  `kingChappy.cpp:1548`). This is the only cross-Emperor coordination, which
  matters for the paired rosters in `last_1` floor 4 and `last_2` floor 10.
- Damage (after eating bombs): key 4 kills everything in the mouth and applies
  `bombs × mBombDamage` (200), then stuns for `mBombDamageTime` frames (10 header,
  180 *disc*); end → Dead or Walk (`:1706-1775`).
- Hide → HideWait with dive effects; Dead → `kill` at animation end.

**Bomb ingestion.** `eatBomb` (`kingChappy.cpp:1009`) takes any `Bomb` (ID 36) in
`BOMB_Wait` that fits an empty mouth slot; several can be eaten in one lick and the
damage multiplies by the count. `checkAttack` also targets eatable bombs beyond
`mInvisibleRange` (70 header, 80 *disc*) when `mCanAttackBombs` is set (default on).
External bomb blasts are quartered (`bombCallBack`, `:875`).

**Damage** (`:824`): ×0.1 while petrified; full damage from a creature stuck to a
collision part; ×0.2 from ground-level attackers within 40 units and no part;
nothing from above. Health 1300 *disc*. `pressCallBack` forwards to the same
function. White Pikmin poison 300. Stone state marks `back` and `ketu` as
stickable and restores them afterwards (`:924-953`).

**Bulblax Kingdom variant.** In `forest_3` (`getCaveID() == 'f_03'`) or with
`mDoForceBig` the Emperor is "big": scale `mBigScale` (1.5 *disc*), health
`mBigLife` (1800 *disc*), speed `mBigSpeed` (45 *disc*), its own rotation and
attack parameters, floor offset forced to 60 (`kingChappy.cpp:61-72`, `148-158`).
Collision (`kingchappy/enemycoll.txt`): root 80 on joint 33, `back` 35 and
`ketu` 40 non-stickable, feet `asiL`/`asiR` 8, stickable `head` 30, `hana` 18,
`kuti` 22.

**Finale.** No story flag, ending hook or movie references `KingChappy` anywhere
in `src`; the "finale" wording on the issue is not backed by boss-specific code.
The corpse is a normal carriable pellet (`startCarcassMotion` plays `carry`).

**Animation keys** (`kingchappy/enemyanimmgr.txt`): `attack` 25:2 40:3 70:4 86:5
92:6; `cry` 33:2 38:3 65:4 100:5 103:6; `damage` 12:2 14:3 15:4 46:5 60:6 65:0
94:1; `dead` 185:2; `dive` 58:2 60:3 90:4; `flick` 30:2 35:3; `move1` 15:0 54:1;
`type3` (appear) 3:2 55:3 58:4; `wait2` 0:0 39:1; `waitact1` 10:0 33:1;
`carry` 10:0 29:1. The state code reacts to types 2 to 6 plus `KEYEVENT_END` and
`KEYEVENT_END_BLEND`; the animator blends between motions over 30 frames when
`mAllowAnimBlending` is set.

## Dependencies a reimplementation must provide

- Enemy base lifecycle, event flags (`EB_Cullable`, `EB_LeaveCarcass`,
  `EB_Bittered`, `EB_NoInterrupt`, `EB_BitterImmune`), state machine, blend
  animator with key-event streams, `Stickers`, mouth slots, `EnemyFunc` search,
  eat, swallow and flick helpers, `InteractPress`/`Attack`/`Flick`/`Astonish`.
- `generalEnemyMgr` lookups for `Baby`, `Rock` and `Bomb` managers and the child
  object budget.
- `SingleGameSection::getCaveID` for `'f_01'`, `'l_02'` and `'f_03'`; `mapMgr`
  height and trace queries; water boxes for the Emperor's eye ripples and splash
  variants; joint shadows for the Empress.
- `PSM::EnemyMidBoss` music requests, camera vibration and rumble tables.
- Pellet births for held treasures with the last-floor squad-weight rule.

## Unknowns and decomp caveats

- `Queen::StateRolling::exec`, `Baby::StateMove::exec`, and the Emperor's
  `StateAttack::exec`, `StateFlick::exec`, `searchTarget` and `checkAttack` still
  carry retained assembly; evaluation order there is reconstructed.
- The Empress's roll argument is a string literal cast to `StateArg*`; any
  non-null pointer means "left".
- `KingChappy::collisionCallback` is a no-op comparison; the intended `kuti`
  handling is lost. `eatWhitePikminCallBack` lacks a return.
- Loop flags live in the animation resources, not source; the type 0/1 frames
  above are the anim manager's markers.
- Natural runtime behavior, performance with 50 larvae and full squads, and
  Piklopedia discovery presentation remain runtime evidence for the enemy lane.
