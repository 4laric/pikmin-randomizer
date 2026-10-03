# Original cannon larvae (issue #1254)

Codex implements literal original enemy IDs 95 (`Rkabuto`, Decorated Cannon
Beetle) and 96 (`Fkabuto`, burrowed Armored Cannon Beetle Larva). Native
`TEKI_Beatle` supplies an allocated chassis; the original FSM, identity,
resources, damage reception, and projectile behavior own its gameplay.

## Source contract

Research `include/Game/enemyInfo.h` identifies 95/96. Research
`src/plugProjectYamashitaU/genEnemy.cpp` creates the base enemy generator for
both: version `????`, empty species tail, null species initializer. The
provider requires the literal source ID, original generator UID, common
fields, and matching reservation. It never substitutes an AP placement.

Research `Kabuto.cpp`, `KabutoState.cpp`, `FixKabuto.cpp`, `EnemyBase.cpp`,
and `EnemyFunc.cpp` supply the FSM, damage and firing rules. Retail parameters
give 95 health 850, 96 health 2000, fixed turning ratio .075 and cap 7.5
degrees. Fixed emergence increments health by one on state entry and clears
stored damage, matching `StateFixAppear::init` calling `lifeIncrement()` once.
Each accepted damage event adds
one flick count; the retail thresholds of three mean the fourth hit starts
flicking. Original attacks accept normal body damage instead of the P1
Beatle armour portion gate.
Pikmin flicks add the source EnemyFunc PI offset before the receiver computes
negative sine/cosine velocity. Source 95 checks death immediately after the
flick key at posed frame 31, as well as at animation END; source 96 follows
the same key-event death rule.

The authored `mouth` joint supplies shot X/Z; the source body position plus
25 supplies Y. Event observation uses posed frames 51 (`attack`) and 56
(`K_attack`). Source 95 fires homing Stone 74, prioritizing the active captain
and otherwise searching eligible nearby creatures; source 96 fires straight.
Flying stones survive shooter retirement without retaining recycled-pointer
collision immunity. Authored Stone death lasts 71 frames.

## Private assets and admission

The legal asset producer supplies `P2_ORIGINAL_CANNON_BANK_1` (14 literal
clips for each species), `P2_ATTACHMENTS_1` (full hierarchy local transforms
for actual BMD/BCA mouth samples), and `P2_ORIGINAL_STONE_BANK_1`. None of
those assets are checked in. Their exact grammar is tested against the private
bank02 files. Resident animation metadata must remain identical on reentry.

`cannon::Native(CorpseResources)` requires a shared source-specific corpse
resource and death-hook verifier. Null refuses admission. A P1 Beatle pellet
profile cannot satisfy that callback: actual original carry minimum/maximum,
seed yield, geometry and death creation must be wired by the shared corpse
owner. The producer verified the retail corpse profile for both: carry 7/15,
seed yield 8/8, money 4, radii 34/34, height 20, offset (29,0,0), and a model-view
corpse without an archive. Fitted source-mesh body collision and effects require ordinary gameplay
review; portable tests and compilation do not establish those mechanics.

## Direct human gameplay script

Use the current original starting-Pikmin overlay: exactly 20 Pikmin, a centered
960x540 native window, a freshly generated private arena and private save/logs.

1. Load literal 95 and 96 placements. Confirm distinct original identities,
   correct models, 95 roaming and 96 initially buried. Approach 96, observe
   emergence, then leave its search range and observe hiding.
2. Let 95 fire, move the active captain sideways and observe the rock curve.
   Switch captains and repeat. Let 96 fire and confirm a straight trajectory.
   Observe real damage/press hits and the authored Stone destruction sequence.
3. Attack both from multiple body angles. Confirm health loss, the fourth-hit
   flick trigger, Pikmin detachment/damage, and fixed attack/flick timing.
4. Kill both. Check actual original corpse appearance, carry threshold and
   onion seed yield against the producer's retail profile. Carry the corpses
   to completion; this gate remains open until typed corpse wiring exists.
5. Unload with a live rock, reload, and confirm no stale actor/socket token or
   reused-address immunity. Save, quit and resume; verify original placement
   identity, death count and respawn interval behavior.

Record the exact executable/commit, arena and assets, observations and failure
logs. Build success is a separate gate from this human gameplay acceptance.
