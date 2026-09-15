# Beetle lane source audit — Kogane (9), Wealthy (10), Fart (11)

Issue: [#212](https://github.com/4laric/pikmin-randomizer/issues/212) (parent [#168](https://github.com/4laric/pikmin-randomizer/issues/168)).
Source: `native/pikmin2-research` decompilation against US GPVE01 rev 0; retail
resources verified against the local legally supplied disc copy
(`output/pikmin2-runtime/pikmin2-source-test.iso`, header `GPVE01` rev 0).
Evidence level achieved: **source contract + converted assets** (per
[the import pipeline](PIKMIN2_ENEMY_IMPORT_PIPELINE.md)); no native hook wiring
in this lane.

## 1. Identity and registration

| ID | Constant | Common name | Obj / Mgr class | Registration |
|---|---|---|---|---|
| 9 | `EnemyID_Kogane` | Iridescent Flint Beetle | `Game::Koganemushi::Obj` / `Mgr` | generalEnemyMgr.cpp:244-245 |
| 10 | `EnemyID_Wealthy` | Iridescent Glint Beetle | `Game::Wealthy::Obj` / `Mgr` | generalEnemyMgr.cpp:247-248 |
| 11 | `EnemyID_Fart` | Doodlebug | `Game::Fart::Obj` / `Mgr` | generalEnemyMgr.cpp:250-251 |

- ID table: `include/Game/enemyInfo.h:68-70`.
- Spawn table: `src/plugProjectYamashitaU/enemyInfo.cpp:25-27` — all three are
  `EFlag_CanBeSpawned | 2 | EFlag_UseOwnID`; Wealthy and Fart alias **all**
  Kogane resource slots (`"Kogane"` in the model/anim/course columns), so a
  single `enemy/data/Kogane/` model+animation bank serves the whole family.
- Family base: `Game::Kogane` (`include/Game/Entities/Kogane.h:10-16`) is an
  abstract base — `changeMaterial()` and `getChangeTexture()` are pure virtual
  (Kogane.h:37, 101) — and has **no own registration** in generalEnemyMgr.cpp.
  `Kogane::Mgr::loadModelData`/`loadAnimData` (KoganeMgr.cpp:22-68) deliberately
  share the first loaded model/anim among the three registered IDs.

### Helper / unused entries (explicit classification)

| Entry | Classification | Evidence |
|---|---|---|
| `Game::Kogane::Obj/Mgr/Parms/FSM` | **Base class, non-spawnable** (no own ID registration) | Kogane.h:22-191; absent from generalEnemyMgr.cpp switch |
| `Game::Koganemushi` | The concrete class behind ID 9 ("Kogane" the ID ≠ "Kogane" the namespace) | Koganemushi.h:17, generalEnemyMgr.cpp:244-245 |
| `ebi::title::Kogane` (`ebiP2TitleKogane.cpp`) | **Title-screen helper**, not gameplay; uses separate `kogane_title.bmd` + `.bck` anims from the title archive | ebiP2TitleKogane.cpp:20-56 |
| `user/Ebisawa/testdata/kogane_title.bmd` | Title-screen asset, not an enemy resource | disc filesystem listing |
| `Kogane::Obj::resetFartTimer` base | **No-op hook** (empty base body, Kogane.cpp:62-64); only `Fart::Obj` overrides it (Fart.cpp:183-187) | — |
| `Kogane::Obj::createFartEffect` base | **No-op hook** (Kogane.h:55 weak empty); only Fart overrides (Fart.cpp:213-230) | — |
| `Kogane::Obj::startBodyEffect/finishBodyEffect/effectDrawOn/Off` | No-op base hooks; Wealthy (sparkle `efx::TOoganeKira`) and Fart (flies `efx::TBabaFly_ver01`) override; Koganemushi has none | Kogane.h:53-57, Wealthy.cpp:124-156, Fart.cpp:193-207 |
| `Kogane::ProperAnimator` | Trivial single-animator wrapper (KoganeAnimator.cpp); all states share one animator | — |

## 2. AI / state machine

Shared FSM (`src/plugProjectNishimuraU/KoganeState.cpp`), five states
(Kogane.h:166-173):

- **Appear (0)**: hidden, collision off, `EB_BitterImmune`, motion stopped
  (KoganeState.cpp:27-39). Transits to Move when a captain or Pikmin enters the
  50-unit sight radius (`isAppear`, Kogane.cpp:356-370). Cleanup scales up and
  plays the dive-out effect + `PSSE_EN_TAMAGOMUSHI_APPEAR` (KoganeState.cpp:57-78).
- **Move (2)**: `EnemyFunc::walkToTarget` at 200 u/s with random headings inside
  ±90° (fp30) of facing; random travel segment 0.3–0.7 s; `createFartEffect()`
  hook fires on entry (KoganeState.cpp:128-137). When the appear timer exceeds
  fp02 (max surface time) it transits to **Disappear**, else to **Wait**
  (KoganeState.cpp:153-167).
- **Wait (3)**: stationary 0.5–2.0 s (kogane) / 1.0–2.0 s (wealthy) / 1.0–3.0 s
  (fart), then back to Move (KoganeState.cpp:182-212).
- **Press (4)**: the "flip" from a Pikmin stomp/hipdrop/earthquake
  (pressCallBack/hipdropCallBack/earthquakeCallBack, Kogane.cpp:139-182, gated
  on `isPiki()`). Only reachable from Move/Wait (`transitDamageState`,
  Kogane.cpp:230-244). Damage animation events drive the drop — see §3.
- **Disappear (1)**: burrow-down scale shrink, dive effect +
  `PSSE_EN_TAMAGOMUSHI_DIVE`, then `kill(nullptr)` (KoganeState.cpp:84-114).
  **Cave relocation**: if never flipped (`mHitCount == 0`) and the enemy carries
  a treasure drop code in a cave, `transitDisappear` re-registers it with
  `Cave::randMapMgr` and re-`init`s instead of dying (Kogane.cpp:250-262) — the
  beetle resurfaces elsewhere until looted once.

Spawning starts at scale 0.0001, invulnerable, no carcass, no death effect
(Kogane.cpp:34-56); the creature can never die by damage — HP (1000/1200/1500)
is only damaged while `EB_Bittered` (spray-petrified; transitDamageState adds
damage only then). Stone state temporarily lifts invulnerability and enables the
life gauge (Kogane.cpp:188-206). Piklopedia mode forces permanent Move
(Kogane.cpp:50-52).

## 3. Animation events (shared bank, `kogane/enemyanimmgr.txt`)

| Clip | Frames | Events (frame → key) | Gameplay meaning |
|---|---|---|---|
| move.bca | 15 | 2→0, 11→1 | loop/visual bounds |
| wait.bca | 15 | 0→0, 14→1 | loop/visual bounds |
| damage.bca | 50 | 5→2, 7→3, 29→4 | KEYEVENT_2 @5: `createPressSESpecial` (Fart only) + NoInterrupt on; KEYEVENT_3 @7: **`createItem()` — the drop** + zukan hide; KEYEVENT_4 @29: NoInterrupt off; END: escape check |

Event handling: KoganeState.cpp:244-268. Only the damage clip's events 2/3/4
are gameplay events; move/wait events are visual loop bounds. Source event
metadata does not itself execute drops — `createItem()` is native code.

## 4. Collision

`kogane/enemycoll.txt` (shared by all three): one root sphere radius 40.0 on
joint 1 (`body`), one child sphere radius 25.0 on the same joint. Stone info:
14 fragments (enemystoneinfo.txt). Retail collision radii differ only via the
per-species scale parm (0.8 kogane / 0.7 wealthy / 0.7 fart) applied through
`koganeScaleUp` (Kogane.cpp:278-295). Fart has smaller map/Pikmin atari radii
(fp01/fp34 = 10 vs 15) and LOD radius 40 vs 50 (retail parm dump, §6).

## 5. Drop / nectar behavior (defeat = flip, never death)

`createTreasureItem` (Kogane.cpp:386-414) runs before every table entry: on the
first flip, a beetle carrying a treasure (`mPelletDropCode`, cave spawns) drops
that treasure with a sparkle + `PSSE_EN_ENEMY_LOOSE_ITEM`, forces the escape
timer and skips the normal table. Otherwise `createItem` per flip count:

| Flip | Kogane (9) | Wealthy (10) | Fart (11) |
|---|---|---|---|
| 1st | surface: 1× 1-pellet · cave: 1× nectar | 3× 5-pellets · cave: 3× nectar | 3× nectar (surface and cave) |
| 2nd | 2× nectar | 3× nectar (or 1× ultra-spicy spray if `DEMO_First_Spicy_Spray_Made`) | 3× nectar (or 1× bitter spray if `DEMO_First_Bitter_Spray_Made`) |
| 3rd | 1× ultra-spicy spray if demo flag else 3× nectar; **then escapes** | same as 2nd; **then escapes** | 1× bitter spray if demo flag else 3× nectar; **then escapes** |

Source: Koganemushi.cpp:53-104, Wealthy.cpp:52-109, Fart.cpp:116-167. Third
flip sets `mAppearTimer = 12800` so the damage-anim END transits to Disappear
(KoganeState.cpp:260-265). Pellets are number-pellets colored randomly among
**met** Pikmin colors, fanned at 120°/(n+1) spacing (Kogane.cpp:420-448);
nectar/sprays via `createDoping` (Kogane.cpp:638-658). Machine-checked drop
tables live in `experimental/pikmin2_kogane_assets.py` (`DROP_TABLES`,
`drop_for`) with tests in `tests/test_pikmin2_kogane_assets.py`.

## 6. Behavior differences (written record)

| Trait | Kogane (9) | Wealthy (10) | Fart (11) |
|---|---|---|---|
| Life (fp00) | 1000 | 1200 | 1500 |
| Scale (fp40) | 0.8 | 0.7 | 0.7 |
| Surface time (fp01/fp02) | 20–30 s | 10–20 s (shortest) | 15–30 s |
| Stop time (fp20/fp21) | 0.5–2.0 s | 1.0–2.0 s | 1.0–3.0 s |
| Gas attack | — | — | **2.5 s cloud per Move entry**, radius fp22=20 around `mFartPosition` (behind body, offset fp20=50 × scale), `InteractGas` with fp24=0 raw damage — harm is the gas/poison stimulus itself, killing non-White Pikmin over time; `PSSE_EN_FART_GAS`/`PSSE_EN_OTAKARA_ATK_GAS`; buzz loop in state ≥ Move (Fart.cpp:24-31, 76-110, 213-230) |
| Loot character | small pellets + spicy spray | big 5-pellets + spicy spray (richest) | nectar only + **bitter** spray (uses `DEMO_First_Bitter_Spray_Made`, not spicy) |
| Treasure carry | cave first-flip treasure drop (all three, shared `createTreasureItem`) | same | same |
| Escape after loot | 3 flips max, then forced burrow (all three) | same | same |
| Unlooted cave escape | relocates via `Cave::randMapMgr` and resurfaces (all three) | same | same |
| Body effect | none | sparkle (`efx::TOoganeKira`) | fly swarm (`efx::TBabaFly_ver01`) |
| Change texture | kogane_s3tc.bti, karada k-color (60,60,60) | oogane_s3tc.bti, (100,100,100) | babakogane_s3tc.bti, (15,15,15) |
| Hit sound | `PSSE_EN_KOGANE_HIT` | `PSSE_EN_OOGANE_HIT` | `PSSE_EN_FART_HIT` (special slot) |
| Map/Pikmin atari fp01/fp34 | 15 / 15 | 15 / 15 | 10 / 10 |

vs. Pikmin 1 foundations: the family has **no Pikmin 1 counterpart** — it is new
in Pikmin 2. The reusable P1-side concepts are generic EnemyBase mechanics the
randomizer already models elsewhere (petrification/stone state, nectar and spray
drops, pellet scattering, burrow emergence analogous to P1's Burrowing Snagret
emerge/dive pattern), but there is no P1 species to proxy; per pipeline §2 the
playable-proxy level would need an explicit P1 behavior mapping decision by the
integration lead.

## 7. Reproducible conversion path

Module: `experimental/pikmin2_kogane_assets.py` (follows the sheargrub/groink
lane pattern; no edits to neighbor modules or shared converters).

```
python -m experimental.pikmin2_kogane_assets \
    --iso output/pikmin2-runtime/pikmin2-source-test.iso \
    --output output/pikmin2-kogane-assets/run1 --pose-limit 3
```

Reads only: `enemy/data/Kogane/{model.szs,anim.szs,kogane_s3tc.bti}`,
`enemy/data/Wealthy/oogane_s3tc.bti`, `enemy/data/Fart/babakogane_s3tc.bti`,
`enemy/parm/enemyParms.szs` (`kogane|wealthy|fart/*`). Output (private, not
committed): shared `enemy.bmd` (6 joints: null1, body, jnt13_1, jnt1_1, jnt5_1,
jnt9_1; 2 embedded textures), 3 clips × 3 sampled rigid poses = 9 `.mod` files +
conversion JSON, per-species parm/texture copies, and a hashed `beetles.json`
manifest.

Conversion note: the karada shape carries a `TEX1MTXIDX` display-list attribute
(retail sets `setTexMtxLoadType(0x2000)`, KoganeMgr.cpp:40-44), which the plain
`convert()` path rejects ("Unsupported display-list attribute"). Poses are baked
through the established explicit-draw-matrix path (`decode(..., bake_rigid=True,
draw_matrices=draw_matrices(blocks(model), pose))` from the Groink lane) — no
converter change was needed.

Reproducibility evidence: two independent runs into fresh directories produced
byte-identical manifests (`beetles.json` equal, all pose/model/texture SHA-256
equal). Run size ≈ 165 KB. Source disc hashes are recorded per file in the
manifest's `source_sha256`.

Limitations (recorded in manifest): sampled rigid poses with approximate
materials; no skeletal playback or event execution; drops, treasure carry,
burrow relocation and the gas attack are source-documented only and not
implemented natively in this lane.

## 8. Tests

`tests/test_pikmin2_kogane_assets.py` — 15 tests, all passing:

- **Spawn**: registry maps IDs 9/10/11 to the correct Obj/Mgr classes, distinct
  change-textures and karada k-colors (`SpawnRegistryTests`).
- **Defeat/drop**: full per-flip drop tables per species incl. cave/surface and
  spicy/bitter demo-flag branches, plus out-of-range rejection
  (`DropTableTests`).
- **Representative behavior**: gas-attack constants (2.5 s duration, state ≥ 2
  gate), damage-clip event frames 5/7/29, animation-registry validation,
  enemyparm parsing with duplicate-key/malformed rejection, pose-budget
  rejection before IO (`BehaviorConstantTests`, `ParmParseTests`,
  `BudgetTests`).

## 9. Open / handoff items

- Native hook wiring (spawn profile, gas InteractGas receiver, drop execution)
  belongs to the native track / integration lead — none touched here.
- `experimental/pikmin2_convert.py` `convert()` does not expose `draw_matrices`;
  the beetle lane works around it via `decode()` like the Groink lane. If the
  integration lead wants one interface, a minimal `convert()` passthrough would
  deduplicate this (shared file — not edited per lane boundaries).
- Playable-proxy level and the six arena gates remain unstarted for this family;
  treasure-carry (`mPelletDropCode`) interaction with cave generator placement
  needs a native-side decision.
- Parallel lanes (Breadbug 38/39/40/83, Mamuta 54) untouched; no shared-file
  changes required by this lane.
