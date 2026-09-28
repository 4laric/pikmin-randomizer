# Ground invertebrates and disguises source audit (#165)

Source behavior audit for enemy IDs 12 `UjiA`, 13 `UjiB`, 14 `Tobi`, 15 `Armor`,
28 `ElecBug`, 65 `Imomushi`, 68 `TamagoMushi`, 79 `Sokkuri` and 84 `Hana`.
Paths are relative to `native/pikmin2-research` unless they name a disc file.
Numbers marked *disc* come from `enemy/parm/enemyParms.szs` on the US GPVE01
revision 0 disc and override the header defaults quoted next to them. This is an
audit, not an implementation: no actor, save or animation interface changes.

## Identity, placement and carcass

| ID | Internal | Piklopedia | Drop table | Health *disc* | Carcass (pokos, carry) | Story caves (floors) | Surface generators |
|---:|---|---:|---|---:|---|---|---|
| 12 | `UjiA` Female Sheargrub | 24 | `BDT_Weak` | 50 | 1, 1 | forest_1:1, forest_2:1, forest_3:3, last_2:1, yakushima_2:2 | Awakening Wood day windows |
| 13 | `UjiB` Male Sheargrub | 23 | `BDT_Weak` | 50 | 2, 1 | forest_1:1, forest_2:1, forest_4:1-2, last_2:1, yakushima_2:2 | Awakening Wood day windows |
| 14 | `Tobi` Shearwig | 25 | `BDT_Weak` | 200 | 2, 1 | forest_4:2, last_2:1, yakushima_1:1 | Wistful Wild, Perplexing Pool initgen and day windows |
| 15 | `Armor` Cloaking Burrow-nit | 26 | `BDT_Strong` | 300 | 3, 8 to 16 | forest_4:2, last_1:7, last_2:1, last_3:11, yakushima_2:2 | Valley, Awakening Wood, Wistful Wild initgen |
| 28 | `ElecBug` Anode Beetle | 28 | `BDT_Normal` | 500 | 3, 5 to 10 | 12 floors across 9 caves | none |
| 65 | `Imomushi` Ravenous Whiskerpillar | 27 | `BDT_Weak` | 200 | 1, 1 | none | Awakening Wood day windows, Wistful Wild and Perplexing Pool initgen |
| 68 | `TamagoMushi` Mitite | 29 | `BDT_Weak` | 50 | 1, 1 | forest_1:4, forest_3:6, last_2:10 (plus Egg and Raging Long Legs births) | none |
| 79 | `Sokkuri` Skitter Leaf | 54 | `BDT_Weak` | 120 | 1, 1 | last_2:1, yakushima_1:1 | Perplexing Pool defaultgen |
| 84 | `Hana` Creeping Chrysanthemum | 53 | `BDT_Strong` | 2500 | 7, 10 to 20 | forest_4:2, last_1:3, last_2:1 | Awakening Wood and Wistful Wild initgen |

Challenge and Battle rosters use all nine except the Whiskerpillar, Antenna Beetle
family aside; the Skitter Leaf and Sheargrubs hold marbles and keys in Challenge
caves, and the Female Sheargrub is in the Battle easy-enemy pool
(`RandEnemyUnit.cpp:1367`). `Armor` carries `EFlag_CanAppearDayEnd` with a day-end
maximum of 4; `UjiB` and `Tobi` also carry `CanAppearDayEnd`; `UjiA` does not.
Bitter kills roll one nectar at 99 percent (`BDT_Weak`) or 90 percent
(`BDT_Normal`/`BDT_Strong`) yellow (`enemyBase.cpp:1327-1349`). Assets:
`enemy/data/<Internal>/model.szs` and `anim.szs` (`UjiB` has no own animation
archive: its registry row shares `UjiA` animations, `enemyInfo.cpp:31`).

## Sheargrubs and Shearwig (`UjiA`, `UjiB`, `Tobi`)

Files: `include/Game/Entities/{Ujia,Ujib,Tobi}.h`, `src/plugProjectNishimuraU/Ujia*.cpp`,
`Ujib*.cpp`, `Tobi*.cpp`. There is no shared base: the three are copy-pasted
`EnemyBase` subclasses with identical helpers (bridge search, appear check, water
damage) and state IDs 0 to 9 (`Dead, Press, Stay, Appear, Dive, Move, MoveSide,
MoveCentre, MoveTop, GoHome`); `UjiB` adds `Attack1, Attack2, Eat`, `Tobi` inserts
`Fly` 10 before `Attack1, Attack2, Eat`.

- **Burrow cycle.** All start buried (Stay: hidden, no collision, invulnerable,
  bitter-immune) and emerge when a Pikmin or captain is inside `mViewAngle`
  (180 *disc*) and `mSightRadius` (150 *disc*), or when a damaged bridge is in range.
  The appear delay only staggers in the Piklopedia; in play they surface at once.
  With nothing to do they walk home (`mHomeRadius` 30 *disc*) and Dive back to Stay,
  then re-emerge on the next sighting.
- **Bridges.** Every one can gnaw a bridge found within `mTerritoryRadius`
  (300 Sheargrubs, 400 Shearwig *disc*): MoveSide/MoveCentre/MoveTop approach, then
  `Attack1` key 2 applies `InteractBreakBridge(mBridgeDamage)` (25 / 50 / 75). The
  bridge target is chosen once per lifetime.
- **Female (`UjiA`)** never attacks: its Move only follows an already stored target
  and `Attack1` is the bridge gnaw. No mouth slot, no flick. Piklopedia hides its
  Pikmin-lost counter.
- **Male (`UjiB`)** re-scans each frame, bites (`Attack2` key 4: `attackNavi` with
  `mAttackDamage` 10 *disc* and `eatPikmin`), one mouth slot on `kamujnt` radius 15,
  then Eat key 2 swallows with `mPoisonDamage` (300).
- **Shearwig (`Tobi`)** is the male plus flight: below `mTakeOffHealthRatio` (0.5)
  it enters Fly, becoming invulnerable and untargetable, wandering at
  `mFlightHeight` (60 header, 75 *disc*) above the floor and healing 0.1 percent of
  max health per tick; it lands above `mLandHealthRatio` (0.7 header, 0.8 *disc*).
  A Pikmin thrown into it mid-air kills it outright (`flyCollisionCallBack`,
  `Tobi.cpp:138`). Petrification or a quake clears the invulnerability. Bite damage
  20 *disc*.
- **Crush.** `pressCallBack` and purple pounds are instant kills (`dead_p`) in any
  above-ground state (not while flying). Normal damage uses the enemy base. None
  can shake Pikmin off. Water deals 2 damage per frame (2.5 for the Shearwig) while
  walking; they drown.
- **Animation keys** (`ujia`/`ujib`/`tobi` `enemyanimmgr.txt`): `move` 0:0 19:1;
  `attack1` 15:2; `attack2` 5:2 12:3 14:4; `eat` 53:2; `fly` 46:0 65:1 (Shearwig);
  `type5` (carry) 10:0 29:1; `appear`, `dive`, `dead`, `dead_p` end only.

## Cloaking Burrow-nit (`Armor`)

Files: `include/Game/Entities/Armor.h`, `src/plugProjectNishimuraU/Armor*.cpp`.
States (`Armor.h:165`): the Sheargrub set plus `Attack1` 9 (bridge), `Attack2` 10
(tongue), `Eat` 11, `Flick` 12, `Fail` 13. Buried start with the same emerge rule
(`mSightRadius` 200 *disc*, view 180); it walks home to burrow (`mHomeRadius` 30).

- **Tongue.** One slot on `kamujnt` radius 25; while the attack animation is between
  frames 17 and 27 every Pikmin inside the slot radius is swallowed with the stab
  flag set (`InteractSwallow`, `mIsStabbed`), key 3 hits captains with
  `mAttackDamage` (10). The loop repeats for `mAttackLoopTimer` (0 header, 1.0
  *disc*) then goes to Eat (swallow, poison 300) or Fail. Bridge gnaw damage 100.
- **Armour.** Damage only registers while petrified or when the hit part is `dmg1`
  (radius 17.5, the only stickable part, `armor/enemycoll.txt`); everything else
  returns false (`Armor.cpp:117-128`). Purple pounds route through the same rule.
- **Flick.** `isStartFlick` polled in Move and GoHome (thresholds *disc* 1/1/2/2
  blows at 1/2/3 stuck); the Flick state's key 2 shakes nearby captains, Pikmin and
  stuck Pikmin with the general shake parameters. Speed 50, territory 400 *disc*.
- **Death.** Normal carcass (`carry`), `BDT_Strong`. No water code.
- **Animation keys**: `appear` 15:2 30:2 45:2; `dive` 15:2; `move` 0:0 19:1;
  `attack1` 15:2; `attack2` 12:0 14:1 18:2 22:3; `eat` 60:2; `flick` 39:2; `dead`
  17:2; `carry` 10:0 29:1.

## Anode Beetle (`ElecBug`)

Files: `include/Game/Entities/ElecBug.h`, `src/plugProjectNishimuraU/ElecBug*.cpp`.
States (`ElecBug.h:143`): Dead, Wait, Turn, Move, Charge, Discharge, ChildCharge,
ChildDischarge, Reverse, Return.

- **Wander.** Turn picks a point between `mHomeRadius` (100 *disc*) and
  `mTerritoryRadius` (200), Move walks there (speed 30), Wait holds `mWaitTime` (1.5).
  An inactivity fuse `mInactiveTimer` (random start, 15 s) forces Charge.
- **Pairing** (`ElecBugState.cpp:216-263`). After 2 s in Charge it lists every other
  beetle in Wait, Turn or Move within 300 units (fixed buffer of 32 without bounds
  check) and picks one at random as its child; both face away from each other. The
  parent discharges after 3 s in Charge, the child after 1 s; Discharge lasts
  `mDischargeTime` (3.0). Only the parent runs the arc test: a thin capsule between
  the two (half-widths 10 and 15) applying `InteractDenki(mAttackDamage)` with a
  knockback built from `mSearchDistance` and `mSearchHeight`. Contact while
  discharging also shocks. Electricity kills any non-Yellow, non-Bulbmin Pikmin and
  flicks captains without the Dream Material (`interactPiki.cpp:334`,
  `interactNavi.cpp:85`).
- **Flip.** It is invulnerable by default; a Pikmin press or purple pound
  (`pressCallBack`) in any active state flips it into Reverse for `mFlipTime` (5.0
  header, 3.0 *disc*), the only vulnerable window (health 500). Petrification also
  drops the invulnerability. Damage to the pair partner is cleared on either side.
- **Death.** `onKill` clears the partner and effects; normal carcass; `BDT_Normal`.
  No damage callback override, no flick state, no water code.
- **Animation keys**: `move` 4:0 13:1; `wait` 0:0 9:1; `charge` 0:0 9:1; `discharge`
  8:2 10:0 17:1; `turn` 30:0 69:1; `recover`, `dead` end only; `carry` 10:0 29:1.

## Ravenous Whiskerpillar (`Imomushi`)

Files: `include/Game/Entities/Imomushi.h`, `src/plugProjectNishimuraU/Imomushi*.cpp`.
States (`Imomushi.h:20`): Dead, Wait, FallDive, FallMove, Stay, Appear, Dive, Move,
GoHome, Attack, Climb, plus three Piklopedia wander states.

- **Berry predation only.** Buried in Stay for 6 s with no Pikmin inside
  `mPrivateRadius` (250 *disc*), it surfaces when a fruiting `ItemPlant` (burgeoning
  spiderwort) is within `mTerritoryRadius` (500), walks to within 30 units, climbs
  the plant's tube collision at `mPlantClimbingSpeed` (2.0), sticks to the `tops`
  part, orbits at `mSeedCirculationSpeed` (0.3) and every `mEatingTime` (10 s) eats
  the nearest berry with `InteractEat(PelletType::Berry)`, which pops a spicy or
  bitter berry (`itemPlant.cpp:1799-1828`). Being hit while feeding drops it off
  (`dropCallBack` → FallDive). With no fruiting plant it returns home and burrows.
- **Harmless.** No attack, eat or flick call exists; the Piklopedia blinds its
  Pikmin-lost counter. The disc `mAttackDamage` of 1000 is unused. Damage uses the
  enemy base; health 200 *disc*. Normal carcass, `BDT_Weak`.
- **Animation keys**: `move1` 0:0 9:1; `move2` (climb) 0:0 14:1; `fall1`/`fall2`
  0:0 9:1; `eat` 5:0 10:2 14:1; `carry` 10:0 39:1; `set`, `dive`, `dead` end only.

## Mitite (`TamagoMushi`)

Files: `include/Game/Entities/TamagoMushi.h`, `src/plugProjectMorimuraU/tamagoMushi*.cpp`.
States (`TamagoMushi.h:239`): Walk, Turn, Appear, Hide, Dead, Wait (ball).

- **Groups.** Each Mitite has `mLeader`. A ground Mitite is its own leader and, once
  a Pikmin or captain is within `mAppearanceRange` (80 header, 120 *disc*), creates
  9 followers (`createGroup(this, 10)`). An Egg births a group of 10 in ball form
  with upward velocity 200 (`egg.cpp:340-360`), falling back to one nectar if
  slots are short; Raging Long Legs births 30 without a slot check. Manager limit
  is 10 above ground and 30 in caves (`generalEnemyMgr.cpp:436-443`). Nothing
  clears followers' leader pointer when the leader dies.
- **Panic.** Only the leader's appearance panics Pikmin within 150 units
  (`InteractAstonish`, 30 s); any Mitite panics Pikmin it touches or that hit it.
  Hits deal zero damage (`damageCallBack` passes 0); only presses, purple pounds,
  quakes and bombs kill it (instant), or five hits while petrified.
- **Lifetime.** `mSurvivalTime` (300 header, 180 *disc*) scaled by 0.8 to 1.0, then
  Hide plays `dive` and kills without a carcass. Walk durations `ip01`/`ip02`
  (60/100 header, 25/80 *disc*) frames, appear delays `ip03`/`ip04` (10/50 header,
  20/90 *disc*). Ball form bounces on landing and scatters.
- **Death** re-enables the carcass, plays the Kochappy bomb and death effects, and
  drops one yellow nectar at `mHoneyRate` (1.0; the z component of the throw uses
  `sin`, a source oddity). `BDT_Weak`. No water code.
- **Animation keys**: `move` 0:0 9:1; `set` 2:2; `wait` 0:0 14:1; `dive`, `dead`
  end only; `carry` 10:0 29:1.

## Skitter Leaf (`Sokkuri`)

Files: `include/Game/Entities/Sokkuri.h`, `src/plugProjectNishimuraU/Sokkuri*.cpp`.
States (`Sokkuri.h:19`): Dead, Press, Stay, Appear, Disappear, Wait, MoveGround,
MoveWater, Flick.

- **Disguise.** Stay hides it as a leaf (bitter-immune, constrained, no life gauge)
  until the nearest captain (nearest Pikmin in the Piklopedia) is within
  `mSightRadius` (150 *disc*). It then flees: each `mMaxTravelTime` (1.0) it turns
  by 45° to 90° (`fp03`/`fp04`) left or right and runs 1000 units out at speed 120,
  waiting with probability `mWaitingProbability` (0.25, 0.4 *disc*) for up to
  `mMaxWaitingTime` (2.0, 3.25 *disc*); walls reflect it; outside `mTerritoryRadius`
  (200) it heads home and re-hides once inside `mHomeRadius` (150) with no target.
  Water uses a separate `wrun1` state at `mUnderwaterMoveSpeed` (25).
- **No attack.** There is no chomp in source; it only flees and shakes off
  attackers (Flick key 3 with the shake parameters). Any Pikmin press or purple
  pound is an instant kill (`pdead1`); normal damage uses the base (health 120).
  The Piklopedia blinds its Pikmin-lost counter. Normal carcass, `BDT_Weak`.
- **Animation keys**: `run1` 4:0 19:1; `wrun1` 6:0 29:1; `wait1` 0:0 9:1; `hide1`
  6:2; `dead1` 14:2; `pdead1` 8:2; `flick1` 14:2 18:3 40:4; `type5` 10:0 29:1.

## Creeping Chrysanthemum (`Hana`)

Files: `include/Game/Entities/Hana.h`, `src/plugProjectNishimuraU/Hana.cpp`,
`HanaMgr.cpp`; behavior inherited from `ChappyBase` (`chappyState.cpp`). States
(`ChappyBase.h:176`): Turn, Dead, Flick, Walk, Attack, TurnToHome, GoHome, Sleep.

- **Flower disguise.** Starts in Sleep at frame 70 of `type1`, buried, invulnerable,
  bitter-immune, without collision. `isWakeup` fires when a captain or Pikmin is
  inside `mPrivateRadius` (70 *disc*); the sleep animation's key 4 restores collision
  and shoves everything within that radius back with the shake knockback
  (`Hana.cpp:186-213`).
- **Bite.** Three mouth slots on `kamu1` to `kamu3` (radius 30) instead of the
  Bulborb five; attack key 2 hits captains with `mAttackDamage` (10) and eats, a
  miss switches to the slam animation; key 3 swallows with poison 300. Flicks use
  the backward angle for stuck, nearby and captain targets.
- **Damage** uses the Bulborb rule: 0.25 scale without a collision part. Health
  2500 *disc*, speed 100, territory 300, sight 500. No water code, no walk smoke or
  nose-bubble effects. Normal carcass, `BDT_Strong`.
- **Animation keys**: `type1` (sleep) 27:2 30:0 100:1 103:3 120:4; `move1` 10:0
  40:1; `attack1` 18:2 71:3; `attack2` 24:2 62:3; `flick` 50:2; `waitact1` 10:0
  40:1; `type5` 10:0 30:1.

## Dependencies a reimplementation must provide

- `ItemBridge` for the gnaw chain and `ItemPlant` berries for the Whiskerpillar;
  tube collision trees and stick targets.
- `InteractDenki`, `InteractAstonish`, `InteractSwallow` with the stab flag, panic
  Pikmin states, `ItemHoney` births and the Egg spawn path.
- Enemy iterator over a manager for Anode Beetle pairing; day-end spawn budget for
  the Burrow-nit, male Sheargrub and Shearwig; `ChappyBase` for the Chrysanthemum.

## Unknowns and decomp caveats

- `StateMove::exec` of the Sheargrubs and Shearwig, several bridge helpers, the
  Burrow-nit bridge helpers and `ElecBug::checkInteract` keep retained assembly.
- Source oddities: swapped attack range and angle arguments in the GoHome checks
  of the Sheargrubs and Burrow-nit, an uninitialised local in the Burrow-nit
  `StateFail`, the unbounded partner buffer, `sin` used for the Mitite nectar z
  velocity, and Skitter Leaf minimum timers acting only as span reducers.
- Natural runtime evidence, group performance for Mitites and day-end respawns on
  the surface stay with the enemy lane.
