# Pikmin 2 Mamuta (Miulin, enemy ID 54) source audit — issue #214

Implementation owner: Codex using shared account 4laric. Parent: #168
(scavengers). Deepens the family-level notes in
[PIKMIN2_SCAVENGER_ENEMY_AUDIT.md](PIKMIN2_SCAVENGER_ENEMY_AUDIT.md) to a
single-species contract. Source-only: no native hook, placement, or gameplay
claim. Evidence read at the local `native/pikmin2-research` checkout (US
GPVE01 rev 0 target); disc assets extracted from a user-owned US GPVE01
revision 0 disc. Behavior comparison in
[PIKMIN2_MAMUTA_BEHAVIOR.md](PIKMIN2_MAMUTA_BEHAVIOR.md).

## Identity and registration

- `EnemyID_Miulin = 54` with comment `// Mamuta` — `include/Game/enemyInfo.h:113`.
- Registry row — `src/plugProjectYamashitaU/enemyInfo.cpp:88`: name `"Miulin"`,
  parent `-1`, member count 1, flags `EFlag_CanBeSpawned | 2 | EFlag_UseOwnID`,
  all resource-name/member fields empty, child ID `-1`, child count 0,
  `BDT_Strong`. It does **not** carry `EFlag_CanAppearDayEnd` (0x10),
  `EFlag_DayEndMax*`, or `EFlag_HasNoInfo` (flag meanings at
  `enemyInfo.h:29-40`).
- Manager construction — `generalEnemyMgr.cpp:394-395`:
  `new Miulin::Mgr(limit, viewNum)`. `Mgr::doAlloc` installs one
  `Miulin::Parms` (`miulinMgr.cpp:22-25`); birth delegates to
  `EnemyMgrBase::birth` (`miulinMgr.cpp:31-34`).
- Generator token `ミウリン` — `genEnemy.cpp:554`.
- Sound: takeoff/drop voice group with Armor/Catfish/BombSarai, volume 0.9,
  pitch 1.3 — `src/utilityU/PSMainSide_Se.cpp:956-961`.

## Construction and spawn side effects

- `Obj::Obj` builds `ProperAnimator` and a fresh FSM (`miulin.cpp:61-66`).
- `onInit` binds joint `jnt_koshi` (asserted), clears search state and starts
  the FSM in `MIULIN_Wait` (`miulin.cpp:45-55`).
- `birth` spawns a group of **five ShijimiChou (Unmarked Spectralids)** 80
  units above the Mamuta when that manager exists
  (`miulin.cpp:27-43`, via `ShijimiChou::Mgr::createGroupByEnemy`,
  `include/Game/Entities/ShijimiChou.h:188`). This is an owner-dependent side
  birth; absence/capacity fallback is not guarded in source beyond the
  manager-null check.

## FSM and AI/state transitions

States (`Miulin.h:20-31`): Wait 0, Walk 1, AttackStart 2, Attacking 3,
AttackEnd 4, Turn 5, Flick 6, Dead 7. Registered in `FSM::init`
(`miulinState.cpp:15-26`).

- **Wait** (`miulinState.cpp:42-77`): frozen `wait` anim, zero velocity,
  hard constraint on, lifegauge hidden. `exec` first requires
  `isStartWalk()` (nearest Pikmin-or-Navi inside view angle/search distance,
  `miulin.cpp:672-688`; flicker timer widens the cone to 180° once). With a
  target: health ≤ 0 → Dead; `isAttackStart()` → AttackStart; large heading
  error (`nextTargetTurnCheck`) → Turn; else Walk. Leaving Wait releases the
  hard constraint and shows the lifegauge.
- **Walk** (`miulinState.cpp:93-194`): `move` anim; dashes at 2× speed/anim
  scale when within the dashable angle (`walkFunc`, `miulin.cpp:705-736`).
  Stuck watchdog: if it has moved < 30 units over 120 frames it forgets the
  target and returns home (`miulin.cpp:724-735`). Out of territory or return
  counter over `ip01` → `setReturnState()` then Turn (`miulinState.cpp:128-133`);
  goal reached while searching → Wait; goal reached with a target needing a
  large turn → Turn. Health ≤ 0 → Dead, `EnemyFunc::isStartFlick` → Flick,
  `isAttackStart()` → AttackStart.
- **Turn** (`miulinState.cpp:403-459`): rotates toward goal/target until within
  `fp06` (10°), then Walk; Dead/Flick/AttackStart pre-empt on the same
  conditions as Walk.
- **AttackStart** (`miulinState.cpp:210-226`): `attack0` (15 frames), exits to
  Attacking at `KEYEVENT_END`.
- **Attacking** (`miulinState.cpp:242-348`): `attack1` (38 frames). At
  `KEYEVENT_2` (frame 0 in retail registry) the plant attack fires — see below.
  `KEYEVENT_3` (frame 4) is a second effect/rumble only. At `KEYEVENT_END`:
  AttackEnd, or immediately re-attack if `isAttackStart()` still holds.
- **AttackEnd** (`miulinState.cpp:364-387`): `attack4` (19 frames), next
  defaults to Turn; Dead on health ≤ 0, Flick on flick trigger.
- **Flick** (`miulinState.cpp:475-515`): `flick` (45 frames); at
  `KEYEVENT_3` (frame 25 retail) flicks nearby/stuck Pikmin and Navis using
  shake parameters; at END → Dead / AttackStart / Turn.
- **Dead** (`miulinState.cpp:531-556`): `dead` (71 frames), runs
  `deathProcedure()` on init; `KEYEVENT_2` (frame 27 retail) plays the landing
  bounce effect (`landEffect`, `miulin.cpp:1055-1058`); `KEYEVENT_END` calls
  `kill(nullptr)`.

## Animation events (retail registry)

`miulin/enemyanimmgr.txt` (in `enemy/parm/enemyParms.szs`) registers nine clips
matching `Miulin.h:254-265` AnimIDs. Retail event frames (extracted profile):

| Clip | AnimID | Frames | Events (frame:type) | Source role |
|---|---|---|---|---|
| attack0 | 0 | 15 | none | windup |
| attack1 | 1 | 38 | 0:2, 4:3 | plant hit at type 2; type 3 effect only |
| attack4 | 2 | 19 | none | recover |
| dead | 3 | 71 | 27:2 | bounce/land at 27; kill at end |
| flick | 4 | 45 | 15:2, 25:3 | shake-off at type 3 |
| move | 5 | 77 | 13:0, 42:1 | footstep/loop marks (visual) |
| type5 | 6 | 40 | 10:0, 29:1 | carcass carry pose (`startCarcassMotion`, `miulin.cpp:141-144`) |
| wait | 7 | 90 | 13:0, 72:1 | idle loop marks |
| waitact | 8 | 30 | 0:0, 29:1 | turn/fidget |

Type 0/1 pairs in move/type5/wait/waitact are loop/footstep visual events, not
gameplay events. Model: 16 joints including `jnt_koshi`, `jnt_footR/L`,
`jnt_handL/R` (extracted `mamuta.json`); 2 embedded textures.

## Collision and physical profile

- Shadow: centered on `jnt_koshi` world position, y = position + 2, bounding
  sphere radius 20, size 25 (`miulin.cpp:103-110`); down-smoke scale 0.85
  (`Miulin.h:154`).
- Walk smoke on `jnt_footR`/`jnt_footL`, scale 5.0 (`miulin.cpp:150-155`).
- `wallCallback` sets a 120-frame no-search counter, drops the target, and
  returns home (`miulin.cpp:130-135`); `doSimulation` decays that counter
  (`miulin.cpp:116-124`).
- `applyImpulse` and `setInitialSetting` are empty overrides
  (`Miulin.h:142-143`).
- Collision volume text preserved at `Miulin/enemycoll.txt` in the extraction;
  not reinterpreted.

## Plant attack (Pikmin planted → flower)

At `attack1` `KEYEVENT_2`, `StateAttacking::exec` (`miulinState.cpp:264-330`)
builds a hit point `mMinAttackRange` (fp08, 25) ahead of the facing direction
and tests a vertical band of ±20 and horizontal radius `mAttackRadius`
(fp22, retail 40):

- Every live Pikmin not stuck to the Mamuta inside the band receives
  `InteractBury(enemy, 0.0f)` (`:292-294`).
- Every live captain inside receives `InteractBury(enemy, 5.0f)` (`:312-314`).
- The same event then flicks nearby/stuck Pikmin and captains with shake
  parameters (retail: chance 1.0, knockback 40, damage 1, range 40) and clears
  `mFlickTimer` (`:317-326`).

Receiver — `InteractBury::actPiki` (`interactPiki.cpp:377-442`):

1. Reject if the Pikmin's current state is invincible.
2. Reject if `GameStat::mePikis >= 99` (US; PAL subtracts `zikatuPikis`).
3. Require a non-bald map triangle, `piki->might_bury()`, and a live
   `ItemPikihead::mgr`.
4. On success: force-birth an `ItemPikihead` sprout of the **same kind at
   Flower stage**, snap it to the floor (`mapMgr->getMinY`), spawn
   `efx::createSimplePkAp`, and kill the original Pikmin with
   `CKILL_DontCountAsDeath`.
5. Any terrain/manager/birth failure transits the Pikmin to Walk instead.

So planting is conditional conversion with a population cap and
terrain/manager dependencies — not damage and not a guaranteed sprout.
`InteractBury::actNavi` (`interactNavi.cpp:218-226`) only starts 5.0 damage;
it never plants.

## Species interactions

- Targets: nearest Navi or searchable, non-stuck Pikmin
  (`isFindTarget`, `miulin.cpp:582-630`; `isStartWalk`, `:672-688`). Pikmin
  stuck to itself are excluded from both search and the bury band.
- Alert ("caution") state: presence of Olimar/Pikmin inside the private
  radius (fp11, 50) or health below `life_before_alert` (fp30, retail 0)
  resets the alert timer; alert persists for `alert_duration` (fp29, retail
  2.0 s) and widens the search cone to 180° (`miulin.cpp:1027-1049`).
- Emotion cues: excitement while dashing/attacking, caution otherwise
  (`miulin.cpp:712-718`; state init functions).
- ShijimiChou companion group of five on birth (above).
- `doUpdate` clears a dead target creature every frame (`miulin.cpp:72-80`).

## Floor/save lifecycle notes

- Lacking `EFlag_CanAppearDayEnd`, Miulin managers are untouched by
  `GeneralEnemyMgr::prepareDayendEnemies` day-end clearing, which kills only
  flagged families with `CKILL_NotKilledByPlayer` so the player is not
  credited (`generalEnemyMgr.cpp:923-941`). Ordinary death goes through
  `StateDead` → `kill(nullptr)`; carcass uses the `type5` carry motion.
- Cave floor/save serialization and generator restore for Miulin were **not**
  traced in this audit; treat day/floor respawn and carcass-return behavior as
  unverified until a native fixture exists.

## Piklopedia

`Zukan_Miulin` maps to `EnemyID_Miulin` (`zukan2D.cpp:179`) and is in the
"hides just pikmin lost" blind group (`zukan2D.cpp:2173-2183`): the
Pikmin-lost counter is blinded, but value/defeated counters are still shown.
Miulin lacks `EFlag_HasNoInfo`, so kills/discoveries are tracked.

## What this audit does not establish

No runtime contact, footprint clearance, carcass return route, day/floor
respawn, save reload, or Piklopedia-entry behavior has been observed natively.
These remain acceptance work for a later integration slice.
