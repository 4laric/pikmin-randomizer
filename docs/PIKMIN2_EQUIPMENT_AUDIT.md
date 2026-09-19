# Equipment and map unlock audit (#141)

This batch adds `experimental.pikmin2_equipment`, a source-backed specification of the
thirteen `OlimarData::ItemIndex` entries and a small host-side data contract that
mirrors the native flag layout. It edits no captain state, actor interface or save
protocol; runtime effects and UI feedback remain open on #141.

```powershell
py -3.12 -m experimental.pikmin2_equipment
```

prints the specification table as JSON.

## Identity

`include/Game/gamePlayData.h` numbers the items 0 to 12. `PelletGoalState::init`
(`src/plugProjectKandoU/pelletState.cpp`) passes `Pellet::getConfigIndex()` straight to
`OlimarData::getItem`, so the index is the `item_config.txt` order:

| Index | Symbol | Config | Dictionary | Effect (source site) |
|---:|---|---|---:|---|
| 0 | BruteKnuckles | `fue_a` | 188 | Punch combo PUNCH2/PUNCH3 (`naviState.cpp` NaviPunchState) |
| 1 | DreamMaterial | `fue_b` | 192 | No electric flick (`interactNavi.cpp` InteractDenki, `navi.cpp` platCallback) |
| 2 | AmplifiedAmplifier | `fue_wide` | 194 | Wide whistle radius (`naviWhistle.cpp`) |
| 3 | ProfessionalNoisemaker | `fue_pullout` | 195 | Whistle plucks sprouts (`itemPikihead.cpp` interactFue) |
| 4 | StellarOrb | `light_a` | 190 | Cave light ramp (`gameLightMgr.cpp` updateSpotType) |
| 5 | JusticeAlloy | `suit_powerup` | 193 | Damage × shield rate (`navi.cpp` startDamage/addDamage) |
| 6 | ForgedCourage | `suit_fire` | 191 | No fire damage (`interactNavi.cpp` InteractFire) |
| 7 | RepugnantAppendage | `dashboots` | 189 | Rush speed, wind immunity, steep slip 4.0 (`navi.cpp`, `naviState.cpp`, `interactNavi.cpp`, `fakePiki.cpp`) |
| 8 | PrototypeDetector | `radar_a` | 186 | Cave radar and map markers (`singleGameSection.cpp`) |
| 9 | FiveManNapsack | `radar_b` | 187 | Hold X 35 frames to be carried, story only (`naviState.cpp`) |
| 10 | SphericalAtlas | `map01` | 184 | `openCourse(1)`; find cutscene ignores distance; `g32_get_map` |
| 11 | GeographicProjection | `map02` | 185 | `openCourse(2)`; find cutscene ignores distance |
| 12 | TheKey | `key` | 196 | Not an Exploration Kit item; see below |

## Acquisition and duplicate receipts

- `getItem` asserts `item < ODII_LAST_NON_EXPLORATION_KIT_ITEM` (12) and sets
  `mFlags[1 - (index >> 3)] |= 1 << (index & 7)`; indices 0 to 7 live in the second
  byte, 8 to 11 in the first. `setDevelopSetting`'s `mFlags[0] |= 4` is the Atlas.
- `hasItem` asserts the same exclusive bound, so index 12 can never be queried.
- A second delivery of the same item sets the same bit again; nothing else changes.
  The find-item cutscene is gated separately by `PlayData::mFindItemFlags`
  (`navi_demoCheck.cpp`, movie `s16_find_item_%02d`), and the Treasure Hoard entry by
  `PelletFirstMemory::firstCarryPellet` (`KCF_Earned`).
- Only `mOlimarData[0]` gates effects; `playData->mOlimarData` is that slot and
  ForgedCourage and the detector read `[0]` explicitly. Both slots are still saved.

## Map unlocks

`openCourse(1)` and `openCourse(2)` are the only equipment side effects. Wistful Wild
(course 3) opens from `singleGS_Ending.cpp` and `singleGS_WorldMap.cpp` once the debt
is paid, and only if course 2 is already open. The detector map type is
`getDetectorFlags(detector, napsack)` = 0, 1, 2 or 3.

## The Key stays distinct

- `PelletGoalState::init` only calls `getItem` for config index < 12, so the Key never
  sets an `OlimarData` bit and `hasItem(12)` would assert.
- Story mode: delivering `key` calls `PlayCommonData::enableChallengeGame` and marks
  the option block for saving. The retail placement is Beady Long Legs in
  `yakushima_1`.
- Challenge mode: `onyonMgr.cpp` sends `InteractGotKey` to every closed geyser
  (`g30_appear_fountain`) and hole (`g2F_appear_hole`); the pollution-up sound is skipped.
- Versus mode: nothing; the Key is not part of the Battle roster logic.
- `item_config` gives it `code 1` (no resting shadow, Breadbugs cannot carry it).

## Persistence

`gamePlayDataMemCard.cpp` writes both `OlimarData` slots as two `itemFlag` bytes each,
the `PelletFirstMemory` journal, `mBitfieldPerCourse` per course and `mFindItemFlags`.
The Python `OlimarData.to_bytes()/from_bytes()` round-trips the two-byte image.

## Contract offered to the captain lane

`OlimarData.has_item/get_item/inventory`, `deliver_upgrade(state, config_name, mode)`,
`detector_map_type`, `find_item_cutscene` and `course_unlocks` encode the rules above.
Tests in `tests/test_pikmin2_equipment.py` check the bit layout, the mode semantics and,
when `native/pikmin2-research` is present (or `PIKMIN2_SOURCE` points at it), that every
cited source file still contains the cited symbol.

## Not covered

Carrying the weight-101 maps, HUD feedback, menu rendering and natural gameplay
evidence are runtime work for the captain, HUD and cargo lanes.
