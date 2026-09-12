# Reward beetles, Breadbugs, nests and Mamuta source audit (#168)

Source behavior audit for enemy IDs 9 `Kogane`, 10 `Wealthy`, 11 `Fart`,
38 `PanModoki`, 39 `PanModokiNest`, 40 `OoPanModoki`, 54 `Miulin` and 83 `PanHouse`.
Paths are relative to `native/pikmin2-research` unless they name a disc file.
Numbers marked *disc* come from `enemy/parm/enemyParms.szs` on the US GPVE01
revision 0 disc and override the header defaults quoted next to them. This is an
audit, not an implementation: no actor, save or animation interface changes.

## Identity, placement and carcass

| ID | Internal | Piklopedia | Drop table | Health *disc* | Carcass (pokos, carry) | Story caves (floors) | Surface generators |
|---:|---|---:|---|---:|---|---|---|
| 9 | `Kogane` Iridescent Flint Beetle | 20 | `BDT_Empty` | 1000 | none | last_1:5, last_2:12, last_3:9, yakushima_1:5 | Awakening Wood initgen |
| 10 | `Wealthy` Iridescent Glint Beetle | 21 | `BDT_Empty` | 1200 | none | forest_3:4, tutorial_3:7, yakushima_4:4, last_2:5 and 12, last_3:9 | Awakening Wood initgen |
| 11 | `Fart` Doodlebug | 22 | `BDT_Empty` | 1500 | none | tutorial_3:1, yakushima_3:6, last_2:8 and 12, last_3:9 | none |
| 38 | `PanModoki` Breadbug | 57 | `BDT_Empty` | 1100 | 3, 3 to 6 | yakushima_2:2, 3, 4 and 6, last_3:11 | none |
| 39 | `PanModokiNest` | none | none | none | none | never placed | never placed |
| 40 | `OoPanModoki` Giant Breadbug | 77 | `BDT_Empty` | 2000 | 10, 10 to 20 | yakushima_2:6 (type 8) | none |
| 54 | `Miulin` Mamuta | 58 | `BDT_Strong` | 500 | 3, 7 to 15 | tutorial_3:5, last_1:3, last_2:5 | none |
| 83 | `PanHouse` Breadbug Nest | none (`EFlag_HasNoInfo`) | `BDT_Empty` | 1100 (inert) | none | never placed | never placed |

Held treasures: the Glint Beetle carries treasures on four story floors (a
crystal, a green block, a white chocolate and more), the Flint Beetle and
Doodlebug carry keys and medals in Challenge caves, the Giant Breadbug carries the
Dream Material in `yakushima_2` and the Key in `ch_MIYA_oopan`, the Mamuta the
Brute Knuckles in `tutorial_3`. None of the eight is a day-end spawner.
`OoPanModoki` is in `IS_ENEMY_BOSS` (`include/Game/enemyInfo.h:214`). Assets:
`enemy/data/Kogane` supplies the model, animations and collision for all three
beetles (registry rows name `Kogane` as donor, `enemyInfo.cpp:25-27`); each beetle
has only its own texture. `PanModokiNest` (39) is enum-only and remapped to
`PanHouse` by `getEnemyResName` (`enemyInfo.cpp:168-175`).

## Reward beetles (`Kogane`, `Wealthy`, `Fart`)

Files: `include/Game/Entities/{Kogane,Koganemushi,Wealthy,Fart}.h`,
`src/plugProjectNishimuraU/Kogane*.cpp`, `Koganemushi*.cpp`, `Wealthy*.cpp`,
`Fart*.cpp`. One base class `Kogane::Obj`; the three subclasses differ only in
material colour, the drop table and the hit sound.

- **States** (`Kogane.h:166`): Appear, Disappear, Move, Wait, Press. Hidden until a
  captain or Pikmin is within `mSightRadius` (50 *disc*), then it scales up, runs
  at `mMoveSpeed` (200 *disc*) with a random heading change of ±`mTurnAngle`
  `fp30` (45, 90 *disc*) each Move, bouncing off walls, alternating Move
  (`fp10`/`fp11`) and Wait (`fp20`/`fp21`). Surface time runs from `mMinAppearTime`
  `fp01` to `mMaxAppearTime` `fp02` (15 / 30 header; *disc* 20 / 30 Flint, 10 / 20
  Glint, 15 / 30 Doodlebug) then it dives. Minimum timers only shrink the random
  span. Scale `fp40` 0.8 (0.7 to 0.8 *disc*).
- **Hits and loot** (`KoganeState.cpp:226-268`, `Koganemushi.cpp:53`, `Wealthy.cpp:52`,
  `Fart.cpp:116`). A hit is a Pikmin press, hip drop or purple pound landing on it
  while moving or waiting; each enters Press and drops once at key 3. The table
  is deterministic by hit count:

  | Hit | Flint Beetle | Glint Beetle | Doodlebug |
  |---:|---|---|---|
  | 1 | one 1-pellet (cave: one nectar) | three 5-pellets (cave: three nectar) | three nectar |
  | 2 | two nectar | one spicy drop if spicy spray unlocked, else three nectar | one bitter drop if bitter spray unlocked, else three nectar |
  | 3 | one spicy drop if unlocked, else three nectar; then burrows | as hit 2; then burrows | as hit 2; then burrows |

  A beetle carrying a roster treasure instead drops it on the first hit and
  burrows (`createTreasureItem`, `Kogane.cpp:386-414`). Pellet colours are chosen
  among met Pikmin colours and fanned over 120°.
- **Invulnerable.** `EB_Invulnerable` is set at init; only while petrified does
  damage apply (`Kogane.cpp:188-206`, `230-234`), so a bittered beetle can be
  shattered. No carcass, no death effect, `BDT_Empty`: a shattered beetle drops
  nothing. Bitter-immune while hidden and diving.
- **Doodlebug gas.** Each Move entry drops a gas cloud behind it at
  `fp40 × mMaxAttackRange` (50 *disc*) for 2.5 s, applying `InteractGas(mAttackDamage)`
  (0 *disc*) to captains and Pikmin within `mAttackRadius` (20 *disc*) every
  frame (`Fart.cpp:76-110`); it plays `PSSE_EN_FART_BUZZ` while surfaced.
- **Despawn.** The dive kills the object without a corpse; in a cave a treasure
  beetle that was never hit instead relocates to a fresh base position and
  re-hides. The Piklopedia hides poko and loss counters (loss only for the
  Doodlebug).
- **Animation keys** (`kogane`, shared): `move` 2:0 11:1; `wait` 0:0 14:1; `damage`
  5:2 7:3 29:4.

## Breadbugs and nest (`PanModoki`, `OoPanModoki`, `PanHouse`)

Files: `include/Game/Entities/{PanModokiBase,PanModoki,OoPanModoki,Nest}.h`,
`src/plugProjectMorimuraU/panModoki*.cpp`, `enemyNest*.cpp`. One base
`PanModokiBase::Obj`; the small Breadbug takes items whose minimum carriers are
below `mMaxCarryWeight` `ip01` (5 header, 11 *disc*), the Giant takes items at or
above it (1 *disc*), and the Giant is stunned only by Purple pounds and uses
larger carry and shadow sizes (`OoPanModoki.h:16-21`, `panModoki.cpp:1707-1744`).

- **Nest.** Each Breadbug births its own `PanHouse` nest at its spawn point,
  scaled by `mNestScale` `fp00` (1.0 / 2.0 *disc*) (`panModoki.cpp:54-75`). The nest
  is an inert prop (no update, no collision reaction, bitter-immune, no
  Piklopedia) that fades out and dies with its owner (`enemyNestMgr.cpp:130-144`).
  Its disc health is never read. The registry declares it as a child of both
  Breadbugs so a slot is reserved.
- **States** (`PanModokiBase.h:29`): Dead, Walk, Back, Pulled, Appear, Hide, Damage,
  Wait, Stick, Sucked, CarryEnd. Walk path-finds and searches for pellets within
  `mSearchDistance` (200 / 100 *disc*) and `mSearchAngle`; Stick grabs the whole
  item in the special slot 9999 and Back hauls it home along a route at
  `mCarrySpeed` `fp03` (10 header, 45 *disc*); CarryEnd eases into the nest and Hide
  consumes the item after `mHideTime` `fp15` (50, 150 *disc*) and **restores full
  health**; Wait lasts `mWaitTime` `fp14` (20, 0 *disc*).
- **Contest.** Steals go through `PelletCarry`: Pikmin pull with their carrier
  count, the Breadbug with `(min + max) / 2` of the item's config; the stronger side
  owns the item and a steal freezes it for half a second (`pelletCarry.cpp:30-98`).
  While out-pulled it sits in Pulled with smoke; when it wins it resumes Back.
  Targets exclude upgrades, captured pellets, items marked not Breadbug-carryable
  (`code` bit 1), items another enemy holds, captain corpses, and treasures once
  it holds 15 (`panModoki.cpp:1047-1088`, `1532-1564`).
- **What the nest keeps.** `endCarry` kills any Pikmin still on the item; the first
  treasure is captured visibly in the nest, further treasures are stored and every
  other item (pellets, carcasses) is destroyed (`panModoki.cpp:1322-1357`). On
  death all stored treasures are re-born and thrown from the nest
  (`throwUpEatItem`, `:1659-1697`). **There is no Giant Breadbug scoring code**: the
  only Giant-specific cargo rule is the inverted weight class; being boss-classed
  only gives its own death drop the last-floor squad weight rule.
- **Damage.** Pikmin attacks do nothing (`damageCallBack` only forwards while
  petrified). Presses and pounds from Walk, Wait, Stick, Back or Pulled enter
  Damage for `mPressDamage` `fp06` (10, 100 *disc*), dropping the item. An item it
  holds being sucked into the Onion or ship drags it along (`InteractSuckFinish`,
  `panModoki.cpp:22-32`); the landing enters Damage with `mSuckDamage` `fp04`
  (10, 1000 *disc*), which kills the small Breadbug outright (health 1100) and
  halves the Giant (2000). Stone drops the item and makes the body stickable.
  Normal carcass (`type5`); `BDT_Empty` means no boss music despite the boss macro.
- **Animation keys** (`panmodoki`/`oopanmodoki`): `move1`, `move2` 10:0 39:1;
  `type1` (pulled) 5:0 10:1; `type3` (hide) 20:2; `type5` 10:0 29:1; `wait1` 10:0
  49:1; `type2`, `type4` end only; `dead` 70:2 (Giant).

## Mamuta (`Miulin`)

Files: `include/Game/Entities/Miulin.h`, `src/plugProjectMorimuraU/miulin*.cpp`.
States (`Miulin.h:20`): Wait, Walk, AttackStart, Attacking, AttackEnd, Turn, Flick,
Dead.

- **Targeting.** It searches with `mSearchAngle`/`mSearchDistance` (200 *disc*),
  widens to 180° when a captain or Pikmin enters `mPrivateRadius` (50) or health
  drops below the alert line, returns home after `mReturnTime` `ip01` (100, 200
  *disc*) frames of fruitless chasing, and dashes at `mDashSpeedMultiplier` `fp04`
  (2.0, 3.0 *disc*) inside `mDashableAngle` `fp07` (30). The pound starts only when a
  Pikmin sits in a ring around `mMinAttackRange` `fp08` (25) within
  `mContinuousPressAngle` `fp03` (20) (`miulin.cpp:170-214`), and re-pounds while
  that holds.
- **Pound** (`miulinState.cpp:264-330`). Key 2 of `attack1` hits a cylinder
  `fp08` ahead of radius `mAttackRadius` (40 *disc*): every Pikmin inside is
  replanted as a sprout of its own colour at flower maturity and the original is
  killed without counting as a death (`InteractBury`, `interactPiki.cpp:377-416`);
  it fails only on bald ground or at the 99 Pikmin cap. Captains take 5 damage.
  The same key shakes off stuck Pikmin and flicks nearby captains and Pikmin.
- **Damage** uses the enemy base; flick thresholds *disc* are 1/2/5/10 blows at
  1/2/3 stuck (cannot interrupt a pound). Immune to knockback impulses. Health 500
  *disc*, speed 30. Collision parts from the disc file: `body` 45 root and a
  stickable `body` 26, feet `asil`/`asir`, hands `tel1`/`ter1`. Normal carcass
  (`type5`), `BDT_Strong`, held treasure released by `deathProcedure`.
- **Spectralids.** At birth it spawns five Spectralids that perch on it and rest,
  purely decorative (`miulin.cpp:27-39`).
- **Animation keys** (`miulin`): `attack1` 0:2 4:3; `flick` 15:2 25:3 (the FSM only
  reads key 3); `move` 13:0 42:1; `wait` 13:0 72:1; `waitact` 0:0 29:1; `dead`
  27:2; `type5` 10:0 29:1; `attack0`, `attack4` end only.

## Dependencies a reimplementation must provide

- Pellet births by colour, `ItemHoney` births, treasure re-birth from config
  names, the spray-unlock demo flags, and cave base-generator relocation for
  beetles.
- `PelletCarry` contest state, whole-object stick slot 9999, `Pellet::startPick`
  and `panmodokiCarryable`, route path-finding to a home waypoint, capture
  matrices for the nest display copy, `InteractSuckFinish` from the pellet goal
  state, the `PanHouse` manager with both house models.
- `InteractBury` with Pikihead births at flower maturity and the Spectralid
  enemy-rest group.

## Unknowns and decomp caveats

- `Kogane.cpp` is only "equivalent" (`createPellet` keeps retained assembly);
  `updateCaptureMatrix` of the Breadbugs, and the Mamuta `isAttackStart` and
  `nextTargetTurnCheck`, keep retained assembly.
- Source oddities: the Breadbug `hipdropCallBack` has no return value, the nest
  draw is flagged for register swaps, the Mamuta passes an uninitialised position
  to the second pound rumble, and the pellet colour pick indexes a default table
  when no Pikmin colour has been met.
- The issue title's "Giant Breadbug scoring" has no counterpart in source; only
  the weight-class inversion distinguishes the Giant's cargo handling.
- Natural runtime evidence, Onion-suck stuns and generated-floor nest placement
  stay with the enemy and cargo lanes.
