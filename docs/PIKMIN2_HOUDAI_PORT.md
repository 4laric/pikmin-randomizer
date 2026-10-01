# Man-at-Legs (Houdai, P2 source id 66): source behaviour and the own-behaviour port (#1012, parent #173)

Paths are relative to `native/pikmin2-research` (the decomp) unless they name a
native file (`pc_port/...`, in the native fork) or a root file. Numbers marked
*disc* are read from `enemy/parm/enemyParms.szs` on the US GPVE01 revision 0
disc (`houdai/enemyparm.txt`, `enemycoll.txt`, `enemyanimmgr.txt`) and override
the header defaults. The older audit of the whole family is
`docs/PIKMIN2_LONG_LEGS_AUDIT.md`; this file records what the Man-at-Legs port
does today, what was wrong or missing before the #1012 work, and the evidence.

## Where P2 places it

| Cave | Floor | Entry | caveinfo type | Held item |
|---|---:|---|---:|---|
| `tutorial_2` | 9 | `Houdai_light_a` (unit pool `1_units_houdai_metal`) | 1 | Stellar Orb (`light_a`) |
| `last_2` | 13 | `Houdai_j_block_yellow` | 1 | yellow block |
| `last_4` | - | `Houdai` | 1 | none |
| `Dam_cave_metal` | - | `Houdai_ahiru` | 1 | none |
| `ch_MUKI_houdai` | 2 | `Houdai_key` | 1 | The Key |

Read from `user/Mukki/mapunits/caveinfo/*.txt` on the disc (TekiInfo rows: name and
weight, then the type on the next row). Every boss that already lives in a P1 boss
arena in the randomizer is listed the same way: Queen, KingChappy, BigTreasure and
DangoMushi are all type 1 in their caves, and Houdai never appears as type 0. It is
not the type 8 special-enemy slot that BigFoot uses in `last_2` and `vs_8_kakukaku`.
So Houdai is a boss-floor species, and the existing arena-boss pattern applies: the
root catalogue already lists it in `ARENA_BOSS_SOURCES` with the `houdai_arena`
descriptor (`randomizer/p2_boss_arenas.py`, #899, footprint 250).

## Source behaviour (what the port is held to)

- **Identity.** Boss; drop table `BDT_Boss`; no child allocation; health 2800,
  territory 800, home 75, private radius 70, sight 600, move speed 250, max turn 60 deg
  (*disc* `fp00/09/10/11/12/06/28`). `Obj::onInit` (`Houdai.cpp:64`) turns hard
  constraint on, disables `EB_Cullable`, `EB_PlatformCollEnabled` and
  `EB_LeaveCarcass`, and starts in Stay.
- **States** (`HoudaiState.cpp`): Stay 94 (waits, damage or a captain/Pikmin inside
  the private radius wakes it), Land 128-219 (the 230-frame `landing` clip with flick
  keys 2/4/5/6 at frames 54/100/130/150), Wait 247 (1.5-3 s, loops `wait` 0..39), Flick
  298 (keys 40/45/68), Walk 340-372 (3.5-7 s IK walk, no clip), Shot 389-515
  (`attack` clip, keys 33/34/35/37/38/39), Dead 32-66. Wait ends in Dead, Flick, Shot
  or Walk in that order; Flick always continues into Shot; Shot ends in Walk.
- **Laser sight and gun** (`HoudaiShotGun.cpp`): attack key 2 (frame
  33) stops the clip and starts the rotation; while it rotates `doUpdate` (:1471) runs
  `searchShotGunRotation` (:1534: head yaw and gun pitch step 0.05 rad per tick toward
  the target) and `setShotGunLockOnPosition` (:1799): from the gun joint it marches the
  gun X axis 50 units, then up to 60 steps of 10 units, clamps to the floor at the first
  step below `getMinY`, creates `efx::THdamaSight` there with the reversed axis as normal
  (or fades it when the ray never reaches the floor) and plays `PSSE_EN_HOUDAI_BEAM`.
  This red sight sweeping across the ground as the gun turns is the laser the owner
  remembers. Key 5 ends the rotation (`finishLockOnEffect`, return at 0.025 rad per tick).
- **Shots** (`HoudaiShotGun.cpp`): key 3 emits one shell per attack loop (frames 34-38)
  from 45 units ahead of the gun joint along its X axis, speed 600, each axis jittered by
  +-`mAttackHitAngle` (0.004 *disc*); bursts run `mMaxShootingOn` 2.5 s on / 1.0 s off
  (*disc* proper `fp10-13`), aiming and firing last at most `mSearchAngle` 7 s (*disc*
  `fp15`). The shell (`HoudaiShotGunNode::update`, :95-235) is a radius-10 sphere moved
  with `mapMgr->traceMove`; a floor or wall contact raises it to ground+10 when it is
  below ground+20, plays `THdamaHit1/2/2W` (`Hit3` in water) and ends it; otherwise it
  expires 1500 units (1000 in y) from the boss. Each tick a capsule of radius
  `mAttackRadius` (10) along the step damages every live creature: captains and Pikmin
  get `InteractBomb(mAttackDamage 10)` with a blast direction sideways from the shell
  line (+100 y for a Pikmin), other enemies 500. A pool of 10 shells.
- **Targeting** (`Houdai.cpp:313-380`): Walk goes to the nearest non-stuck Pikmin in the
  view cone and sight radius, otherwise to random points on the home ring, home when
  outside the territory; the gun aims at the nearest non-stuck Pikmin or captain within
  `mSearchDistance` (800 *disc*) over a full circle, or at a random point after 1 s with no
  target. (Hole of Heroes only: territory becomes `fp20` 130 and a 50 percent roll aims at
  the captain's party; cave id `l_02` never occurs in the P1 world.)
- **Legs** (`Houdai.cpp:541-700`, `IKSystemMgr`): four legs of three joints driven by the
  IK manager; Walk copies the IK centre into the body; there is no walk clip. The legs only
  start IK at the end of Land (`StateLand::cleanup`). Flick and Shot run with blend
  motion on. No press damage. `Houdai::setupCollision` asks for a tube tree on `rht1`, but
  `enemycoll.txt` has no such node, so that call does nothing.
- **Collision** (`enemycoll.txt` *disc*): root `none` r50 (`____`) and one child `tama`
  r30 (`st__`, offset 5 along the kosi X axis), both on the `kosi` joint. `tama` is the
  only stickable part (`CollPart::isStickable` matches `s***`).
- **Damage paths.** Only `damageCallBack` is overridden (`Houdai.cpp:223`): the US build
  accepts a Pikmin that is stuck to the boss through a part (`isPiki && isStickTo`), scales
  it by 0.25 in Land, and refuses everything else, so captain punches and loose Pikmin
  do nothing. Every other path uses the `EnemyBase` default (`enemyBase.cpp:2762-2930`):
  **bombs** (`bombCallBack`) add the full damage in every state (`addDamage` is gated only by
  `EB_Invulnerable`); Purple **hip-drop** (`hipdropCallBack`) adds `mPurplePikiStunDamage`
  (50 *disc* `fp36`); press, flying collision, drop, farm and earthquake do nothing
  (earthquake is ignored while hard constrained); bitter spray is refused while
  `EB_BitterImmune` (Stay and Land). Every accepted hit raises the flick counter; the
  shake-off tiers are 10/15/25/30 blows at 30/37/50 stuck Pikmin (*disc* `ip01-07`).
- **Death** (`HoudaiState.cpp:32-66`): the `dead` clip (140 frames, no keys) plays, the
  held item is thrown straight down from `kosi` at the clip end, the dead-bomb effect
  plays and the object is killed. There is no carcass. Below 35 percent health the legs
  smoke (`updatePinchLife`, `Houdai.cpp:1096`).

## Gaps found in the port before #1012

| # | Gap | Source |
|---|---|---|
| 1 | No laser sight at all; the gun was a fixed turret at the bind-pose height (112), nothing was drawn for the aim | `HoudaiShotGun.cpp:1799` |
| 2 | Only the bind mesh was drawn: no landing clip (the drop-in was a 300-unit fall of the bind mesh), no wait bob, no flick crouch, no gun deployment, dead held the standing body | clips `landing/wait/flick/attack/dead` |
| 3 | The standing body was drawn at the bind height (kosi 138) while the source clips stand at 114 (and crouch to 62 in Flick), so legs and collision sat in the wrong place | `wait.bca`, `flick.bca` |
| 4 | Stay was hidden and intangible, although the source draws the crouched landing frame 0 and keeps the collision tree live; nothing could latch onto it | `StateStay::init`, `mCollTree->update()` |
| 5 | Collision was the host vehicle's parts, not the retail tree (only `tama` stickable) | `enemycoll.txt` |
| 6 | Bombs were refused ("stuck Pikmin only"), but only `damageCallBack` has that rule; `bombCallBack` adds full damage | `enemyBase.cpp:2908` |
| 7 | Shell origin used the bind-pose gun height, shell contact only tested the floor height (walls were ignored), shell effects were one puff per tick | `HoudaiShotGun.cpp:95-235` |
| 8 | No life gauge height for 66 in the shared table | `enemyparm.txt` fp27 115 |
| 9 | The dead corpse was the standing boss | - |

Open and unchanged: no sound (no P1 equivalent of `PSSE_EN_HOUDAI_BEAM` or the steam
loop is mapped), no 35-percent smoke, the Hole-of-Heroes target pattern, the Purple
hip-drop path, and the source dead-bomb and appear effects are P1 stand-ins.

## What #1012 implemented

- **Sampled rig** (`experimental/pikmin2_houdai_rig.py`, native `pc_port/pc_p2_houdai_rig.*`): the five
  disc clips sampled into model-space joint matrices (239 poses: landing 52, wait 40, flick 49, attack 50,
  dead 48; every clip at least 24, the source key frames are samples), interpolated by slerp. Written to
  `longlegs_Houdai_rig_00.txt`; the cache keeps it in `output/p2-content-dense/Houdai/rig/`.
- **Draw**: the clip pose drives the body (Stay shows landing frame 0, Land plays the 230-frame rise),
  the gun turns toward its aim, the ported IK rewrites the twelve leg joints from the end of Land, a carried
  corpse shows the dead clip's last pose. The brain reads the gun pivot from the posed joint.
- **Laser sight**: the source ground march from the gun axis; the red sight is P1 red-tinted glow effects
  along the ray and at the lock point plus a red line in the draw pass (`P2_HOUDAI_SIGHT*`).
- **Shots**: Groink map trace and shell effects (trail, glow, floor marker, hit) on the source shell rules.
- **Collision**: the retail tree swapped in; only `tama` latches and only a Pikmin latched there damages it.
  Bombs damage it; the life gauge height is 115.
- **Admission**: pool row, roster evidence, `houdai_arena` placement profile (footprint 250 carried over
  from #899, measured leg spread 114).

## Evidence

See the roster entry for 66 in `docs/PIKMIN2_ENEMY_ROSTER_EVIDENCE.json` (run a4: kill, carry, Onion receipt
`onion:p2:66:3`; run a1: sight, shells, latch damage, life gauge). A frame dump of run a6 showed the boss
standing with thin legs and its health bar. Unit gates: `p2_houdai_rig_test` (real rig via
`P2_HOUDAI_RIG_FILE`), `p2_houdai_fsm_test`, `tests/test_pikmin2_houdai_rig.py`.

## Owner playtest 2026-09-30 and the fix

The first package (exe 342bacde) was played by hand and reported as "never stood up, stuck in the ground sliding
around, no collision". The brain was right (it woke, walked and shot, from the risen gun height) but the drawn mesh
never left landing frame 0: the private mesh's vertex storage is rewritten on the CPU every frame and the resident-mesh
cache (`pc_gfx_mark_dynamic_vertex_range`, as `p2pose::write` does) was not told, so the first pose drawn stayed on
screen. Collision was posed correctly (`P2_HOUDAI_POSE_DIAG` logs `tama_y` about 123 above the ground in Wait) but
looked absent because the body was drawn sunk. Fixed in `houdaiIkPose`; a source-level test
(`tests/test_pikmin2_houdai_rig.py::test_native_private_mesh_is_marked_dynamic`) pins it.

Wake condition (`StateStay::exec`, `HoudaiState.cpp:94-125`; `isThereOlimar` `enemyAction.cpp:1525`, `isTherePikmin`
`:1250`): the captain or any searchable Pikmin within `mPrivateRadius` (70 *disc*, fp11) by 3D distance, or any damage
(`EB_TakingDamage`). The port now uses the 3D test for the captain. The tick runs from `gameCoreSection`, outside
`Creature::update`, so the P1 AI-grid culling (`creature.cpp:678`) does not stop it. A run with no damage multiplier
(b2) rises, walks, runs Wait->Shot->Walk with the laser sight and hits Pikmin.
