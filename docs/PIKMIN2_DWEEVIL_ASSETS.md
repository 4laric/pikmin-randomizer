# Dweevil family + fixed elemental hazards source audit — FireOtakara (59), WaterOtakara (60), GasOtakara (61), ElecOtakara (62), BombOtakara (93); Hiba (20), GasHiba (21), ElecHiba (22)

Issue: [#349](https://github.com/4laric/pikmin-randomizer/issues/349) (parent [#170](https://github.com/4laric/pikmin-randomizer/issues/170)).
Source: `native/pikmin2-research` decompilation at
`632af93787b9c95b63f0c13be32b161375ce3a96`; retail resource/parameter tables
re-read from the US GPVE01 rev 0 disc (`output/pikmin2-runtime/pikmin2-source-test.iso`),
so the clip registry, event streams, archive layout and per-file hashes below
are disc-confirmed. Evidence level: **source contract + converted assets** (per
[the import pipeline](PIKMIN2_ENEMY_IMPORT_PIPELINE.md)); no native hook wiring
in this lane. Tank (done) and Titan Dweevil / BigTreasure (#246) are explicitly
out of scope.

## 1. Identity and registration

| ID | Constant | Common name | Obj / Mgr class | Registration |
|---|---|---|---|---|
| 59 | `EnemyID_FireOtakara` (enemyInfo.h:118) | Fiery Dweevil | `Game::FireOtakara::Obj` / `Mgr` | generalEnemyMgr.cpp:409 |
| 60 | `EnemyID_WaterOtakara` (enemyInfo.h:119) | Caustic / Hydro Dweevil | `Game::WaterOtakara::Obj` / `Mgr` | generalEnemyMgr.cpp:412 |
| 61 | `EnemyID_GasOtakara` (enemyInfo.h:120) | Munge Dweevil | `Game::GasOtakara::Obj` / `Mgr` | generalEnemyMgr.cpp:415 |
| 62 | `EnemyID_ElecOtakara` (enemyInfo.h:121) | Anode Dweevil | `Game::ElecOtakara::Obj` / `Mgr` | generalEnemyMgr.cpp:418 |
| 93 | `EnemyID_BombOtakara` (enemyInfo.h:152) | Volatile Dweevil | `Game::BombOtakara::Obj` / `Mgr` | generalEnemyMgr.cpp:421 |

- Spawn table: `src/plugProjectYamashitaU/enemyInfo.cpp` — all five are
  `EFlag_CanBeSpawned | 2 | EFlag_UseOwnID` concrete spawnables
  (enemyInfo.cpp:96-99,110). No parent alias; BombOtakara carries
  `childID = EnemyID_Bomb, childNum = 1` (enemyInfo.cpp:110), which is its
  payload rather than a duplicate spawnable.
- **Shared base:** all five derive from `OtakaraBase::Obj`/`Mgr`
  (OtakaraBase.h:11-17; FireOtakara.h:13, WaterOtakara.h:17, GasOtakara.h:13,
  ElecOtakara.h:13, BombOtakara.h:12). They share one StateID enum, one AnimID
  bank, one `OtakaraBase::Parms` block and one physical model/anim bank.
- **Resource aliasing:** the four elemental dweevils list `model = "FireOtakara"`
  and `anim = "FireOtakara"` and `animmgr/collision/stone = "Otakara"`
  (enemyInfo.cpp:97-99); `FireOtakara` itself leaves those slots empty and
  therefore resolves to its own `enemy/data/FireOtakara/` bank
  (enemyInfo.cpp:96). BombOtakara is the same alias (enemyInfo.cpp:110).
  `getEnemyResName` confirms the shared `"Otakara"` anim name for the four
  elemental dweevils (enemyInfo.cpp:157-166). `OtakaraBase::Mgr::loadModelData`
  and `loadAnimData` then copy the first loaded model/anim across the five
  managers (OtakaraBaseMgr.cpp:24-44, 50-69).
- Per-species identity is **procedural texture only**: each `Mgr::loadTexData`
  loads a colour `otakara_*_s3tc.bti` (FireOtakaraMgr.cpp:10,
  WaterOtakaraMgr.cpp:8, GasOtakaraMgr.cpp:8, ElecOtakaraMgr.cpp:8,
  BombOtakaraMgr.cpp:8), applied in `Obj::changeMaterial()`.

### Fixed elemental hazards (explicit reclassification)

The three hazard IDs are numbered in `EnemyID` and are registered spawnables,
so they are **not** unregistered scenery. They are nevertheless flagged
`EFlag_HasNoInfo` with empty resource slots and `BDT_Empty`, i.e. they have no
Piklopedia/creature identity and are used as fixed, scenery-adjacent elemental
hazards. They do **not** inherit `OtakaraBase`.

| ID | Constant | Hazard | Obj / Mgr class | Classification | Evidence |
|---|---|---|---|---|---|
| 20 | `EnemyID_Hiba` (enemyInfo.h:79) | Fire geyser | `Game::Hiba::Obj` / `Mgr` | fixed scenery-adjacent fire hazard | enemyInfo.cpp:41 (`EFlag_HasNoInfo \| EFlag_CanBeSpawned \| 2 \| EFlag_UseOwnID`, `BDT_Empty`); generalEnemyMgr.cpp:274; Hiba.h:21,68 |
| 21 | `EnemyID_GasHiba` (enemyInfo.h:80) | Gas pipe | `Game::GasHiba::Obj` / `Mgr` | fixed scenery-adjacent gas hazard; bridge/gate linked | enemyInfo.cpp:42; generalEnemyMgr.cpp:277; GasHiba.h:28,81; `setInitLivingThing` GasHiba.cpp:193-296 |
| 22 | `EnemyID_ElecHiba` (enemyInfo.h:81) | Electrical wire | `Game::ElecHiba::Obj` / `Mgr` | fixed scenery-adjacent electric hazard; two-node team | enemyInfo.cpp:43; generalEnemyMgr.cpp:280; ElecHiba.h:42,107; ElecHibaMgr.cpp:110-131 |

The code records this classification in `HAZARD_CLASSIFICATION`; the module
does not treat the hazards as enemy-family members and does not convert their
models.

## 2. Shared AI / state machine

Every dweevil registers the same 14-state FSM in `OtakaraBaseState.cpp:14-34`,
covering normal, item-carry and Bomb-carry states. Shared `StateID`
(OtakaraBase.h:22-39): `dead=0, flick=1, wait=2, move=3, turn=4, take=5,
item_wait=6, item_move=7, item_turn=8, item_flick=9, item_drop=10,
bomb_wait=11, bomb_move=12, bomb_turn=13`. The Bomb states are reached only by
BombOtakara once its `EnemyID_Bomb` payload is captured on the `otakara` joint
(OtakaraBase.cpp:649-677); the shared code kills the carrier if the payload
pointer disappears (OtakaraBaseState.cpp:761-763, 816-819, 880-882).

Hazard FSMs are separate and shallower:
- Hiba and GasHiba: Dead/Wait/Attack (HibaState.cpp:14-20; GasHibaState.cpp:13-19),
  state IDs `HIBA_Dead/Wait/Attack` and the identical `GASHIBA_*` set
  (Hiba.h:136-141; GasHiba.h:151-156).
- ElecHiba: Dead/Wait/Sign/Attack (ElecHibaState.cpp:13-20; ElecHiba.h:197-203),
  with parent-only FSM updates and recursive child init (ElecHiba.cpp:67-73,88-93).

## 3. Animation clips and event streams

Clip order equals the shared `AnimID` enum (OtakaraBase.h:179-193) and the
shared `otakara/enemyanimmgr.txt` registration order, re-read from the disc.
The shared bank has 12 clips; every stem (including slot 4 `takeitem` and the
trailing `dead`/`carry`) is registered on disc and is no longer inferred.

| Slot | AnimID | Disc stem | Disc events (frame, type) | Gameplay types |
|---|---|---|---|---|
| 0 | `OTAKARAANIM_Wait` | `wait1` | (0,0), (29,1) | — |
| 1 | `OTAKARAANIM_Move` | `move1` | (4,0), (15,1) | — |
| 2 | `OTAKARAANIM_Turn` | `pivot1` | (4,0), (15,1) | — |
| 3 | `OTAKARAANIM_Attack` | `attack1` | (12,2), (20,0), (27,1), (35,3) | 2 → 3 |
| 4 | `OTAKARAANIM_TakeItem` | `takeitem` | (10,2) | 2 |
| 5 | `OTAKARAANIM_ItemWait` | `wait2` | (10,0), (19,1) | — |
| 6 | `OTAKARAANIM_ItemMove` | `move2` | (4,0), (15,1) | — |
| 7 | `OTAKARAANIM_ItemTurn` | `pivot2` | (4,0), (15,1) | — |
| 8 | `OTAKARAANIM_ItemAttack` | `attack2` | (12,2), (20,0), (27,1), (35,3) | 2 → 3 |
| 9 | `OTAKARAANIM_DropItem` | `dropitem2` | (5,2) | 2 |
| 10 | `OTAKARAANIM_Dead` | `dead` | — | — |
| 11 | `OTAKARAANIM_Carry` | `carry` | (10,0), (29,1) | — |

Event types 0/1 are loop markers, not gameplay events; the disc registry uses
only types 0/1/2/3 (there is no 1000 sentinel). Gameplay semantics are taken
directly from the shared state reads: `StateFlick::exec`
(OtakaraBaseState.cpp:101-135), `StateTake::exec` (:369-386),
`StateItemFlick::exec` (:630-664), `StateItemDrop::exec` (:698-725).
`EXPECTED_EVENTS` records the ordered tuple of disc gameplay types only, never
fabricated frame numbers; the disc frames are preserved verbatim in extraction.
Hazard clips are the smaller banks in Hiba.h:117-121, GasHiba.h:132-136 and
ElecHiba.h:179-182 (`wait`, `attack`; ElecHiba `wait` only); the disc
`hiba/` and `gashiba/` registries are `wait` then `attack`, and `elechiba/` is
`wait` only.

## 4. Retail parameters (header defaults vs disc)

Headers list __build-time defaults__; the disc block is the retail value. The
shared `OtakaraBase::ProperParms` (OtakaraBase.h:150-156) defaults are
`fp01=100.0` (otakara life), `fp10=1.0` (normal attack), `fp11=1.25`
(otakara attack) and `fp21=2.5` (treasure catch). The retail disc block is
identical except where noted:

| Proper parm | Header default | Fire/Water/Elec/Bomb retail | Gas retail |
|---|---|---|---|
| fp01 otakara life | 100.0 | **80.0** | 100.0 |
| fp10 normal attack | 1.0 | 1.0 | 1.0 |
| fp11 otakara attack | 1.25 | 1.25 | 1.25 |
| fp21 treasure catch | 2.5 | 2.5 | 2.5 |

The shared general (`EnemyParmsBase`) block is essentially common across the
family; retail differences are the life (fp00), move speed (fp06), attack
damage (fp24) and stun chance (fp37):

| General parm | Fire (59) | Water (60) | Gas (61) | Elec (62) | Bomb (93) |
|---|---|---|---|---|---|
| fp00 life | 150 | 150 | **350** | 150 | 150 |
| fp06 move speed | 80 | 80 | **100** | 80 | 80 |
| fp24 attack | 10 | **0** | **0** | 10 | **0** |
| fp37 stun chance | 1 | 1 | 1 | 1 | **0** |
| fp09/fp10/fp11 territory/home/private | 200 / 75 / 70 | 200 / 75 / 70 | 200 / 75 / 70 | 200 / 75 / 70 | 200 / 75 / 70 |
| fp12/fp13 sight / FOV | 200 / 180 | 200 / 180 | 200 / 180 | 200 / 180 | 200 / 180 |
| fp22/fp23 hit range / angle | 60 / 0 | 60 / 0 | 60 / 0 | 60 / 0 | 60 / 0 |
| ip01–ip07 shake thresholds | 6/5/12/10/17/20/22 | same | same | same | same |

The module keeps `PROPER_PARM_DEFAULTS` (header) and `DISC_PARMS` (retail)
separate and never flattens them; `profile()` rejects any drift. Retail values
and the general blocks below are read verbatim from the disc
`<species>/enemyparm.txt` tables; the shared `otakara/enemyparm.txt` folder does
not exist on disc (the shared archive carries only the anim/collision/stone
tables).

### Hazard parameters (header defaults)

| Hazard | Proper block (header defaults) |
|---|---|
| Hiba | fp02 wait 2.5, fp01 fire time 2.5, fp03 stop 10.0, fp90/91 LOD 0.085/0.05 |
| GasHiba | fp02 wait 2.5, fp01 gas time 2.5, fp03 attack start 1.0, fp04 stop 10.0, fp90/91 LOD |
| ElecHiba | fp02 wait 2.5, fp03 warning 2.5, fp01 discharge 2.5, fp04 stop 10.0, fp90/91 LOD |

Retail hazard proper blocks are read from disc and differ from the header
defaults: `hiba` = fp01 2.5 / fp02 3.0 / fp03 30.0; `gashiba` = fp01 3.0 /
fp02 0.0 / fp03 0.6 / fp04 30.0; `elechiba` = fp01 2.5 / fp02 1.5 / fp03 1.5 /
fp04 30.0. The module continues to report the header (build-time) defaults in
`HAZARD_PROPER_PARM_DEFAULTS`; the disc blocks are preserved in the extracted
`<hazard>/enemyparm.txt`.

## 5. Resource map on disc

Whole family — one shared bank plus per-species colour texture:

| Resource | Path | Notes |
|---|---|---|
| Model (shared) | `enemy/data/FireOtakara/model.szs` (`enemy.bmd`) | OtakaraBaseMgr.cpp:24-44 |
| Anim (shared) | `enemy/data/FireOtakara/anim.szs` | exactly `attack1, attack2, carry, dead, dropitem2, move1, move2, pivot1, pivot2, takeitem, wait1, wait2` `.bca`, one per AnimID; OtakaraBaseMgr.cpp:50-69 |
| Parameters (shared) | `enemy/parm/enemyParms.szs` → `otakara/enemystoneinfo.txt`, `otakara/enemycoll.txt`, `otakara/enemyanimmgr.txt` | shared anim registry, collision tree and stone info |
| Parameters (per species) | `enemy/parm/enemyParms.szs` → `<species>/enemyparm.txt` | `fireotakara/waterotakara/gasotakara/elecotakara/bombotakara` each hold only `enemyparm.txt` |
| Fire colour tex | `enemy/data/FireOtakara/otakara_red_s3tc.bti` | FireOtakaraMgr.cpp:10 |
| Water colour tex | `enemy/data/WaterOtakara/otakara_blue_s3tc.bti` | WaterOtakaraMgr.cpp:8 |
| Gas colour tex | `enemy/data/GasOtakara/otakara_purple_s3tc.bti` | GasOtakaraMgr.cpp:8 |
| Elec colour tex | `enemy/data/ElecOtakara/otakara_yellow_s3tc.bti` | ElecOtakaraMgr.cpp:8 |
| Bomb colour tex | `enemy/data/BombOtakara/otakara_bomb_s3tc.bti` | BombOtakaraMgr.cpp:8 |

`OtakaraBase::Mgr::createModel` additionally rebuilds the `mat_body` shape's
display list for `J3DMDF_TexCoord1 | J3DMDF_DiffTexCoordScale`
(OtakaraBaseMgr.cpp:75-88), matching the procedural colour swap; this is a
material effect, not a separate model. Hazard parm folders are `hiba/`,
`gashiba/` and `elechiba/`.

## 6. Reproducible conversion path

Module: `experimental/pikmin2_dweevil_assets.py` (follows the ground-invert/
bulblax lane pattern; no edits to neighbour modules or shared converters).

```
python -m experimental.pikmin2_dweevil_assets \
    --iso output/pikmin2-runtime/pikmin2-source-test.iso \
    --source native/pikmin2-research \
    --output output/p2-lane-verify/dweevil2 --pose-limit 2
```

Reads the shared `enemy/data/FireOtakara/{model.szs,anim.szs}`, the shared
`otakara/{enemyanimmgr,enemycoll,enemystoneinfo}.txt` tables and each
`<species>/enemyparm.txt` from `enemy/parm/enemyParms.szs`; records the
per-species `otakara_*_s3tc.bti` change-texture source path; and writes the
hazard `<hazard>/*` metadata under `hazards/<name>/`. Output (private, not
committed): per-species `enemy.bmd`, all 12 `.bca` clips, the four metadata
text files, sampled rigid `.mod` pose files + conversion JSON, and a hashed
`dweevils.json` manifest (`schema=1`, disc id/revision, source revision,
per-file SHA-256, `native_ready=false`, `gameplay_events_executed=false`,
`btk_playback=false`). Immutable render resources are pinned so a pose set never
mutates shared model data.

Verified disc run (`--pose-limit 2`): 5/5 species, 12/12 clips converted per
species, 24/24 sampled poses converted, 0 unsupported; the three hazards are
recorded with their classification and parm metadata.

Reproducibility evidence: extract hashes every disc resource read; duplicate
runs must produce identical `dweevils.json`.

## 7. Tests

`tests/test_pikmin2_dweevil_assets.py` — mirror of the ground-invertebrate test
layout with synthetic parameter blocks and a mocked disc/filesystem:

- **Registry/profiles**: IDs 59/60/61/62/93 → correct `SPECIES`/state/clip maps,
  shared `OtakaraBase` base and one shared 12-clip bank.
- **Disc aliasing**: the 12 stems/order, shared `FireOtakara` model bank and
  shared `otakara/` parm folder, and the `(2, 3)` gameplay type set are pinned
  to the disc-confirmed contract.
- **Parm parsing**: retail `DISC_PARMS` values match; header defaults stay
  separate (Fire fp01 80 vs 100); Gas retail fp01 = header 100 is still read
  from the disc block; no keys default from the header here.
- **Rejection**: unknown general key (fp07), unknown proper key, general and
  proper disc drift, and clip/event-stream mismatch are all rejected.
- **Hazards**: 20/21/22 classification is explicit and records the
  `HasNoInfo` evidence; header parm defaults are checked.
- **Budget/gate**: pose-limit validation enforces 2..12 before any IO; output
  overwrite is refused before source access; the wrong disc (`GPVJ01`) is
  refused with no output. TEXT non-claims are asserted.

## 8. Open / handoff items

- Disc confirmation is closed for this lane: the 12 `.bca` stems/order and loop
  events, the shared `otakara/` parm-folder layout, the per-species
  `enemyparm.txt` retail values and the hazard parm blocks were all re-read from
  the US GPVE01 rev 0 disc and the verified run above exercises them.
- Per-pose conversion of every sampled frame succeeded here; a future lane can
  raise `--pose-limit` to 12 to broaden coverage, but no unsupported-pose reason
  is currently observed.
- Native hook wiring (shared-base spawn profile, treasure capture/drop, Bomb
  payload linkage, ElecHiba two-node team, Hiba/GasHiba timers) belongs to the
  native/integration track — none touched here.
- Parallel lanes (Tank, Titan Dweevil / BigTreasure #246, other #170 batches)
  untouched; no shared-file changes required by this lane.
