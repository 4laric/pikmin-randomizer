# Aquatic and hopping enemies, Crawmad and Bloysters source audit (#167)

Source behavior audit for enemy IDs 17 `Frog`, 18 `MaroFrog`, 26 `Catfish`,
27 `Tadpole`, 63 `Jigumo`, 64 `JigumoNest`, 71 `UmiMushi`, 100 `UmiMushiBase` and
101 `UmiMushiBlind`. Paths are relative to `native/pikmin2-research` unless they
name a disc file. Numbers marked *disc* come from `enemy/parm/enemyParms.szs` on
the US GPVE01 revision 0 disc and override the header defaults quoted next to them.
This is an audit, not an implementation: no actor, save or animation interface
changes.

## Identity, placement and carcass

| ID | Internal | Piklopedia | Drop table | Health *disc* | Carcass (pokos, carry) | Story caves (floors) | Surface generators |
|---:|---|---:|---|---:|---|---|---|
| 17 | `Frog` Yellow Wollywog | 41 | `BDT_Strong` | 800 | 5, 7 to 14 | last_2:6, yakushima_1:2 | Awakening Wood, Wistful Wild, Perplexing Pool initgen; Pool `nonloop/0-9` |
| 18 | `MaroFrog` Wollywog | 42 | `BDT_Strong` | 1100 | 7, 7 to 14 | ten floors across forest_3, yakushima_3 and 4, last_1 to last_3 | none |
| 26 | `Catfish` Water Dumple | 11 | `BDT_Normal` | 200 | 3, 5 to 10 | tutorial_3:6, yakushima_1:4, yakushima_3:3, last_1:6, last_2:6, last_3:10 | Valley, Perplexing Pool initgen |
| 27 | `Tadpole` Wogpole | 43 | `BDT_Weak` | 200 | 1, 1 | yakushima_3:1, last_2:6 | Awakening Wood defaultgen; Pool `nonloop/0-29` |
| 63 | `Jigumo` Hermit Crawmad | 30 | `BDT_Strong` | 500 | 3, 5 to 8 | yakushima_1:4, yakushima_3:3, last_2:6, last_3:1 | Wistful Wild, Perplexing Pool initgen |
| 64 | `JigumoNest` | none | none | none | none | never placed | never placed |
| 71 | `UmiMushi` Ranging Bloyster | 76 | `BDT_Boss` | 1500 | 15, 3 to 6 | yakushima_3:7, last_2:7 | none |
| 100 | `UmiMushiBase` | none | `BDT_Boss` | none | none | never placed | never placed |
| 101 | `UmiMushiBlind` Toady Bloyster | 40 | `BDT_Strong` | 1000 (`fp12`) | 10, 3 to 6 | none | Perplexing Pool initgen |

Held treasures: the Wollywog carries a green diamond in `last_1` and a coin in
`forest_3`, the Yellow Wollywog a dairy lid in `yakushima_1`, the Crawmad a
chocolate in `yakushima_1`, the Ranging Bloyster the Amplified Amplifier in
`yakushima_3` and a green ring in `last_2`; Challenge caves hand all of them keys
and medals. Both Wollywogs carry `EFlag_CanAppearDayEnd` with a day-end maximum
of 4. Assets: `enemy/data/<Internal>` for each spawnable ID; the Crawmad's burrow
model comes from `enemy/data/JigumoHouse`, and the Bloysters share
`enemy/data/UmiMushi` with a single parameter directory.

## Aliases and the unspawnable base

- **`JigumoNest` (64)** is an enum-only ID: no registry row and no manager case.
  `getEnemyResName` remaps it (and `PanModokiNest`) to `PanHouse` before any
  lookup (`enemyInfo.cpp:168-175`). Nothing spawns it; the burrow is created by
  the Crawmad itself.
- **`UmiMushiBase` (100)** is the manager and resource identity of one shared
  class. There is only `UmiMushi::Obj`; the two spawnable rows set
  `parentID = UmiMushiBase` without `EFlag_UseOwnID`, so both resolve to it
  (`enemyInfo.cpp:102-104`, `generalEnemyMgr.cpp:450`). `Mgr::createObj` stamps a
  per-slot `mBloysterType` from the counts of IDs 71 and 101; the base row lacks
  `EFlag_CanBeSpawned`, has no generator (`genEnemy.cpp:591`) and leaves the type
  field uninitialised, which is why spawning it crashes.

## Wollywogs (`Frog`, `MaroFrog`)

Files: `include/Game/Entities/{Frog,MaroFrog}.h`, `src/plugProjectNishimuraU/Frog*.cpp`,
`MaroFrog*.cpp`. `MaroFrog::Obj` inherits `Frog::Obj` and overrides only the type ID
and `attackNaviPosition`, which re-aims the jump at any captain inside the attack
cone (`MaroFrog.cpp:21-33`); every other difference is disc data.

- **States** (`Frog.h:24`): Dead, Wait, Turn, Jump, JumpWait, Fall, Attack, Fail,
  TurnToHome, GoHome. Wait sees the nearest Pikmin or captain within `mSightRadius`
  (360 *disc*) and jumps when it is inside `mMaxAttackRange` (200 / 250 *disc*)
  and `mMaxAttackAngle` (30); otherwise it turns. Stuck Pikmin trigger a vertical
  jump; with Pikmin attached the jump fails with `mJumpFailChance` (0.2 / 0.1
  *disc*).
- **Jump arc** (`Frog.cpp:354-367`, `:72-105`): take-off velocity `mJumpSpeed` (400,
  320 / 350 *disc*) upward with horizontal speed set to reach the target in
  `mAirTime` (1.5, 1.0 *disc*); it steers toward the target only while ascending,
  hangs untargetable at the apex, then falls at `mFallSpeed` (300 / 330 *disc*).
  Jump key 2 shoves nearby captains and Pikmin with zero knockback.
- **Crush.** While falling, any grounded captain or Pikmin it touches is pressed
  with `mAttackDamage` (10 / 20 *disc*) (`collisionCallback`, `Frog.cpp:177-194`);
  landing shakes stuck Pikmin off and plays the splash or dust effect, camera
  vibration and rumble. There is no landing shockwave flick.
- **Damage** is the enemy base rule; it cannot be crushed. It is untargetable
  from take-off to the apex and targetable again during the fall. Petrification
  mid-jump returns it to Turn. Water only changes effects and sounds; both
  Wollywogs move freely between land and water. GoHome hops toward home and
  relocates home if stuck for 7.5 s.
- **Animation keys** (`frog`/`marofrog`): `move1` 0:0 4:2 28:3 34:1; `waitact1`
  10:0 29:1; `type1` (jump) 8:2; `wait2` 18:0 19:1; `dead` 67:2; `type5` 10:0
  29:1; `wait1`, `waitact2`, `type2`, `attack`, `damage` end only.

## Water Dumple (`Catfish`)

Files: `include/Game/Entities/Catfish.h`, `src/plugProjectNishimuraU/Catfish*.cpp`,
behavior from `KochappyBase` (`src/plugProjectYamashitaU/kochappyState.cpp`).

- A Dwarf Bulborb variant: the same Wait, Turn, Walk, Attack, Flick, TurnToHome,
  GoHome, Press and Demo states, pursuit within `mSearchDistance` (200 *disc*) and
  `mTerritoryRadius` (280), attack at `mMaxAttackRange` (50). Differences: two
  mouth slots on `kamu1`/`kamu2` (radius 20, `Catfish.cpp:83-92`) instead of one, a
  press deals damage instead of the instant Dwarf Bulborb kill (`:60-64`), and the
  shadow hangs from `kosi`.
- **No water logic exists.** Neither the Dumple nor its base reads the water box;
  its pond confinement comes from placement and territory radius alone. Water
  callbacks are stubbed, so it makes no splash. Attack key 2 bites captains for
  `mAttackDamage` (10) and eats, key 3 swallows with poison 300.
- **Animation keys**: `attack` 17:2 75:3; `flick` 25:2 47:3; `move1` 0:0 24:1;
  `wait1` 0:0 29:1; `type5` 10:0 29:1; `dead`, `waitact2` end only.

## Wogpole (`Tadpole`)

Files: `include/Game/Entities/Tadpole.h`, `src/plugProjectNishimuraU/Tadpole*.cpp`.
States (`Tadpole.h:19`): Dead, Wait, Move, Amaze, Escape, Leap.

- Harmless: no attack or eat code. It mills around home inside `mTerritoryRadius`
  (200 *disc*) and, on seeing a captain within `mSightRadius` (200; Pikmin are
  ignored), startles (Amaze key 2 flicks nearby Pikmin with the shake
  parameters) and swims directly away, clamped to the territory circle. Schooling
  is emergent from shared home points; there is no flock code.
- Out of water it enters Leap: flops at `mPitterPatterMoveSpeed` (20) with random
  yaw until it lands back in water. A purple pound is an instant kill
  (`Tadpole.cpp:99-107`); ordinary presses do nothing. It never turns into a
  Wollywog: no such code or child row exists. Normal carcass, `BDT_Weak`.
- **Animation keys**: `wait1` 5:0 24:1; `move1` 5:0 14:1; `waitact1` (startle)
  3:2 12:3; `piti1` (flop) 14:2 15:0 29:3 30:4 44:1; `dead` 3:2 17:2; `type5`
  10:0 29:1.

## Hermit Crawmad (`Jigumo`)

Files: `include/Game/Entities/Jigumo.h`, `src/plugProjectMorimuraU/jigumo*.cpp`,
nest in `enemyNest*.cpp`. States (`Jigumo.h:36`): Wait, Appear, Hide, Dead, Attack,
Miss, Return, Carry, Flick, Eat, Search, SAttack, SMiss.

- **Burrow.** At birth it asks the `PanHouse` manager for a nest at its own
  position, sets the nest type to Crawmad so it draws the `JigumoHouse` model,
  and scales it with its random size roll (`jigumo.cpp:78-97`). The nest is
  inert; on the Crawmad's death it fades out and is killed (`enemyNestMgr.cpp:133`).
  It surfaces after `mHidingTime` `ip01` (30 s) only when a captain or Pikmin is
  inside `mTerritoryRadius` (400 *disc*), and burrows again with no target.
- **Attacks.** Search turns toward the nearest Pikmin or captain; inside
  `mAttackRadius` (200 *disc*) it snaps in place (`SAttack`, eats at frame 13),
  otherwise it lunges (`Attack`) at `mMoveSpeed` (300 *disc*) with doubled
  velocity for the first tenth of the animation, biting captains for
  `mAttackDamage` (10) and grabbing one Pikmin into its single `kamu_joint1`
  slot; grounded Pikmin only. Caught Pikmin are dragged home backward at
  `mCarrySpeed` (100, 75 *disc*) and swallowed with poison 300; a miss retreats
  at `mReturnSpeed` (100, 30 *disc*).
- **Vulnerability.** Damage registers only during Carry and Return, and only if
  the attacker is nearer the `body` sphere than the `head` (`jigumo.cpp:325-356`);
  `body` is the sole stickable part while outside. Shake-off thresholds *disc*
  are 25/30/30/30 blows, so shedding happens mostly at the scripted flicks when
  it burrows. Petrifying a burrowed Crawmad makes it hittable. Water swaps the
  dust and splash effects and the attack sound.
- **Animation keys**: `appear1` 10:2; `attack1` 26:2; `backrun1` 10:0 19:1;
  `backwait1` 0:0 9:1; `dive1` 23:2 28:3 33:4 38:5 43:6 59:7 80:8; `flick1` 9:2
  16:3; `rflick1` 14:2 21:3; `runaway1` 0:0 19:1; `sattack1` 15:2 26:3 56:4 61:5
  66:6 71:7 76:8 91:9 115:10; `turn1` 0:0 14:1; `wait1` 0:0 29:1; `dead1` 24:2;
  `type5` 10:0 29:1.

## Bloysters (`UmiMushi`, `UmiMushiBlind`)

Files: `include/Game/Entities/UmiMushi.h`, `src/plugProjectMorimuraU/umiMushi*.cpp`,
`src/plugProjectNishimuraU/UmimushiShadow.cpp`. One class; the Toady variant is
selected by `mBloysterType` and gets half scale, `fp12` health, reduced turn rate
(`mBlindTurnRateReduction` 0.3), move and wait intervals `fp13`/`fp14` (200 each)
and no captain tracking (`umiMushi.cpp:48-63`, `157-174`, `843-847`).

- **States** (`UmiMushi.h:57`): Wait, Walk, Find, Search, Turn, Flick, Attack, Eat,
  Dead, Lost. Walk roams to random points on the territory ring (`mTerritoryRadius`
  300 / 500 *disc*, `mCaveTerritory` `fp10` 200 in caves) with a sinusoidal weave;
  Search slides straight toward the target at `fp04` (10, 30 *disc*).
- **Dual-captain targeting** (Ranging only, `isChangeNavi`, `umiMushi.cpp:843-886`):
  in single player it locks onto the active captain, in two player the nearest
  captain within `mSearchDistance` (400 *disc*) with 1.2× hysteresis; a change
  plays the Find animation and crossfades the tail material and eye effects to
  red for Olimar or blue for Louie. The Toady Bloyster never tracks a captain but
  still bites one that wanders into its cone. Both also chase the nearest Pikmin.
- **Attack.** Inside `mAttackRadius` (170 *disc*) and `mAttackHitAngle` (30) it
  licks: key 3 opens the tongue, `eatPikmin` fills up to seven `kamu_joint` slots
  (radius 30 / 25), key 5 damages captains in a slot, key 6 flicks; Eat swallows
  with poison 300. After an attack it waits `mWaitTimeAfterAttack` `ip01` (100).
- **Weak point.** Full damage only from a Pikmin stuck to a part (the `weak` bulb,
  the sole stickable part, scaled by `mTailScale` 1.4); part-less hits are scaled
  by `mDamageRate` `fp01` (1.0, 0.03 *disc*) and rejected above 50 units.
  Purple pounds and presses are scaled by `mPurpleDamageRate` `fp09` (0.0, 0.05
  *disc*). Stone marks `head`, `kuti` and `ketu` stickable. `applyImpulse` is a
  no-op.
- **Boss classing.** Both IDs are in `IS_ENEMY_BOSS`, but the sound object comes
  from each row's own drop table: Ranging (`BDT_Boss`) gets mid-boss music and
  camera shakes, Toady (`BDT_Strong`) gets none (`enemyBase.cpp:3100-3136`).
  No death effect flag; the corpse is the `type5` carry. Speed 15 *disc*.
- **Animation keys** (`umimushi`): `attack1` 25:2 39:3 40:4 50:5 66:6; `dead1`
  83:2 110:3 113:4; `flick1` 9:2; `run1` 0:0 59:1; `search1` 48:2; `srun1` 0:0
  39:1; `sturn1` 0:0 39:1; `type5` 10:0 29:1; `eat1`, `outview1`, `fsearch1` end
  only.

## Dependencies a reimplementation must provide

- `PanHouse` nest manager and `JigumoHouse` model for the Crawmad; the
  `PanHouse` remap for the two nest aliases.
- Flying simulation path keyed on `EB_Untargetable` for the Wollywog jump;
  `InteractPress` on contact; water box queries for effects.
- `KochappyBase` for the Dumple; captain identity, material colour animation and
  mid-boss music for the Ranging Bloyster; tube and sphere joint shadows.

## Unknowns and decomp caveats

- The Dumple's inherited `kochappyState.cpp`, the Crawmad `walkFunc` and the
  Bloyster targeting and movement functions keep retained assembly; the Wollywog
  and Wogpole units are fully matching.
- Source oddities: the Bloyster captain damage test drops the X axis, its
  `postPikiAttack` passes true in both branches, the Toady's floor offset write
  mutates shared parameters, and the Crawmad asserts the wrong effect pointer.
- Natural runtime evidence, generated-floor nest placement and day-end Wollywog
  respawns stay with the enemy lane.
