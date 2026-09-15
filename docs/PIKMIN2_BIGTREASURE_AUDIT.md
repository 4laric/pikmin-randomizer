# Pikmin 2 BigTreasure (Titan Dweevil, enemy ID 73) source audit — issue #246

Implementation owner: Codex using shared account 4laric. Parent: #175;
roadmap tier 8: #197; integration contract: #186. Source-only: no native
hook, placement, converter or gameplay claim. Evidence read at the local
`native/pikmin2-research` checkout, revision
`632af93787b9c95b63f0c13be32b161375ce3a96` (US GPVE01 rev 0 target, remote
`projectPiki/pikmin2`). Paths below are relative to that checkout. Follows the
format of [PIKMIN2_MAMUTA_AUDIT.md](PIKMIN2_MAMUTA_AUDIT.md) and
[PIKMIN2_CANNON_GROINK_AUDIT.md](PIKMIN2_CANNON_GROINK_AUDIT.md). Waterwraith
(BlackMan) and Tyre are explicitly out of scope.

## Identity and registration

- `EnemyID_BigTreasure = 73` with comment `// Titan Dweevil` —
  `include/Game/enemyInfo.h:132`.
- Registry row — `src/plugProjectYamashitaU/enemyInfo.cpp:105`: name
  `"BigTreasure"`, parent `-1`, member count 1, flags
  `EFlag_CanBeSpawned | 2 | EFlag_UseOwnID`, all resource-name/member fields
  empty, child ID `-1`, child count 0, `BDT_FinalBoss`. It does **not** carry
  `EFlag_CanAppearDayEnd` or `EFlag_DayEndMax*` (flag meanings at
  `enemyInfo.h:29-40`).
- Manager construction — `src/plugProjectYamashitaU/generalEnemyMgr.cpp:456-458`:
  `new BigTreasure::Mgr(limit, viewNum)`. `Mgr::doAlloc` installs one
  `BigTreasure::Parms` (`src/plugProjectNishimuraU/BigTreasureMgr.cpp:40-43`).
- Generator token `オオオタカラムシ` —
  `src/plugProjectYamashitaU/genEnemy.cpp:575`.
- `IS_ENEMY_BOSS` includes BigTreasure (`enemyInfo.h:219`), which makes its
  `throwupItem` treasure carry-weight squad-adjusted on the last cave floor
  in story mode (`src/plugProjectYamashitaU/enemyBase.cpp:2605-2608`).
- All five carried pellets are preloaded by the manager constructor:
  `"elec"`, `"fire"`, `"gas"`, `"water"`, `"loozy"` via `pelletMgr->setUse`
  (`BigTreasureMgr.cpp:25-33`).

## Construction and spawn side effects

- `Obj::Obj` builds `ProperAnimator`, a fresh FSM, and four subsystems: IK
  (`IKSystemMgr` + parms + ground callback), shadow (`BigTreasureShadowMgr`),
  attack (`BigTreasureAttackMgr`) and effects
  (`src/plugProjectNishimuraU/BigTreasure.cpp:48-57`).
- `onInit` (`BigTreasure.cpp:71-109`): sets `EB_Untargetable`, hard
  constraint on, disables `EB_Cullable`, `EB_PlatformCollEnabled`,
  `EB_LeaveCarcass`; sets up IK/shadow/attack/collision/treasures/materials/
  effects; removes the plain creature shadow; starts the FSM in `Stay`. In
  Zukan mode it transits straight to `Land`; otherwise it runs
  `doAnimationCullingOff` while hidden and starts the shine particle at the
  home position.
- First-encounter boot-up demo: story mode + unseen
  `DEMO_Find_Titan_Dweevil` plays movie `g36_find_louie` with the boss as
  target (`BigTreasure.cpp:2160-2177`), driven from `StateStay::exec`
  (`src/plugProjectNishimuraU/BigTreasureState.cpp:163-168`).
- `doUpdate` = material color + FSM exec + IK update
  (`BigTreasure.cpp:126-131`); `doUpdateCommon` adds the attack manager and
  boss BGM upkeep (`BigTreasure.cpp:137-142`). `inWaterCallback` and
  `outWaterCallback` are empty overrides (`include/Game/Entities/BigTreasure.h:113-114`).

## FSM states and transitions

Twelve states (`BigTreasure.h:57-72`), registered in `FSM::init`
(`BigTreasureState.cpp:20-35`):

| ID | State | Role |
| --- | --- | --- |
| 0 | Dead | Death sequence |
| 1 | Stay | Hidden/dormant, bitter-immune, waits for target in private radius |
| 2 | Land | Emergence animation, per-leg ground effects and Pikmin shakes |
| 3 | Wait | Idle without weapons |
| 4 | ItemWait | Idle carrying at least one weapon |
| 5 | Flick | Shake-off animation |
| 6 | PreAttack | Weapon charge-up; selects weapon |
| 7 | Attack | Active weapon attack |
| 8 | PutItem | Post-attack settle |
| 9 | DropItem | Animation played when the last weapon was knocked off |
| 10 | Walk | Weaponless locomotion (IK) |
| 11 | ItemWalk | Locomotion carrying weapons |

Transition rules (all in `BigTreasureState.cpp`):

- **Stay** (`:132-176`): on target (Olimar or Pikmin within private radius),
  play the boot demo if available, then transit to **Land** after ~4 s.
- **Land** (`:190-289`): key events 2/4/6/8/9 fire per-leg ground effects and
  `flickStickPikmin`; KEYEVENT_10 restarts as `Appear2` when no weapons
  remain. On KEYEVENT_END: health ≤ 0 → **Dead**; flick trigger →
  **PreAttack** if any weapon remains else **Flick**; else **ItemWalk** with
  weapons, **Walk** without. Cleanup clears `EB_BitterImmune` and starts
  programmed IK (`:284-289`).
- **Wait** (`:295-348`): health ≤ 0 → **Dead**; flick trigger → **Flick**;
  timer > 5 s → **Walk**.
- **ItemWait** (`:354-408`): no weapons left → **DropItem**; flick trigger or
  `isAttackLimitTime()` → **PreAttack**; timer > 5 s → **ItemWalk**.
- **Flick** (`:414-466`): KEYEVENT_2 applies the shake; KEYEVENT_END →
  **Dead** if health ≤ 0 else **Walk**.
- **PreAttack** (`:472-545`): init calls `setTreasureAttack()` (weapon pick)
  and the charge BGM. Exec: no weapons at all → **DropItem**; the *chosen*
  weapon knocked off mid-charge → re-enter **PreAttack** (init re-runs and
  picks a new weapon); timer past the per-weapon pre-attack time → finish
  motion; KEYEVENT_3 selects the directional fire pre-attack; KEYEVENT_END →
  **Attack**.
- **Attack** (`:551-614`): same two weapon-loss guards as PreAttack (all
  gone → **DropItem**; chosen gone → **PreAttack**); KEYEVENT_2 calls
  `startAttack()`; timer past per-weapon attack time → finish motion;
  KEYEVENT_END → **PutItem**. Cleanup always calls `finishAttack()` (tears
  down all four controllers) and ends the attack BGM (`:608-614`).
- **PutItem** (`:620-673`): same two weapon-loss guards; KEYEVENT_END →
  **PreAttack** on flick trigger else **ItemWalk**.
- **DropItem** (`:679-723`): KEYEVENT_END → **Dead** / **Flick** / **Walk**.
- **Walk** (`:729-789`): health ≤ 0 → **Dead**; flick → **Flick**; timer >
  10 s → **Wait**; IK motion must finish before transiting.
- **ItemWalk** (`:795-874`): health ≤ 0 → **Dead**; if weapons ran out
  mid-walk it swaps to the drop-item animation; flick trigger or attack-limit
  time → **PreAttack** with weapons, **Flick** without; timer > 10 s →
  **ItemWait**/**Wait**; transits only when the IK motion reports finished.

## Weapon treasures as dependent actors

- The four weapons are ordinary `Pellet` objects birthed from `pelletMgr`
  with names `"elec"`, `"fire"`, `"gas"`, `"water"` (index order =
  `BIGATTACK_Elec/Fire/Gas/Water`, `BigTreasure.h:74-81`), plus `"loozy"`
  (Louie / King of Bugs) on joint `otakara_loozy` — `setupTreasure`
  (`BigTreasure.cpp:703-742`). Each pellet is attached with
  `startCapture(jointWorldMatrix)` on joints `otakara_elec/fire/gas/water`;
  initial weapon HP is 6000 each (`BigTreasure.cpp:723`). Weapon carry
  weights/configs live in the disc pellet configuration, not in source (open
  question Q1).
- Ownership: the boss owns the `Pellet*` in `mTreasures[4]`/`mLouie`
  (`BigTreasure.h:250-251`) and drives `updateCapture` every frame from
  `updateTreasure` (`BigTreasure.cpp:748-782`), including the hit-shake
  wobble and a fixed −22 Y offset for the gas weapon (`:770-772`). Nothing
  else writes these pointers.
- Knock-off: `addTreasureDamage` reduces weapon HP (0.1× while bittered;
  pinch smoke starts crossing 3000) (`BigTreasure.cpp:864-887`).
  `updateTreasure` → `dropTreasure()` scans for HP ≤ 0, spawns the parts-off
  effect, ends capture, pops the pellet upward at 100 and nulls the slot
  (`BigTreasure.cpp:788-818`). Pikmin stuck to the lost weapon's collision
  part are flicked off and the part is neutralized; when *all* weapons are
  gone the `tam1`/`tam2` body parts switch special ID so the body becomes
  damageable — `setupBigTreasureCollision` (`BigTreasure.cpp:670-697`).
- Cargo pickup after drop: `endCapture` returns the pellet to normal pellet
  simulation; pickup/carry is the generic pellet path (no BigTreasure-specific
  code). Delivering the `loozy` pellet sets the Louie-rescued story flag
  (`src/plugProjectKandoU/pelletState.cpp:246-250`; special naming also at
  `src/plugProjectKandoU/pelletMgr.cpp:876`).
- Weapon selection for the next attack is health-weighted random:
  weight = 12000 − weaponHP per live weapon, bands ordered
  elec→fire→gas→water — weaker weapons are picked more often
  (`BigTreasure.cpp:984-1035`).
- `isAttackLimitTime()` paces attacks: threshold `4 + 2 × liveWeapons`
  seconds, 3× timer rate while an unstuck outsider is nearby, and requires a
  live Navi/Pikmin within a 225-unit XZ box (`BigTreasure.cpp:356-403`).

## Per-weapon attack controllers

All four controllers live in `src/plugProjectNishimuraU/BigTreasureAttack.cpp`
under `BigTreasureAttackMgr` (pools: 8 fire, 200 gas, 16 water, 17 elec
nodes; 16 shared attack-shadow slots — constructor at `:1043-1097`). Each
has a "normal" (weapon HP > 3000) and a "damaged" parameter set via
`isNormalAttack` (`BigTreasure.cpp:1200-1203`).

- **Fire (Flare Cannon)** — node update `BigTreasureAttack.cpp:85-139`:
  emit ratio grows to 1 at 3/s; swept segment of length `scale × 200`,
  radius 25, Y gate `40 × scale`; applies `InteractFire` with general attack
  damage; Navi fallback 0.33 flick else zero-damage attack. New node every
  0.1 s from joint `otakara_fire_eff` while started (`:1203-1268`); flame
  scale 1.0 normal / 1.25 damaged (`BigTreasureMgr` parms `ff00/ff10`,
  `BigTreasure.h:366-367`). Fire has four directional pre-attack/attack/end
  animation triplets chosen by angle to nearest Navi
  (`BigTreasure.cpp:1116-1146`, anim IDs `BigTreasure.h:474-489`).
- **Gas (Comedy Bomb)** — node update `:189-244`: ratio grows at 0.27/s;
  `InteractGas` at radius 10 (15 past half extent), Y gate 30; Navi fallback
  0.67 flick. 3 arms slow (0.015 rad/frame) when normal; damaged picks
  4 arms fast (0.02) with reversal every 30 s or 2 s (`:1315-1377`,
  parms `fg00–fg40`). New arm set every 0.1 s; rotation frozen while
  bittered (`:1399-1467`).
- **Water (Monster Pump)** — node update `:283-337`: ballistic bubble,
  `velocity.y -= 20` per update, `InteractBubble` at radius 20 (30 on ground
  hit), Navi always flicks on resist. Shots every 0.5 s normal / 0.25 s
  damaged with angle/distance jitter (`:1761-1796`, parms `fw00–fw12`).
  Target: random non-Blue Pikmin, else nearest Navi in a 180° × 1280 cone,
  else a random ring point (`:2220-2246`). Ground impact fades the bubble
  effect, spawns the hit effect and recycles the node (`:2171-2197`).
- **Electricity (Shock Therapist)** — node update `:404-494`: first node is
  invisible and tracks joint `otakara_elec_eff`; visible nodes are bouncing
  spheres (map-traced, floor friction, bounce sound). After the scatter
  delay, `startNewElecList` chains successive nodes pairwise
  (`mConnectedNode`); each chain segment applies `InteractDenki` in a
  10 × 20 cross-section with 150-up knockback; Navi fallback 0.5 flick
  (`:2712-2782`). Four parameter sets: normal picks discharge set 1-1/1-2,
  damaged picks 2-1/2-2 (counts 10/12/8/14, parms `fe00–fe37`,
  `:2252-2321`). `finishElecAttack` recycles all nodes with break effects
  (`:2979-3003`).

Teardown asymmetries (relevant to fixtures): `finishAttack()`
(`:3009-3019`) clears all started flags, fades fire/gas, and recycles elec
nodes, but `finishWaterAttack` is empty (`:2203-2205`) — in-flight water
bubbles keep flying and hitting until ground impact. Separately,
`BigTreasureAttackMgr::update` force-finishes the whole attack when the boss
is bittered and the corresponding weapon is gone (`:1167-1175`).

## Phase transitions

There is no numeric "phase" state. Phase behavior is emergent from per-weapon
HP and weapon count:

- **Per-weapon escalation at 3000 HP:** pinch smoke starts
  (`BigTreasure.cpp:879-881`) and every weapon switches to its damaged
  parameter set (fire scale, gas arms/speed/reversal, water interval, elec
  discharge sets) the next time that weapon is used.
- **Weapon loss:** drop effect + BGM step-down by remaining count
  (`startBossItemDropBGM`, `BigTreasure.cpp:1629-1664`), FSM falls back
  through the DropItem/weapon-loss guards above.
- **All weapons gone:** body becomes damageable
  (`setupBigTreasureCollision`, `BigTreasure.cpp:688-696`), body material
  alpha fades to 0 with the shell-change effect and sound
  (`setAttackMaterialColor(false)` no-treasure branch,
  `BigTreasure.cpp:1392-1403`), eye colors switch palettes, and the BGM
  drops to the no-weapons track (`BigTreasure.cpp:1593-1611`).

## Vulnerability and damage rules

- `damageCallBack` (`BigTreasure.cpp:248-275`): only Pikmin sources count
  (`creature->isPiki()`), and only with a collision part. Hits on a weapon
  part go to that weapon's HP (and bump the flick timer); body hits apply to
  boss HP **only when no weapons remain**. During `Land` all damage is
  quartered. `hipdropCallBack` returns the *negation* of `damageCallBack`
  (`:281-284`) — preserve this oddity in any port (Q7).
- Stone/bitter state: damage coefficient 0.5 (`BigTreasure.h:115`); weapon
  damage is additionally reduced to 0.1× while bittered
  (`BigTreasure.cpp:869-871`); finishing stone state force-flicks stickers
  (`BigTreasure.cpp:299-303`). Boss is bitter-immune during Stay/Land
  (`BigTreasureState.cpp:138,287`).
- Flicking: weapon/body damage increments `mFlickTimer`; the standard
  `EnemyFunc::isStartFlick` gates Flick/PreAttack entries, and each flick
  uses the general shake chance/knockback/damage parms.

## Defeat and finale exits

- `StateDead` (`BigTreasureState.cpp:41-126`): death procedure on entry,
  blend to anim 27 (`Dead`), foot bomb effect; key events stage mouth/body/
  per-leg bubble effects, leg bombs with camera/rumble at KEYEVENT_10, and
  shrink the shadow after frame 280. **KEYEVENT_100** calls
  `EnemyBase::throwupItem()` (births the `mPelletDropCode` treasure at the
  `kosi` joint with zero velocity — `BigTreasure.cpp:327-341`,
  `enemyBase.cpp:2590-2630`; boss/final-floor squad weight adjust applies)
  and `releaseItemLoozy()` (Louie pops up at 150 — `BigTreasure.cpp:912-920`).
  **KEYEVENT_END** calls `kill(nullptr)`; `EB_LeaveCarcass` was disabled at
  init, so no carcass remains (`BigTreasure.cpp:80`).
- `onKill` additionally releases Louie and fades the shine effect before the
  shared `EnemyBase::onKill` (`BigTreasure.cpp:115-120`).
- Weapons still attached at death are **not** released anywhere in source
  (`mTreasures[]` is only cleared through the HP knock-off path). Vanilla
  body damage cannot reach zero while weapons remain, so this is only
  reachable through forced HP (fixtures) or non-Pikmin damage sources that
  bypass `damageCallBack` — teardown for this case must be defined by the
  lane (Q3).

## Weapon-removed-mid-attack edge cases

1. Chosen weapon knocked off during **PreAttack**/**Attack**/**PutItem** →
   the state re-enters **PreAttack** and picks a new weapon
   (`BigTreasureState.cpp:502-505,578-581,647-650`).
2. Last weapon knocked off in those states → **DropItem**, then Walk/Flick.
3. Leaving **Attack** for any reason runs `StateAttack::cleanup` →
   `finishAttack()`: elec nodes are recycled with break effects, fire/gas
   effects fade, in-flight water bubbles persist (above).
4. Bittered + active weapon gone → attack manager force-finishes mid-update
   (`BigTreasureAttack.cpp:1167-1175`); the drop-BGM request is suppressed
   unless this exact case applies (`BigTreasure.cpp:1657-1663`).
5. Elec chain setup assumes a next node exists; pools and counts are sized so
   it holds in source (17 nodes ≥ 1 + 16 max discharge), but a reduced-pool
   port must keep that invariant (`BigTreasureAttack.cpp:2712-2747`,
   `:1074-1078`).

## Animation, motion and model references

- 30 animation registrations (`BigTreasure.h:468-513`): appear ×2, waits,
  four fire direction triplets (PreAttack/Attack/AttackEnd × F/FR/FL/FB),
  water/gas/elec triplets, DropItem, Flick, Dead, moves. The blend animator
  drives two animator slots with frame-preserving blends
  (`BigTreasure.cpp:1470-1521`).
- Model: default `EnemyMgrBase` BMD load with loader flags `0x01240030`
  (`BigTreasure.h:294-297`); every shape gets tex-matrix load type `0x2000`
  (`BigTreasureMgr.cpp:67-75`); model uses a single shared display list
  (`BigTreasureMgr.cpp:81-86`).
- Material color (body alpha + two eye palettes) is fully procedural through
  `changeMaterial`/`updateMaterialColor` (`BigTreasure.cpp:180-202`,
  `:1413-1464`). The `btk`/`brk` path statics exist
  (`BigTreasureMgr.cpp:12-13`) but no load call references them (contrast
  `DamagumoMgr.cpp:76`) — treat disc btk/brk as unconfirmed requirement (Q2).
- Locomotion is IK-driven: 12 leg joints across four limbs
  (`BigTreasure.cpp:453-469`), parms from general + proper parm blocks
  (`:475-485`); the FSM gates transits on `isFinishIKMotion()`.
- Shadow system: full joint-shadow tree (head, 4×4 leg tubes/spheres,
  4 treasure spheres, hand/antenna tubes) bound to named joints
  (`src/plugProjectNishimuraU/BigTreasureShadow.cpp:12-123`), plus 16
  pooled projectile shadow nodes (`BigTreasureAttack.cpp:3025-3099`).
- Effects: TOoota*/TDama* banks created per leg/weapon/body
  (`BigTreasure.cpp:1739-1761`, attack effects at
  `BigTreasureAttack.cpp:1080-1096`). BGM: charge/attack per weapon
  (ShockTherapist/FlareCannon/ComedyBomb/MonsterPump), weapon-count tracks,
  no-weapons flick (`BigTreasure.cpp:1541-1680`); SFX are the
  `PSSE_EN_BIGTAKARA_*` family plus `PSSE_EN_BIGTAKARA_SHELL` on body
  exposure.

## Parameters

`BigTreasure::Parms::ProperParms` (`BigTreasure.h:305-453`): IK factors
`fp01–fp06`; per-weapon pre-attack waits `fp10–fp13, fp31` and attack
durations `fp20–fp23`; elec discharge sets `fe00–fe38`; fire scales
`ff00/ff10`; gas rotation `fg00–fg40`; water discharge `fw00–fw12`; pattern
check debug switches. General parms (health, move speed, turn, radii, attack
damage, shake chance/knockback/damage) come from the shared
`EnemyParmsBase`/`GeneralParms` block and the disc parm file.

## Host integration notes (patterns to reuse)

- Follow the Groink host pattern (#169,
  [PIKMIN2_GROINK_PROTOTYPE.md](PIKMIN2_GROINK_PROTOTYPE.md)): a standalone
  `pc_port/pc_p2_bigtreasure.h/.cpp` policy module plus `tools/` test,
  host-supplied terrain/sphere-trace adapter for elec/water ballistics,
  authoritative 30 Hz source-rate ticks (never wall-clock), explicit attack
  emission events, no shared hooks — root serializes shared
  hooks/converter/build/export per issue #246.
- Arena staging follows the shared P1 arena contract (#186) and the boss
  staged-phases gate from the issue: fixed placement first, mixed levels
  later; the boss/multi-actor lifetime contract requirement of
  [PIKMIN2_ENEMY_IMPORT_PIPELINE.md](PIKMIN2_ENEMY_IMPORT_PIPELINE.md)
  (helper/receiver lifetimes before gameplay integration) applies to the
  five captured pellets and the pooled attack nodes.
- Per the implementation plan, randomized P1 stand-ins do not count as
  implemented P2 enemies; per-element acceptance is required separately
  ([PIKMIN2_IMPLEMENTATION_PLAN.md](PIKMIN2_IMPLEMENTATION_PLAN.md)).

## Open questions and unknowns

1. **Pellet configs:** carry weights, names and OTAKARA metadata for
   `elec`/`fire`/`gas`/`water`/`loozy` are disc data (pellet configuration),
   not source. Extraction needed with the model/motion import (dependency
   #128).
2. **Material animations:** `oootakara_model.btk/.brk` path statics exist in
   `BigTreasureMgr.cpp:12-13` with no loader call; confirm whether disc
   btk/brk are needed beyond the procedural `changeMaterial` path.
3. **Death with weapons attached:** no source release path for
   `mTreasures[]` at kill; define fixture teardown (release vs leak) for
   forced-HP defeats.
4. **Persistence:** no BigTreasure `doSave`/serialization override found
   (same default `Creature::save` situation as the Groink audit); weapon HP,
   knocked-off weapon cargo state and boss state across cave-floor/day
   transitions are unresolved — verify natively, do not infer.
5. **throwupItem drop code:** the emitted finale treasure identity comes from
   `mPelletDropCode` (generator/enemy-parms data), not this source file;
   confirm which treasure US GPVE01 assigns (expected King of Bugs is the
   separate `loozy` pellet; the thrown-up item needs asset confirmation).
6. **Water teardown:** `finishWaterAttack` is intentionally empty; fixtures
   must cover in-flight bubbles surviving state exit and their hit window.
7. **hipdropCallBack inversion:** `BigTreasure.cpp:281-284` returns the
   negation of `damageCallBack`; confirm host port preserves this exact
   semantics (affects hip-drop damage reporting).
8. **Elec pool invariant:** chain setup dereferences `nextNode` while
   linking; a port with reduced node pools must keep `1 + maxDischarge ≤ 17`.
9. **Attack-limit box:** `isAttackLimitTime` uses a 225-unit XZ box test
   plus territory/home logic; exact parity needs the general parm values
   (private/sight/territory radii) from the disc parm file.
