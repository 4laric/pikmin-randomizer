# Aquatic-remainder lane source audit — Catfish (26), Tadpole (27), Jigumo (63), UmiMushi (71)

Issue: [#347](https://github.com/4laric/pikmin-randomizer/issues/347) (parent [#167](https://github.com/4laric/pikmin-randomizer/issues/167)).
Source: `native/pikmin2-research` decompilation against US GPVE01 rev 0; retail
resources verified against the local legally supplied disc copy
(`output/pikmin2-runtime/pikmin2-source-test.iso`, header `GPVE01` rev 0).
Evidence level achieved: **source contract + converted assets** (per
[the import pipeline](PIKMIN2_ENEMY_IMPORT_PIPELINE.md)); no native hook wiring
in this lane. Pikmin 1 counterpart mapping is **not** claimed. The source C++
audit is [PIKMIN2_AQUATIC_ENEMY_AUDIT.md](PIKMIN2_AQUATIC_ENEMY_AUDIT.md).

## 1. Identity and registration

| ID | Constant (`enemyInfo.h`) | Common name | Obj / Mgr class | Registration |
|---|---|---|---|---|
| 26 | `EnemyID_Catfish` (enemyInfo.h:85) | Water Dumple | `Game::Catfish::Obj` / `Mgr` | generalEnemyMgr.cpp:292-293 |
| 27 | `EnemyID_Tadpole` (enemyInfo.h:86) | Wogpole | `Game::Tadpole::Obj` / `Mgr` | generalEnemyMgr.cpp:295-296 |
| 63 | `EnemyID_Jigumo` (enemyInfo.h:122) | Hermit Crawmad | `Game::Jigumo::Obj` / `Mgr` | generalEnemyMgr.cpp:424-425 |
| 71 | `EnemyID_UmiMushi` (enemyInfo.h:130) | Ranging Bloyster | `Game::UmiMushi::Obj` (shared `UmiMushi::Mgr`) | generalEnemyMgr.cpp:450-451 |

- Spawn table (`src/plugProjectYamashitaU/enemyInfo.cpp`): Catfish
  (enemyInfo.cpp:49) and Tadpole (:50) are `EFlag_CanBeSpawned | 2 |
  EFlag_UseOwnID` concrete spawnables with **all-empty resource slots**, so each
  loads its own `enemy/data/<OwnName>/` model+anim bank. Jigumo (:100) is the
  same flag triple and additionally advertises `EnemyID_PanHouse` as one child
  (`childNum = 1`). UmiMushi (:103) is `EFlag_CanBeSpawned | 2` with parent
  `EnemyID_UmiMushiBase`, and its seven resource slots all read `"UmiMushi"`.
- The single `UmiMushi::Mgr` serves base, ordinary and Blind objects: its
  `getEnemyTypeID()` returns `EnemyID_UmiMushiBase` (UmiMushi.h:285) and
  `createObj` tags objects per-ID (`EnemyID_UmiMushi`, `EnemyID_UmiMushiBlind`)
  from the per-ID counts (`umiMushiMgr.cpp:86`). The import therefore keys all
  three on one `UmiMushi` asset bank.

### Helper / nonspawnable / alias reclassification (explicit)

| Entry | Classification | Evidence |
|---|---|---|
| `EnemyID_JigumoNest` (64) | **Alias / helper**, no independent table row — resolves to `PanHouse` only in `getEnemyResName` | enemyInfo.h:123; enemyInfo.cpp:168-169; Jigumo child link enemyInfo.cpp:100 |
| `EnemyID_UmiMushiBase` (100) | **Nonspawnable base** — `EFlag_UseOwnID` without `EFlag_CanBeSpawned`; header comment "Bloyster base (crashes)" | enemyInfo.cpp:102; enemyInfo.h:159; genEnemy.cpp:590-591 excludes the base ID from direct generation |
| `EnemyID_UmiMushiBlind` (101) | **Concrete spawnable child** of base 100; shares the `"UmiMushi"` asset slots | enemyInfo.cpp:104; parent column `EnemyID_UmiMushiBase`; header enemyInfo.h:160 |
| `Game::Catfish::Obj` | **Concrete spawnable**, but not an aquatic FSM of its own — inherits `KochappyBase::Obj` and forwards `onInit` to the base | Catfish.h:14; Catfish.cpp:23 |
| `EnemyID_Frog` (17) / `EnemyID_MaroFrog` (18) | Out of scope (separate lane); concrete aquatic spawnables, not part of this remainder batch | enemyInfo.cpp:28-29 |

## 2. AI / state machine

State ID enums (source lines). The module's `STATE_IDS` covers the claimed
states; `_NULL` sentinels and tail counters are excluded.

| Species | States (claimed) | Source lines | Notes |
|---|---|---|---|
| Catfish | 9 (Wait 0 … Press 8) | KochappyBase.h:155-167 | `KOCHAPPY_Demo = 9` exists but is not a normal spawn state. Catfish reuses the KochappyBase FSM (`Catfish.cpp:23`). |
| Tadpole | 6 (Dead 0, Wait 1, Move 2, Amaze 3, Escape 4, Leap 5) | Tadpole.h:19-28 | 6-state FSM registered at TadpoleState.cpp:14. Wait/Move/Escape leap when outside a water box (audit §Frog/Wogpole). |
| Jigumo | 13 (Wait 0 … SMiss 12) | Jigumo.h:36-52 | 14-slot FSM registered at jigumoState.cpp:16 (`create(JIGUMO_StateCount)`). Wait/Appear/Hide/Attack/Miss/Return/Carry/Flick/Eat/Search/SAttack/SMiss. |
| UmiMushi | 10 (Wait 0 … Lost 9) | UmiMushi.h:57-70 | Shared FSM; `Obj::onInit` starts Walk (`umiMushi.cpp:94`). Ordinary and Blind share the FSM and differ by per-ID parameters. |

`mNextState`/FSM flags are runtime behavior and are **not** executed by this
lane; state IDs are installed as data only.

## 3. Animation registry and key events

Clip order and AnimID enum semantics come from the headers; the shipped
`.bca` set and event streams come from each `enemyanimmgr.txt` on disc and are
rebuilt by the module's duplicate-preserving `anim_mgr_rows` parser. Key events
(frame → event type; 0/1 = visual loop bounds, 2 = damage/drop/native hooks,
3/4 = misc. native hooks, higher ints = further native receivers) are preserved
as data only.

| Species | Shipped clips | AnimID source | Notable event streams |
|---|---|---|---|
| Catfish | 7 (Wait1 is registered three times) | KochappyBase.h:129-140 | attack 17→2, 75→3; flick 25→2, 47→3; move1 0→0, 24→1; type5 10→0, 29→1; wait1 (footstep variant) 0→0, 29→1 |
| Tadpole | 6 | Tadpole.h:108-116 | dead 3→2, 17→2; wait1 5→0, 24→1; move1 5→0, 14→1; waitact1 3→2, 12→3; piti1 14→2, 15→0, 29→3, 30→4, 44→1; type5 10→0, 29→1 |
| Jigumo | 17 | Jigumo.h:319-339 | dive1 (`JIGUMOANIM_Eat = 5`, Jigumo.h:326) 23→2 … 80→8; sattack1 15→2 … 115→10; rflick1 14→2, 21→3; runaway1/backrun1 0→0, 19→1; backwait1 0→0, 9→1 |
| UmiMushi | 11 registered + `wait1.bca` unregistered | UmiMushi.h:299-312 (no Wait entry) | attack1 25→2, 39→3, 40→4, 50→5, 66→6; dead1 83→2, 110→3, 113→4; run1 0→0, 59→1; srun1/sturn1 0→0, 39→1; search1 48→2; flick1 9→2 |

Registration rules enforced by the module:

- `MGR_ROWS` records the full `enemyanimmgr.txt` row order **with duplicates**;
  `profile()` requires the parsed registration tuple to equal `MGR_ROWS[species]`.
  Catfish `wait1.bca` is registered three times, and the test suite asserts the
  duplicate count is preserved.
- `EXPECTED_EVENTS` is rebuilt from the **first** registration of each file stem
  (the one a name-index lookup resolves); the later Catfish `wait1` footstep
  variant is still enforced by `MGR_ROWS` order.
- `UNREGISTERED = {'UmiMushi': ('wait1',)}`: `wait1.bca` ships in `anim.szs`
  but has no `enemyanimmgr.txt` row on this revision, and `UmiMushi.h:299-312`
  has no Wait AnimID. It is cataloged and pose-sampled as unregistered. The
  module refuses to treat a shipped clip as neither registered nor unregistered.

## 4. Header defaults vs retail disc values

Proper-parameter header defaults: KochappyBase.h:105-107 (Catfish),
Tadpole.h:87-88, Jigumo.h:98-103, UmiMushi.h:76-89. Retail values are read from
`enemyParms.szs` and validated byte-exact by `DISC_PARMS`. On this revision every
species' proper block serializes **all** header keys, so there are no
header-defaulted gaps (unlike the ground-invertebrate lane); `profile()` enforces
exact key-set equality.

| Trait | Catfish (26) | Tadpole (27) | Jigumo (63) | UmiMushi (71) |
|---|---|---|---|---|
| Life (fp00) | 200 | 200 | 500 | 1500 |
| Speed (fp06) | 60 | 180 | 300 | 15 |
| Territory (fp09) | 280 | 200 | 400 | 300 |
| Home range (fp10) | 80 | 50 | 25 | 30 |
| Sight (fp12) | 200 | 200 | 400 | 700 |
| Attack radii (fp20/fp22) | 50 / 50 | none (0) | 200 / 40 | 30 / 170 |
| Attack damage (fp24) | 10 | 0 | 10 | 10 |
| Proper key fp01 | 2.0 (absent-minded time) | 20.0 (piti move speed) | 75.0 (carry speed) | 0.03 (damage rate) |
| Other proper keys on disc | fp02 poison 300; fp03 rotation-end 90 | — | fp02 return 30; fp03/fp04 scale 1.0/2.0; fp05 poison 500; ip01 hide 30 | fp02 turn-start 30; fp03 turn-end 10; fp04 search move 85; fp06/fp07 rotate 0.05/2.5; fp09 purple-rate 0.05; fp10 cave territory 300; fp11 white 200; fp12 blind health 800; fp13/fp14 blind wait/move 200; ip01 post-attack wait 0 |

Retail semantics cross-checked against the source audit
(PIKMIN2_AQUATIC_ENEMY_AUDIT.md): Catfish attack hit fp22 = 50 with fp20 = 50,
200 HP, 280 territory; Tadpole 200 HP / 180 speed and zero attack; Jigumo 500 HP
/ 400 territory / carry speed fp01 = 75 / return fp02 = 30; UmiMushi 1500 HP /
700 sight / attack hit fp22 = 170 / damage rate fp01 = 0.03 / Blind health
fp12 = 800.

## 5. Resources on disc

Each species reads `enemy/data/<Species>/{model.szs,anim.szs}` on GPVE01 rev 0,
and `enemy/parm/enemyParms.szs` under `<species>/{enemyanimmgr.txt,
enemyparm.txt,enemycoll.txt,enemystoneinfo.txt}`. Two extra files are hashed and
byte-preserved without interpretation:
`enemy/data/Jigumo/kochappy_body_s3tc.1.bti` (shared Kochappy-family S3TC
texture; no repackaging) and `enemy/data/UmiMushi/umimusi_model1.btk` (material
palette animation; no btk playback). Per-file SHA-256 is recorded in the
manifest.

Collision (`enemycoll.txt`) and stone fragments (`enemystoneinfo.txt` joint
count), read and written by the module but not otherwise reworked:

| Species | Root | Children | Stone joints |
|---|---|---|---|
| Catfish | r22.5 @jnt4 | r10 @jnt5, r10 @jnt4 | 7 |
| Tadpole | r25 @jnt1 | r10 @jnt1 | 2 |
| Jigumo | r40 @jnt0 | head r15 @jnt5, dummy r12 @jnt1, body r10 @jnt2 | 21 |
| UmiMushi | r180 @jnt0 | head r80 @jnt1, kuti r40 @jnt14, ketu r25 @jnt18, weak r10 @jnt24 | 33 |

## 6. Reproducible conversion path

Module: `experimental/pikmin2_aquatic_assets.py` (follows the Bulblax/Frog and
ground-invertebrate lane pattern; no edits to neighbor modules or shared
converters). Exact invocation (matches the module's `__main__` argparse):

```
python -m experimental.pikmin2_aquatic_assets \
    --iso output/pikmin2-runtime/pikmin2-source-test.iso \
    --source native/pikmin2-research \
    --output output/pikmin2-aquatic-assets/run1 --pose-limit 3
```

Reads only the four `enemy/data/<Species>/{model.szs,anim.szs}` pairs, the four
`<species>/*` metadata files from `enemy/parm/enemyParms.szs`, and the two extra
hashed files. Output (private, not committed): per-species `enemy.bmd`, all
`.bca` clips, the four metadata text files, the hashed extras, sampled rigid
`.mod` pose files (UmiMushi weighted via `draw_matrices`) plus conversion JSON,
and a hashed `aquatic.json` manifest (`schema=1`, policy `P2_AQUATIC_IMPORT_1`,
disc id/revision, source revision, per-file SHA-256) alongside `p2-aquatic.txt`.

Guards (validated before use): pose limit must be an `int` in 2..`MAX_POSES`
(12); an existing output directory is refused **before** any revision or disc
access; the source revision must be a 40-hex git HEAD; the disc header must be
`GPVE01` (a wrong region raises before any output directory is created). Every
disc read is hashed, and the immutable render-resource set is pinned so a pose
set never mutates shared model data. Limitations are recorded in the manifest:
sampled weighted/rigid poses, no skeletal playback, no event execution
(`native_ready`, `gameplay_events_executed`, `btk_playback` all `false`), and no
native install.

## 7. Tests

`tests/test_pikmin2_aquatic_assets.py` — mirror of the ground-invertebrate and
Bulblax test layout with a mocked disc reader:

- **Identity/profile**: IDs 26/27/63/71 → correct `SPECIES`/`STATE_IDS`/
  `ANIM_IDS`; block/row counts per species.
- **Registration**: `anim_mgr_rows` rebuilds Catfish's three-fold `wait1`
  duplicate and rejects count mismatch, odd event pairs, a missing `-1`
  terminator, and non-`.bca` entries; `profile` rejects row reorder, event
  drift, and dropped duplicates.
- **Unregistered clips**: UmiMushi `wait1` is shipped-but-unregistered; the
  module refuses to classify it as neither, and raises when the declaration is
  removed.
- **Parms**: `DISC_PARMS` retail values match; proper-key drift (add/remove),
  general drift, and proper-value drift are rejected.
- **Non-claims**: `TEXT` carries `native_ready false`,
  `gameplay_events_executed false`, `btk_playback false`; `LIMITATIONS` names the
  btk and unregistered-clip facts.
- **Gates**: refuse-overwrite-before-source-access, wrong-region refusal with
  mocked `disc_files`, and pose-limit bounds (2..12, rejecting `bool`/`str`).

Run from the repo root:

```
python -m pytest tests/test_pikmin2_aquatic_assets.py -q
```

## 8. Open / handoff items

- Native hook wiring (Catfish KochappyBase FSM/shadow joint, Jigumo PanHouse
  ownership and nest persistence/limits, UmiMushi shared-Mgr base exclusion and
  Blind parameter split) belongs to the native track / integration lead — none
  touched here.
- `EnemyID_JigumoNest` (64) and `EnemyID_UmiMushiBase` (100) are **not**
  independent shuffle entries; only the concrete spawnables are claimed.
- Frog (17) and MaroFrog (18) are out of scope; they are source-identified but
  owned by a different lane.
- No btk/texture-matrix playback, no S3TC repackaging, no event execution, no
  AI/FSM, no install or arena placement is provided by this slice.
- Physical placement, carcass/drop behavior, nest day-end restore and gameplay
  sign-off remain unstarted and are explicit handoff work.
- Parallel lanes (Sheargrub/Shearwig, Beetle, Bulblax, Breadbug, Mamuta,
  flying remainder) untouched; no shared-file changes required by this lane.

## Batch 2 — install + arena (#374)

Implementation owner: opencode through shared `4laric`. Pipeline §4 for the
aquatic remainder lane; batch 1 is #347 (commit `a7c9ad7`). New modules only; no
neighbor lane or shared native file is edited here.

### Install contract

`experimental/pikmin2_aquatic_install.py` binds the batch-1 `aquatic.json`
(schema 1, policy `P2_AQUATIC_IMPORT_1`, disc GPVE01 rev 0, species IDs
26/27/63/71) and requires a live/idle, attack and death anchor clip per spawned
species (`Catfish` wait1/attack/dead, `Tadpole` wait1/move1/dead, `Jigumo`
wait1/attack1/dead1, `UmiMushi` run1/attack1/dead1). Every pose carrying a `file`
is bound by SHA-256; the optional sampled visual bank is all-or-nothing, so a
partial bank, a stray `.mod`, a hash mismatch, an unsafe filename or an existing
target is refused **before** any write. Absent pose files install configs only
and return `visuals='absent_baseline_preserved'`, leaving the room baseline
untouched. Into a private run it writes `p2-aquatic-profile.txt` (per-species
general/proper parms), `p2-aquatic-bank.txt` (clip/frame/event/pose listing),
`p2-aquatic-actors.txt` (`P2_AQUATIC_ACTORS_1` + generator/species bindings),
the receipt `aquatic-install.json` (manifest/config/pose SHA-256, generators,
visuals, `native_ready=False`) and the requested
`aquatic_<species>_<clip>_<nn>.mod` poses under
`assets/dataDir/courses/pikmin2room/`. `plan`, `install` and `verify_install`
(round-trip) share one validation path; sibling `p2-*-actors.txt` bindings are
scanned for generator-ID overlap. Real batch-1 manifest smoke run: 79 poses /
1,973,024 bytes installed and re-verified (`installed == generated`).

### Arena contract

`experimental/pikmin2_aquatic_arena.py` follows
[docs/PIKMIN2_ENEMY_ARENA.md](PIKMIN2_ENEMY_ARENA.md). `roster(assets)` appends
five actors to the original practice stage: 374001 Catfish (`TEKI_Namazu` 30, P1
Water Dumple ancestor), 374002 Tadpole (`TEKI_Otama` 25, P1 Wogpole ancestor),
374003 Jigumo and 374004 UmiMushi (both have **no** P1 counterpart and use
`TEKI_Chappy` 3 as a placement vehicle only), plus 374005 ordinary P1 Chappy
control. Position + offset is translation only (zero offset, validated); full
expected XYZ is recorded; source yaw is `None`, recorded unapplied; IDs are
checked against the stage's existing placements at staging time. `prepare(assets,
imported, output)` overlays a private run, zeroes the default generator scatter
circle via the deterministic fixture override (engineered choice, not production
placement evidence), calls `install`/`verify_install`, re-hashes the preserved
original course and writes `arena.json`. `GATES` covers the common acceptance
gates plus the batch-1 open items; identity, FSM, proxy, combat, death and carry
gates are marked **blocked**, spawn/control are untested.

### Native registration (family-owned)

Workflow revision 2026-09-13 ([#186](https://github.com/4laric/pikmin-randomizer/issues/186)):
the aquatic family owner implements these narrow additive registration hooks. The
entry points below are recorded for #186 coordination and acceptance; edits to
shared semantics still require focused review. None is implemented in this batch.

- **Build**: add `pc_port/pc_p2_aquatic.cpp` (+`pc_p2_aquatic.h`,
  `pc_p2_aquatic_policy.h`) to the `pikmin_pc` source list following the
  `pc_p2_kochappy.cpp` family registration; no new third-party dependencies.
- **Setup** (`pc_p2_aquatic_setup()`, called once after generators exist,
  alongside the other family setup): parse `P2_AQUATIC_ACTORS_1`
  (`<generator> <Species>`), reset first, treat an absent config as a no-op P1
  fallback, and reject duplicate/unknown generator IDs and unknown species.
  Build one visual bank per species from `aquatic_<species>_*.mod`, bind the
  `p2-aquatic-profile.txt` parms and `p2-aquatic-bank.txt` clip/event data, and
  register **Catfish 26** (`PC_P2_CATFISH`, KochappyBase FSM host + shadow
  joint), **Tadpole 27** (`PC_P2_TADPOLE`, water-box leap/Escape gate),
  **Jigumo 63** (`PC_P2_JIGUMO`, owns the `PanHouse`/`JigumoNest` child with
  nest persistence and limits) and **UmiMushi 71** (`PC_P2_UMIMUSHI_OBJ`).
- **Update**: Catfish/Tadpole/Jigumo advance their source state machine on the
  authoritative native animation counter; until that lands, the P1 ancestor
  proxies keep host AI. No actor update may skip damage/death receivers.
- **Draw**: add `pc_p2_aquatic_draw` to both the live and corpse fallback chains
  in `tekibteki.cpp`, selecting by typed actor ID; ordinary P1 controls and
  actors without an installed bank keep the existing fallback.
- **Reset/teardown**: call `pc_p2_aquatic_reset()` at every family
  reset/teardown/cave-reentry point in `tekimgr.cpp` and on actor reuse; clear
  per-actor banks, model/shape references and the Jigumo PanHouse child link
  before heap reuse (never assume a pointer is not recycled).
- **Shared `UmiMushi::Mgr` boss/helper**: instantiate the shared manager once and
  tag objects per ID. Base 100 `UmiMushiBase` stays **non-spawnable/excluded**
  (no spawn flag); ordinary 71 and Blind 101 are spawnable children sharing the
  same `"UmiMushi"` bank. Blind uses its own parms (`fp12` blind health 800,
  `fp13`/`fp14` 200, `ip01` 0). The boss weak-point collision (`weak` joint 24,
  `st__`), `eat`/`flick` receivers and shared reset belong in the same
  registration pass. `JigumoNest` 64 and `UmiMushiBase` 100 are **not**
  independent shuffle entries.

### Tests

`tests/test_pikmin2_aquatic_install.py` (synthetic schema-1 import, real bytes
and recorded hashes): actor-count/duplicate/invalid-ID rejection before IO;
schema/policy/disc/species/enemy-ID rejection; missing-anchor and pose-hash
mismatch rejection; install + verify round-trip (installed == generated);
overwrite refusal; tamper detection on an installed pose and on the actor config;
absent-bank baseline preservation; partial-bank and sibling-overlap refusal;
non-junction room refusal; arena proxy-type constants, gate coverage,
`roster`-on-missing-path and translation-only five-actor contract. Run from the
repo root:

```
python -m pytest tests/test_pikmin2_aquatic_install.py tests/test_pikmin2_aquatic_assets.py -q
```
