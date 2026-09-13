# Waterwraith / roller lane source audit — Tyre (98), BlackMan (99)

Issue: [#352](https://github.com/4laric/pikmin-randomizer/issues/352) (parent
[#175](https://github.com/4laric/pikmin-randomizer/issues/175)).
Source: `native/pikmin2-research` decompilation against US GPVE01 rev 0.
Evidence level achieved: **source contract + converted assets** (per
[the import pipeline](PIKMIN2_ENEMY_IMPORT_PIPELINE.md)); no native hook wiring
in this lane. Pikmin 1 counterpart mapping is **not** claimed. No ISO was
available in this workstream, so retail numeric values below are taken from the
parent #175 Waterwraith/Titan audit's disc annotations and are flagged where
unverified; every structural field is derived directly from the decomp headers,
sources and registration tables cited inline.

## 0. Reclassification and evidence level

This lane retires an earlier grouping that treated the rollers as part of the
Waterwraith boss. They are two distinct enemy IDs with a parent/child relation:

- **98 `Tyre` is a helper.** `enemyInfo.cpp:112` registers it `BDT_Empty`,
  parent ID `-1`, no child, no Piklopedia row (parent #175 audit §1); it is
  **absent** from `IS_ENEMY_BOSS` (`include/Game/enemyInfo.h:214-219`). It has no
  steering or AI of its own: the wraith births it and pushes position,
  velocity, facing and scale into it every frame (`blackMan.cpp:159-167`,
  `:448-478`, `:982-995`).
- **99 `BlackMan` is the boss.** `enemyInfo.cpp:111` registers it `BDT_Boss`
  with `childID = EnemyID_Tyre, childNum = 1`; it **is** in `IS_ENEMY_BOSS`
  (`include/Game/enemyInfo.h:214-219`). It is spawned by cave-layout code, not a
  surface generator (parent #175 audit §1).

**Retained assembly caveat.** `BlackMan::walkFunc`, `findNextRoutePoint`,
`findNextTraceRoutePoint`, `setPathFinder`/`releasePathFinder` and the
`lHand`/`rHand`/`lFoot`/`rFoot`/`body` matrix callbacks are reconstructed
beside retained PowerPC assembly (`blackMan.cpp:831+` and the trailing asm
block at `:1938+`) and the roller/tube shadow code (`plugProjectNishimuraU/
TyreShadow.cpp`). **Their evaluation order is inferred, not authoritative.**
Nothing in this lane executes them; this is a source/asset contract only.

## 1. Identity and registration

| ID | Constant | Common name | Obj / Mgr class | Registry (`src/plugProjectYamashitaU/generalEnemyMgr.cpp`) | Spawn table (`src/plugProjectYamashitaU/enemyInfo.cpp`) |
|---|---|---|---|---|---|
| 98 | `EnemyID_Tyre` (`include/Game/enemyInfo.h:157`) | Waterwraith rollers | `Game::Tyre::Obj` / `Mgr` (`Tyre.h:48,125`) | `:494-496` — `new Tyre::Mgr(limit, viewNum)` | `:112` — `EFlag_CanBeSpawned \| 2 \| EFlag_UseOwnID`, `BDT_Empty` |
| 99 | `EnemyID_BlackMan` (`include/Game/enemyInfo.h:158`) | Waterwraith | `Game::BlackMan::Obj` / `Mgr` (`BlackMan.h:42,202`) | `:491-493` — `new BlackMan::Mgr(limit, viewNum)` | `:111` — `EFlag_CanBeSpawned \| 2 \| EFlag_UseOwnID`, `BDT_Boss`, child `EnemyID_Tyre` ×1 |

- Both rows have **all-empty resource slots**, so each loads its own
  `enemy/data/<OwnName>/` bank (`enemyMgrBase.cpp:519-533`, `:539-564`). No
  aliasing between the two.
- `EmpireInfo`/manager include sites: `generalEnemyMgr.cpp:7` (BlackMan),
  `:63` (Tyre).
- `BDT_Boss` gives BlackMan boss music and a boss drop table; `BDT_Empty` gives
  Tyre no carcass, no drops and no entry in `IS_ENEMY_BOSS` (evidence above).

## 2. AI / state machine

FSM registration: `tyreState.cpp:10-17` (Tyre), `blackManState.cpp:18-30`
(BlackMan). State IDs (`Tyre.h:235-240`, `BlackMan.h:367-378`):

| Species | States (ID → name) |
|---|---|
| Tyre | 0 `move`, 1 `land`, 2 `freeze`, 3 `dead` |
| BlackMan | 0 `walk`, 1 `dead`, 2 `freeze`, 3 `bend`, 4 `escape`, 5 `fall`, 6 `flick`, 7 `recover`, 8 `tired` |

| Species | Sketch |
|---|---|
| Tyre | Starts in `land` (`tyre.cpp:79`); floor contact → `flick`, land effect, `freeze` (`tyreState.cpp:105-115`). Wraith `moveRestart` → `move` (`Tyre.cpp:565-572`). Quake while moving → `freeze` (`tyre.cpp:347-353`). Death only when health ≤ 0 **and** the wraith has set `EB_Invulnerable` after its dismount (`tyreState.cpp:67-69`, `:152-153`), playing `tyre_getoff` and killing on the end key. |
| BlackMan | `walk` route-finds toward pod/waypoints, regenerating 5 HP/frame while riding (`blackMan.cpp:843-848`); two-step speed after `mTimerToTwoStep` frames. `isTyreFreeze` → `bend`; `isStartFlick` → `flick`; `isTyreDead` → `escape`. `fall` (hard constraint) → `recover` → `walk`. `freeze` (`kagebozu_bend2`) is the rollerless stun; `tired` (`kagebozu_wait2`) precedes the post-escape wind-down; `dead` releases the held treasure on key 5 and kills on end. |

All of the above is **reconstructed-evaluation-order** where the function body
sits beside retained assembly (see §0).

## 3. Roller lifecycle notes

- Birthed by `BlackMan::onInit` (`blackMan.cpp:159-167`), `mOwner` set back to
  the wraith. Starts underground/constrained in `land`.
- On first floor contact `StateLand::exec` flicks and enters `freeze`
  (`tyreState.cpp:105-115`); `moveStart` releases the constraint and enters
  `move` (`tyre.cpp:565-572`).
- Six collision spheres `tyr1`..`tyr6` become stickable only in `freeze`/stone:
  `collisionStOn`/`collisionStOff` (`tyre.cpp:578-601`).
- Roll rate = distance travelled ÷ `WRAITH_ROLLER_CIRCUMFERENCE` (44π,
  `Tyre.h:15`), scaled by proper `fp01` (`blackMan.cpp:988-995`,
  `tyreState.cpp:51-65`). Front wheel leans with steering angle
  (`tyre.cpp:421-475`); rear wheel follows terrain with a ±50 clamp
  (`tyre.cpp:481-559`).
- Shadow is two joint tubes scaled from 0.01 to 1 after the fall begins
  (`tyre.cpp:721-727`, `plugProjectNishimuraU/TyreShadow.cpp:217-257`).
- Dead (`tyre_getoff`) fires two burst effects and kills on the end key
  (`tyreState.cpp:180-197`, `tyre.cpp:648-658`).

## 4. Animation events (per-species `enemyanimmgr.txt`)

Clip order = AnimID enum order (`Tyre.h:201-205`, `BlackMan.h:338-354`) =
`enemyanimmgr.txt` row order. Format frame → event type; 0/1 = loop bounds,
2/3/4/5 = native/visual hooks.

| Species | Clips | Notable event streams |
|---|---|---|
| Tyre | `tyre_move`, `tyre_getoff` | none declared: the retained FSM consumes only the terminal `KEYEVENT_END` (`tyreState.cpp:194`) and references no per-frame key, so streams are recorded empty pending disc verification |
| BlackMan | `kagebozu_bend`, `bend2`, `dead`, `flick`, `flick2`, `getoff`, `move`, `recover`, `run`, `wait`, `wait2`, `walk`, `through`, `land` | dead 14→2, 65→3, 102→4, 125→5; getoff 5→2, 13→3, 21→4, 26→5; recover 14→2, 41→3, 43→4, 50→5; run 0→0, 1→2, 5→3, 11→1; walk 7→0, 20→2, 35→3, 36→1; bend 4→2, 5→0, 24→1; land 0→0, 0→1, 4→2; through 6→0, 6→1 |

The source `enemyanimmgr.txt` is preserved verbatim in each species folder and
validated. Events are **data only** — no native execution in this lane.

## 5. Parameters (header defaults vs retail)

Headers list **build-time defaults**; `enemy/parm/enemyParms.szs` may override
them. The module reports the two separately and, for BlackMan, records
`proper_keys_defaulted_from_header` for keys the parent audit lists without a
disc value (`ip03`..`ip06`).

| Species | Proper key (member, source) | Header default | Retail (disc) |
|---|---|---|---|
| Tyre | `fp01` `mTyreRotationSpeed` (`Tyre.h:159`) | 0.5 | 25.0 |
| BlackMan | `fp01` `mPodMoveSpeed` (`BlackMan.h:238`) | 10.0 | 20.0 |
| BlackMan | `fp02` `mEscapeSpeed` (`:240`) | 10.0 | 250.0 |
| BlackMan | `fp03` `mEscapeRotationSpeed` (`:241`) | 0.1 | 0.2 |
| BlackMan | `fp04` `mMaxEscapeRotationStep` (`:242`) | 10.0 | 30.0 |
| BlackMan | `fp05` `mTravelSpeed` (`:244`) | 200.0 | 120.0 |
| BlackMan | `fp06` `mRotationSpeed` (`:245`) | 0.1 | 0.04 |
| BlackMan | `fp07` `mMaxRotationStep` (`:246`) | 10.0 | 3.0 |
| BlackMan | `fp11` `mWalkingSpeed` (`:248`) | 10.0 | 50.0 |
| BlackMan | `ip01` `mTimerToTwoStep` (`:249`) | 300 | 0 |
| BlackMan | `ip03` `mDosinStopTimerLength` (`:250`) | 200 | header default (not asserted) |
| BlackMan | `ip04` `mFreezeTimerLength` (`:251`) | 200 | header default (not asserted) |
| BlackMan | `ip05` `mContinuousEscapeTimerLength` (`:252`) | 200 | header default (not asserted) |
| BlackMan | `ip06` `mStandStillTimerLength` (`:253`) | 200 | header default (not asserted) |

General-block disc values asserted by the module: BlackMan `fp00` life 1500;
Tyre `fp00` life 1800 and `fp24` attack damage 10. Tags `fp08`-`fp10` and
`ip02` do not exist (`BlackMan.h:234-270` and parent #175 audit §Waterwraith).
The valid general key set is copied from `EnemyParmsBase.h:55-101` (`fp00`-
`fp38` except `fp07`, plus `ip01`-`ip07`).

## 6. Resources on disc

| Species | Model | Anim | Extra | Parm metadata (`enemy/parm/enemyParms.szs/<species>/`) |
|---|---|---|---|---|
| Tyre | `enemy/data/Tyre/model.szs` → `enemy.bmd` | `enemy/data/Tyre/anim.szs` | — | `tyre/{enemyanimmgr,enemyparm,enemycoll,enemystoneinfo}.txt` |
| BlackMan | `enemy/data/BlackMan/model.szs` → `enemy.bmd` | `enemy/data/BlackMan/anim.szs` | `enemy/data/BlackMan/kagebozu_model.btk` (`blackManMgr.cpp:58-71`) | `blackman/{enemyanimmgr,enemyparm,enemycoll,enemystoneinfo}.txt` |

- `enemy.bmd` inside `model.szs` is the loader contract (`enemyMgrBase.cpp:494`,
  `:519-533`); `anim.szs` is mounted the same way (`:539-564`).
- Both managers call `setTexMtxLoadType(0x2000)` on every shape
  (`tyreMgr.cpp:38-47`, `blackManMgr.cpp:43-52`), so poses are baked through the
  explicit draw-matrix path (`decode(..., bake_rigid=True,
  draw_matrices=draw_matrices(blocks(model), pose))`).
- `kagebozu_model.btk` is hashed and preserved but never played.
- Collision parts: roller `tyr1`..`tyr6` (`tyre.cpp:231-236`); wraith `kosi`,
  `mune`, `head` (`blackMan.cpp:336-338`, `:557-559`).
- The `enemystoneinfo.txt` slot is kept from the shared parm-archive contract
  inherited from the ground-invertebrate lane; it is not independently verified
  for these two IDs without an ISO.

## 7. Reproducible conversion path

Module: `experimental/pikmin2_waterwraith_assets.py` (follows the
ground-invertebrate lane; no edits to neighbour modules or shared converters).

```
python -m experimental.pikmin2_waterwraith_assets \
    --iso output/pikmin2-runtime/pikmin2-source-test.iso \
    --source native/pikmin2-research \
    --output output/pikmin2-waterwraith-assets/run1 --pose-limit 3
```

Reads only the two `enemy/data/<Name>/{model.szs,anim.szs}` pairs, the BlackMan
`kagebozu_model.btk`, and the two `<species>/*` metadata sets from
`enemy/parm/enemyParms.szs`. Output (private, not committed): per-species
`enemy.bmd`, all `.bca` clips, the four metadata text files, the `.btk`, sampled
rigid `.mod` pose files + conversion JSON, and a hashed `waterwraith.json`
manifest (`schema=1`, disc id/revision, source revision, per-file SHA-256) plus
`p2-waterwraith.txt`. Extra resources are recorded under each species'
`extra_resources`. Duplicate runs must produce identical `waterwraith.json`.

## 8. Tests

`tests/test_pikmin2_waterwraith_assets.py` — mirror of the ground-invertebrate
test layout with a mocked disc reader:

- **Registry**: IDs 98/99 → `SPECIES`/clip/event/state maps, 2 and 14 clips.
- **Parm parsing**: retail `DISC_PARMS` values validated; header defaults kept
  separate; BlackMan `ip03`..`ip06` recorded as
  `proper_keys_defaulted_from_header`.
- **Rejection**: general key (`fp07`/`ip99`), proper key (`fp99`), disc-param
  drift (general health, proper `fp01`/`fp02`), clip order and event-stream
  drift all raise `ValueError`.
- **Budget/gate**: pose-limit enforces 2..12 before any IO; output overwrite is
  refused before source access; disc header/revision gate rejects non-`GPVE01`
  with no output directory created.

## 9. Open / handoff items

- Native hook wiring (cave `mIsWaterwraithAlive` gate, floor `f016` timer, route
  pathfinding, joint callbacks, XFB/BTK material, boss music, treasure throw)
  belongs to the native track / integration lead — none touched here.
- The retained-assembly functions in §0 need a natural-runtime pass before any
  behavior claim; this lane only pins the source/asset contract.
- `enemystoneinfo.txt` presence for IDs 98/99 and the exact disc proper-block
  membership of `ip03`..`ip06` need one ISO read to confirm.
- Parallel lanes (BigTreasure 73, DangoMushi 94, Bulblax, Breadbug, Mamuta,
  flying/aquatic families) untouched; no shared-file changes required.

## 10. Batch 2 — install + arena (#352)

Batch 2 takes the batch-1 `waterwraith.json` assets into the runtime through the
shared core (`experimental/pikmin2_batch2_core.py`) bound by
`experimental/pikmin2_waterwraith_install.py` and
`pikmin2_waterwraith_arena.py`.

- **Install**: hash-bound `plan`/`install`/`verify_install`; schema-1
  `P2_WATERWRAITH_1` manifest, exact-byte pose binding, conflict refusal before
  mutation, optional all-or-nothing visual bank (baseline preserved when
  absent). Actors are BlackMan (boss) and Tyre (dependent roller child).
- **Arena**: private original Impact Site staging — BlackMan, Tyre and one
  ordinary P1 control, unique generator IDs 352001–352003, full expected XYZ,
  zero offset, source yaw unapplied. Staging the dependent Tyre child as an
  independent vehicle is an engineered choice; identity is not claimed and the
  neutral Chappy placement vehicle is used.
- **Real-disc evidence**: install + verify round-trip against
  `output/p2-lane-verify/waterwraith/waterwraith.json` → **30 installed, 30
  verified** (SHA-256 bound). Generated evidence stays under private `output/`.
- **Status**: install + arena staging level. Native gates (`native_identity`,
  `natural_AI`, `combat`, `death_corpse`, `boss_phases`, `tyre_roll_crush`,
  `purple_vulnerability`, `boss_corpse`) are BLOCKED pending the hook request on
  #186. No shared/native code touched; no disc assets committed.
