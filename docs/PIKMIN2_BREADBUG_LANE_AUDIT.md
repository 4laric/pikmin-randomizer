# Breadbug lane audit (#213)

Lane child of #168 (parallel to beetle lane #212 and Mamuta lane). Implementation
owner: Codex on shared account 4laric. Source evidence read from the local
`native/pikmin2-research` decompilation snapshot (US GPVE01 rev 0); disc resources
from a locally supplied US rev 0 ISO. This audit installs no native hook,
placement, save or reward behavior.

## 1. Registered identity and classification

| ID | Name | Role | Spawnable | Evidence |
|---|---|---|---|---|
| 38 | PanModoki | creature (Breadbug) | yes | `include/Game/enemyInfo.h:97`; `EFlag_CanBeSpawned` at `enemyInfo.cpp:66`; own `PanModoki::Mgr` at `generalEnemyMgr.cpp:328-330` |
| 39 | PanModokiNest | helper_alias | **no** | `enemyInfo.h:98`. Only a resource-name alias: `EnemyInfoFunc::getEnemyResName` rewrites 39→83 before lookup (`enemyInfo.cpp:168-173`). Generator token "パンモドキ巣" parses (`genEnemy.cpp:532-534`), but there is **no EnemyInfo table row for 39** and **no case 39** in `generalEnemyMgr.cpp`. It has no manager, no FSM and no parameter binding of its own; exposing it as a spawnable creature would dereference a base that does not exist |
| 40 | OoPanModoki | source_boss (Giant Breadbug) | yes | `enemyInfo.h:99`; `EFlag_CanBeSpawned` at `enemyInfo.cpp:67`; listed in `IS_ENEMY_BOSS` (`enemyInfo.h:216`); own `OoPanModoki::Mgr` at `generalEnemyMgr.cpp:331-333` |
| 83 | PanHouse | helper_nest (Breadbug Nest) | **no** | `enemyInfo.h:142`; table row carries `EFlag_HasNoInfo` (`enemyInfo.cpp:68`). `Nest::Mgr` is constructed only for ID 83 (`generalEnemyMgr.cpp:334-335`), but `Nest::Obj` is born and killed exclusively by its owner Breadbug (`panModoki.cpp:54-75, 1520-1526`). Helper lifetime is parent-bound; never autonomous |

`experimental/pikmin2_breadbug_lane.py` records this classification as
`ENTRIES`; `tests/test_pikmin2_breadbug_lane.py` fails if 39 or 83 ever become
`spawnable`.

## 2. AI / state transitions (PanModokiBase FSM)

Eleven states (`PanModokiBase.h:29-43`), registered in
`panModokiState.cpp:13-27`:

| State | Entered from | Key behavior | Exits to |
|---|---|---|---|
| Appear (4) | birth (`panModoki.cpp:114`); Hide timeout (`panModokiState.cpp:432-435`) | type2 motion, appear effect/rumble, hard constraint on | Walk at KEYEVENT_END |
| Walk (1) | Appear end, Wait end, Stick abort | waypoint/pellet seeking via `walkFunc` (`panModoki.cpp:921-989`) | Stick when in pellet radius (`panModoki.cpp:1013-1017`); Dead on health ≤ 0 |
| Stick (8) | Walk near target | approaches cargo; 200-frame/2.5×size abort (`panModokiState.cpp:614-618`); on contact `startStick(target, 9999)` + `startPick` | Back (grabbed) or Walk |
| Back (2) | Stick/Pulled | drags cargo toward nest over pathfinder waypoints; `carryTarget(1.0f)` pulls with `mCarryStrength` (`panModoki.cpp:1268`) | CarryEnd at nest; Pulled if contest lost (`!canBack()`); Wait if cargo invalid/another teki sticks |
| Pulled (3) | Back when Pikmin out-pull | reverse drag (contest); Giant plays PSSE_EN_OPAN_HIPPARARE per loop (`panModokiState.cpp:283-287`) | Back when it re-wins; Wait on invalid cargo |
| CarryEnd (10) | Back at nest | walks into home position | Hide at motion end/loop end |
| Hide (5) | CarryEnd | type3 motion; at KEYEVENT_END: health refills to full, `endCarry()` consumes cargo, BitterImmune (`panModokiState.cpp:422-427`) | Appear after `fp15` frames (150) with no cargo |
| Damage (6) | press/hipdrop callbacks (`panModoki.cpp:462-515`), stone bounce (`:570-575`) | releases cargo (`giveup(2)`), applies fp04 (sucked) or fp06 (press) damage | Wait, or Dead on health ≤ 0 |
| Wait (7) | Damage end, invalid cargo release | waits `fp14` frames (retail 0 — effectively immediate) | Walk |
| Sucked (9) | Onion/ship vacuum (`suckFinish`, `panModoki.cpp:1381-1392`) | drops cargo, sets `mCanReactToPress` | Damage on ground bounce |
| Dead (0) | any state, health ≤ 0 | releases stick, `deathProcedure`, `killNest` | kill at KEYEVENT_END |

Animation/event mapping (`PanModokiBase.h:242-253`): Dead=dead.bca (99f),
Walk=move1 (54f, events [10,0],[39,1]), Back=move2 (49f, [10,0],[39,1]),
Pulled=type1 (49f, [5,0],[10,1]), Appear=type2 (69/70f), Hide=type3 (49f,
[20,2]), Damage=type4 (54f small / 24f giant), Carry=type5 (39f, corpse
carry), Wait=wait1 (59f). Source events are metadata only; no damage, capture,
sound or drop executes in the converted banks.

## 3. Collision

Small Breadbug: 2 nodes — root `{none}` r=30 on joint 6 (`body`), child
`{body}` r=15 same joint (`enemycoll.txt`, verified in
`breadbug-lane.json`). Giant: root `{none}` r=50 + child `{body}` r=30, both
joint 0. Nest: two `{none}` spheres r=50/60 on joint 0, scaled by fp00
(`panModoki.cpp:40-48`). Mouth slot binds joint `kamu`, radius 30
(`panModoki.cpp:672-681`); walk smoke on `asiL`/`asiR` (`:750-755`). Stone
state retags the body part `st__`/`____` (`:722-744`). Nest collision is
disabled 80 frames after kill (`enemyNestMgr.cpp:143-152`).

## 4. Cargo drag / contest

- Eligibility: `findNearestPellet` (`panModoki.cpp:1047-1088`) requires a
  pickable, alive, non-upgrade, uncaptured pellet within search angle/distance
  and ±10 y-units, passing `isTargetable` (`:1532-1564`) — no teki stuck,
  `pellet->panmodokiCarryable()`, treasure slot cap 15, and
  `pullable(PCS_Unk2, (min+max)*0.5)` — plus the variant `canTarget` threshold.
- Contest strength: `mCarryStrength = (pelletMin + pelletMax) * 0.5`
  (`panModoki.cpp:1314`). A 1-pellet (1/2) gives 1.5: beats one carrier,
  loses to two. A 10/20 treasure gives 15.
- Contest mechanics: `PelletCarry::pull/pullable`
  (`pelletCarry.cpp:30-60`). Same channel or idle always wins; cross-channel
  requires strictly greater strength, and a takeover stalls the pellet 0.5 s.
  `canBack()` (`panModoki.cpp:1029-1041`) polls `pullable` every frame: while
  the Breadbug wins it drags (Back), when Pikmin win it is dragged (Pulled).
- Capture: `endCarry` (`panModoki.cpp:1322-1357`) kills every Pikmin still
  stuck to the pellet, gives up the pull channel, then: treasure slot 0 is
  kept captured-alive into the nest matrix (visible in the mound), later
  treasures are killed and recorded, carcasses/items are killed outright.

## 5. Nest ownership and spawn-linking

`Obj::birth` (`panModoki.cpp:54-75`) spawns a PanHouse through
`generalEnemyMgr->getEnemyMgr(EnemyID_PanHouse)` at the Breadbug position,
sets `mNest`, assigns `setHouseType(getEnemyTypeID())` (both breadbug species
→ `NEST_Breadbug=1`; only Jigumo maps to 0, `enemyNest.cpp:60-67`) and applies
fp00 nest scale. Nest home/Tr matrix sits 10 units low (`enemyNest.cpp:41-42`).
On death `killNest` sets `mDeathTimer=1` (`panModoki.cpp:1520-1526`); the nest
fades and drops collision after 80 frames (`enemyNestMgr.cpp:143-152`).
Treasure slot 0 renders captured inside the mound via `mHouseTrMatrix`
(`panModoki.cpp:171-176`).

## 6. Defeat and cargo recovery

`onKill` (`panModoki.cpp:687-696`) runs `throwUpEatItem`
(`:1659-1697`): every recorded held treasure (up to 15) is re-initialized
alive at nest position +10y with the base throw velocity plus a 50-unit radial
ring offset (`TAU*i/n`, skipped when n=1), with the kira effect and loose-item
sound. No held treasure is deleted; none is duplicated. Then the pathfinder
handle is released and the nest killed. Carcass/item cargo never returns —
it was killed at `endCarry`.

## 7. Behavior differences

### Breadbug (38) vs Giant Breadbug (40)

| Property | PanModoki | OoPanModoki | Anchor |
|---|---|---|---|
| Health (general fp00) | 1100 | 2000 | retail `enemyparm.txt` block 1; `EnemyParmsBase.h:55` |
| Weight threshold (proper ip01) | 11 — targets strictly lighter (`weightLimit > pelMinWeight`) | 1 — targets at-or-above (`weightLimit <= pelMinWeight`) | `PanModoki.h:16-19`, `OoPanModoki.h:16`, `PanModokiBase.h:203` |
| Return/carry speed (fp03) | 35 | 45 | proper block 2 |
| Receiver/suck damage (fp04) | 1000 | 1000 | proper block 2 |
| Press damage (fp06) | 200 | 100 | proper block 2 |
| Walk anim speed (fp16) | 2.0 | 1.0 | proper block 2 |
| Nest scale (fp00) | 1.0 | 2.0 | proper block 2 |
| Press immunity | none | non-Purple Pikmin presses rejected (`panModoki.cpp:1738-1744`) | Giant pressCallBack |
| Sucked/pulled sounds | shared | OPAN_HIPPARARE / OPAN_DOWN_NEW extras | `panModokiState.cpp:283-287, 471-473` |
| Waypoint slack radius | 100 | 150 | `panModoki.cpp:926-929` |
| Effect/shadow sizes | carry diff 20, shadow 15, appear 1.0 | 40 / 30 / 1.6 | `panModoki.cpp:133-136, 1707-1714` |
| Boss flag | no | yes (`IS_ENEMY_BOSS`) | `enemyInfo.h:216` |
| Score/drop | neither entry has an enemyInfo bonus/death table entry (BDT_Empty, `enemyInfo.cpp:66-67`); value comes from the carcass as carryable cargo, not a fixed score | same | — |

### Nest helpers: 39 vs 83

39 is a name-level alias that exists so generator files can say "パンモドキ巣";
the only resolved behavior is the resource-name rewrite to 83
(`enemyInfo.cpp:168-173`). 83 is the real helper: it has the `Nest::Mgr`, the
Jigumo-house co-load (`enemyNestMgr.cpp:49-78`), `EFlag_HasNoInfo`, a static
one-joint model and no animation bank. Neither may appear in a randomizer
spawn pool; 83 instances come only from a Breadbug birth.

### vs Pikmin 1 Breadbug foundations

The P1 native Breadbug (`native/src/plugPikiNakata/taicollec.cpp`) is the
existing proxy base: carry power 2 (line 509), target eligibility excluding
ship parts/overweight pellets (846+), nest delivery via `getNestPosition`.
P2 changes that matter for any port: contest strength becomes per-cargo
`(min+max)/2` instead of a flat 2; eligibility splits by variant threshold;
cargo is eaten (treasure stored up to 15, recoverable on death) rather than
only delivered; the creature hides underground to digest and refills health
(`panModokiState.cpp:422-427`); and the Giant adds Purple-only press
interaction. The existing P1 proxy intentionally keeps P1 cargo rules until
these are translated.

## 8. Reproducible assets

`experimental/pikmin2_breadbug_lane.py` re-extracts all three species from the
local ISO (`enemy/data/{PanModoki,OoPanModoki,PanHouse}/{model,anim}.szs` plus
`enemy/parm/enemyParms.szs`), recording SHA-256 of every source file.

- Breadbug: 14 joints, 9 clips, rigid first-pose+event-frame MODs
  (38 poses; existing supported converter path).
- Giant Breadbug: 13 joints, 9 clips, **39 sampled weighted poses** now convert
  via `pikmin2_skinning.draw_matrices` (authored EVP1 inverse matrices) — the
  earlier `breadbug-assets-02` failure (`Unsupported display-list attribute`)
  was the direct texture-matrix index on shape 1, accepted only on the
  weighted path. Texture-matrix animation is approximated as static;
  `panModokiMgr.cpp:73-90` post-tex-mtx setup remains unimplemented.
- Nest: 1 joint, no animation bank, static `nest.mod`.

Reproduce:

```powershell
python -m experimental.pikmin2_breadbug_lane --iso <local US GPVE01 rev0 iso> --output <fresh dir>
```

Evidence: `output/p2-lifecycle-batch/breadbug-lane-01` and `-02` are two
independent runs; all 188 files match byte-for-byte except converter sidecar
JSONs that embed their own output path. `breadbug-lane.json` is identical.

## 9. Tests

`tests/test_pikmin2_breadbug_lane.py` (15 tests, all passing):
spawn classification and alias safety, nest house-type/death-fade linking,
contest pull/pullable channels with variant strengths, endCarry fates and the
15-slot cap, throw-up ring recovery geometry, and — when the lane extraction
output is present — real-asset verification of clip counts, retail profile
values and recorded pose hashes. Existing suites
(`test_pikmin2_breadbug_assets/cargo_bank/cargo_install/actor/visual` and
their native fixture wrappers) continue to pass unchanged.

## 10. Remaining open work

- Native arena placement/combat gates for the Giant (native hook track owns
  wiring); Giant texture-matrix animation fidelity.
- P2 FSM port (cargo steal/digest/recover) vs the current explicit P1 proxy.
- Nest-linked treasure persistence across day saves; no AP reward ownership.
- Live gameplay acceptance of contest drag and death recovery.
