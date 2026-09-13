# Snagret family + Segmented Crawbster source audit — SnakeCrow (34), SnakeWhole (70), DangoMushi (94)

Issue: [#351](https://github.com/4laric/pikmin-randomizer/issues/351) (parent [#174](https://github.com/4laric/pikmin-randomizer/issues/174)).
Source: `native/pikmin2-research` decompilation. Retail parameter values and
per-clip key events were re-read directly from the supplied US GPVE01 rev 0
disc (`output/pikmin2-runtime/pikmin2-source-test.iso`) and cross-checked
against the published US Pikmin 2 enemy property listings (Pikipedia "Pikmin 2
enemy properties", pages 1-4). The disc proper blocks differ from the header
constructor defaults (DangoMushi's disc block even omits `fp10`), and the
DangoMushi `enemyanimmgr.txt` bank is missing the `{` before `attack_2.bca`;
both facts are handled explicitly by the module.
Evidence level achieved: **source contract + converted assets** (per
[the import pipeline](PIKMIN2_ENEMY_IMPORT_PIPELINE.md)); no native hook wiring
in this lane. Pikmin 1 counterpart mapping is **not** claimed.

Family coverage is tracked as `burrow_roll` in
[PIKMIN2_CONTENT_COVERAGE.md](PIKMIN2_CONTENT_COVERAGE.md) (3 IDs, issue
#174); this lane claims all three.

## 1. Identity and registration

| ID | Constant | Common name | Obj / Mgr class | Registration |
|---|---|---|---|---|
| 34 | `EnemyID_SnakeCrow` (enemyInfo.h:93) | Burrowing Snagret | `Game::SnakeCrow::Obj` / `Mgr` | generalEnemyMgr.cpp:316 |
| 70 | `EnemyID_SnakeWhole` (enemyInfo.h:129) | Pileated Snagret | `Game::SnakeWhole::Obj` / `Mgr` | generalEnemyMgr.cpp:447 |
| 94 | `EnemyID_DangoMushi` (enemyInfo.h:153) | Segmented Crawbster | `Game::DangoMushi::Obj` / `Mgr` | generalEnemyMgr.cpp:497 |

- Spawn table: `src/plugProjectYamashitaU/enemyInfo.cpp` — all three are
  `EFlag_CanBeSpawned | 2 | EFlag_UseOwnID` concrete spawnables with
  **all-empty resource slots**, so each loads its own `enemy/data/<OwnName>/`
  model+anim bank (SnakeCrow enemyInfo.cpp:62, SnakeWhole enemyInfo.cpp:63,
  DangoMushi enemyInfo.cpp:113). No aliasing between the three.
- All three are source bosses: `IS_ENEMY_BOSS` (enemyInfo.h:214-219) lists
  `EnemyID_SnakeCrow`, `EnemyID_SnakeWhole` and `EnemyID_DangoMushi`; the
  content inventory flags each as `source_boss`
  (PIKMIN2_CONTENT_INVENTORY.json:6670,7066,7330). SnakeCrow/SnakeWhole carry
  `EFlag_DayEndMax1 | EFlag_CanAppearDayEnd` (enemyInfo.cpp:62-63); DangoMushi
  does not.
- `loadModelData` for all three calls `setTexMtxLoadType(0x2000)` on every J3D
  shape (SnakeCrowMgr.cpp:49-57, SnakeWholeMgr.cpp:49-57,
  DangoMushiMgr.cpp:57-65); the plain converter path is bypassed and poses use
  the explicit draw-matrix path (see §6).
- DangoMushi additionally requires a material animation:
  `Mgr::loadTexData` attaches `/enemy/data/DangoMushi/dangomushi.brk`
  (DangoMushiMgr.cpp:13,71-84) and `Mgr::createModel` rebuilds the `body`
  material display list (DangoMushiMgr.cpp:90-112). SnakeCrow/SnakeWhole have
  no such material bank.
- DangoMushi registers falling helpers in the manager allocation path:
  generalEnemyMgr.cpp:842-848 tops up `EnemyID_Egg` to 10 and `EnemyID_Rock`
  to 30, and `Obj::createCrashEnemy` births them (DangoMushi.cpp:649-776).
  That child-spawner behavior is source-documented only.

## 2. Shared-base reclassification (explicit)

**SnakeCrow + SnakeWhole are one shared-base pair. DangoMushi is distinct.**

| Species | Family classification | Code base | Animator base | Shared with |
|---|---|---|---|---|
| SnakeCrow | Snagret (shared base) | `Game::SnakeJointMgr` | `EnemyAnimatorBase::ProperAnimator` | SnakeWhole |
| SnakeWhole | Snagret (shared base) | `Game::SnakeJointMgr` | `EnemyAnimatorBase::ProperAnimator` | SnakeCrow |
| DangoMushi | Segmented Crawbster (standalone) | none (direct `EnemyBase`) | `EnemyBlendAnimatorBase::ProperAnimator` | — |

Evidence:

- `Game::SnakeJointMgr` is the spine driver shared by both snagrets. Its owner
  comment is literally `// _00, SnakeCrow obj or SnakeWhole obj`
  (SnakeJointMgr.h:30) and it drives the six `bodyjnt3`-`bodyjnt8` joints
  (SnakeJointMgr.h:47).
- Both objects construct it: `SnakeCrow::Obj::createJointCallBack` does
  `new SnakeJointMgr(this)` (SnakeCrow.cpp:1471) and
  `SnakeWhole::Obj::createJointCallBack` does the same (SnakeWhole.cpp:1898).
- The two `ProperAnimator` implementations are the same thunk pair at the same
  address (`0x8034B63C`, `0x8034B644`): SnakeCrowAnimator.cpp:9-21 ==
  SnakeWholeAnimator.cpp:9-21.
- The proper-parm blocks share `fp01/fp11/fp12/fp21`; SnakeWhole is the
  reduced variant (no `mWFGHealth`/fp31) and inserts the `run1` jump clip at
  AnimID slot 12 (SnakeWhole.h:236-241).
- **DangoMushi is not a snagret and not a chappy/bulborb base.**
  `DangoMushi::Obj : public EnemyBase` directly (DangoMushi.h:72), uses
  `EnemyBlendAnimatorBase` for its segmented, blended body (DangoMushi.h:224),
  never constructs a `SnakeJointMgr`, and has no `ChappyBase` base, FSM or
  parameter block. Its body is driven by `animate()` +
  `mMatLoopAnimator->animate(30.0f)` (DangoMushi.cpp:106-134) and the brk
  material loop.

## 3. AI / state machines

Each species registers its own FSM in `*State.cpp`; the enums match the
registration order.

| Species | States (registration) | Sketch |
|---|---|---|
| SnakeCrow | 9 (SnakeCrowState.cpp:21-33) | Stay underground → Appear1/Appear2 (fast vs. slow emerge, `mFastAppearChance` chooses) → Wait → Attack (5 directional bite anims) → Eat (swallows head-stuck Pikmin with poison damage) → Struggle → Disappear (`dive` burrow) → Dead. Unused `SNAKECROW_NULL = -1`. |
| SnakeWhole | 11 (SnakeWholeState.cpp:21-35) | Same burrow/emerge/attack/eat/struggle core, plus Walk (`run1` leap at fp06=1000) and Home (return within home range); `isOutTerritory`/`isInHomeRange` gate the walk/home loop (SnakeWhole.cpp:245-257). |
| DangoMushi | 9 (DangoMushiState.cpp:15-28) | Stay (falls from above via shadow scale) → Appear (fly) → Wait → Move → Attack (ball roll, `DANGOANIM_Attack`, press damage) → Turn (wall crash, invulnerable flip) → Recover → Flick (`attack2` arm swing) → Dead. No idle buried state; rolls on `mIsRolling`. |

State ID enums: SnakeCrow.h:54-66, SnakeWhole.h:53-67, DangoMushi.h:23-35.
DangoMushi's crash/turn path is the only source use of `KEYEVENT_LOOP_START`
in this family (DangoMushiState.cpp:530).

## 4. Animation clips and event streams

Clip order equals each `AnimID` enum (SnakeCrow.h:225-243, SnakeWhole.h:223-242,
DangoMushi.h:210-222), the per-species `enemyanimmgr.txt` row order, and the
`.bca` member names in `anim.szs`. `EXPECTED_EVENTS` in
`experimental/pikmin2_snagret_assets.py` records the **exact disc `(frame,
type)` key events**; the trailing `-1` is the registry terminator, not an event,
and `KEYEVENT_END` (1000) is generated on clip completion rather than stored.
The disc DangoMushi bank omits the `{` before `attack_2.bca`, so the module
parses records by their `-1` terminator instead of the shared brace parser.

| Species | Slots | Clips | Notable event streams |
|---|---|---|---|
| SnakeCrow | 13 | dead, appear1, appear2, dive, hit_near, hit, hit_far, hit_r, hit_l, wait1, waitact1, waitact2, type5 | dead 67:2,75:2,110:5,131:3,143:4,149:4; appear2 20:2,58:3,115:4,141:5; hit_near 33:2,36:3,48:4 |
| SnakeWhole | 14 | dead, appear1, appear2, dive, hit_near, hit, hit_far, hit_r, hit_l, wait1, waitact1, waitact2, run1, type5 | dead 65:5,89:2,118:3,131:4; appear2 20:2,58:3,115:4,145:5,159:6; run1 10:0,10:2,32:3,34:1 |
| DangoMushi | 9 | fly, wait, move, attack, attack_2, turn, recover, dead, carry | attack 6:2,17:3,23:4,50:0,100:1,118:5 (LOOP_END roll gate); turn 10:2,32:0,81:1,108:3,114:4 (LOOP_START); attack_2 26:2,32:3,38:2,50:3,57:2,65:3 |

Event-type semantics come directly from the state reads cited in the module
(SnakeCrowState.cpp:58-87,245-272,313-353,395-424,456-526,554-632,657-687,
713-738; SnakeWholeState.cpp:60-90,251-301,343-398,433-474,510-541,568-626,
654-695,722-817,842-887,913-951; DangoMushiState.cpp:53-78,171-212,249-287,
316-379,411-465,507-554,587-607,637-670). The attack stems are the disc
spellings `hit_near`/`hit`/`hit_far` (SnakeCrow.h:232-236, SnakeWhole.h:230-234)
and DangoMushi flick is `attack_2` (DangoMushi.h:210-222).

## 5. Retail parameters (header defaults vs disc)

Headers list **build-time defaults**; the disc block is the retail value. The
module keeps `GENERAL_DEFAULTS`/`PROPER_PARM_DEFAULTS` (header) separate from
`DISC_PARMS` (retail) and never flattens them.

General `EnemyParmsBase` header defaults are declared in EnemyParmsBase.h:55-101
(fp00 life 100, fp06 speed 80, fp09 territory 200, fp10 home 15, fp12 sight 200,
fp32 LOD 40, …). Retail values differ substantially:

| General parm | SnakeCrow | SnakeWhole | DangoMushi | Header default |
|---|---|---|---|---|
| fp00 life | **1500** | **5000** | **3000** | 100 |
| fp06 speed | **0** (stationary) | **1000** (leap) | **50** | 80 |
| fp09 territory | **80** | **380** | **150** | 200 |
| fp10 home | 100 | 100 | 100 | 15 |
| fp11 private | 100 | 100 | 150 | 70 |
| fp12 sight | 150 | 400 | 500 | 200 |
| fp20/21 attack range/angle | 0/0 (bite only) | 0/0 | **300/15** (ranged shock) | 70/15 |
| fp24 attack damage | 10 | 10 | 10 | 10 |
| fp28 max turn | 10 | 10 | **5** | 10 |
| fp32 LOD | 225 | 225 | 250 | 40 |
| fp33/34 | 111/5 | 130/5 | 200/50 | 40/40 |
| fp36/37/38 purple | 50/0.1/5 | 50/0.01/5 | 10/0/0 | 10/0.05/10 |

Proper blocks: header constructor defaults stay in `PROPER_PARM_DEFAULTS`; the
disc block is re-read into `DISC_PARMS`. The disc values are **not** the header
defaults (only DangoMushi fp01 coincides), and the DangoMushi disc block stores
only fp01/fp02/fp03 — fp10 is absent, so the header `mFlipTime` 7.5 is reported
as defaulted:

| Species | Header proper defaults | Disc proper values |
|---|---|---|
| SnakeCrow | fp01 0.8, fp11 2.0, fp12 1.0, fp21 300.0, fp31 `mWFGHealth` 7500.0 | fp01 0.6, fp11 2.5, fp12 2.5, fp21 200.0, fp31 2500.0 |
| SnakeWhole | fp01 0.8, fp11 2.0, fp12 1.0, fp21 300.0 (no fp31) | fp01 0.6, fp11 0.5, fp12 2.5, fp21 400.0 |
| DangoMushi | fp01 rolling speed 200.0, fp02 turn accel 0.1, fp03 max turn 10.0, fp10 flip time 7.5 | fp01 200.0, fp02 0.03, fp03 3.0 (fp10 not stored; header default 7.5) |

SnakeCrow-specific source behavior: in White Flower Garden cave `f_02`
story mode, `setParameters()` overrides `mHealth` with the proper
`mWFGHealth` (fp31) value (SnakeCrow.cpp:95-105).

## 6. Resource map on disc

All paths are under the US GPVE01 rev 0 disc. Each species reads its own bank;
there is no shared model.

| Resource | Path | Notes |
|---|---|---|
| SnakeCrow model | `enemy/data/SnakeCrow/model.szs` (`enemy.bmd`) | SnakeCrowMgr.cpp:49-57 |
| SnakeCrow anim | `enemy/data/SnakeCrow/anim.szs` (13 `.bca`) | SnakeCrowMgr.cpp |
| SnakeCrow metadata | `enemy/parm/enemyParms.szs/snakecrow/{enemyanimmgr,enemyparm,enemycoll,enemystoneinfo}.txt` | enemyInfo.cpp:62 |
| SnakeWhole model | `enemy/data/SnakeWhole/model.szs` | SnakeWholeMgr.cpp:49-57 |
| SnakeWhole anim | `enemy/data/SnakeWhole/anim.szs` (14 `.bca`) | SnakeWholeMgr.cpp |
| SnakeWhole metadata | `.../snakewhole/*` | enemyInfo.cpp:63 |
| DangoMushi model | `enemy/data/DangoMushi/model.szs` | DangoMushiMgr.cpp:57-65 |
| DangoMushi anim | `enemy/data/DangoMushi/anim.szs` (9 `.bca`) | DangoMushiMgr.cpp |
| DangoMushi brk | `enemy/data/DangoMushi/dangomushi.brk` | DangoMushiMgr.cpp:13,71-84 |
| DangoMushi metadata | `.../dangomushi/*` | enemyInfo.cpp:113 |

## 7. Reproducible extraction path

Module: `experimental/pikmin2_snagret_assets.py` (follows the ground-invert /
dweevil lane pattern; no edits to neighbour modules or shared converters).

```
python -m experimental.pikmin2_snagret_assets \
    --iso output/pikmin2-runtime/pikmin2-source-test.iso \
    --source native/pikmin2-research \
    --output output/p2-lane-verify/snagret2 --pose-limit 2
```

Reads only the three `enemy/data/<Species>/{model.szs,anim.szs}` pairs, the
DangoMushi `dangomushi.brk`, and the three `<species>/*` metadata files from
`enemy/parm/enemyParms.szs`. Output (private, not committed): per-species
`enemy.bmd`, all `.bca` clips, the four metadata text files, sampled rigid
`.mod` pose files + conversion JSON, and a hashed `snagret.json` manifest
(`schema=1`, disc id/revision, source revision, per-file SHA-256,
`native_ready=false`, `gameplay_events_executed=false`, `btk_playback=false`),
plus `p2-snagret.txt`. A pose the converter cannot bake (e.g. a singular normal
transform) is recorded with `unsupported_reason` instead of aborting the run.

Conversion note: all three species carry the `TEX1MTXIDX` display-list
attribute (`setTexMtxLoadType(0x2000)`), so poses are baked through the
explicit-draw-matrix path and immutable render resources are pinned.
Reproducibility evidence: extract hashes every disc resource read; duplicate
runs must produce identical `snagret.json`.

## 8. Tests

`tests/test_pikmin2_snagret_assets.py` — mirror of the ground-invertebrate
test layout with synthetic parameter blocks and a mocked disc:

- **Registry/profiles**: IDs 34/70/94 → correct `SPECIES`/state/clip/event
  maps; SnakeCrow 13 clips, SnakeWhole 14, DangoMushi 9; disc spellings
  `hit_near`/`hit_far`/`attack_2`.
- **Shared-base**: `SnakeJointMgr` base for both snagrets; DangoMushi
  `base_class is None`, empty `shared_with`, `EnemyBlendAnimatorBase`.
- **Parm separation**: retail general values match `DISC_PARMS` while header
  defaults stay distinct (e.g. fp00 1500/5000/3000 vs 100; fp09 80/380/150 vs
  200); proper header defaults/retail are reported separately, and DangoMushi
  fp10 is recorded as defaulted from the header.
- **Disc parser**: the terminator-based `animation_rows` accepts the DangoMushi
  bank whose `attack_2.bca` record is missing its opening brace.
- **Rejection**: unknown general key (fp07/fp99), unknown proper key, general
  and proper disc drift, omitted proper key, clip-order mismatch and
  event-stream mismatch are all rejected.
- **Budget/gate**: pose-limit validation enforces 2..12 before any IO; output
  overwrite is refused before source access; the wrong disc (`GPVJ01`) is
  refused with no output. TEXT non-claims are asserted.

## 9. Open / handoff items

- Exact `.bca` key-event frames and per-file disc hashes are now re-extracted
  (`EXPECTED_EVENTS`); loop attributes are `2` (repeat) for all 36 clips, and
  the attack stems are the disc `hit_near`/`hit`/`hit_far` (DangoMushi
  `attack_2`). A few sampled poses are converter-unsupported (singular normal
  transform) and are recorded with a reason; no opt-in tolerance is enabled.
- The disc proper blocks were independently re-read: SnakeCrow fp11 2.5 / fp12
  2.5 / fp21 200.0 / fp31 2500.0, SnakeWhole fp11 0.5 / fp12 2.5 / fp21 400.0,
  DangoMushi fp02 0.03 / fp03 3.0 with fp10 absent. `mWFGHealth` (fp31) is the
  disc value 2500, not the header default 7500.
- Native hook wiring (SnakeJointMgr spine callback, shared-base spawn profile,
  five-directional bite selection, DangoMushi roll/turn crash, falling
  Rock/Egg helper lifetime, brk material loop) belongs to the native/integration
  track — none touched here.
- DangoMushi's falling Rock/Egg child spawner (generalEnemyMgr.cpp:842-848)
  and SnakeCrow's White Flower Garden health override are source-documented
  only.
- Parallel lanes (other #174 batches, Long Legs #173, Waterwraith/Titan #175)
  untouched; no shared-file changes required by this lane.
