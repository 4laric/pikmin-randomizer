# Pikmin 2 aquatic enemy source audit (#167)

Implementation owner: Codex using shared account 4laric. This is a source audit
only. It records what the checked-in decompilation establishes, not replacement
compatibility, successful native spawning in every generator, route safety,
carcass delivery, drops, or a completed gameplay sign-off.

**Scope and evidence.** Reviewed `projectPiki/pikmin2` at
`632af93787b9c95b63f0c13be32b161375ce3a96` (randomizer integration base
`93ad07f505f78c097757a5c5355dbf518bdde786`). The IDs and display identities are
declared in `include/Game/enemyInfo.h:76-86,122-123,130,159-160`. Live C++ was
read through the named functions below; large commented-out assembly blocks were
not treated as a second implementation. “Drop” in the Frog method names is an
effect/state term here, not evidence of loot.

Source paths below are relative to the decompilation checkout. Bare Frog, MaroFrog, Catfish, and Tadpole filenames are under `src/plugProjectNishimuraU/`; Jigumo and UmiMushi files are under `src/plugProjectMorimuraU/`; `enemyInfo.cpp`, `genEnemy.cpp`, and `generalEnemyMgr.cpp` are under `src/plugProjectYamashitaU/`.

## Registration, concrete classes, and aliases

`GeneralEnemyMgr` creates distinct managers for Frog, MaroFrog, Catfish,
Tadpole, and Jigumo at `src/plugProjectYamashitaU/generalEnemyMgr.cpp:241,256,
292,295,424`. It registers only `EnemyID_UmiMushiBase` at line 450. The generator
name dispatch nevertheless accepts the eight concrete generator IDs, including
JigumoNest and both Bloysters, at `genEnemy.cpp:495-573`; its base-ID case is
separate at line 591. That proves parser coverage, not a safe direct base spawn.

The data table says Frog 17 and MaroFrog 18 are independently spawnable and
day-end eligible (`enemyInfo.cpp:28-29`), while Catfish 26 and Tadpole 27 are
spawnable (`:49-50`). Jigumo 63 is spawnable and advertises PanHouse as one child
(`:100`). `enemyInfo.cpp:168` maps JigumoNest 64 to PanHouse only when resolving
the resource name; it has no independent table row. It must therefore not be
treated as an ordinary independent enemy. UmiMushiBase 100 has `EFlag_UseOwnID`
but lacks `EFlag_CanBeSpawned`; the header comment labels it “Bloyster base
(crashes),” which is a decomp annotation rather than reproduced runtime proof.
UmiMushi 71 and UmiMushiBlind 101 inherit its asset entry and are
marked spawnable (`enemyInfo.cpp:102-104`). Direct ID 100 generation is therefore
excluded from direct generation by this audit.

MaroFrog is a concrete subclass of `Frog::Obj` (`include/Game/Entities/MaroFrog.h:12`),
with its own manager allocating `Frog::Parms` and `MaroFrog::Obj`
(`MaroFrogMgr.cpp:20,29`). It shares Frog code but retains its own type ID, so it
is not an interchangeable table alias. Catfish is `KochappyBase::Obj` rather
than a new aquatic FSM: `Catfish::Obj::onInit` delegates to that base at
`Catfish.cpp:23`; it adds the `kosi` shadow joint, two mouth slots (`kamu1`,
`kamu2`) of radius 20 (`:83`), and press damage forwarding (`:63`). The base
Kochappy behavior remains an unresolved source trace for this batch.

## Frog, Wollywog, and Wogpole contracts

Frog initialises the shared FSM, alert/air flags, effects, and starts in Wait
(`Frog.cpp:36`); the FSM registers ten states at `FrogState.cpp:13`. Targeting in
`StateWait::exec` (`:85`) asks `getNearestPikminOrNavi`, checks view/sight and
attack range/angle, then selects Jump. `StateJump::exec` (`:245`) performs its
flick at animation key event 2, begins the jump attack, and selects water or dry
jump sound based on `mWaterBox`. `StateFall::exec` (`:339`) waits for a floor
triangle, and `StateAttack::init` (`:362`) calls `pressOnGround`; the latter
flicks stuck Pikmin and chooses water splash/sound or land-drop effect
(`Frog.cpp:385`). Falling collision presses a grounded Navi/Pikmin only while the Frog is not bittered and `mIsFalling` is set
(`Frog.cpp:177`). Thus the trace establishes event-driven stomp/flick mechanics
and water-sensitive presentation, not that all water geometry is navigable.

Death calls `deathProcedure` then kills at the dead animation end
(`FrogState.cpp:32,45`); `Obj::onKill` only finishes its jump effect before the
base kill (`Frog.cpp:52`). No concrete loot drop has been verified in these
functions. `doStartWaitingBirthTypeDrop` / `doFinishWaitingBirthTypeDrop` merely
hide/show effects (`Frog.cpp:246,256`), so they do not establish a drop table.

Tadpole has its own six-state FSM (`TadpoleState.cpp:14`), begins Wait
(`Tadpole.cpp:32`), and targets only the nearest *Navi* in Wait/Move
(`TadpoleState.cpp:79,135`), then computes a position away from it bounded by
territory (`Tadpole.cpp:110`). Its Wait, Move, and Escape states immediately
enter Leap when `mWaterBox` is absent (`TadpoleState.cpp:79,135,242`).
`StateLeap::exec` (`:307`) ends/leaves its leaping cycle when it encounters a
water box, otherwise steers toward a random target, and emits water dive versus
dry effect at animation keys through `createLeapEffect` (`Tadpole.cpp:173`).
Hipdrop kills a live, non-bittered Tadpole by adding its entire health
(`Tadpole.cpp:89`). This is a strong placement boundary: dry placement has
specific leap fallback, but it is not proof of recoverable routing.

## Hermit Crawmad and nest ownership

`Jigumo::Obj::birth` creates a PanHouse through its manager, stores it in
`mHouse`, assigns house type from the Crawmad type, and scales it
(`jigumo.cpp:73`). It tests `nestMgr`, but after birth asserts the resulting
`nest` (`P2ASSERTLINE(86)`), so manager capacity/exhaustion is a real native
acceptance risk, not a graceful no-nest fallback. `onKill` calls the base then
`killNest`; `killNest` sets the house death timer to one and nulls the owner
reference (`:548,1737`). This is an actual owner link,
not evidence that ID 64 can be independently shuffled. The nest manager/type,
day-end reset behavior, and persistence serialization were not fully traced and
remain unresolved.

The fourteen-state FSM is registered at `jigumoState.cpp:16`. Appear/hide make
the actor constrained/inactive around its house; attack activates collision at
key 2, attacks Navis, calls `eatPikmin`, and if it catches one enters Carry
(`StateAttack::exec:314`). Carry returns to the home goal and enters Eat near
it (`StateCarry::exec:517`); Eat calls `swallowPikmin(enemy, 300.0f, nullptr)`
at key 8 then hides (`StateEat::exec:648`). Short attack has the analogous
swallow at key 10 (`StateSAttack::exec:792`). Its damage callback only permits
normal damage in Carry/Return and rejects hits closer to head than body
(`jigumo.cpp:325`); it also distinguishes water/soil attack effects by
`mWaterBox`. `outWaterCallback` delegates to base and applies gravity
(`:383`), which is a concrete dry/out-of-water behavior but not a navigation
guarantee.

## Bloyster shared base and receiver boundaries

One `UmiMushi::Mgr` allocates objects tagged first as UmiMushi then Blind based
on per-ID counts (`umiMushiMgr.cpp:86`). `Obj::onInit` (`umiMushi.cpp:94`) starts
the shared FSM in Walk. For Blind it calls `setParameters` (scale 0.5, tail
weak-point scale), overwrites health with `mBlindHealth`, and installs eye/weak
joint callbacks; ordinary UmiMushi takes the mid-boss sound path. Both initialise
seven mouth slots, radius 30 ordinary or 25 Blind (`umiMushi.cpp:552`).

The shared walk state explicitly bifurcates: Ranging Bloyster continuously uses
`walkFunc`; Toady Bloyster alternates configured move and wait timers
(`umiMushiState.cpp:130`). Captain targeting is concrete rather than assumed:
the state transitions consult `isChangeNavi`, target selection is represented by
`mTargetNavi`, and the ordinary/Blind distinction alters movement. The concrete
`Obj::isChangeNavi` helper starts at `umiMushi.cpp:843`: Blind returns false;
ordinary two-player operation chooses the nearest Navi, otherwise the active one;
an existing target expands the range by 1.2 and a live, in-range change updates
both target and goal. Its null-Navi path retains the old target. That still does
not demonstrate all caller/receiver lifetime conditions, so captain behaviour
outside these branches remains unresolved.

Weakpoint/receiver behavior is also bounded. `damageCallBack` (`umiMushi.cpp:467`)
accepts bitter damage; otherwise it asserts a source, casts it to Piki without an
explicit `isPiki` rejection, and accepts a live `isStickTo` source with a
collision part, or a live source below body height without one (then applies
`mDamageRate`). Press/hipdrop/earthquake scale Purple Pikmin damage
(`:493, :512, :531`). This does not prove a tail collision-ID rule or every
collision-part weakpoint receiver: that caller chain remains outside the reviewed
functions.
`StateAttack::exec` (`umiMushiState.cpp:510`) marks tongue activity at key 3,
uses `eatPikmin`, optionally attacks Navis at key 5 only if `mCanEatNavis`, and
flicks nearby/stuck Pikmin and Navis at key 6. `StateEat::exec` (`:606`) swallows
at animation end. Death performs `deathProcedure` and kills at end
(`:634,649`). Neither establishes a randomized loot drop or persistent reset.

## Audit disposition

These IDs are source-identified candidates only. Before enabling a swap: exercise
generator parsing and birth for every concrete ID; reject ID 100; preserve the
Jigumo-to-PanHouse ownership relation; observe water/dry anchors, stomp/swallow
receivers, captain selection, death/carcass carry, drops, day-end restore and
persistence. The incomplete Catfish base trace, Bloyster target helper/receiver
trace, nest persistence, and all physical route tests are explicit open work.

---

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
