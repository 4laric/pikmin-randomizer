# Flora, Candypops and enemy-manager scenery source audit (#171)

Source behavior audit for enemy IDs 0 `Pelplant`, 3 to 8 `BluePom`, `RedPom`,
`YellowPom`, `BlackPom`, `WhitePom`, `RandPom`, 82 `Pom`, and the seventeen plants
46 `Tanpopo`, 47 `Clover`, 48 `HikariKinoko`, 49 `Ooinu_s`, 50 `Ooinu_l`, 51 `Wakame_s`,
52 `Wakame_l`, 80 `Tukushi`, 81 `Watage`, 85 `DaiodoRed`, 86 `DaiodoGreen`, 87 `Magaret`,
88 `Nekojarashi`, 89 `Chiyogami`, 90 `Zenmai`, 91 `KareOoinu_s`, 92 `KareOoinu_l`.
Paths are relative to `native/pikmin2-research` unless they name a disc file. Numbers
marked *disc* come from `enemy/parm/enemyParms.szs` on the US GPVE01 revision 0 disc.
This is an audit, not an implementation: no actor, save or animation interface changes.

## Identity and placement

| ID | Internal | Piklopedia | Registry (`enemyInfo.cpp`) | Story caves | Surface |
|---:|---|---:|---|---|---|
| 0 | `Pelplant` Pellet Posy | 46 | line 10, `BDT_Empty`, no day-end | none (stripped from Challenge, kept in Battle: 16 layouts) | every course's day-window generators |
| 3 to 8 | Candypop Buds | 47 to 52 | lines 19 to 24, parent `Pom`, `BDT_Empty` | 51 floor rosters (Violet 17, Ivory 16, Queen 11, Lapis 3, Crimson 3, Golden 1) | none |
| 82 | `Pom` base | none | line 18, no `CanBeSpawned` | never placed | never placed |
| 46, 47, 48, 50, 52, 80, 81, 85, 87, 88, 90 | plants with entries | 59 to 69 | lines 70 to 86, `BDT_Empty` | type-6 plant rosters | `plantsgen.txt` per course |
| 49, 51, 86, 89, 91, 92 | variants and paper | none (`EFlag_HasNoInfo`) | same block | `Chiyogami` in `yakushima_2` floor 2; glowstem green on 17 floors | figworts, shoots, foxtail in `plantsgen.txt` |

The paper decoration `Chiyogami` is placed in retail (Shower Room floor 2, type 6),
so it is used content, not scenery-only. Assets: every ID except the six colour
buds has its own `enemy/data` directory; the buds all point at `Pom` for model,
animation, parameters and collision (`enemyInfo.cpp:18-24`).

## Pellet Posy (`Pelplant`)

Files: `include/Game/Entities/Pelplant.h`, `src/plugProjectYamashitaU/pelplant*.cpp`.
States (`Pelplant.h:37`): WaitSmall, WaitMiddle, WaitFull, GrowSmallMid, GrowMidFull,
Damage, Dead and three Wither blends.

- **Growth** is a seconds timer: small to middle after `fp01` (120 header, 90 *disc*),
  middle to full after `fp02` (120, 60 *disc*), advancing only while the Growing
  flag is set; a farm interaction (`farmCallBack`, the only enemy implementing it)
  can force growth or withering. Battle mode starts posies pre-grown. Pellet size
  1, 5, 10 or 20 comes from the generator; sizes 10 and 20 use the `bgrow1`
  animation, while `bdamage1` and `bdead1` are unreachable in code.
- **Colour** is fixed by the generator or, with the random setting, cycles every
  `fp03` (1.5 s) through Blue, Red, Yellow skipping colours not yet met. **No code
  makes the flower follow the attacking Pikmin's colour**; the cycle is purely
  time based (`pelplant.cpp:407-450`).
- **Harvest.** Only a full posy takes damage (health 50 *disc*); the dead state
  releases the captured pellet instead of destroying it. A collision part whose
  special code ends in `0` (the `head`, `s__0` on disc) fells it instantly when a
  Pikmin latches (`pelplant.cpp:485`, `:518`). There is no regrowth timer; a new
  posy is a generator respawn. Invulnerable while small or growing, bitter-immune,
  no corpse, no death effect, no sounds in source. The Piklopedia hides its value
  and loss counters.
- **Animation keys** (`pelplant`): `wait1`/`wait2`/`wait3` 0:0 29:1; the grow,
  damage and dead clips have no keys.

## Candypop Buds (`Pom` family)

Files: `include/Game/Entities/Pom.h`, `src/plugProjectNishimuraU/Pom*.cpp`. One class
whose instance type is stamped per slot from the counts of the six colour IDs
(`PomMgr.cpp:96-109`); the base ID 82 gets no slot, no generator and an
uninitialised colour, which is why it cannot be spawned.

- **Cycle** (`Pom.h:120`): Wait (one frame) to Open; the open animation's key 2
  at frame 25 arms it; a touch starts Swing; it closes after `mRemainOpenTime`
  `fp01` (30 header, 1.0 *disc*) since the last swallow or when the budget is
  used; Close goes to Shot if Pikmin are inside, else reopens; Shot key 2 at frame
  20 spits, then reopens or dies.
- **Conversion.** Pikmin enter only through a press on the `slot` part (radius 30)
  while armed (`Pom.cpp:154-169`); any colour is accepted. Capacity is a lifetime
  budget: `mNormalMaxSlots` `ip01` (5) for colour buds, `mQueenMaxSlots` `ip11` (1)
  for the Queen, and throwing in the bud's own colour refunds the slot
  (`:296-298`). Each stuck Pikmin is killed without counting as a loss and
  replaced by sprouts of the bud colour: one per Pikmin, or `ip13` (5 header,
  9 *disc*) per Pikmin for the Queen, launched at (110, 750, 110) with random
  bearing as **leaf** Pikihead sprouts. Bulbmin convert too but are not removed
  from the birth counters. `ip02`, `ip12` and `fp03` are unread.
- **Queen colour** cycles Blue, Red, Yellow every `fp02` (1.25 header, 2.6 *disc*)
  skipping unmet colours; it is not random.
- **Spawn gating in story caves** (`PomMgr.cpp:38-89`): Violet and Ivory buds refuse
  to spawn on floors 1 to 2 (or in Emergence Cave and White Flower Garden) when
  the player already has 20 of that colour; Ivory needs Whites met except in White
  Flower Garden; Lapis and Golden need their colour met. Dropped buds land exactly
  on their point (excluded from the drop jitter) and become invulnerable once they
  land. Bitter-immune, no shadow, no corpse; death only from an exhausted budget.
  The Piklopedia hides all counters. Cutscenes for the first Violet and Ivory bud
  use a 350 unit trigger (`navi_demoCheck.cpp:42`).
- **Animation keys** (`pom`): `type1` (open) 25:2; `type3` (shot) 20:2; `wait`,
  `dead`, `type2`, `type4` end only.

## Enemy-manager plants (seventeen IDs)

Files: `include/Game/plantsMgr.h`, `src/plugProjectMorimuraU/plants*.cpp`. One base
`Plants::Obj` with an empty subclass per species; no shared resources. Each plant
has a single animation clip.

- **Behavior.** Invulnerable, bitter-immune, no corpse, constrained; the disc
  health of 1100 is never read. A captain or Pikmin moving faster than 1 unit
  past the collision file's volume plays the sway clip (`collisionCallback`,
  `plants.cpp:141-166`); only captains trigger the touch sound (`PSSE_PL_TOUCH_LEAF`,
  glowcap and glowstems have their own). Purple quakes also sway them. Enemies
  pass through. The general parameters are repurposed as LOD volumes: territory
  lifts the sphere; private and home radius define cylinders for the paper,
  glowstems, glowcap, foxtail, horsetail, shoots and fiddlehead. The `fp01`
  values on Clover and the brown figworts (25 / 45 / 20 *disc*) are the general
  floor offset, not a plant parameter.
- **Spectralids.** A plant whose generator carries the Spectralid pellet sentinel
  spawns five yellow Spectralids on its first touch (`plants.cpp:187-201`). Only
  `Tanpopo`, `Ooinu_l` and `Magaret` declare that child so slots are reserved
  (`enemyInfo.cpp:70,76,83`, `generalEnemyMgr.cpp:818-838`); any other species so
  configured would spawn without a reservation. The seeding dandelion also
  releases its seed effect.
- **Piklopedia.** Eleven entries (59 to 69) registered by finishing a sway;
  `Ooinu_s`, `Wakame_s`, `DaiodoGreen`, `Chiyogami` and both brown figworts carry
  `EFlag_HasNoInfo` and are represented by their large, red or green sibling.
  All plant entries hide all three counters.
- **Placement.** Cave type 6 rosters treat the weight as a target count consumed
  in order across free plant spawn points, capped at 100 (`RandPlantUnit.cpp`);
  the surface reads `plantsgen.txt` per course after `defaultgen.txt`
  (`baseGameSection.cpp:660-677`). None appears at day end.

## Dependencies a reimplementation must provide

- Pellet number births and capture on the posy head, farm interactions, the
  generator's colour, size and state bytes.
- Pikihead sprout births, birth counters, per-colour cave gating, the Spectralid
  plant group and the plant spawn sentinel.
- Plant generator files, cave plant placement, LOD cylinders and touch sounds.

## Unknowns and decomp caveats

- All three plant units, the Pom units and the Pellet Posy units are fully
  matching; the posy's `setPelletColor` and the Queen's colour selection index
  the same table by value and index, which only works because the first three
  entries equal their index.
- Enemy ID 0 doubles as the "unset" enemy type in generators and the cave info
  defaults, so remapping the Pellet Posy ID would break those conventions.
- Natural runtime evidence, Onion-side seed behavior and Battle posy balancing
  stay with the species and mode lanes.
