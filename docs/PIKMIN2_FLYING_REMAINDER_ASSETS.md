# Flying remainder source asset bundles (#348, parent #166)

`python -m experimental.pikmin2_flying_assets --iso <local US ISO> --source <pikmin2-research checkout> --output <new directory> [--pose-limit 6]`

Source: `native/pikmin2-research` decompilation against US GPVE01 rev 0; retail resources verified against `assets/disc/PIKMIN2 for GAMECUBE.iso` (header `GPVE01` rev 0, 995 557 376 bytes). Evidence level: **source contract + converted assets** (per [the import pipeline](PIKMIN2_ENEMY_IMPORT_PIPELINE.md)); no native hook wiring in this lane. Skull icon notes from the Kogane audit below indicate read-only decomp anchors; no files were modified.

## 1. Identity and registration

| ID | Constant | Common name | Obj / Mgr class | Registration | Parentage |
|---|---|---|---|---|---|
| 29 | `EnemyID_Mar` | Puffy Blowhog | `Game::Mar::Obj` / `Mar::Mgr` | generalEnemyMgr.cpp:301-302 | Sibling `EnemyBase` (Mar.h:39) |
| 55 | `EnemyID_Hanachirashi` | Withering Blowhog | `Game::Hanachirashi::Obj` / `Hanachirashi::Mgr` | generalEnemyMgr.cpp:397-398 | Sibling `EnemyBase` (Hanachirashi.h:45) |
| 77 | `EnemyID_ShijimiChou` | Unmarked Spectralids | `Game::ShijimiChou::Obj` / `ShijimiChou::Mgr` | generalEnemyMgr.cpp:471-477 | `EnemyBase` (ShijimiChou.h:58); **helper only** |

**enemyInfo.cpp spawn table**: Mar (line 52), Hanachirashi (line 53), ShijimiChou (line 106) — all three `EFlag_CanBeSpawned | 2 | EFlag_UseOwnID`; Mar/Hanachirashi have no child ID (childID -1, childNum 0, BDT_Strong). ShijimiChou is also spawned as a helper by:
- Tanpopo (enemyInfo.cpp:70): childID `EnemyID_ShijimiChou`, childNum 5
- Ooinu_l (enemyInfo.cpp:76): childID `EnemyID_ShijimiChou`, childNum 5
- Magaret (enemyInfo.cpp:83): childID `EnemyID_ShijimiChou`, childNum 5
- Damagumo (enemyInfo.cpp:90, under `#if BUGFIX`): childID `EnemyID_ShijimiChou`, childNum `SHIJIMICHOU_GROUP_COUNT` (25, enemyInfo.h:211)

ShijimiChou instance limit: surface 10, cave `SHIJIMICHOU_GROUP_COUNT` (generalEnemyMgr.cpp:471-477).

**Cave/base relationship note**: Mar and Hanachirashi are independent Obj classes, not parent/child — both inherit directly from `EnemyBase`. Hanachirashi's `enemyanimmgr.txt` source paths all reference `Z:\Pikmin2Data\conversion\enemy\nishimura\Mar\anim\`, evidence of a shared legacy Mar art workspace during development. They use separate resource banks at runtime.

### Helper / unused entries (explicit classification)

| Entry | Classification | Evidence |
|---|---|---|
| `Game::Mar::Obj / Parms / FSM` | Concrete spawnable enemy | enemyInfo.cpp:52, generalEnemyMgr.cpp:301-302 |
| `Game::Hanachirashi::Obj / Parms / FSM` | Concrete spawnable enemy (wither variant) | enemyInfo.cpp:53, generalEnemyMgr.cpp:397-398 |
| `Game::ShijimiChou::Obj / Parms / FSM` | Concrete spawnable; **reclassified as helper only for this lane** (full runtime ownership left to family owners: Tanpopo, Ooinu_l, Magaret, Damagumo, Mamuta, plant nodes) | enemyInfo.cpp:106, shijimiChouMgr.cpp:14-93, miulin.cpp:30-37, plants.cpp:191-198 |
| `ShijimiChou::Mgr` group factories | Three distinct spawn paths, all source-only here: `createGroup` (:123), `createGroupByBigFoot` (:202, Damagumo.cpp:624), `createGroupByPlants` (:224, plants.cpp:191-198), `createGroupByEnemy` (:246, miulin.cpp:30-37) | shijimiChouMgr.cpp, Damagumo.cpp:616-626, BigFoot.cpp:671 |
| `ChappyBase::Obj` | Excludes `EnemyID_ShijimiChou` from base Atari logic (ChappyBase.cpp:162) | — |
| Mar `fuusen_model.btk` / `.brk` | Material animation (blimp color); hash-only preserved, no btk playback | MarMgr.cpp:11-12 |
| Hanachirashi `hanachirashi_model.btk` / `.brk` | Material animation; hash-only preserved | HanachirashiMgr.cpp:11-12 |

## 2. Resource map

All three use own-name resource paths (empty model/anim/animMgr columns in enemyInfo.cpp resolve via `EnemyInfoFunc::getEnemyName`, enemyInfo.cpp:157-174 → `EnemyMgrBase::loadModelData/loadAnimData`, enemyMgrBase.cpp:519-568).

| Species | model.szs (BMD) | anim.szs clips | Extra material files |
|---|---|---|---|
| Mar | `enemy/data/Mar/model.szs` (18 080 bytes) | 10 clips: dead, dead2, damage, flick, wait2, move1, move2, type1, type2, attack | `fuusen_model.btk` (384 bytes), `fuusen_model.brk` (256 bytes) — hash-only |
| Hanachirashi | `enemy/data/Hanachirashi/model.szs` (21 408 bytes) | 11 clips: same as Mar + laugh | `hanachirashi_model.btk` (384 bytes), `hanachirashi_model.brk` (256 bytes) — hash-only |
| ShijimiChou | `enemy/data/ShijimiChou/model.szs` (5 600 bytes) | 3 clips: carry, dead, move | None |

Parm archive: `enemy/parm/enemyParms.szs` contains per-species `enemyanimmgr.txt`, `enemyparm.txt`, `enemycoll.txt`, `enemystoneinfo.txt` under each lowercased species name.

## 3. Animation key events

Event lists from each `enemyanimmgr.txt`, matched against AnimID enum order (Mar.h:183-195, Hanachirashi.h:190-203, ShijimiChou.h:285-290) and state code.

**Mar** (10 clips, MarAnimID 0–9):

| Clip | AnimID | Key events (frame, type) | Semantic |
|---|---|---|---|
| dead | 0 | — | death fly; `KEYEVENT_END` → `throwupItem` + `kill` (MarState.cpp:65-68) |
| dead2 | 1 | — | death ground; same END logic |
| damage | 2 | `[[15, 2]]` | fly flick; EVENT_2 drops Pikmin |
| flick | 3 | `[[30, 2]]` | ground flick |
| wait2 | 4 | `[[0, 0], [39, 1]]` | ground wait loop (0=loop start, 1=loop end) |
| move1 | 5 | `[[0, 0], [39, 1]]` | fly wait loop |
| move2 | 6 | — | landing transition |
| type1 | 7 | `[[30, 2]]` | takeoff; EVENT_2 enables fly mode |
| type2 | 8 | `[[5, 0], [19, 1]]` | fall loop bounds |
| attack | 9 | `[[50, 2]]` | wind attack; EVENT_2 activates wind (MarState.cpp:883-885) |

**Hanachirashi** (11 clips, HanachiAnimID 0–10):

Same as Mar except `flick` = `[[25, 2]]` (earlier wind burst), and adds `laugh` (AnimID 10) with no events — entered after successful `windTarget()` (HanachirashiState.cpp:882-884).

**ShijimiChou** (3 clips, ShijimiAnimID 0–2):

| Clip | AnimID | Key events | Semantic |
|---|---|---|---|
| carry | 0 | `[[10, 0], [29, 1]]` | nectar/carry loop bounds |
| dead | 1 | — | death; `KEYEVENT_END` → `kill` |
| move | 2 | `[[0, 0], [7, 1]]` | flight loop bounds |

## 4. AI / state machine

**Mar FSM** (`MarState.cpp:15-30`, `create(MAR_StateCount)` = 12 states, Mar.h:20-35):

| State | ID | Notes |
|---|---|---|
| Dead | 0 | Fly or ground death motion (MarState.cpp:36-70) |
| Wait | 1 | Height hold; search Pikmin → Chase; timeout → Move (MarState.cpp:84-128) |
| Move | 2 | Random heading via `setRandTarget`, `EnemyFunc::walkToTarget`; timeout → Wait |
| Chase | 3 | Pursues target; enters ChaseInside when inside wind radius |
| ChaseInside | 4 | Close pursuit; enters Attack when within attack range |
| Attack | 5 | `startMotion(MARANIM_Attack)`; wind active at EVENT_2 (MarState.cpp:859-904); `mIsWindAttackActive` flag, `windTarget()` |
| Fall | 6 | Falling while carrying Pikmin; timer + gravity; EVENT_END → Land/Ground |
| Land | 7 | Landing transition; END → WaitGround |
| Ground | 8 | Ground walk; timeout → TakeOff |
| TakeOff | 9 | EVENT_2 → enters fly mode (MarState.cpp:1073-1097) |
| FlyFlick | 10 | EVENT_2 drops stuck Pikmin (MarState.cpp:1123-1146) |
| GroundFlick | 11 | EVENT_2 drops ground Pikmin |

**Hanachirashi FSM** (`HanachirashiState.cpp:15-31`, 13 states, Hanachirashi.h:27-43):

Identical to Mar plus `Laugh` (ID 12) — entered when `windTarget()` returns true during Attack (HanachirashiState.cpp:882-884); `StateLaugh::init` (HanachirashiState.cpp:1240) starts `HANACHIANIM_Laugh` motion.

**ShijimiChou FSM** (`shijimiChouState.cpp:15-25`, 6 states, ShijimiChou.h:41-48):

| State | ID | Notes |
|---|---|---|
| Wait | 0 | Pre-flight delay; leader-init group setup |
| Fly | 1 | `fly()` flight path via `checkFlyStart`; group leader driven |
| Fall | 2 | Falling (e.g. after Bitter Spray or death trigger); timer + `fallBehavior()` |
| Dead | 3 | Death; `deadEffect()`, `KEYEVENT_END` → `kill` |
| Leave | 4 | Swarm departure; group teardown |
| Rest | 5 | Nectar/item rest; collision on for atari, ignores non-resting Pikmin |

ShijimiChou birth sources (all source-only here):
- Mamuta: `miulin.cpp:30-37` — `createGroupByEnemy(arg, this, 5, true)` on Mamuta death
- Plant nodes: `plants.cpp:191-198` — `createGroupByPlants(birthArg, 5)`
- Damagumo: `Damagumo.cpp:616-626` — `createGroupByBigFoot(birthArg, SHIJIMICHOU_GROUP_COUNT)` = 25
- Mamuta's Miulin-derived ShijimiChou defaults: group count 25 via `SHIJIMICHOU_GROUP_COUNT` (enemyInfo.h:211, ShijimiChou.h:245)

## 5. Collision

| Species | Root joint | Root radius | Children |
|---|---|---|---|
| Mar | joint 6 | 90 | 8 `st__` parts: radii 10/12.5/10/10/10/10/30/42.5 (joints 8/7/3/2/5/4/6/1) |
| Hanachirashi | (same structure) | — | (same class, same collision factory) |
| ShijimiChou | joint 0 | 30 | 1 `st__` child: radius 20, joint 0 |

ShijimiChou proper collision: root sphere at center (30 units), child at `st__` (20 units) — used for Pikmin atari in Rest state (ShijimiChou.h:91-103: `ignoreAtari` returns false only in Rest state).

## 6. Parameter values

### ProperParms header defaults vs disc (retail)

Mar and Hanachirashi proper parms share the same 8-key schema (Mar.h:146-168, Hanachirashi.h:152-175); ShijimiChou has 8 keys with different semantics (ShijimiChou.h:215-238).

| Key | Mar default | Mar disc | Hanachirashi disc | ShijimiChou default | ShijimiChou disc |
|---|---|---|---|---|---|
| fp01 | 90.0 | **80.0** | **70.0** | 300.0 | **250.0** |
| fp02 | 1.0 | 1.0 | 1.0 | 1.0 | **0.2** |
| fp03 | 3.0 | 3.0 | 3.0 | 100.0 | **70.0** |
| fp04 | 3.0 | **1.0** | **1.0** | 0.05 | **0.02** |
| fp05 | 2.5 | 2.5 | 2.5 | 1.0 | **2.0** |
| fp06 | 5.0 | 5.0 | 5.0 | 0.1 | 0.1 |
| fp10 | 3.0 | **1.0** | **1.0** | — | — |
| ip01 | 10 | **6** | **4** | — | — |
| fp08 | — | — | — | 100.0 | **250.0** |
| fp07 | — | — | — | 0.1 | 0.1 |

Key semantic annotations: fp01 = flight height, fp10 = ground wait time, fp04 = shake-off/fall time, ip01 = minimum Pikmin to trigger fall, fp08 = plant-source flight time (ShijimiChou only), fp06/fp07 = red/purple Spectralid spawn chance (ShijimiChou).

### GeneralParms disc values (representative subset)

| Key | Mar disc | Hanachirashi disc | ShijimiChou disc |
|---|---|---|---|
| fp00 (health) | 3000.0 | 1800.0 | 200.0 |
| fp06 (speed) | 120.0 | 100.0 | 150.0 |
| fp09 (territory) | 400.0 | 250.0 | 250.0 |
| fp10 (home range) | 100.0 | 100.0 | 30.0 |
| fp12 (sight range) | 275.0 | 275.0 | 700.0 |
| fp17 (attack range) | 200.0 | 150.0 | 150.0 |
| fp20 (attack zone) | 200.0 | 200.0 | 30.0 |
| fp22 (attack hit range) | 300.0 | 300.0 | 30.0 |
| fp24 (attack damage) | 0.0 | 0.0 | **10.0** |
| fp32 (LOD radius) | 125.0 | 80.0 | 30.0 |
| fp34 (Pikmin atari) | 40.0 | 30.0 | 7.0 |

Mar/Hanachirashi fp24 = 0: wind attack does no direct HP damage; Pikmin are blown away, not damaged.

## 7. Carcass

| Species | carcass_config.txt entry | Money | Carry min/max | dynamics |
|---|---|---|---|---|
| Mar | None | — | — | — |
| Hanachirashi | None | — | — | — |
| ShijimiChou | Line 1013 | 1 | 1 / 1 | never |

ShijimiChou carcass: radius 9, height 8, pikicountmax/min 1, dynamics `never` — not physically carried by Pikmin. Money 1 poko. Mar/Hanachirashi have no `carcass_config` entry; default enemy corpse physics apply but no per-species pouch config is stored.

## 8. Material animation (hash-only)

Mar and Hanachirashi both have `btk` + `.brk` material animation files loaded by their respective `Mgr::loadTexData` overrides (MarMgr.cpp:56-80, HanachirashiMgr.cpp:56-79). These files are hashed and byte-preserved only; no btk playback or texture animation is executed by this module. Runtime material animation (blimp color cycle for Mar, withering glow for Hanachirashi) is a native implementation concern.

## 9. Converter behaviour and known limitations

Pose extraction follows the established lane pattern: hashed disc reads, bounded frame sampling, deterministic `bca_pose` → `draw_matrices` → `decode` → `write_model` → `resource_chunks` pipeline. Supported tolerances are recorded per-clip; no new converter hooks are introduced.

| Species | Envelopes | Draw matrices | Skinning notes |
|---|---|---|---|
| Mar | 2 | 17 | Weighted rig; mat1 differed display list (MarMgr.cpp:93-94) |
| Hanachirashi | 5 | 23 | Weighted rig; mat_shijimi_hane_v differed display list (HanachirashiMgr.cpp:59-60, shijimiChouMgr.cpp:59) |
| ShijimiChou | 0 | 3 | Rigid model (3 joints: center, Lhane, Rhane); no envelopes; bake_rigid=True always |

**LIMITATIONS**:
1. Sampled weighted/rigid poses with approximate materials; no skeletal playback or event execution.
2. Animation key events, loop markers and parameter text are preserved as data only; no wind attack, flick, shake-off, nectar-drop or death behavior executes.
3. Mar `fuusen_model.btk`/`.brk` and Hanachirashi `hanachirashi_model.btk`/`.brk` are hashed and byte-preserved only; no btk playback.
4. No native runtime, AI/FSM, install, arena placement or spiral-bridge spawning is provided by this slice.
5. ShijimiChou is source-only helper data; full runtime ownership (group factory wiring, colour selection, nectar-roll, spawn-source attribution) belongs to the respective family owners (Tanpopo, Ooinu_l, Magaret, Damagumo, Mamuta, plant nodes) and is not wired here.
6. Hanachirashi `enemyanimmgr.txt` source paths reference the Mar animation workspace (`Z:\Pikmin2Data\conversion\enemy\nishimura\Mar\anim\`); disc archive filenames are species-scoped and do not overlap.

## 10. Test acceptance

`python -m pytest tests/test_pikmin2_flying_assets.py` passes. Three test classes cover:
- profile validation (enemy ID, state IDs, clip registry, events, proper keys, disc vs header defaults, carcass contract, ShijimiChou group-count constant)
- registration / helper classification citations (enemyInfo.cpp, generalEnemyMgr.cpp, Damagumo.cpp, ShijimiChou.h)
- asset-conversion non-regression (three species model hashes, clip counts, per-clip pose budget)

No native actors, P1 substitutions, shared converter edits, builds or gameplay runs were performed. All assets remain local.

## Batch 2 — install + arena (#375)

Follows batch 1 (#348, commit `a7c9ad7`). Adds pipeline §4 (install + arena) for
IDs 29 Mar, 55 Hanachirashi and 77 ShijimiChou. Static/source-level evidence
only: no shared native code, converter, build or gameplay run was touched.

### Install (hash-bound)

Module: `experimental/pikmin2_flying_install.py` (follows
`pikmin2_mamuta_install.py` #221 and `pikmin2_kogane_install.py` #219; no
shared-file edits).

- `plan(imported, actors)` validates the roster **before** any manifest IO:
  1..100 actors, unsigned-unique IDs, spawnable species only. It then binds the
  batch-1 `flying.json`: schema 1, policy `P2_FLYING_1`, `native_ready == false`,
  the exact species set and enemy IDs (29/55/77), and the helper classification
  (`ShijimiChou` = helper only). Every installed pose is bound by SHA-256.
- Actor rows are `(generator, species)` for Mar/Hanachirashi only. A
  `ShijimiChou` actor row is rejected; the helper is instead recorded as
  helper/reward metadata (enemy ID, clip count, group count 25, runtime owner)
  in the receipt and profile. No ShijimiChou pose is installed and no runtime
  ownership is claimed.
- Exact-byte outputs into an already private, non-junction run:
  `p2-flying-profile.txt` (species/role/helper/retail-parm tokens),
  `p2-flying-bank.txt` (per-species clip/frame/event/pose listing),
  `p2-flying-actors.txt` (`P2_FLYING_ACTORS_1` + generator/species rows),
  receipt `flying-install.json`, and the optional pose bank
  `fly_<species>_<clip>_<nn>.mod` under
  `assets/dataDir/courses/pikmin2room/`.
- Optional visual bank is all-or-nothing over the spawnable species: absent
  `.mod` files (or absent bank dirs) install configs only and preserve the room
  baseline (`visuals='absent_baseline_preserved'`); a partial bank, stray pose
  or any hash mismatch is refused before mutation. Sibling `p2-*-actors.txt`
  bindings are scanned for generator-ID overlap.
- `verify_install(imported, run, actors)` reloads a layout and proves the
  profile/bank/actors configs and every installed pose byte match the import
  and the receipt hashes.

### Arena staging

Module: `experimental/pikmin2_flying_arena.py` per
[the arena contract](PIKMIN2_ENEMY_ARENA.md).

- Original Impact Site (practice) map/collision/routes preserved byte-identical
  (per-file SHA-256 re-verified after overlay); stage slot `chal0`.
- Roster: one explicit actor per spawnable species plus one ordinary control —
  generators 375001 Mar / 375002 Hanachirashi / 375003 P1 Chappy control at
  (-150,30,1850) / (-50,30,1850) / (150,30,1550). IDs are checked against the
  actual stage records at staging time.
- Mar and Hanachirashi stage on the P1 Puffy Blowhog proxy
  (`tekimgr.cpp` tekiNames[16] "mar"); the control is ordinary P1 Chappy
  (Dwarf Bulborb, type 3). Because the withering Hanachirashi variant has no P1
  counterpart, its behavior is a proxy only.
- Generator position + offset is translation only (zero offset, validated);
  source yaw unapplied (`source_yaw=None`). The default scatter circle is
  zeroed by the deterministic fixture override — an engineered choice, not
  production placement evidence.
- ShijimiChou is recorded as helper metadata (`spawned: false`,
  `installed_visuals: false`) and is neither spawned nor installed.
- `GATES`/`GATE_STATES`: every behavior gate is marked **blocked** until native
  registration exists (`native_identity`, `natural_AI`, `wind_attack`,
  `flick_shakeoff`, `death_corpse`, `day_floor_reset`, `save_load`,
  `piklopedia_observation`, `helper_group_ownership`).

### Native registration (family-owned, not implemented in this batch)

Workflow revision 2026-09-13 ([#186](https://github.com/4laric/pikmin-randomizer/issues/186)):
the flying family owner implements these narrow additive registration hooks.
Mar (29) and Hanachirashi (55) only; shared-semantics edits still require
focused review.

- **Build sources:** add `native/pc_port/pc_p2_mar.cpp` and
  `pc_p2_hanachirashi.cpp` (headers `.h`) to the `pc_port` build source list
  (`native/configure.py` / CMake), or one shared `pc_p2_flying.cpp` with a
  species switch. No shared files are edited by this lane.
- **setup:** `pc_p2_mar_setup()` / `pc_p2_hanachirashi_setup()` read
  `P2_FLYING_ACTORS_1`, `p2-flying-profile.txt` and `p2-flying-bank.txt`, and
  bind the installed pose bank (`fly_<species>_<clip>_<nn>.mod`) onto the
  registered actor, preserving the baseline when the bank is absent (same
  pattern as `pc_p2_kogane_setup`/`pc_p2_mamuta_setup`).
- **update:** `pc_p2_flying_update()` ticks the per-species source FSM
  (MarState.cpp / HanachirashiState.cpp registrations), including wind
  activation at event 2 and Hanachirashi's Laugh transition.
- **draw:** `bool pc_p2_<species>_draw(BTeki*, Graphics&, const Matrix4f&,
  bool corpse=false);` replaces the P1 Puffy proxy model in the draw dispatch;
  expose `const char* pc_p2_flying_name(PelletView*)` and
  `int pc_p2_flying_source_id(PelletView*)` returning 29 (Mar) / 55
  (Hanachirashi).
- **reset:** `void pc_p2_flying_reset();` added to the `#if PIKI_PC_PORT`
  reset lists in `TekiMgr::initTekiMgr` and `TekiMgr::TekiMgr`, and
  `void pc_p2_flying_forget(BTeki*);` to the teardown/forget path, so both
  species registrations clear on death/reset without stale identity reuse.
- **Not requested / retained elsewhere:** no ShijimiChou (77) actor,
  `ShijimiChou::Mgr` factory, colour/nectar-roll or spawn-source registration.
  That runtime ownership stays with its family owner (Tanpopo, Ooinu_l,
  Magaret, Damagumo, Mamuta, plant nodes); this lane binds helper/reward
  metadata only.

### Tests

`python -m pytest tests/test_pikmin2_flying_install.py
tests/test_pikmin2_flying_assets.py -q` passes. The install test covers
pre-IO actor count/duplicate/invalid-ID rejection, schema/identity drift,
helper-only actor exclusion, pose hash mismatch, partial-bank refusal,
install/verify round-trip, overwrite refusal, tamper detection on installed
pose/config, absent-bank baseline preservation, sibling generator overlap and
non-junction room enforcement, plus arena proxy-type constants, gate coverage
(all blocked), helper non-spawn metadata and `roster` failing on a missing
stage.
