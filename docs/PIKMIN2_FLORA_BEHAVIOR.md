# Flora and Candypop source behavior model (lane 23, #171)

Pure-Python, engine-independent behavior reference for the 25 flora identities
in the #171 audit:

- Pellet Posy `Pelplant` (enemy ID 0),
- the six Candypop Buds `BluePom` 3, `RedPom` 4, `YellowPom` 5, `BlackPom` 6,
  `WhitePom` 7, `RandPom` 8,
- the nonspawnable shared base `Pom` (82),
- the seventeen enemy-manager plants 46-52 and 80/81/85-92.

Code: `experimental/pikmin2_flora_behavior.py`.
Tests: `tests/test_pikmin2_flora_behavior.py`.
Source audit: [`docs/PIKMIN2_FLORA_AUDIT.md`](PIKMIN2_FLORA_AUDIT.md) (#171).
Asset contract: [`docs/PIKMIN2_FLORA_ASSETS.md`](PIKMIN2_FLORA_ASSETS.md) (#353).

## Scope

This slice is a **source behavior policy model only**. It encodes the audit's
facts as pure functions and constants; nothing here executes game behavior,
touches the ISO, the native build or saves, and no actor/AI/FSM is installed.
The module is import-safe and side-effect free.

Not in scope (deliberately pending):

- **Pellet capture/release on the posy head and the Onion seed reward.**
  `pellet_released_on_death` only models the dead-state release rule; the
  actual `attachPellet`/`startCapture`/`endCapture` wiring and the Onion-side
  seed accounting remain with the receiver/native lanes.
- **The native Candypop actor.** No actor install, slot reservation or
  `ItemPikihead` birth executes here.
- **Plant spawn placement** (cave type 6 rosters and surface `plantsgen.txt`).
- **Hikari camera-facing behavior** (#429).

## Identity and spawnability

`FLORA` holds all 25 IDs. `is_spawnable` returns False only for the shared base
`Pom` (82), which has no `EFlag_CanBeSpawned`, no `Mgr` slot and an
uninitialised colour, so it must never be treated as a spawnable identity
(`enemyInfo.cpp:18`, audit lines 55-58). `CLASSIFICATION` splits the roster into
`enemy_flora` (Pelplant + six buds), `prop_flora` (the seventeen plants) and
`nonspawnable_base` (`Pom`).

## Pellet Posy (`Pelplant`, ID 0)

| Fact | Value | Anchor |
|---|---|---|
| Growth small -> middle | `fp01` 90.0 disc / 120.0 header | `pelplantState.cpp:193-257`, `Pelplant.h:284` |
| Growth middle -> full | `fp02` 60.0 disc / 120.0 header | `pelplantState.cpp:193-257`, `Pelplant.h:285` |
| Random colour cycle period | `fp03` 1.5 s | `pelplant.cpp:407-450` |
| Health (full only) | 50 disc | `enemy/parm/enemyParms.szs pelplant/enemyparm.txt` |
| Pellet sizes | 1, 5, 10, 20 (10/20 use `bgrow1`) | audit lines 35-38 |
| Instant fell part | special code ending in `0` (`s__0` head) | `pelplant.cpp:485,518` |
| Regrowth timer | none | audit lines 43-49 |

Pure functions: `pellet_growth` (seconds-based, advances only while the Growing
flag is set), `pellet_is_vulnerable` (full only), `pellet_size_uses_bgrow`,
`pellet_instant_fell`, `pellet_released_on_death` (the dead state releases the
captured pellet instead of destroying it) and `pellet_colour` (generator-fixed,
or a time-based Blue/Red/Yellow cycle skipping unmet colours).

There is **no attacker-colour following** in source (`pelplant.cpp:407-450`);
`PELLET_FOLLOWS_ATTACKER_COLOUR` is `False` and `pellet_colour` takes no
attacker colour.

## Candypop Buds (`Pom` family, IDs 3-8)

One class (`Game::Pom::Obj`) whose per-slot identity is stamped from the six
colour counts (`PomMgr.cpp:95-109`). Pikmin enter only through a press on the
`slot` part (radius 30) while armed (`Pom.cpp:154-169`); any colour is accepted.
The lifetime slot budget is `ip01` (5) for colour buds and `ip11` (1) for the
Queen; throwing in a colour bud's own colour refunds the slot
(`Pom.cpp:296-298`). Each stuck Pikmin is killed without counting as a loss and
replaced by leaf `ItemPikihead` sprouts: one per Pikmin, or `ip13` (9 disc) per
Pikmin for the Queen, launched at (110, 750, 110) with random bearing. The bud
closes after `mRemainOpenTime` `fp01` (1.0 s disc / 30 header) or when the budget
is spent; Close goes to `shot` when Pikmin are inside, else reopens
(`PomState.cpp:101-235`). The Queen cycles colour Blue/Red/Yellow every `fp02`
(2.6 s disc) deterministically (`Pom.cpp:330-355`).

Pure functions: `candypop_accept`, `candypop_refund`, `candypop_close`,
`candypop_shot_count`, `candypop_budget`, `candypop_own_colour`,
`candypop_queen_colour` and `candypop_spawn_allowed`.

Story-cave spawn gating (`PomMgr.cpp:38-89`): Violet (`BlackPom`) and Ivory
(`WhitePom`) refuse floors 1-2 (or Emergence Cave / White Flower Garden) once
the player already holds 20 of that colour; Ivory additionally needs Whites met
except in White Flower Garden; Lapis (`BluePom`) and Golden (`YellowPom`) need
their colour met. Dropped buds land exactly on point (excluded from drop
jitter) and are invulnerable once landed; death only from an exhausted budget
(`POM_EXCLUDED_FROM_DROP_JITTER`, `POM_INVULNERABLE_AFTER_LANDING`). The first
Violet/Ivory cutscene uses a 350-unit trigger (`navi_demoCheck.cpp:42`).

`ip02`, `ip12` and `fp03` are serialized on disc but unread
(`POM_UNREAD_KEYS`). Header and disc values are kept separate
(`POM_PROPER_HEADER` vs `POM_PROPER_DISC`).

## Plants (IDs 46-52, 80/81, 85-92)

One `Plants::Obj` base with an empty subclass per species, separate resources
and a single `PLANTANIM_Default` clip; no FSM. Invulnerable, bitter-immune, no
corpse, and the disc health of 1100 is never read (audit lines 89-99,
`plantsMgr.h:36-39`).

- **Sway-on-touch.** A captain or Pikmin moving faster than 1 unit past the
  collision volume restarts the single clip; only captains trigger
  `PSSE_PL_TOUCH_LEAF`; Purple quakes sway them and enemies pass through
  (`plants.cpp:141-166`). Pure: `plant_sways`, `plant_touch_sound`.
- **LOD volumes.** General parameters are repurposed: territory lifts the
  sphere and private/home radius define cylinders
  (`PLANT_LOD_ROLES`, `plant_lod`).
- **Spectralid sentinels.** A generator carrying the pellet sentinel spawns five
  yellow Spectralids on the plant's first touch (`plants.cpp:187-201`). Only
  `Tanpopo`, `Ooinu_l` and `Magaret` declare the child and reserve slots
  (`enemyInfo.cpp:70,76,83`; `generalEnemyMgr.cpp:818-838`); any other species so
  configured would spawn without a reservation. Pure: `spectralid_spawn`,
  `spectralid_reserved`.
- **Piklopedia.** Eleven entries (59-69) registered by finishing a sway. The
  `EFlag_HasNoInfo` variants fold into a representative
  (`HAS_NO_INFO_FOLDED_INTO`); `Chiyogami` has no representative entry and is
  used content (Shower Room floor 2). Pure: `piklopedia_number`, `folded_into`.

## Reconstructed / approximated

`RECONSTRUCTED` marks facts the audit labels reconstructed or approximated:

- **`plant_floor_offset`** (`plant_floor_offset`): the audit reads `fp01` on
  Clover and the brown figworts as the general floor offset (25/45/20 disc,
  audit lines 100-102), but the asset contract corrects Clover - its general
  `fp01` is 40.0 and the 25.0 value is an inert unreferenced trailing block
  (`FLORA_ASSETS` §5, `plantsMgr.cpp:46-48`). Both readings are recorded, not
  flattened.
- **`brown_figwort_offset_assignment`**: which of the 45/20 disc values belongs
  to the small versus large brown figwort is not stated.

## Remaining blockers and next slice

- **#405 conversion: done.** The Candypop conversion/refund math is already
  covered by `reference_conversion` in
  [`experimental/pikmin2_flora_assets.py`](../experimental/pikmin2_flora_assets.py);
  this behavior model adds the acceptance/refund/close/shot paths as pure
  policy.
- **Gate 5 source reward: open.** The Pellet-to-Pom conversion and the
  Onion-side seed reward still need a source-backed receiver/arrival contract;
  no reward is produced here.
- **Hikari camera-facing #429: open.** `HikariKinoko` (48) still needs the
  camera-facing behaviour that the static extraction cannot provide.
- **Next native slice.** Wire the pure functions into the existing
  `pc_p2_batch2` Candypop/Pelplant display path one identity at a time, then
  add the Pelplant pellet capture/release and the Onion seed-reward receiver
  so a posy can be harvested and a bud can convert a real Pikmin.

## Validation

```
py -3.12 -m pytest tests/test_pikmin2_flora_behavior.py -q
py -3.12 -m pytest tests/test_pikmin2_bulblax_behavior.py -q
```

No runtime/native acceptance is claimed; this is a source-behavior model slice.
