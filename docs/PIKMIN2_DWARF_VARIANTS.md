# Dwarf Orange Bulborb and Dwarf Bulbear — source/variant audit (#200)

Evidence level: **Converted assets** (audit + deterministic model/pose banks + tests).
This document is source-only: it contains no disc content and no binary dumps.
Native installation, arena staging, playable proxy and P2-mechanics parity are
**NOT implemented** in this batch.

## Provenance

- Decomp research checkout: `native/pikmin2-research` (READ-ONLY), git revision
  `632af93787b9c95b63f0c13be32b161375ce3a96`. Per-file SHA-256 of every consulted
  source file is recorded in the private extraction metadata
  (`output/p2-dwarf-batch/*/dwarf-*-profile.json`, key `research_sha256`).
- Disc: local US **GPVE01 revision 0** image (game code and revision read from
  the disc header at runtime). Resource offsets/sizes are runtime catalogued;
  SHA-256 of every consumed file recorded in the same metadata (`source_sha256`).

## 1. Concrete identities vs aliases

From `include/Game/enemyInfo.h`, `src/plugProjectYamashitaU/enemyInfo.cpp` and
`src/plugProjectYamashitaU/generalEnemyMgr.cpp`:

| Species (internal) | EnemyID | Display name | Spawnable | Base class | FSM |
| --- | --- | --- | --- | --- | --- |
| `BlueKochappy` | 44 | Dwarf Orange Bulborb | Yes (`EFlag_CanBeSpawned`, `generalEnemyMgr.cpp` case registers `BlueKochappy::Mgr`) | `KochappyBase::Obj` | `KochappyBase::FSM` |
| `KumaKochappy` | 76 | Dwarf Bulbear | Yes (`KumaKochappy::Mgr` registered in `generalEnemyMgr.cpp`) | `Game::EnemyBase` (own `KumaKochappy::Obj`) | `KumaKochappy::FSM` (own) |

Resource-alias resolution (`enemyInfo.cpp` row fields → `enemyMgrBase.cpp`
`loadModelData`/`loadAnimData`/`initParms`/`initObjects` fallback to the own
name when a field is empty):

| Identity | model.szs | anim.szs | enemyAnimMgr.txt | enemyParm.txt | enemyColl.txt | texture swap |
| --- | --- | --- | --- | --- | --- | --- |
| BlueKochappy | `Kochappy` (alias) | `Kochappy` (alias) | `kochappy/` (alias) | `bluekochappy/` (own) | `kochappy/` (alias) | `/enemy/data/BlueKochappy/kochappy_body_s3tc.3.bti` replaces image 0 (`BlueKochappyMgr::loadTexData`, `BlueKochappy::Obj::changeMaterial`) |
| KumaKochappy | `KumaKochappy` (own; empty model field falls back to own name) | `Kochappy` (alias) | `kochappy/` (alias) | `kumakochappy/` (own) | `kochappy/` (alias) | none — own model embeds its full TEX1 (1120-byte TEX1 vs the 128-byte 8x8 placeholder in the shared Kochappy BMD) |

**Family nuance verified in source:** the dwarf bulborbs (`Kochappy`,
`BlueKochappy`, `YellowKochappy`) all derive from `KochappyBase::Obj` and are
texture variants of one shared model; `KumaKochappy` is a standalone
`EnemyBase` subclass with its own model, FSM, parameters and the
`ChappyRelation` parent link to `KumaChappy` (EnemyID 35, Spotty Bulbear). The
decomp source itself carries no breadbug-family class for the dwarf bulborbs —
they are `KochappyBase` (grub-dog line) code regardless of P2 lore labels; the
Dwarf Bulbear is likewise a grub-dog (`KumaKochappy`/`KumaChappy` line), and
**unlike** the dwarf bulborbs it is not a texture variant of a parent species.

Nonspawnable bases/helpers: `KochappyBase` is a shared base, not an enemyInfo
entry; `KumaChappy` (35) is a separately spawnable adult, not an alias of 76.

## 2. Retail parameter blocks (unflattened)

Blocks are `creature` / `general` / `proper` groups from
`enemy/parm/enemyParms.szs`, parsed without flattening duplicate keys across
groups. Raw retail values (all keys preserved in the extraction metadata):

**BlueKochappy** (`bluekochappy/enemyparm.txt`, SHA-256 `fd5724cb…89f572f`):

- creature: `s000=0.5 s001=0.5 s002=0.25 s003=0.1 s004=0.3` (scale/radius factors)
- general (45 keys): `fp00 health=250`, `fp01=20`, `fp02=0.2`, `fp03=0.25`, `fp04=0.3`,
  `fp05=0.1`, `fp06 move speed=60`, `fp08 turn rate=0.4`, `fp09 territory=500`,
  `fp10 home radius=80`, `fp11 private=70`, `fp12 sight=95`, `fp13 view angle=180`,
  `fp14 search dist=200`, `fp15 search angle=180`, `fp16 shake chance=1.0`,
  `fp17 shake knockback=50`, `fp18 shake damage=1`, `fp19 shake range=17`,
  `fp20 attack range=30`, `fp21 attack angle=20`, `fp22 attack hit radius=35`,
  `fp23 attack hit angle=20`, `fp24 attack damage=10`, `fp25 fov height=50`,
  `fp26 search height=50`, `fp27 life meter height=50`, `fp28 max turn=10`,
  `fp29 alert=15`, `fp30 vigilant life=30`, `fp31 regen=0`, `fp32 LOD=40`,
  `fp33 cell radius=20`, `fp34 pikmin radius=10`, `fp35 bitter time=1`,
  `fp36 purple damage=50`, `fp37 purple chance=0.3`, `fp38 purple stun=5s`,
  `ip01..ip07 = 1 1 1 2 2 3 2`
- proper: `fp01 absentminded=2`, `fp02 white-pikmin poison=300`, `fp03 rotation end angle=180`

**KumaKochappy** (`kumakochappy/enemyparm.txt`, SHA-256 `dac475d1…b6046df`):

- creature: identical `s000..s004` to BlueKochappy
- general (45 keys): differences from BlueKochappy: `fp00 health=500`,
  `fp12 sight=150`, `fp14 search dist=400`, `fp20 attack range=35`,
  `fp21 attack angle=25`, `fp22 attack hit radius=38`, `fp23 attack hit angle=25`,
  `fp26 search height=100`; all other keys identical (move speed 60, stun 5s,
  home radius 80, etc.)
- proper: `fp01 white-pikmin damage=500` (single key — `KumaKochappy::ProperParms`
  declares only `fp01 mPoisonDamage`)

**Header-vs-retail differences** (`include/Game/EnemyParmsBase.h`,
`KochappyBase.h`, `KumaKochappy.h` constructor defaults): retail overrides the
header defaults for health (100→250/500), move speed (80→60), purple stun
(10s→5s), and KumaKochappy proper `fp01` (300→500). KochappyBase proper `fp03`
rotation end angle header default is 90, retail is 180. Never read header
defaults as gameplay values.

## 3. State / motion mapping

Both species drive the same nine shared clips from
`enemy/data/Kochappy/anim.szs` (SHA-256 `4d837ac7…7bddd72c`), with event frames
from `kochappy/enemyanimmgr.txt` (SHA-256 `4c880816…aadbe3`). Event types: 0/1
are loop/motion timing (visual), 2/3 are gameplay-relevant (2 = notice cry /
flick apply / eat apply, 3 = swallow apply); END is the loop bound.

| Clip | AnimID (both) | Source frames | Event frames (frame→type) | Notes |
| --- | --- | --- | --- | --- |
| wait1 | 6 | 75 | 10→0, 60→1, 61→2 | 61 = `PSSE_EN_KOCHAPPY_NOTICE` cry in Wait states |
| move1 | 3 | 55 | 10→0, 39→1 | walk loop |
| attack | 0 | 90 | 8→2, 88→3 | 8 = eat apply, 88 = swallow/white-pikmin poison apply |
| dead | 1 | 90 | none | END triggers `kill(nullptr)` |
| flick | 2 | 80 | 31→2 | 31 = flick/shake apply |
| type1 (press) | 4 | 105 | none | squash death |
| type5 (carry) | 5 | 40 | 10→0, 29→1 | carcass motion |
| waitact1 (turn) | 7 | 25 | 6→0, 19→1 | turn action |
| waitact2 (eat-idle) | 8 | 17 | none | attack-miss eat motion |

**KochappyBase FSM** (BlueKochappy inherits all 10 states): Wait(0), Dead(1),
Turn(2), Walk(3), Attack(4), Flick(5), TurnToHome(6), GoHome(7), Press(8),
Demo(9) — `include/Game/Entities/KochappyBase.h`,
`src/plugProjectYamashitaU/kochappyState.cpp`.

**KumaKochappy FSM** (own, 7 states): Dead(0), Press(1), Wait(2), Attack(3),
Flick(4), Walk(5), WalkPath(6) — `include/Game/Entities/KumaKochappy.h`,
`src/plugProjectNishimuraU/KumaKochappyState.cpp`. WalkPath is the
parent-following state: it steers toward `setTargetParentPosition()`, a
formation slot `10*index+15` world units from the nearest living `KumaChappy`
found within `fp14`/`fp15` search distance/angle (`KumaKochappy.cpp`).
WalkPath moves at `setTargetSpeed(mSearchHeight())` — the decomp itself flags
this (`// ????`) as an apparent source quirk reusing fp26 as a speed.

## 4. Collision, joints, drops, receivers, cleanup

- Collision: shared `kochappy/enemycoll.txt` (SHA-256 `99db7c52…d47e296`) for
  both species: root sphere radius 20 at offset (0, −2.5, 2.5) joint 0, plus
  child spheres (first child radius 10, code `{s___}`, joint 3, …).
- Attachment/mouth: single mouth slot on joint `kamu`, radius 15
  (`KochappyBase.cpp` / `KumaKochappy.cpp initMouthSlots`). Shadow joint `ago`.
  Walk smoke on `asiL`/`asiR` (radius 4.0). KumaKochappy down-smoke scale 0.4.
- Stone/corpse pose: `kumakochappy/enemystoneinfo.txt` (19 joints,
  SHA-256 `828bf808…734406a`); kochappy-line uses `kochappy/enemystoneinfo.txt`.
- Drops/rewards: both are `BDT_Normal` bitter-drop class in `enemyInfo.cpp`;
  corpse carries use the shared carry (type5) motion and mouth/carry slots.
  No pellet drops defined in the audited parameter blocks.
- Elemental receivers: white-pikmin poison is applied at attack swallow
  (KEYEVENT_3, frame 88) via `EnemyFunc::swallowPikmin` with proper `fp01`
  (300 kochappy-line / 500 KumaKochappy). Purple-pikmin hipdrop: `fp36`
  damage 50, `fp37` chance 0.3, `fp38` stun 5s; `pressCallBack` /
  `hipdropCallBack` transit to Press (squash) when not bittered.
- Cleanup dependencies: `KumaKochappy::Obj::onKill` calls `releaseParent()`
  (removes its `ChappyRelation` node from the parent KumaChappy list) before
  `EnemyBase::onKill` — any future native port must clear this relation on
  death/reset. Dwarf bulborbs have no such external relation.

## 5. Converted assets (this batch)

Modules (new, family-prefixed, extraction/profile separate from bank/evidence):

- `experimental/pikmin2_dwarf_orange_profile.py` — audit + extraction (BlueKochappy).
- `experimental/pikmin2_dwarf_orange_bank.py` — deterministic pose bank (`P2_DWARF_ORANGE_BANK_1`).
- `experimental/pikmin2_dwarf_bear_profile.py` — audit + extraction (KumaKochappy).
- `experimental/pikmin2_dwarf_bear_bank.py` — deterministic pose bank (`P2_DWARF_BEAR_BANK_1`).

Exported models: `dwarf-orange.bmd` SHA-256
`a3f7b72c66c31f40c6508af1ecfedea2884c66a1f97e6106fb790e1388a37e1b` (11,392 bytes,
image-0 texture replaced with the .3.bti per `changeMaterial`);
`dwarf-bear.bmd` SHA-256
`939837e979d934e933e5f977e196c2a7a494088b65b9b3047a858684577ef8f2` (10,272 bytes,
self-contained). Both skeletons have 13 joints; all nine shared clips evaluate
on both.

Pose banks (12-sample base + event frames merged, 24-pose cap): 64 poses each.
Dwarf Orange: 1,024,000 mod bytes (wait1 14 poses, move1 12, attack 13, dead 12,
flick 13 — event frames 10/60/61, 10/39, 8/88, –, 31 all preserved; first=0 and
last=duration−1 on every clip). Dwarf Bulbear: 894,976 mod bytes, same pose
counts. Budgets: 512 KiB/clip, 2 MiB total — within limits.

Material/TEV approximations: rigid bake via the existing converter with
`approximate_materials=True`; TEV stages are approximated, not source-faithful;
nonuniform BCA scale enabled (`allow_scale=True`) matching the Kochappy-line
importer. Unsupported: no J3D material fidelity, no blending between poses, no
event execution (damage/sound/drops), no skinned/weighted meshes needed here.

Reproducibility: two independent extraction+bank runs into fresh private dirs
under `output/p2-dwarf-batch/`; SHA-256 of every generated binary/text file is
identical across runs (`output/p2-dwarf-batch/reproducibility.json`,
conclusion PASS; converter sidecar JSON embeds run-directory provenance paths
and is compared with those fields stripped; wall-clock seconds excluded).

## 6. Behavior differences vs a P1 proxy (NOT implemented this batch)

| P2 behavior | Classification | Source |
| --- | --- | --- |
| Dwarf Orange Bulborb: identical FSM/AI to Dwarf Red Bulborb (shared `KochappyBase::FSM`) | covered-by-P1-proxy (P1 Dwarf Bulborb AI approximates chase/attack/flick; timing differs) | `BlueKochappy.cpp` `setFSM(new KochappyBase::FSM)` |
| Dwarf Orange: notice cry at wait1 frame 61 alerting/consistency | needs-P2-mechanics (P1 has no `PSSE_EN_KOCHAPPY_NOTICE` event frame) | `kochappyState.cpp` StateWait KEYEVENT_2 |
| Dwarf Orange: health 250 / move speed 60 / stun 5s vs P1 dwarf bulborb tuning | needs-P2-mechanics (parameter hook) | `bluekochappy/enemyparm.txt` |
| Dwarf Orange: purple-pikmin stun (fp36–38) | needs-P2-mechanics (P1 has no purple pikmin) | `EnemyParmsBase.h`, kochappyState flick/press |
| Dwarf Orange: press/squash death (type1) and carcass (type5) motions | covered-by-P1-proxy visually; needs-P2-mechanics for exact timing | KochappyBase AnimID 4/5 |
| Dwarf Bulbear: follows nearest living Spotty Bulbear in a formation slot (`ChappyRelation`, WalkPath) | needs-P2-mechanics (no P1 equivalent; requires parent KumaChappy actor + relation list) | `KumaKochappy.cpp` setNearestParent/setTargetParentPosition, `KumaKochappyState.cpp` StateWalkPath |
| Dwarf Bulbear: spotting via sight radius 150 / view 180° then Walk→Attack | covered-by-P1-proxy (P1 chase approximates; source uses `EnemyFunc::getNearestPikminOrNavi`) | `KumaKochappy.cpp` getSearchedTarget |
| Dwarf Bulbear: orphan behavior (no parent found → Wait at current position, `updateHomePosition` pins home to self) | needs-P2-mechanics | `KumaKochappyState.cpp` StateWait/StateWalkPath, `updateHomePosition` |
| Dwarf Bulbear: eat two-phase attack (frame 8 eat, frame 88 swallow + white-pikmin 500 damage) | needs-P2-mechanics (P1 attack is single-event) | `KumaKochappyState.cpp` StateAttack KEYEVENT_2/3 |
| Dwarf Bulbear: flick (frame 31) shaking off stuck + nearby Pikmin and leaders | covered-by-P1-proxy approximately; needs-P2-mechanics for exact receivers | `KumaKochappyState.cpp` StateFlick |
| Dwarf Bulbear: press/hipdrop squash → Press state, health zeroed, type1 motion | covered-by-P1-proxy (P1 squash exists); timing differs | `KumaKochappy.cpp` pressCallBack/hipdropCallBack |
| Both: death → dead.bca then kill at KEYEVENT_END; bitter (BDT_Normal) drop table | needs-P2-mechanics (P2 bitter/spray drops do not exist in P1) | StateDead, `enemyInfo.cpp` |
| Both: zukan/piklopedia random start frame | N/A (menu-only) | `KumaKochappy.cpp` resetZukanAnimationFrame |
| Both: day-end takeoff appearance flags | N/A (out of scope for import) | `enemyInfo.h` flags |

## 7. Tests

`tests/test_pikmin2_dwarf_orange.py` and `tests/test_pikmin2_dwarf_bear.py`:
profile validation (malformed groups, nonfinite/boolean rejection, wrong retail
values), source-audit mismatch rejection per file mutation, event-frame
preservation and ordering, bank parse (header/order/truncation/trailing),
byte-budget and resource-mismatch rejection in `validate_files`, exact-byte
config writes (no CRLF translation), build-time source mismatch (model/clip
hash, wrong species) and refusal to write into pre-existing/invalid state.
Full pikmin2 suite: 654 passed, 2 skipped (pre-existing platform skips).
