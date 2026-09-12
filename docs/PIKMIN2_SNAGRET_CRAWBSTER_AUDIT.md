# Burrowing Snagret, Pileated Snagret and Segmented Crawbster source audit (#174)

Source behavior audit for enemy IDs 34 `SnakeCrow`, 70 `SnakeWhole` and 94 `DangoMushi`.
Paths are relative to `native/pikmin2-research` unless they name a disc file.
Numbers marked *disc* come from `enemy/parm/enemyParms.szs` on the US GPVE01
revision 0 disc and override the header defaults quoted next to them. This is an
audit, not an implementation: no actor, save or animation interface changes.

## Identity and placement

| ID | Internal | Piklopedia | Drop table | Registry (`src/plugProjectYamashitaU/enemyInfo.cpp`) |
|---:|---|---:|---|---|
| 34 | `SnakeCrow` | 78 | `BDT_Boss` | line 62: day-end spawnable, at most one, own ID |
| 70 | `SnakeWhole` | 79 | `BDT_Boss` | line 63: day-end spawnable, at most one, own ID |
| 94 | `DangoMushi` | 80 | `BDT_Boss` | line 113: own ID |

All three are in `IS_ENEMY_BOSS` (`include/Game/enemyInfo.h:214`). Both Snagrets carry
`EFlag_CanAppearDayEnd` and `EFlag_DayEndMax1`: at sunset every such enemy is killed
silently and one already-discovered candidate can be respawned at the takeoff site,
consuming the whole day-end budget (`generalEnemyMgr.cpp:924-1000`).

Carcasses (`carcass_config.txt`): `SnakeCrow` 10 pokos, carry 5 to 10; `SnakeWhole`
15 pokos, carry 5 to 10; `DangoMushi` 15 pokos, carry 20 to 30.

Retail rosters (caveinfo; type 8 means the special-enemy slot) and surface generators:

| Place | Floor | Entry | Held treasure |
|---|---:|---|---|
| `forest_2` (White Flower Garden) | 5 | `SnakeCrow_radar_b` | Five-man Napsack |
| `forest_4` (Snagret Hole) | 3 | `SnakeCrow_apple_blue`, `SnakeCrow` (type 8) | Insect Condo |
| `forest_4` | 6 | `SnakeCrow_chess_queen_white`, `SnakeCrow` (type 8) | white queen |
| `forest_4` | 7 | `SnakeWhole_suit_powerup` (type 8) | Justice Alloy |
| `last_1` (Cavern of Chaos) | 10 | `DangoMushi_doll` | doll |
| `last_2` (Hole of Heroes) | 4 | `SnakeWhole_gold_medal`, `SnakeCrow` (type 0) | gold medal |
| `ch_MAT_t_hunter_enemy` | 5 | `SnakeCrow_key` | The Key |
| `ch_MAT_crawler` | 2 | `SnakeWhole_key` | The Key |
| Awakening Wood `initgen.txt` | surface | `SnakeCrow` | none |
| Valley of Repose `nonloop/5-29`, `loop/30-39`, `40-49`, `50-59` | surface | `SnakeCrow` | none |

No Battle definition spawns any of the three. Assets: `enemy/data/{SnakeCrow,SnakeWhole,DangoMushi}`
model and animation archives; the Crawbster also has `dangomushi.brk`.

## Shared Snagret machinery

Both Snagrets share `SnakeJointMgr` (`src/plugProjectNishimuraU/SnakeJointMgr.cpp`),
a joint callback on `bodyjnt8` that bends `bodyjnt3` to `bodyjnt8` downward with
ratios 0 to 1 so the beak reaches the strike point, ramping over the frames until the
attack animation's key 3 and back until key 4. They share the same five peck boxes
(`hit_near`, `hit`, `hit_far`, `hit_r`, `hit_l`), three mouth slots on `kamujnt1` to
`kamujnt3` (radius 15) taking one Pikmin per peck, White Pikmin poison `fp21` (300),
a `bod1` tube tree for the neck and a stickable `head` whose latched Pikmin turn a
pending peck into the Struggle animation. Captains in a peck box take `mAttackDamage`
(10 *disc*) and are never swallowed. Each surfacing heals 10 health
(`lifeIncrement`). Only Pikmin damage them; a hit with no collision part (a Purple
pound) is scaled to 0.1 (`SnakeCrow.cpp:193`, `SnakeWhole.cpp:157`). Petrified
damage coefficient 0.25; bitter-immune only while buried.

**Burrow cycle.** Buried (Stay) for at least `fp12` (1.0 header, 2.5 *disc*), then
a Pikmin or captain inside `mTerritoryRadius` of home triggers a surfacing 120 units
from the target, facing it (`appearNearByTarget`); `fp01` (0.6 *disc*) is the
chance of the fast `appear1` over the slow `appear2`. It dives (Disappear) after
`fp11` seconds without a target (2.0 header; 2.5 *disc* Burrowing, 0.5 *disc*
Pileated) or when the stuck-Pikmin shake threshold is reached; the dive's key 2
flicks nearby captains, Pikmin and stuck Pikmin. Nothing within 400 units clears the
boss music flag.

**Death.** Both throw the held treasure from the beak joint `kutijnt1` at a dead
animation key (Burrowing key 3, Pileated key 2), swap the joint shadow for a normal
one and leave a carriable corpse (`type5` carry animation).

## Burrowing Snagret (`SnakeCrow`)

Files: `include/Game/Entities/SnakeCrow.h`, `src/plugProjectNishimuraU/SnakeCrow.cpp`,
`SnakeCrowState.cpp`, `SnakeCrowShadow.cpp`, `SnakeCrowMgr.cpp`.

**States** (`SnakeCrow.h:54`): Dead 0, Stay 1, Appear1 2, Appear2 3, Disappear 4,
Wait 5, Attack 6, Eat 7, Struggle 8. It never moves: Wait turns toward the target
(`PSSE_EN_SNAKE_TURN`, 25° tolerance) and attacks when a target enters a box.
Peck boxes (forward × lateral units): near 0–80 × ±30, normal 80–160 × ±30, far
160–220 × ±30, right 50–130 × 50..110, left 50–130 × −110..−50, strike points at
40/120/190/90/90 forward (`SnakeCrow.cpp:324-340`, `502-507`). At the attack's key 4
it re-pecks if a mouth slot is free and a target remains. Struggle lasts 1.5 s.

**White Flower Garden.** In `forest_2` its health is replaced by `mWFGHealth` fp31
(7500 header, 2500 *disc*; normal health 1500 *disc*) (`SnakeCrow.cpp:95-105`).

**Shadow.** Eight tube and eight sphere joint shadows on `bodyjnt2` to `bodyjnt8` and
`kutijnt1`, hidden while buried; the head shadow projects 80 units along the beak.

**Animation keys** (`snakecrow/enemyanimmgr.txt`): `appear1` 14:2; `appear2` 20:2
58:3 115:4 141:5; `dive` 12:2 28:3; `hit_near` 33:2 36:3 48:4; `hit` 32:2 34:3 48:4;
`hit_far` 32:2 36:3 48:4; `hit_r`/`hit_l` 28:2 32:3 48:4; `wait1` 0:0 49:1;
`waitact1` 42:2; `waitact2` 0:0 19:1; `type5` 10:0 29:1; `dead` 67:2 75:2 110:5
131:3 143:4 149:4.

## Pileated Snagret (`SnakeWhole`)

Files: `include/Game/Entities/SnakeWhole.h`, `src/plugProjectNishimuraU/SnakeWhole.cpp`,
`SnakeWholeState.cpp`, `SnakeWholeShadow.cpp`, `SnakeWholeMgr.cpp`.

**States** (`SnakeWhole.h:53`): Dead 0, Stay 1, Appear1 2, Appear2 3, Disappear 4,
Wait 5, Walk 6, Home 7, Attack 8, Eat 9, Struggle 10. The two extra states are the
foot-assisted pursuit.

**Hopping** (`run1`, `SnakeWhole.cpp:263-306`): at key 2 it launches a hop toward
the live target (Walk) or home (Home), at key 3 it lands. It translates only when
facing within 30° of the target, at `min(distance, mMoveSpeed) × 11/15`, so the
disc speed of 1000 gives 733 units per second per hop; otherwise it only pivots at
up to `angle/22` per frame. A target entering a peck box cuts the hop short into
Attack. Leaving `mTerritoryRadius` (380 *disc*) sends it Home until inside
`mHomeRadius` (100 *disc*). View angle widens to 180° while Pikmin are stuck to it.
Peck boxes (forward × lateral): near 0–120 × ±30, normal 120–180, far 180–260, right
80–160 × 50..110, left 80–160 × −110..−50, strike points 60/150/220/120/120
(`SnakeWhole.cpp:740-756`, `904-951`). Health 5000 *disc*; no cave health override.

**Shadow.** Nine tube and nine sphere joint shadows from `foot_joint1` through the
leg and body joints to `kutijnt1`, with a 100 unit beak tube.

**Animation keys** (`snakewhole/enemyanimmgr.txt`): `appear1` 13:2 17:3 30:4;
`appear2` 20:2 58:3 115:4 145:5 159:6; `dive` 12:2 31:3 33:4 45:5; the five `hit*`
as the Burrowing Snagret; `wait1` 0:0 49:1; `waitact1` 42:2; `waitact2` 0:0 19:1;
`run1` 10:0 10:2 32:3 34:1; `type5` 10:0 29:1; `dead` 65:5 89:2 118:3 131:4.

## Segmented Crawbster (`DangoMushi`)

Files: `include/Game/Entities/DangoMushi.h`, `src/plugProjectNishimuraU/DangoMushi.cpp`,
`DangoMushiState.cpp`, `DangoMushiMgr.cpp`.

**States** (`DangoMushi.h:23`): Dead, Stay, Appear, Wait, Move, Attack, Turn, Recover,
Flick. It drops in from above: Stay grows a shadow at 0.6 per second once a captain
or Pikmin is within `mPrivateRadius` (100 *disc*), then Appear plays `fly`. Wait
(up to 3 s) and Move (up to 10 s, `mMoveSpeed` 50 *disc*, territory 150, home 100)
enter Attack when a target is within `mMaxAttackRange` (300 *disc*) and
`mMaxAttackAngle` (15 *disc*).

**Roll** (`DangoMushiState.cpp:393-480`, `rollingMove` `DangoMushi.cpp:412`): the
`attack` animation's key 4 starts rolling toward the active captain (else the nearest
Pikmin or captain within `mSightRadius`, 500 *disc*) at `mRollingMoveSpeed` fp01
(200), turning with gain fp02 (0.1, 0.03 *disc*) and clamp fp03 (10, 3 *disc*)
degrees per frame. Every rolling contact presses grounded creatures with
`mAttackDamage` (10 *disc*); the ball halves its floor offset from 120 to 60. The
roll budget is 15 s, burned 3× to 5× faster while grinding a wall. A head-on wall
hit at over 100 speed and within 60° of the normal flips it (Turn).

**Flip window** (`:486-567`): Turn rains 10 `Rock` enemies (30 s lifetime) around the
active captain and, with probability equal to the captain's group share of all
Pikmin, one `Egg` at home (`createCrashEnemy`, `DangoMushi.cpp:649-776`; 30 rocks and
10 eggs are reserved per Crawbster in `generalEnemyMgr.cpp:842`). Between the
animation's loop-start key and key 3 the body parts `bod0`/`bod1` become stickable
and `EB_Invulnerable` clears; this is the only time Pikmin can latch and damage it.
After `mFlipTime` fp10 (7.5 s, 3.0 *disc*) it enters Recover, turns 180° and swings
its arm (Flick, `attack_2`): captains and non-Purple Pikmin are scattered
(`InteractHanaChirashi`), Purples are flicked; an arm over a ledge aborts the swing.

**Damage** (`DangoMushi.cpp:204-221`): Pikmin only; on `bod0`/`bod1` while stickable,
or anywhere while petrified. Petrification also clears invulnerability
(`doStartStoneState`), coefficient 0.2. Immune to quakes. Health 3000 *disc*. Death
is only checked in Wait, Move and Turn. Collision parts from the disc file: right arm
`haR0` to `haR4`, head `heaL`/`heaR`/`heaC`, back `baC0`/`baL0`/`baR0`, tail `taC`/`taL`/`taR`
0 to 3, body `bod0` (only `haR0`, `bod0` and `bod1` are referenced in code).

**Death.** No custom drop code: the held treasure and the carriable corpse (`carry`)
come from the enemy base; the `dead` animation's key 3 explodes with a hard shake.

**Animation keys** (`dangomushi/enemyanimmgr.txt`): `fly` 13:2 30:3 35:4; `wait` 0:0
39:1; `move` 0:0 8:2 19:1; `attack` 6:2 17:3 23:4 50:0 100:1 118:5; `turn` 10:2 32:0
81:1 108:3 114:4; `recover` 20:2; `dead` 32:2 40:3; `carry` 10:0 29:1.

## Dependencies a reimplementation must provide

- Joint callbacks (`SnakeJointMgr` neck bend, Crawbster hand and arm effects), mouth
  slots, `InteractSwallow`/`InteractAttack`/`InteractPress`/`InteractHanaChirashi`.
- Day-end enemy budget handling and generator spawning for the surface Snagrets;
  cave ID check for White Flower Garden.
- `Rock` and `Egg` managers for the Crawbster's flip hazard, ground triangle queries
  for the ledge test, blend animator with `KEYEVENT_END_BLEND`.
- `PSM::EnemyBoss` music, joint shadows for the Snagrets, BRK material animation for
  the Crawbster.

## Unknowns and decomp caveats

- Snagret `appearNearByTarget`, `setAttackPosition`, `getAttackPiki`, `getAttackNavi`
  and `SnakeJointMgr::makeMatrix`, plus Crawbster `rollingMove` and
  `flickHandCollision`, keep retained assembly; their constants are reconstructed.
- The Crawbster passes `"blend"` string literals as state arguments and swaps the
  attack range and angle arguments in two of three call sites.
- The disc parameter labelled Forest 2 Life is the White Flower Garden health
  override, not an emergence health pool.
- Natural runtime evidence, surface day-end behavior and full-squad performance stay
  with the enemy lane.
