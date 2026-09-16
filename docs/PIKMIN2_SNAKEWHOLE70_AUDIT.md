# P0 source audit + import contract: SnakeWhole70 (Pileated Snagret, issue #376)

Lane shard-enemies-1-snagret70-p0, generation 2. P0 only: no native build,
no runtime, no ADMIT, no playability claim. Issue #376 stays OPEN; this P0
does not close it. Parent/child group ownership preserved: SnakeCrow and
DangoMushi evidence is consumed read-only and never relabelled.

## Why this slice exists

Source 70 SnakeWhole had zero acceptance evidence: the advance report
carries no gates for it, and legacy lane 25 covered DangoMushi94, not
SnakeWhole. No active lane owned any snagret file (registry scan
2026-09-16).

## Decoded definition (read-only research checkout, hashes validated)

| Fact | Observed |
|---|---|
| Manager | `EnemyID_SnakeWhole`, `mObj` array, `setTexMtxLoadType(0x2000)` |
| States | 11 (`SNAKEWHOLE_NULL=-1`, Dead 0, Stay 1, Appear1 2, Appear2 3, Disappear 4, Wait 5, Walk 6, Home 7, Attack 8, Eat 9, Struggle 10, Count 11) |
| Animations | 14 distinct (`Dead 0`, `Appear1 1`, `Appear2 2`, `Dive 3`, `HitNear 4`, `Hit 5`, `HitFar 6`, `HitRight 7`, `HitLeft 8`, `Wait 9`, `Eat 10`, `Struggle 11`, `Jump 12`, `Carry 13`); `AttackOffset == HitNear == 4` |
| Proper parms | `fp01` FastAppearChance 0.8, `fp11` WaitTime 2.0, `fp12` UndergroundTime 1.0, `fp21` PoisonDamage 300.0 |
| Health | `mHealth` general parm; `lifeIncrement` adds +10 capped at general health |
| Body chain | `SnakeJointMgr` declared/used (segmented snagret body) |
| Identity (roster) | `BDT_Boss`, `day_end_max 1`, `child_count 0`, `spawnable`, `use_own_id` |

Source hashes (sha256) are pinned in the adapter and asserted by the tests
for all six inspected files, so drift fails loudly instead of silently
re-baselining: header `2216410a...`, SnakeWhole.cpp `982856ba...`,
SnakeWholeMgr.cpp `0d50fbd5...`, SnakeWholeState.cpp `06a0f014...`,
SnakeWholeAnimator.cpp `36c79466...`, SnakeJointMgr.cpp `6e3c6c57...`.

## Reused framing (no forked parser)

Retail enemyparm text goes through
`experimental.pikmin2_engine_parms.parse_parm_text` when supplied, and all
identity facts come from the canonical
`docs/PIKMIN2_ENEMY_ROSTER.json` row for source 70.

## Exact P1 blockers

1. P1 actor birth: no host manager registers `EnemyID_SnakeWhole` (the P1
   teki roster has no SnakeWhole). Provider shard
   `actor-birth-projectiles` owns the generic seam; #169/#186 coordination.
2. Mesh/bank: retail model plus `SnakeJointMgr` segment bank not
   converted/installed (asset pipeline #128 / #376).
3. Receiver: `damageCallBack` and mouth-slot Eat/Struggle receivers need a
   live bound actor (#376 P1 actor acceptance).
4. Corpse/carry route: `BDT_Boss` drop and corpse corridor unproven on P1
   (#376 / reward shard).

## Verification

`py -3.12 -m pytest tests/test_pikmin2_snakewhole70_audit.py -q` -> 13
passed (hash pins, enum/alias decode, parm defaults, manager identity,
roster identity, packet shape, blockers, reused framing; plus malformed
and missing-source negatives).

All six runtime gates UNTESTED; fixture adoption N/A (P0 tooling handoff).
Next bounded scope: P1 actor birth for SnakeWhole70 once provider shard
`actor-birth-projectiles` publishes its seam (report to integrator #437).
