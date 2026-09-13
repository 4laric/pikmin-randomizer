# Flora & Candypop lane source contract — Pelplant (0), BluePom (3), RedPom (4), YellowPom (5), BlackPom (6), WhitePom (7), RandPom (8), Tanpopo (46), Clover (47), HikariKinoko (48), Ooinu_s/Ooinu_l (49/50), Wakame_s/Wakame_l (51/52)

Issue: [#353](https://github.com/4laric/pikmin-randomizer/issues/353) (parent
[#171](https://github.com/4laric/pikmin-randomizer/issues/171); integration
contract [#186](https://github.com/4laric/pikmin-randomizer/issues/186)).
Source: `native/pikmin2-research` decompilation against US GPVE01 rev 0; retail
resources are the `enemy/parm/enemyParms.szs` blocks and disc-derived values
already recorded in the #171 audit (`docs/PIKMIN2_FLORA_AUDIT.md`, commit
`e00608e`). Evidence level achieved: **source contract + converted-asset
preparation** (per [the import pipeline](PIKMIN2_ENEMY_IMPORT_PIPELINE.md)); no
native hook wiring in this lane. Pellet-to-Pom conversion math is documented as
a **reference predicate only**.

## 1. Identity and registration

| ID | Constant (`include/Game/enemyInfo.h`) | Common name | Obj / Mgr class | `enemyInfo.cpp` row | `generalEnemyMgr.cpp` case |
|---|---|---|---|---|---|
| 0 | `EnemyID_Pelplant` (:59) | Pellet Posy | `Game::Pelplant::Obj` / `Mgr` | :10 | :217-218 |
| 3 | `EnemyID_BluePom` (:62) | Lapis Lazuli Candypop Bud | `Game::Pom::Obj` / `Mgr` | :19 | :238-239 (`EnemyID_Pom`) |
| 4 | `EnemyID_RedPom` (:63) | Crimson Candypop Bud | `Game::Pom::Obj` / `Mgr` | :20 | :238-239 |
| 5 | `EnemyID_YellowPom` (:64) | Golden Candypop Bud | `Game::Pom::Obj` / `Mgr` | :21 | :238-239 |
| 6 | `EnemyID_BlackPom` (:65) | Violet Candypop Bud | `Game::Pom::Obj` / `Mgr` | :22 | :238-239 |
| 7 | `EnemyID_WhitePom` (:66) | Ivory Candypop Bud | `Game::Pom::Obj` / `Mgr` | :23 | :238-239 |
| 8 | `EnemyID_RandPom` (:67) | Queen Candypop Bud | `Game::Pom::Obj` / `Mgr` | :24 | :238-239 |
| 46 | `EnemyID_Tanpopo` (:105) | Dandelion | `Game::Tanpopo::Obj` / `Mgr` | :70 | :340-341 |
| 47 | `EnemyID_Clover` (:106) | Clover | `Game::Clover::Obj` / `Mgr` | :72 | :343-344 |
| 48 | `EnemyID_HikariKinoko` (:107) | Common Glowcap | `Game::HikariKinoko::Obj` / `Mgr` | :73 | :346-347 |
| 49 | `EnemyID_Ooinu_s` (:108) | Figwort (red small) | `Game::Ooinu_s::Obj` / `Mgr` | :74 | :349-350 |
| 50 | `EnemyID_Ooinu_l` (:109) | Figwort (red large) | `Game::Ooinu_l::Obj` / `Mgr` | :76 | :355-356 |
| 51 | `EnemyID_Wakame_s` (:110) | Shoot (small) | `Game::Wakame_s::Obj` / `Mgr` | :78 | :361-362 |
| 52 | `EnemyID_Wakame_l` (:111) | Shoot (large) | `Game::Wakame_l::Obj` / `Mgr` | :79 | :364-365 |

- One Mgr case handles all six colour buds: `case EnemyTypeID::EnemyID_Pom:
  mgr = new Pom::Mgr(limit, viewNum)` (`generalEnemyMgr.cpp:238-239`); the
  per-slot concrete identity is stamped later from the six colour IDs
  (`PomMgr.cpp:95-109`). The registration entries 3-8 therefore point their
  `parent ID` at `EnemyID_Pom` (`enemyInfo.cpp:19-24`).
- Two-identity small/large groups: `Ooinu_s`/`Ooinu_l` (49/50) and
  `Wakame_s`/`Wakame_l` (51/52) are separate registered IDs with separate
  Obj/Mgr classes and resources. The small siblings carry `EFlag_HasNoInfo`
  (`enemyInfo.cpp:74,78`) and fold into the large sibling for Piklopedia
  purposes; this lane models the pair as `VARIANT_GROUPS` but does not alias
  their runtime IDs.
- Out-of-scope siblings registered in the same block: `KareOoinu_s/_l`
  (91/92), `Tukushi` (80), `Watage` (81), `DaiodoRed/Green` (85/86),
  `Magaret` (87), `Nekojarashi` (88), `Chiyogami` (89), `Zenmai` (90), and the
  unspawnable `Pom` base (82, `enemyInfo.cpp:18`, `EFlag_UseOwnID` only, no
  `EFlag_CanBeSpawned`). None is claimed by this lane.
- Spectralid child linkage: only `Tanpopo`, `Ooinu_l` and `Magaret` declare the
  Spectralid child and reserve slots (`enemyInfo.cpp:70,76,83`;
  `generalEnemyMgr.cpp:824-836`); the other plants, even if generator-flagged,
  would spawn without a reservation. Not wired here.

## 2. Candypop shared base and the Pelplant/Pom receptor relationship

- **Shared base.** All six colour buds are one class (`Game::Pom::Obj`) and
  read the base resources: their `enemyInfo.cpp` resource slots are all the
  literal `"Pom"` (`:19-24`), so model, animation, parameter and collision all
  resolve to `enemy/data/Pom/` and `pom/…`. `Pom::Obj::getEnemyTypeID()`
  returns the stored `mPomID` (`Pom.h:37-40,73`), which `Mgr::createObj`
  stamps per slot (`PomMgr.cpp:99-107`). Base ID 82 has no slot, no generator
  and no `EFlag_CanBeSpawned`, which is why it cannot be spawned
  (`enemyInfo.h:35,141`); it is explicitly **not** exposed as a spawnable
  identity by this module.
- **Receptor (Pom side).** `Pom::Obj` owns one `MouthSlots` mapped to
  `jnt_center` (`Pom.cpp:197-201`). A Pikmin enters only through a press on the
  `slot` collision part while the bud is armed and under its lifetime budget
  (`Pom.cpp:154-169`); any colour is accepted. `shotPikmin` kills the stuck
  Pikmin and births leaf `ItemPikihead` sprouts of the bud colour
  (`Pom.cpp:280-322`), with an own-colour slot refund for the non-Queen buds
  (`Pom.cpp:296-298`).
- **Receptor (Pelplant side).** `Pelplant::Obj` captures a
  `Game::PelletNumber::Object` (`mPellet`, `Pelplant.h:236`) onto `headjnt`
  via `attachPellet`/`startCapture` (`pelplant.cpp:456-475`) and releases it
  from the dead state with `endCapture` (`pelplantState.cpp:445-451`). The
  pellet is what makes a full posy a living/damageable target
  (`Pelplant.h:187-190`) and what a Pikmin carries off. Both Pelplant and Pom
  derive from `EnemyBase` and expose a `PelletView` sub-object
  (`Pelplant.h:241`, `Pom.h:74`).
- **Reference predicate.** `reference_conversion()` in
  `experimental/pikmin2_flora_assets.py` encodes the source math (Pelplant
  pellet size 1/5/10/20 → Pikmin; Pom swallowed → one sprout each or the Queen
  `ip13` multiplier; own-colour refund for colour buds) as a pure function
  returning `reference_only=True`. It is never called by `extract` and is not
  wired into any converter, arrival or receiver path.

## 3. State machines (source facts)

- `Pelplant::StateID` (`Pelplant.h:37-50`): WaitSmall/WaitMiddle/WaitFull,
  GrowSmallMid, GrowMidFull, Damage, Dead, WitherFull/WitherMiddle/WitherSmall.
  Growth is a seconds timer (`fp01` small→middle, `fp02` middle→full,
  `pelplantState.cpp:193-257`); only Full is vulnerable and releases the pellet
  on death.
- `Pom::StateID` (`Pom.h:153-161`): Wait, Dead, Open, Close, Shot, Swing. Open
  key-2 arms swallow; Swing closes after `fp01` or when the budget is spent;
  Close goes to Shot if Pikmin are inside, else reopens
  (`PomState.cpp:101-235`). The Queen cycles colour on `fp02`
  (`Pom.cpp:330-355`).
- Prop flora have **no FSM**: `Game::Plants::Obj` allocates no state machine
  and only reacts to collision/earthquake by restarting the single clip
  (`plants.cpp:101-201`, `plantsMgr.h:36-39`).

## 4. Animation key events

Clip order equals the AnimID enum order and the `enemyanimmgr.txt` row order.
Events are data only (0/1 = loop bounds, 2 = native event hook); none is
executed here.

- **Pelplant** (`Pelplant.h:328-340`): `damage3, dead3, grow1, grow2, wait1,
  wait2, wait3, bgrow1, bdamage1, bdead1`. `wait1`/`wait2`/`wait3` carry
  `0:0 29:1`; grow, damage and dead clips have no keys.
- **Candypops** (`Pom.h:130-138`): `wait, dead, type1, type2, type3, type4`.
  `type1` (open) has key `25:2`; `type3` (shot) has key `20:2`; `wait`, `dead`,
  `type2` and `type4` end only.
- **Prop flora** (`plantsMgr.h:36-39`): a single `PLANTANIM_Default` clip per
  species; no key events are claimed in source. The per-species bca stem is
  read from the disc at extraction time (see §9).
- **Large-variant registration casing**: on disc the `Ooinu_l` and `Wakame_l`
  rows register `ooinu_L.bca` and `wakame_L.bca` (capital `L`) while `anim.szs`
  stores the lowercase members `ooinu_l.bca`/`wakame_l.bca`. `flora_animation_rows`
  keeps the same token/event grammar with a case-insensitive file pattern and
  the extractor resolves the archive member by casefold, so the registered stem
  is normalised to `ooinu_l`/`wakame_l` for the clip registry and report.

## 5. Parameter contract (header defaults vs retail disc)

`experimental/pikmin2_flora_assets.py` keeps `PROPER_PARM_DEFAULTS` (C++
constructor values) and `DISC_PARMS` (retail `enemyParms.szs` values) separate
and reports keys that fell back to a header default in
`proper_keys_defaulted_from_header`. Every proper key is serialized on this disc
revision, so nothing falls back to a header default. Enemy flora serialize
creature + general + proper (3 blocks); prop flora allocate a plain
`EnemyParmsBase` (`plantsMgr.cpp:18-21`), whose `read` consumes only
`CreatureParms` and `mGeneral` (`EnemyParmsBase.h:162-166`), so they read
creature + general (2 blocks). Clover additionally ships an inert third block
after its general block (`{'fp01': 25.0}`), verified and reported under
`unused_disc_blocks` but never consumed by `Clover::Mgr::doAlloc`
(`plantsMgr.cpp:46-48`). General keys are validated against the declared
`EnemyParmsBase` fields `fp00-fp38` (except `fp07`) and `ip01-ip07`
(`EnemyParmsBase.h:51-150`); unknown keys are rejected.

| Identity | Header proper defaults | Retail disc proper | Defaulted from header |
|---|---|---|---|
| Pelplant | `fp01=120, fp02=120, fp03=1.5` (`Pelplant.h:284-286`) | `fp01=90, fp02=60, fp03=1.5` | none |
| BluePom..RandPom | `ip01=5, ip11=1, ip13=5, fp01=30, fp02=1.25, fp03=0.15` (`Pom.h:100-105`) | `ip01=5, ip02=1, ip11=1, ip12=1, ip13=9, fp01=1.0, fp02=2.6, fp03=0.0` | none |
| Prop flora | none (`plantsMgr.cpp:18-21`) | general only; Clover also `extra fp01=25` (unused) | — |

`ip02` and `ip12` are serialized in the Pom proper block but are not declared by
`Pom::Parms::ProperParms` (`Pom.h:96-115`); they are reported separately in
`proper_retail_only` and are not treated as header defaults. `fp03` is `0.0` on
disc (`proper_retail`) versus the `0.15` constructor default. General-block
retail values recorded: Pelplant `fp00=50` (health); prop flora `fp00=1100`
(health, never read, plants.cpp). Clover's general block `fp01` is `40.0`; the
`25.0` value belongs to the inert trailing block, not to `mGeneral` (the earlier
"floor offset" reading was wrong). The audit notes Violet/Ivory floor gating and
Queen/own-colour refund are behavior, not serialized parms, and are out of scope
here.

## 6. Model + animation + parm resource map

Reads on GPVE01 rev 0 (`EnemyMgrBase::loadModelData/loadAnimData`,
`enemyMgrBase.cpp:519-548`):

| Resource directory | Identities | Model | Animation | Parm archive subdir |
|---|---|---|---|---|
| `enemy/data/Pom/` | BluePom, RedPom, YellowPom, BlackPom, WhitePom, RandPom | `model.szs → enemy.bmd` | `anim.szs` | `pom/` |
| `enemy/data/Pelplant/` | Pelplant | `model.szs → enemy.bmd` | `anim.szs` | `pelplant/` |
| `enemy/data/<Name>/` | Tanpopo, Clover, HikariKinoko, Ooinu_s, Ooinu_l, Wakame_s, Wakame_l | `model.szs → enemy.bmd` | `anim.szs` | `<name>/` |

The parm archive subdirs are lowercase (`pelplant/`, `pom/`, `ooinu_l/`, …) and
on GPVE01 rev 0 every flora subdir holds only `enemyanimmgr.txt`,
`enemyparm.txt` and `enemycoll.txt` — none ships `enemystoneinfo.txt` (that is
an enemy petrification parm). The three present files are preserved verbatim and
hashed into the manifest; the absent member is recorded per species in
`metadata_absent` and is not required. The `resource_id()` helper encodes the
Pom aliasing so the six buds read the shared `Pom` bank.

## 7. Reproducible extraction path

Module: `experimental/pikmin2_flora_assets.py` (follows the ground-invertebrate
lane; no edits to neighbouring modules or shared converters).

```
python -m experimental.pikmin2_flora_assets \
    --iso output/pikmin2-runtime/pikmin2-source-test.iso \
    --output output/pikmin2-flora-assets/run1 --pose-limit 3
```

Reads only the `enemy/data/<resource>/{model.szs,anim.szs}` pairs and the
`<resource>/*` metadata from `enemy/parm/enemyParms.szs`. Output (private, not
committed): per-identity `enemy.bmd`, all `.bca` clips, the metadata text
files that exist, sampled rigid `.mod` poses + conversion JSON, and a hashed `flora.json`
manifest (`schema=1`, policy `P2_FLORA_1`, disc id/revision, source revision,
per-file SHA-256) plus `p2-flora.txt`. `extract` hashes every disc read so
duplicate runs must produce identical manifests, and refuses to overwrite an
existing output directory before touching the source.

## 8. Tests

`tests/test_pikmin2_flora_assets.py` — mirror of the ground-invertebrate test
layout with a mocked disc reader (no ISO required):

- **Registry**: IDs 0, 3-8, 46-52 → `SPECIES`, clip/event/state maps; enemy
  flora require a proper block, prop flora take two blocks (plus Clover's inert
  third) and reject any other trailing block; the 49/50 and 51/52 variant groups
  are paired and contiguous.
- **Parm parsing**: retail proper/general values match `DISC_PARMS`; header
  defaults stay distinct (`Pelplant fp01=120` vs disc 90, `Pom ip13=5` vs disc
  9, `Pom fp03=0.15` vs disc `0.0`); all serialized keys are present so nothing
  is recorded as defaulted; `ip02`/`ip12` are reported as `proper_retail_only`;
  Clover's extra block and `metadata_absent` are recorded; unknown general and
  proper keys and any disc-param drift are rejected.
- **Animation registry**: clip order and event streams enforce the disc order;
  `flora_animation_rows` accepts the capital `L` stems for `Ooinu_l`/`Wakame_l`
  and the profile normalises them to the lowercase archive stems; swapped clips
  and drifted events are rejected.
- **Shared base / reference predicate**: `resource_id` resolves all colour
  buds to `Pom`; `reference_conversion` yields 1:1 sprouts, the Queen `ip13`
  multiplier and own-colour refund, and rejects out-of-range input.
- **Gate/non-claims**: `native_ready false`,
  `gameplay_events_executed false`, `btk_playback false`; overwrite refusal
  precedes source access; wrong-region disc and source-revision gates reject
  before any output is created; pose-limit bounds enforce 2..12.

Validation (repo root): `python -m pytest tests/test_pikmin2_flora_assets.py -q`.

## 9. Explicit non-claims

- No native hooks, no actor/AI/FSM execution, no installs, no arena placement,
  no converter or arrival/receiver wiring.
- The Pellet-to-Pom conversion math is a **reference predicate only**; it is
  not called from `extract` and does not alter gameplay.
- No btk playback, no TEV/material equivalence claim, no save/lifecycle claim.
- Base `Pom` (82) is never exposed as spawnable; the six colour identities are
  prepared as shared-base resources, not as runtime-stamped actors.
- Prop-flora single-clip bca stems are confirmed on disc (`tanpopo.bca`,
  `clover.bca`, `hikarikinoko.bca`, `ooinu_s.bca`, `ooinu_l.bca`, `wakame_s.bca`,
  `wakame_l.bca`); the decomp source exposes only the index `PLANTANIM_Default`.
  The `Ooinu_l`/`Wakame_l` registration spelling uses a capital `L`, resolved
  case-insensitively against the lowercase archive member.
- No flora parm subdir ships `enemystoneinfo.txt` on this revision; absence is
  recorded per species in `metadata_absent`, not treated as an error.
- Converter-limited poses are recorded as unsupported with a reason and never
  fabricated. As of #405 the sampled Pelplant keys convert (10/10 clips) under
  the opt-in `singular_scale='allow'` + `singular_normal='transpose-adjugate'`
  pair (see [PIKMIN2_SINGULAR_SCALE.md](PIKMIN2_SINGULAR_SCALE.md)); the single
  HikariKinoko clip still fails on an unsupported shape-matrix type (billboard,
  type 1) and is recorded as unsupported. The run completes and writes
  `flora.json`.
- Spectralid spawning and cave floor gating (Violet/Ivory/Queen budgets) are
  recorded as source facts only.

## 10. Open / handoff items

- Converter/arrival wiring for the Candypop shared base, Pelplant pellet
  capture and the plant spawn sentinel belongs to #186 — untouched here.
- Native hook wiring (Pelplant farm `farmCallBack` growth/wither, spectralid
  plant groups, Queen colour cycle, bud lifetime budget) belongs to the native
  track.
- Parallel flora IDs (80/81/85-92) remain with their own audit; no shared-file
  changes are required by this lane.

## 11. Batch 2 — install + arena (#353)

Batch 2 takes the batch-1 `flora.json` assets into the runtime through the
shared core (`experimental/pikmin2_batch2_core.py`) bound by
`experimental/pikmin2_flora_install.py` and `pikmin2_flora_arena.py`.

- **Install**: hash-bound `plan`/`install`/`verify_install`; schema-1
  `P2_FLORA_1` manifest, exact-byte pose binding, conflict refusal before
  mutation, optional all-or-nothing visual bank (baseline preserved when
  absent). Pelplant (0/10) and HikariKinoko (0/1) have no converted poses on
  this disc and are excluded from the visual actor set.
- **Arena**: private original Impact Site staging — the six Candypop colour buds
  plus one ordinary P1 control, unique generator IDs 353001–353007, full
  expected XYZ, zero offset, source yaw unapplied. Buds have no P1 counterpart,
  so the neutral Chappy placement vehicle is used and identity is not claimed.
- **Real-disc evidence**: install + verify round-trip against
  `output/p2-lane-verify/flora2/flora.json` → **66 installed, 66 verified**
  (SHA-256 bound). Generated evidence stays under private `output/`.
- **Status**: install + arena staging level. Native gates
  (`native_identity`, `candypop_shared_pom_base`, `pellet_to_pom_conversion`,
  `pelplant_receptor`, `sprout_birth`, `prop_flora_scenery`) are BLOCKED pending
  the hook request on #186. No shared/native code touched; no disc assets
  committed.

### Native registration (family-owned)

Workflow revision 2026-09-13 ([#186](https://github.com/4laric/pikmin-randomizer/issues/186)):
the flora family owner implements narrow additive registration hooks.
Implemented in this pass by the shared `native/pc_port/pc_p2_batch2.cpp` unit,
wired through `pc_p2_batch2_setup/draw/reset/forget`; the six Candypop colour
buds bind as `TEKI_Chappy` placement vehicles from `p2-flora-actors.txt` /
`p2-flora-bank.txt` and the `flora_*` pose bank. See
[Batch-2 native registration](PIKMIN2_BATCH2_NATIVE_REGISTRATION.md). Visual-only
P1 proxy; all runtime gates remain BLOCKED/UNTESTED pending a supplied-asset
runtime pass.
