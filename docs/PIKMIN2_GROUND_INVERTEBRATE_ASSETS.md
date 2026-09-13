# Ground-invertebrate lane source audit — Armor (15), ElecBug (28), Imomushi (65), TamagoMushi (68), Sokkuri (79), Hana (84)

Issue: [#346](https://github.com/4laric/pikmin-randomizer/issues/346) (parent [#165](https://github.com/4laric/pikmin-randomizer/issues/165)).
Source: `native/pikmin2-research` decompilation against US GPVE01 rev 0; retail
resources verified against the local legally supplied disc copy
(`output/pikmin2-runtime/pikmin2-source-test.iso`, header `GPVE01` rev 0).
Evidence level achieved: **source contract + converted assets** (per
[the import pipeline](PIKMIN2_ENEMY_IMPORT_PIPELINE.md)); no native hook wiring
in this lane. Pikmin 1 counterpart mapping is **not** claimed in this lane.

## 1. Identity and registration

| ID | Constant | Common name | Obj / Mgr class | Registration |
|---|---|---|---|---|
| 15 | `EnemyID_Armor` (enemyInfo.h:74) | Cloaking Burrow-nit | `Game::Armor::Obj` / `Mgr` | generalEnemyMgr.cpp:271 |
| 28 | `EnemyID_ElecBug` (enemyInfo.h:87) | Anode Beetle | `Game::ElecBug::Obj` / `Mgr` | generalEnemyMgr.cpp:298 |
| 65 | `EnemyID_Imomushi` (enemyInfo.h:124) | Ravenous Whiskerpillar | `Game::Imomushi::Obj` / `Mgr` | generalEnemyMgr.cpp:427 |
| 68 | `EnemyID_TamagoMushi` (enemyInfo.h:127) | Mitite | `Game::TamagoMushi::Obj` / `Mgr` | generalEnemyMgr.cpp:436 |
| 79 | `EnemyID_Sokkuri` (enemyInfo.h:138) | Skitter Leaf | `Game::Sokkuri::Obj` / `Mgr` | generalEnemyMgr.cpp:485 |
| 84 | `EnemyID_Hana` (enemyInfo.h:143) | Creeping Chrysanthemum | `Game::Hana::Obj` / `Mgr` | generalEnemyMgr.cpp:488 |

- Spawn table: `src/plugProjectYamashitaU/enemyInfo.cpp` — all six are
  `EFlag_CanBeSpawned | 2 | EFlag_UseOwnID` concrete spawnables with **all-empty
  resource slots**, so each loads its own `enemy/data/<OwnName>/` model+anim
  bank (Armor cpp:32, Imomushi cpp:34, ElecBug cpp:51, Hana cpp:59,
  TamagoMushi cpp:101, Sokkuri cpp:109). No aliasing between species — each has
  its own `model.szs`/`anim.szs` on disc.
- Hana is the exception in family terms: `Game::Hana::Obj` inherits
  **`ChappyBase::Obj`** (Hana.h:14) — same attack/death/flick FSM as the
  bulborb family — but `Hana::Mgr` inherits `EnemyMgrBase` directly (Hana.h:50)
  and never overrides `loadAnimData`/textures (HanaMgr.cpp:47-55), so it owns
  its own `enemy/data/Hana/` model + anim bank and keeps an extra `mBuried`
  flag at `_2E4` (Hana.h:46) exposed through `isUnderground()` (Hana.h:33).
- `loadModelData` for both Sokkuri (SokkuriMgr.cpp:49-57) and Hana
  (HanaMgr.cpp:47-55) calls `setTexMtxLoadType(0x2000)` on every J3D shape —
  these two need the explicit draw-matrix pose path (see §7).

### Helper / adjacent entries (explicit classification)

| Entry | Classification | Evidence |
|---|---|---|
| `Game::Egg` (ID 37, `EnemyID_Egg`) | **Helper spawner**, not an invert; spawns 10 TamagoMushi children (`childID = EnemyID_TamagoMushi, childNum = 10`) | enemyInfo.cpp:65, enemyInfo.h:106; generalEnemyMgr.cpp:325 |
| `Game::BigFoot` (ID 69, `EnemyID_BigFoot`) | Adjacent spawner of 30 TamagoMushi (`childNum = TAMAGOMUSHI_GROUP_COUNT`); **not claimed by this lane** | enemyInfo.cpp:94, enemyInfo.h:212 |
| `Hana::Obj` inherit path | Not a separate registered entry — Hana is one of the claimed six, sharing ChappyBase FSM code | Hana.h:14 |
| `Game::Hanachirashi` (ID 55, Withering Blowhog) | Out of scope (another lane); distinct manager, not related to Hana | generalEnemyMgr.cpp:397 |

## 2. AI / state machine

Each species has its own FSM registered in its `*State.cpp`; Hana reuses the
ChappyBase FSM. State ID enums (source lines): Armor `StateID` Armor.h:164-181
(14 states), ElecBug.h:143-155 (10), Imomushi.h:20-37 (14 incl. 3 Zukan
states), TamagoMushi.h:239-247 (6), Sokkuri.h:19-31 (9), ChappyBase.h:176-186
(8).

| Species | States (registration lines) | Sketch |
|---|---|---|
| Armor | 14 (ArmorState.cpp:17-30) | Stay → Appear (surface emerge) → Move/GoHome, side/centre/top attack pick, Attack1/Attack2, Eat after bite, Flick, Fail, Dive (burrow). `EFlag_DayEndMax4` caps surfaced duplicates at day end. |
| ElecBug | 10 (ElecBugState.cpp:21-30) | Wait/Turn/Move stroll; Charge → Discharge (sparks to nearby Pikmin) and ChildCharge/ChildDischarge; Reverse; Return anim; Dead. |
| Imomushi | 14 (ImomushiState.cpp:19-33, one non-register line) | Wait → Stay; Appear/Dive via seed attract; Move / Climb up plants (fp01 climbing speed); FallDive/FallMove when dislodged; Attack with fp11 eating time; GoHome; plus ZukanStay/Appear/Move for Piklopedia. |
| TamagoMushi | 6 (tamagoMushiState.cpp:18-23) | Walk (ip01/ip02 wander times) → Appear/Hide from ground (fp02 appearance range, ip03/ip04 appear times); Turn; Wait; Dead. Timer-limited survival fp01. |
| Sokkuri | 9 (SokkuriState.cpp:18-26) | Stay → Appear (pop from leaf); MoveGround via `run1`/Wait (`wait1`); MoveWater via `wrun1` while submerged (fp21-fp23); Hide (`hide1`); Disappear (`type5` change); Press/Dead/Flick. |
| Hana | 8 (ChappyBase StateID, ChappyBase.h:176-186) | Turn/Dead/Flick/Walk/Attack/TurnToHome/GoHome/Sleep; Sleep is the buried ("underground") state driven by `mBuried`; `isWakeup()`/`resetUnderGround`/`setUnderGround` overridden in Hana.h:23-28. |

TamagoMushi has a special manager limit override in
generalEnemyMgr.cpp:436-443 — a surface spawn is capped at 10, a cave spawn at
`TAMAGOMUSHI_GROUP_COUNT` (30, enemyInfo.h:212). The other five take the
standard per-area `limit` argument.

## 3. Animation events (per-species `enemyanimmgr.txt`)

Clip order = AnimID enum order (precise citations: CLIPS in
`experimental/pikmin2_ground_inverts_assets.py`, `enemyanimmgr.txt` on disc).
Key events (frame → event type; 0/1 = visual loop bounds, 2 = damage.dll/drop
hooks, 3/4 = misc. native hooks) verified byte-exact against the disc:

| Species | Clips | Notable event streams |
|---|---|---|
| Armor | dead, appear, dive, move, attack1, attack2, eat, flick, attack_fail, carry | appear 15/30/45 → 2 (emerge step sfx); attack2 12→0, 14→1 (bite loop), 18→2, 22→3; eat 60 → 2 |
| ElecBug | dead, move, wait, charge, discharge, turn, recover, carry | discharge 8→2 (spark), 10→0, 17→1; turn 30→0, 69→1 |
| Imomushi | dead, set, dive, move1, move2, fall1, fall2, eat, carry | eat 5→0, 10→2, 14→1 |
| TamagoMushi | dead, dive, move, set, wait, carry | set 2→2 (appear in-place); move 0→0, 9→1 |
| Sokkuri | run1, appear1, wait1, hide1, dead1, pdead1, wrun1, flick1, type5 | hide1 6→2; dead1 14→2; pdead1 8→2; wrun1 6→0, 29→1; flick1 14→2, 18→3, 40→4 |
| Hana | attack1, dead, flick, move1, type1, type5, wait2, waitact1, attack2 | attack1 18→2, 71→3 (bite + swallow frames); type1 (burrow) 27→2, 30→0, 100→1, 103→3, 120→4; waitact1 10→0, 40→1 |

As with the bulborb lane, the source `enemyanimmgr.txt` is preserved verbatim
in each species folder and validated; events are **data only** — no native
event execution in this lane.

## 4. Collision

Per-species `enemycoll.txt` (root sphere + children; offsets listed as radius +
joint index / id):

| Species | Root | Children | Stone fragments (enemystoneinfo.txt) |
|---|---|---|---|
| Armor | {none} r40 @jnt6 | {dmg1} r17.5 @jnt1, {none} r22.5 @jnt7 | 17 |
| ElecBug | {none} r32.5 @jnt0 | {none} r17.5 @jnt0 | 23 |
| Imomushi | {none} r17.5 @jnt2 | {body} r12.5 @jnt2 | 6 |
| TamagoMushi | {none} r18 @jnt0 | {body} r13 @jnt0 | 5 |
| Sokkuri | {none} r25 @jnt0 | {head} r10 @jnt0, {body} r12.5 @jnt3 | 17 |
| Hana | {none} r75 @jnt0 | {body} r35 @jnt0, {udeL} r10 @jnt17, {udeR} r10 @jnt19 | 22 |

## 5. Behavior differences (retail, written record)

Retail `enemyparm.txt` values were read from the disc and are validated by the
module. Headers list __build-time defaults__; where a disc block omits a key,
the C++ constructor default applies (that is recorded per species in the
module as `proper_keys_defaulted_from_header`). Most-notable retail facts:

| Trait | Armor (15) | ElecBug (28) | Imomushi (65) | TamagoMushi (68) | Sokkuri (79) | Hana (84) |
|---|---|---|---|---|---|---|
| Life (fp00) | 300 | 500 | 200 | 50 | 120 | 2500 |
| Speed (fp06) | 50 | 30 | 40 | 100 | 120 | 100 |
| Territory (fp09) | 400 | 200 | 500 | 120 | 200 | 300 |
| Home range (fp10) | 30 | 100 | 30 | 30 | 150 | 15 |
| Sight (fp12) | 200 | 200 | 500 | 150 | 150 | 500 (angle 90) |
| Attack damage (fp24) | 10 | 10 | 1000 (via eat) | 0 | 0 | 10 |
| Sweep/attack radii | fp20/22 = 75/75 | fp20/22 = 70/70 | none (0) | none (0) | none (0) | 75 / 80 (angle 25/30) |
| LOD radius (fp32) | 60 | 50 | 40 | 40 | 40 | 100 |
| Proper keys defaulted on disc (from header) | fp12=100 (bridge dmg) | — | — | — | — | fp03=400 (bulborb wake radius, ChappyBase.h) |
| Special gimmick | `EFlag_DayEndMax4` (surface fake-limiter at day end) | flips on its back: flip time fp01=5.0, wait fp02=1.5, discharge fp11=3.0 | climbs plants at fp01=2.0; white-seed circulation fp02=0.3; translate/rotate correction fp90=0.75/fp91=0.075 | survival fp01=180 s; honey-rate fp03=1.0; cave group = 30 | wait probability fp11=0.4 over fp12/fp13=3.25/1.75 s; swims at fp21=25 while submerged | sleep/buried via `mBuried`; poison (white-Pikmin) fp02=2500; foot range fp01=30 |

Hana inherits ChappyBase parameters; its `ChappyParms` block on the disc has
only `fp01` (foot range) and `fp02` (white-Pikmin poison) — the bulborb-style
wake radius `fp03` is not serialized there, so `ChappyBase::Parms` applies its
constructor default 400.0 (`ChappyBase.h:127`). Hana overrides `isWakeup()`
(Hana.h:23), so damage-side wake behavior differs from a plain bulborb.

## 6. Resources on disc

Each species reads `enemy/data/<Species>/{model.szs,anim.szs}` on GPVE01 rev 0,
and `enemy/parm/enemyParms.szs` under `<species>/{enemyanimmgr.txt,
enemyparm.txt,enemycoll.txt,enemystoneinfo.txt}`. Hana additionally has a
separate `enemy/data/Hanachirashi/` set owned by the Withering Blowhog lane
(not read here). Disc hashes are recorded per file in the manifest.

## 7. Reproducible conversion path

Module: `experimental/pikmin2_ground_inverts_assets.py` (follows the sheargrub/
bulblax lane pattern; no edits to neighbor modules or shared converters).

```
python -m experimental.pikmin2_ground_inverts_assets \
    --iso output/pikmin2-runtime/pikmin2-source-test.iso \
    --output output/pikmin2-ground-inverts-assets/run1 --pose-limit 3
```

Reads only: the six `enemy/data/<Species>/{model.szs,anim.szs}` pairs and the
six `<species>/*` metadata files from `enemy/parm/enemyParms.szs`. Output
(private, not committed): per-species `enemy.bmd`, all `.bca` clips, the four
metadata text files, sampled rigid `.mod` pose files + conversion JSON, and a
hashed `ground_inverts.json` manifest (`schema=1`, disc id/revision, source
revision, per-file SHA-256).

Conversion note: Sokkuri and Hana models carry a `TEX1MTXIDX` display-list
attribute (retail sets `setTexMtxLoadType(0x2000)`, SokkuriMgr.cpp:49-57 /
HanaMgr.cpp:47-55), which the plain `convert()` path rejects; poses for every
species are baked through the established explicit-draw-matrix path
(`decode(..., bake_rigid=True, draw_matrices=draw_matrices(blocks(model),
pose))`) so the manifest stays uniform. Immutable render resources are pinned
so a pose set never mutates shared model data.

Reproducibility evidence: extract hashes every disc resource read; duplicate
runs must produce identical `ground_inverts.json`. Limitations are recorded in
the manifest: sampled weighted/rigid poses, no skeletal playback, no
`EVP1`/`DRW1` execution, no flick/bite/spark/gas native events, no install.

## 8. Tests

`tests/test_pikmin2_ground_inverts_assets.py` — mirror of the bulblax test
layout with a mocked disc reader:

- **Registry**: IDs 15/28/65/68/79/84 → correct `SPECIES`/clip/event/state
  maps, distinct resources per species.
- **Parm parsing**: `enemyparm.txt` → blocks; retail parm values match
  `DISC_PARMS`; a proper block may omit header-defaulted keys (Armor fp12;
  Hana fp03) which are recorded as defaulted.
- **Animation registry**: clip list and event streams enforce the disc order;
  malformed/duplicate entries are rejected.
- **Budget/gate**: pose-limit validation enforces 2..12 before any IO; disc
  header/revision and source-revision gates reject the wrong disc or source.

## 9. Open / handoff items

- Native hook wiring (spawn profile, TamagoMushi group capping, Hana
  `mBuried` sleep, ElecBug discharge spark, Armor DayEndMax4 limiter) belongs
  to the native track / integration lead — none touched here.
- Egg (37 as spawner) and BigFoot (69 as spawner) are **not** claimed by this
  lane; their TamagoMushi child linkage is source-documented only.
- Playable-proxy level and arena gates remain unstarted for this family;
  Pikmin 1 counterpart mapping is an explicit integration decision, not made
  here.
- Parallel lanes (Hanachirashi 55, Sheargrub/Shearwig 12-14, Beetle 9-11,
  Bulblax, Breadbug 38-40/83, Mamuta 54) untouched; no shared-file changes
  required by this lane.