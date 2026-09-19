# Cannon larvae + projectile hazards source audit — Kabuto (75), Rkabuto (95), Fkabuto (96), Rock (19), Stone (74), Bomb (36), Egg (37), FminiHoudai (97)

Issue: [#350](https://github.com/4laric/pikmin-randomizer/issues/350) (parent [#169](https://github.com/4laric/pikmin-randomizer/issues/169)).
Source: `native/pikmin2-research` decompilation against US GPVE01 rev 0;
retail resources verified against the local legally supplied disc copy
(header `GPVE01` rev 0; the `enemy/parm/enemyParms.szs` member set already
extracted locally under `output/pikmin2-extract-bombsarai/` was re-read here,
no fresh ISO run). Evidence level achieved: **source contract + converted
assets** (per [the import pipeline](PIKMIN2_ENEMY_IMPORT_PIPELINE.md)); no
native hook wiring in this lane. Projectile lifecycle mechanics are
**cross-referenced, not reimplemented** — see
[the BombSarai projectile contract](PIKMIN2_BOMBSARAI_PROJECTILE_CONTRACT.md)
(#244), [the cannon/groink audit](PIKMIN2_CANNON_GROINK_AUDIT.md), and
[the Groink prototype](PIKMIN2_GROINK_PROTOTYPE.md) (#169).

## 1. Identity and registration

| ID | Constant | Common name | Obj / Mgr class | `enemyInfo.cpp` row | `generalEnemyMgr.cpp` |
|---|---|---|---|---|---|
| 19 | `EnemyID_Rock` (enemyInfo.h:78) | Falling boulder | `Game::Rock::Obj` / `Mgr` | 36 (`EFlag_HasNoInfo`) | 259-260 |
| 36 | `EnemyID_Bomb` (enemyInfo.h:95) | Bomb-rock | `Game::Bomb::Obj` / `Mgr` | 64 (`EFlag_HasNoInfo`) | 322-323 |
| 37 | `EnemyID_Egg` (enemyInfo.h:96) | Egg | `Game::Egg::Obj` / `Mgr` | 65 (`EFlag_HasNoInfo`, child Mitite x10) | 325-326 |
| 74 | `EnemyID_Stone` (enemyInfo.h:133) | Rock projectile | `Game::Rock::Obj` / `Mgr` (parent Rock) | 37 (no `EFlag_UseOwnID`) | via Rock::Mgr 259 |
| 75 | `EnemyID_Kabuto` (enemyInfo.h:134) | Armored Cannon Beetle Larva | `Game::GreenKabuto::Obj` / `Mgr` | 38 (`EFlag_CanBeSpawned`) | 459-460 |
| 95 | `EnemyID_Rkabuto` (enemyInfo.h:154) | Decorated Cannon Beetle | `Game::RedKabuto::Obj` / `Mgr` | 39 (`EFlag_CanBeSpawned`) | 462-463 |
| 96 | `EnemyID_Fkabuto` (enemyInfo.h:155) | Armored Cannon Beetle Larva (burrowed) | `Game::FixKabuto::Obj` / `Mgr` | 40 (`EFlag_CanBeSpawned`) | 465-466 |
| 97 | `EnemyID_FminiHoudai` (enemyInfo.h:156) | Gatling Groink (pedestal) | `Game::FixMiniHoudai::Obj` / `Mgr` | 108 (`EFlag_CanBeSpawned`) | 482-483 |

Notes:

- Rock, Stone, Bomb and Egg are **`EFlag_HasNoInfo` projectile/hazard entries**
  (enemyInfo.cpp:36,37,64,65): they are tracked as projectiles, not creatures,
  so they carry no Piklopedia entry.
- Kabuto (75) and Rkabuto (95) are the concrete creature spawnables; the
  content inventory records their Piklopedia numbers as 15 and 16. They share
  one `AnimID`/`StateID` FSM family through `Kabuto::Obj` (Kabuto.h:28-44,
  146-162).
- `GreenKabuto`, `RedKabuto` and `FixKabuto` are three distinct managers that
  each allocate `Kabuto::Parms` and their own object array
  (`GreenKabutoMgr.cpp:16-38`, `RedKabutoMgr.cpp:16-38`,
  `FixKabutoMgr.cpp:16-38`); Green and Fix use the baby texture, Red the
  decorated texture.

### Helper / nonspawnable reclassification (explicit)

For this lane, "helper/nonspawnable" means a distinct `EnemyID` that is **not
independently documented or staged as a creature**, not a cleared
`EFlag_CanBeSpawned` bit. The registration rows still set
`EFlag_CanBeSpawned`, so the distinction is drawn from resource aliasing, the
content inventory classification and the behavior source.

| Entry | Classification | Evidence |
|---|---|---|
| Fkabuto (96) | **Buried helper variant**, no separate identity (`variant_no_separate_entry`) | enemyInfo.cpp:40 aliases every resource slot to `"Kabuto"`; `FixKabuto::Obj` only overrides textures/effects and the buried FSM; `KabutoState.cpp:391-438` starts hidden, non-Atari, invulnerable, gauge hidden and restores them on appear; content inventory classifies it `variant_no_separate_entry`, displayed as representative Kabuto |
| FminiHoudai (97) | **Fixed-pedestal helper alias** of MiniHoudai (78) | enemyInfo.cpp:108 aliases every resource slot to `"MiniHoudai"`; `FixMiniHoudai::Mgr` shares the base manager/parameters with its own allocation (`FixMiniHoudaiMgr.cpp:10-40`); fixed ID enables `EB_Constrained` during init (`MiniHoudai.cpp:36-55`); content inventory classifies it `variant_no_separate_entry`; the roaming MiniHoudai identity belongs to the Groink lane (#169) |
| Stone (74) | **Projectile variant owned by the Rock manager** | enemyInfo.cpp:37 has no `EFlag_UseOwnID` and resolves `mParentID` to Rock; `RockMgr.cpp:101-115` builds one object array over `{EnemyID_Rock, EnemyID_Stone}` and stamps `mRockType`; Kabuto fires it through `createStoneAttack` against the Rock manager (`Kabuto.cpp:268-289`) |
| Rock / Bomb / Egg | **Projectile/hazard entries** | enemyInfo.cpp:36,64,65 carry `EFlag_HasNoInfo`; RockMgr/bombMgr/eggMgr plain object arrays; no creature roster tracking |

## 2. State IDs

Source enums cited per family; the module exposes them as `STATE_IDS`.

| Family | States | Source |
|---|---|---|
| Kabuto / Rkabuto / Fkabuto | dead 0, wait 1, turn 2, move 3, flick 4, attack 5, fixstay 6, fixappear 7, fixhide 8, fixwait 9, fixturn 10, fixattack 11, fixflick 12 | Kabuto.h:28-44 |
| Rock / Stone | wait 0, appear 1, dropwait 2, fall 3, move 4, dead 5 | Rock.h:178-186 |
| Bomb | wait 0, bomb 1 | Bomb.h:182-186 |
| Egg | wait 0 | Egg.h:159-162 |
| FminiHoudai (MiniHoudai base) | dead 0, rebirth 1, lost 2, attack 3, flick 4, turn 5, turnhome 6, turnpath 7, walk 8, walkhome 9, walkpath 10 | MiniHoudai.h:25-39 |

The Kabuto family shares one FSM registration of normal
wait/turn/move/flick/attack plus buried stay/appear/hide/wait/turn/attack/flick
(`KabutoState.cpp:15-31`). Fkabuto's buried attack emits the same Stone at
`KEYEVENT_2` as the surfaced attack (`KabutoState.cpp:347-374,712-750`).

## 3. Animation events (`enemyanimmgr.txt`)

Clip order = `AnimID` enum order and the resolved `enemyanimmgr.txt` row order.
Key events are `(frame, event type)`; 0/1 = visual loop bounds, 2+ = native
gameplay hooks. The module parser accepts the capitalised `K_*.bca` buried
clips (the shared sheargrub parser rejects them), recorded in `CLIPS` /
`EXPECTED_EVENTS`.

The registration name and the shipped archive member differ in case for the
seven buried Kabuto clips: `enemyanimmgr.txt` keeps the authored `K_pivot.bca`
… `K_hide.bca` names (source paths `...\babykabuto\anim\K_*.bca`, matching the
`KABUTOANIM_Fix*` comments in Kabuto.h),
but the packed `enemy/data/Kabuto/anim.szs` stores them as `k_pivot.bca` …
`k_hide.bca` on both the US GPVE01 rev 0 test image and the retail disc. The
module records this in `SHIPPED_MOTION_ALIASES` and `motion_member` resolves
the registered name to the shipped member (with a case-insensitive fallback);
a missing or ambiguous member is rejected rather than silently aliased. All
other banks ship byte-identical names (`Rock/dead.bca`, `Bomb/hit_start.bca`,
`MiniHoudai/attack1.bca`, …).

| Species (resolved bank) | Clips | Notable event streams |
|---|---|---|
| Kabuto / Rkabuto / Fkabuto (Kabuto bank) | dead, move, flick, attack, pivot, wait, K_pivot, K_wait, K_attack, K_flick, K_dead, K_appear, K_hide, carry | move 15→0, 44→1; attack 50→2 (Stone emission `KEYEVENT_2`); flick 30→2; K_attack 55→2 (buried Stone emission); K_dead / K_appear / K_hide terminate only; carry 10→0, 29→1 |
| Rock / Stone (Rock bank) | dead, run | dead ends; run 0→0, 39→1. The dormant `stone/enemyanimmgr.txt` names `move.bca` instead of `run.bca` but is not selected (mAnimMgrName resolves to `"Rock"`) |
| Bomb | hit_start, hit_loop | hit_start 10→2 (arm on animation start); hit_loop 0→0, 7→1 (8-frame arm loop) |
| Egg | damage1 | none (single damage clip) |
| FminiHoudai (MiniHoudai bank) | walk, search1, turn1, attack1, flick1, dead1, type5, rebirth | walk 10→0, 18→2, 25→1; turn1 5→0, 16→1; attack1 11→2, 22→3, 25→4, 32→5 (pause/charge, charge end, shell emission, rotation finish); flick1 10→2; dead1 32→2, 52→3; type5 10→0, 29→1; rebirth 32→2, 45→3 |

As with the bulborb lane, the resolved `enemyanimmgr.txt` is preserved
verbatim in each species folder and validated; events are **data only** — no
native event execution in this lane.

## 4. Model + anim + parm resource map

Empty `EnemyInfo` resource slots fall back to the row's own name
(`enemyMgrBase.cpp:519-565`); the following aliases are resolved explicitly in
the module (`RESOURCE_OWNER`, `PARM_OWNER`):

| Entry | `model.szs` / `anim.szs` | `enemycoll.txt` / `enemystoneinfo.txt` | `enemyparm.txt` | `enemyanimmgr.txt` |
|---|---|---|---|---|
| Kabuto 75 | `enemy/data/Kabuto/` | `kabuto/` (stoneinfo 2497 B) | `kabuto/` | `kabuto/` |
| Rkabuto 95 | `enemy/data/Kabuto/` (alias) | `kabuto/` (alias) | `rkabuto/` (SHA-identical to Kabuto) | `kabuto/` (alias) |
| Fkabuto 96 | `enemy/data/Kabuto/` (alias) | `kabuto/` (alias) | `fkabuto/` (life differs) | `kabuto/` (alias) |
| Rock 19 | `enemy/data/Rock/` | `rock/` (no stoneinfo) | `rock/` | `rock/` |
| Stone 74 | `enemy/data/Rock/` (alias) | `rock/` (alias) | `rock/` (alias; dormant `stone/` copy SHA-identical) | `rock/` (alias; dormant `stone/` names `move.bca`) |
| Bomb 36 | `enemy/data/Bomb/` | `bomb/` (stoneinfo 1272 B) | `bomb/` | `bomb/` |
| Egg 37 | `enemy/data/Egg/` | `egg/` (no stoneinfo) | `egg/` | `egg/` |
| FminiHoudai 97 | `enemy/data/MiniHoudai/` (alias) | `minihoudai/` (alias; stoneinfo 4875 B) | `fminihoudai/` | `minihoudai/` (alias) |

The Kabuto `anim.szs` member casing is the one archive-level wrinkle the
`RESOURCE_OWNER` alias does not cover: Rkabuto/Fkabuto resolve to the Kabuto
bank, whose buried clips are registered `K_*.bca` but shipped `k_*.bca` (see
§3). Dormant duplicates are recorded, not consumed: `stone/enemyparm.txt` is
SHA-256 identical to `rock/enemyparm.txt`, and `stone/enemycoll.txt` to
`rock/enemycoll.txt`, while `stone/enemyanimmgr.txt` differs only in the
`move.bca` filename. The manager row (enemyInfo.cpp:37) selects `"Rock"` for
all seven resource names, so none of the `stone/*` text is loaded.

## 5. Retail parms (retail vs header defaults)

Headers list **build-time defaults**; the disc supplies the shipped values.
They are kept separate in the module (`PROPER_PARM_DEFAULTS` vs `DISC_PARMS`)
and never flattened. For Kabuto/Rkabuto/Fkabuto every general value is
disc-only and there is no proper block (`Kabuto::Parms::ParmParms` declares no
fields, Kabuto.h:125-144).

| Entry | Key retail facts | Header default vs disc |
|---|---|---|
| Kabuto 75 | life fp00 850, speed fp06 60, sight fp12 350, attackable fp20 180, attack damage fp24 10; proper empty | proper `{}` both |
| Fkabuto 96 | life fp00 **2000**, rotate rate fp08 0.075, max rotate speed fp28 7.5; otherwise as Kabuto | proper `{}` both |
| Rkabuto 95 | parm block SHA-identical to Kabuto; homing is code (`getEnemyTypeID()==Rkabuto`, Kabuto.cpp:285-287), not a parm | proper `{}` both |
| Rock 19 / Stone 74 | life fp00 99999 (immortal by HP), speed fp06 250, sight/search fp14 1000 / fp26 550, attack hit range fp22 20; proper search-rumble speed fp01 **100** | proper `fp01` default 150.0 → disc 100.0 |
| Bomb 36 | fuse health fp00 4.5, blast radius fp22 90, Navi/Pikmin damage fp24 10; proper damage-to-enemies fp01 **500**, blast half-height fp02 50, damage limit ip01 **1**, trigger limit ip02 **15** | fp01 250→500, fp02 50=50, ip01 2→1, ip02 50→15 |
| Egg 37 | life fp00 50, flick force fp17 150; proper single-nectar fp01 **0.5**, double-nectar fp02 **0.35**, mitite fp03 0.05, spicy fp04 0.05, bitter fp05 0.05 | all five default 1.0 → disc values |
| FminiHoudai 97 | life fp00 **700** (MiniHoudai 78 is 1200), speed 100, attack rad 500/15, attack hit 65°, damage 10; proper gauge delay fp11 **2.0**, respawn rate fp12 **118.0** | fp11 30.0→2.0, fp12 10.0→118.0 |

Bomb's retail values corroborate
[the engine-lane extraction](PIKMIN2_ENGINE_DISC_PARMS.md) (#128/#244), which
independently recorded bomb fp01 500, fp02 50, ip01 1, ip02 15.

## 6. Collision

Per-species `enemycoll.txt` (root sphere + children; radius @ joint index,
offset XYZ). Rkabuto/Fkabuto reuse the Kabuto tree; Stone reuses Rock.

| Entry | Root | Children |
|---|---|---|
| Kabuto / Rkabuto / Fkabuto | `{none}` r55 @jnt0 | nose r20 @jnt3, head r20 @jnt2, body r20 @jnt1, hips r20 @jnt10, lhan r7.5 @jnt5, lleg r7.5 @jnt6, rhan r7.5 @jnt8, rleg r7.5 @jnt9 |
| Rock / Stone | `{none}` r40 @jnt6 | `{none}` r27 @jnt6 |
| Bomb | `{none}` r20 @jnt0 | `{none}` r15 @jnt0 |
| Egg | `{none}` r15 @jnt1 (0,12,0) | `{none}` r12 @jnt0 (0,11,0) |
| FminiHoudai / MiniHoudai | `{none}` r55 @jnt0 (0,0,10) | body r27.5 @jnt0, asiL r10 @jnt4, asiR r10 @jnt8, cov1 r25 @jnt9, cov2 r20 @jnt9, cov3 r17.5 @jnt9, coll r27.5 @jnt0 |

`enemystoneinfo.txt` is present (fragment tables) for Kabuto, Bomb and
MiniHoudai and absent for Rock, Stone, Egg and FminiHoudai; the module records
whichever files exist in `metadata_sha256`.

## 7. Projectile lifecycle notes (cross-referenced, not reimplemented)

- **Rock / Stone:** `Rock::Obj::onInit` is invulnerable with damage animation,
  carcass, health gauge and death effect disabled and `mSourceEnemy=nullptr`
  (`Rock.cpp:47-110`). Falling Rock hides in Wait/DropWait; Appear scales and
  enables Atari; Fall ends on floor/collision; Move rolls until health 0 or the
  15-second timeout; Dead disables Atari and kills after the break animation
  (`RockState.cpp:30-286`). Contacts use one shared hitbox: Navi/Pikmin
  `InteractPress` with general attack damage, Teki `InteractAttack` for 250,
  non-fake-Pikmin contacts zero health, ordinary rocks suppress mutual
  collision, wall contact kills a rolling Stone, and the collision scale grows
  with the visual scale (`Rock.cpp:204-341`). The collision policy is owned by
  the Groink/#169 track and the BombSarai contract cross-reference; this lane
  only imports visuals/parms.
- **Kabuto/Rkabuto/Fkabuto Stone attack:** `createStoneAttack` obtains the Rock
  manager, sets `birthArg.mTypeID = EnemyID_Stone`, spawns at the mouth joint
  with Y `25 + mPosition.y`, inits, assigns `mSourceEnemy=this`, and enables
  homing only when `getEnemyTypeID()==Rkabuto` (`Kabuto.cpp:268-289`). Failed
  births are silently tolerated. No reflection/bounce trajectory branch exists;
  homing is steering toward a target.
- **Bomb:** initializes in `BOMB_Wait`, non-carcass/non-death-effect, starts
  constrained for non-drop-group births; capture is invulnerable except in
  versus and release clears the constraint (`bomb.cpp:23-113`). Drop-group
  bounce/non-Teki collision forces `BOMB_Bomb`; nearby bomb Teki arm each other
  with a delay (`bomb.cpp:383-425`). Wait arms on animation start and kills an
  escaped uncaptured bomb past counter 200 (`bombState.cpp:39-102`). Detonation
  waits ten ticks after health zero, then applies a height-gated spherical
  blast: Teki take `mDamageToEnemies`, Navi/Pikmin take general attack damage
  with knockback attributed to the carrier (`bombState.cpp:103-200`). The
  isolated projectile lifecycle policy (clock, capture/in-flight/armed/
  burning/despawned phases, single recorded blast event) is **not duplicated
  here** — see
  [PIKMIN2_BOMBSARAI_PROJECTILE_CONTRACT.md](PIKMIN2_BOMBSARAI_PROJECTILE_CONTRACT.md)
  (#244).
- **Egg:** one wait state; stationary/constrained for non-drop births; a bounce
  or non-Teki collision in a drop group makes it health-zero and exposes the
  gauge (`egg.cpp:22-67,169-191`). Wait breaks it when health is zero and calls
  `genItem`, choosing pellets/nectar/Mitites/sprays from the five chance
  parameters; the forced drop type overrides the random choice; spicy/bitter are
  downgraded to nectar until the first-spray demo flag exists; Mitite-group
  allocation failure falls back to nectar; each item birth is null-checked
  (`egg.cpp:243-385`).
- **FminiHoudai / Groink:** fixed ID 97 enables `EB_Constrained` during init;
  the FSM covers Dead/Rebirth/Lost/Attack/Flick/Turn plus path/home walking
  (`MiniHoudaiState.cpp:18-32`). Attack event 2 pauses motion and starts
  rotation/charge, 3 ends charge and emits smoke, 4 emits shells under
  `!isFinishMotion() || !(mHealth <= 0)`, 5 pauses and finishes rotation
  (`MiniHoudaiState.cpp:281-340`). Shell emission uses up to three inactive
  nodes at 25 units ahead of the head joint with random spread; each shell is a
  radius-10 swept sphere with `velocity.y -= 20`, returning to the pool on
  floor/wall contact or >1000 from its owner (`MiniHoudaiShotGun.cpp:86-243,
  1345-1384`). Carcass revival is replacement-object rebirth, not same-object
  resurrection (`MiniHoudai.cpp:293-325`). The pedestal's fixed fire policy,
  terrain trace and receiver routing are owned by the #169 Groink lane and are
  **not reimplemented here** — see
  [PIKMIN2_GROINK_PROTOTYPE.md](PIKMIN2_GROINK_PROTOTYPE.md) and
  [PIKMIN2_CANNON_GROINK_AUDIT.md](PIKMIN2_CANNON_GROINK_AUDIT.md).
- **Save/resume:** no family override serializing Bomb, Egg, Rock/Stone,
  Kabuto or MiniHoudai transient state was found; in-flight projectiles, armed
  bombs, buried Kabuto and groink carcass regeneration remain unresolved (audit
  §"Reset, persistence, and unknowns").

## 8. Reproducible conversion path

Module: `experimental/pikmin2_cannon_projectile_assets.py` (follows the
ground-invertebrate lane pattern; no edits to neighbor modules or shared
converters).

```
python -m experimental.pikmin2_cannon_projectile_assets \
    --iso output/pikmin2-runtime/pikmin2-source-test.iso \
    --source native/pikmin2-research \
    --output output/pikmin2-cannon-projectile-assets/run1 --pose-limit 3
```

Reads only: the resolved `enemy/data/<owner>/{model.szs,anim.szs}` pairs and
the `<owner>/*` metadata files from `enemy/parm/enemyParms.szs` (with the
`PARM_OWNER` override for Stone and `RESOURCE_OWNER` aliases for
Rkabuto/Fkabuto/Stone/FminiHoudai). Output (private, not committed):
per-species `enemy.bmd`, all resolved `.bca` clips, the metadata text files
present, sampled rigid/weighted pose `.mod` files + conversion JSON, and a
hashed `cannon_projectile.json` manifest (`schema=1`, policy
`P2_CANNON_PROJECTILE_1`, disc id/revision, source revision, per-file SHA-256).
The report records each entry's `role`, `resource_owner` and `parm_owner`.

Reproducibility evidence: extract hashes every disc resource read; duplicate
runs must produce identical `cannon_projectile.json`. Limitations are recorded
in the manifest and in `LIMITATIONS`: sampled weighted/rigid poses, no skeletal
playback, no `EVP1`/`DRW1` execution, no Stone/bomb/egg/shotgun native events,
no install.

## 9. Tests

`tests/test_pikmin2_cannon_projectile_assets.py` — mirror of the
ground-invertebrate test layout with a self-contained mocked disc reader:

- **Registry**: IDs 19/36/37/74/75/95/96/97 → correct
  `SPECIES`/clip/event/state maps; separate resources per entry.
- **Parm parsing**: `enemyparm.txt` → blocks; retail parm values match
  `DISC_PARMS`; header build-time defaults (`PROPER_PARM_DEFAULTS`) stay
  distinct from disc values (Bomb fp01 250 vs 500, Rock fp01 150 vs 100,
  FminiHoudai fp11 30 vs 2, Egg fp01 1.0 vs 0.5); the Kabuto family proper
  block is empty.
- **Reclassification**: `HELPER_ENTRIES` (Fkabuto, FminiHoudai) and
  `PROJECTILE_ENTRIES` (Rock, Stone, Bomb, Egg); Stone parm equals Rock;
  Fkabuto life 2000 vs Kabuto 850; FminiHoudai life 700.
- **Animation registry**: clip list and event streams enforce the resolved
  disc order; malformed/reordered entries are rejected.
- **Shipped motion names**: `SHIPPED_MOTION_ALIASES` maps the seven registered
  `K_*.bca` names to the shipped `k_*.bca` members and `motion_member` rejects
  missing or case-ambiguous archive members.
- **Budget/gate**: pose-limit validation enforces 2..12 before any IO; disc
  header/revision and source-revision gates reject the wrong disc or source;
  overwrite is refused before source access.

## 10. Open / handoff items

- Native hook wiring (Stone birth/homing, Fkabuto buried reveal, Rock
  fall/roll/dead, Bomb fuse/blast, Egg drop table, FminiHoudai fixed fire)
  belongs to the native/`#169` track and the BombSarai contract; none touched
  here.
- The content-inventory `variant_no_separate_entry` label for Fkabuto/FminiHoudai
  is documentation-level; the rows still carry `EFlag_CanBeSpawned`, so
  "nonspawnable" is not asserted as a cleared spawn flag in this lane.
- The dormant `stone/enemyparm.txt` / `stone/enemyanimmgr.txt` / `stone/enemycoll.txt`
  copies are recorded but never selected by the Rock manager row; if a future
  source revision re-points `mParamName`, the module's `PARM_OWNER`/`CLIPS`
  would need to follow.
- Bomb/Egg/Rock model/anim conversion is exercised through the same bounded
  pose path; effect meshes (`bomb effect`, blast, stone fragments) are not
  imported.
- Parallel lanes (MiniHoudai 78 Groink #169, BombSarai #244, Fuefuki/BigTreasure
  #245/#246) untouched; no shared-file changes required by this lane.

## 11. Batch 2 — install + arena (#350)

Batch 2 takes the batch-1 `cannon_projectile.json` assets into the runtime
through the shared core (`experimental/pikmin2_batch2_core.py`) bound by
`experimental/pikmin2_cannon_projectile_install.py` and
`pikmin2_cannon_projectile_arena.py`.

- **Install**: hash-bound `plan`/`install`/`verify_install`; schema-1
  `P2_CANNON_PROJECTILE_1` manifest, exact-byte pose binding, conflict refusal
  before mutation, optional all-or-nothing visual bank (baseline preserved when
  absent). Staged actors are Kabuto/Rkabuto/Fkabuto/Rock/Bomb/Egg; Stone (Rock
  alias) and FminiHoudai remain installable but unplaced.
- **Arena**: private original Impact Site staging — six actors plus one ordinary
  P1 control, unique generator IDs 350001–350007, full expected XYZ, zero
  offset, source yaw unapplied. Kabuto/Rkabuto/Fkabuto use the P1 Armored Cannon
  Beetle (Beatle 17) ancestor as a placement vehicle and Rock uses the P1
  Rolling Boulder (Iwagon 2); Bomb/Egg use the neutral Chappy vehicle. Identity
  is not claimed.
- **Real-disc evidence**: install + verify round-trip against
  `output/p2-lane-verify/cannon2/cannon_projectile.json` → **93 installed, 93
  verified** (SHA-256 bound). Generated evidence stays under private `output/`.
- **Status**: install + arena staging level. Native gates
  (`native_identity`, `cannon_projectile_pool`, `rock_roll`, `bomb_lifecycle`,
  `egg_drop`, `buried_emerge`, `muzzle_alignment`) are BLOCKED pending the hook
  request on #186. No shared/native code touched; no disc assets committed.

### Native registration (family-owned)

Workflow revision 2026-09-13 ([#186](https://github.com/4laric/pikmin-randomizer/issues/186)):
the cannon/projectile family owner implements narrow additive registration
hooks. Implemented in this pass by the shared `native/pc_port/pc_p2_batch2.cpp`
unit, wired through `pc_p2_batch2_setup/draw/reset/forget`; Kabuto/Rkabuto/
Fkabuto bind as `TEKI_Beatle` (P1 Armored Cannon Beetle), Rock as `TEKI_Iwagon`
(P1 Rolling Boulder) and Bomb/Egg as `TEKI_Chappy`, from
`p2-cannon-actors.txt` / `p2-cannon-bank.txt` and the `cannon_*` pose bank. See
[Batch-2 native registration](PIKMIN2_BATCH2_NATIVE_REGISTRATION.md). Visual-only
P1 proxy; all runtime gates remain BLOCKED/UNTESTED pending a supplied-asset
runtime pass.
