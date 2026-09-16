# P0 source audit + import contract: KumaChappy35 (Spotty Bulbear, issue #613)

Lane shard-enemies-6-kumachappy35-p0, generation 2. P0 only: no native
build, no runtime, no ADMIT, no playability claim. Issue #613 stays OPEN;
this P0 does not close it. Parent/child group ownership preserved: the
Bulborb/Bulbear family (#120) and sibling Snow Bulborb 45 evidence are
consumed read-only, never relabelled. Shared generic providers
(actor-birth-projectiles, treasure-receipts, placement-catalog,
save-progression, runtime-fixtures) belong to their provider shards.

## Why this slice exists

Source 35 KumaChappy carries NO acceptance row in the current overlay:
every arena gate is effectively UNTESTED. The only related history is the
adult-Bulborb slice #120 and the CLOSED dwarf batch #200; no bounded child
issue for Spotty Bulbear exists except this lane issue #613.

## Decoded definition (read-only research checkout, hashes validated)

| Fact | Observed |
|---|---|
| Manager | `246-KumaChappyMgr`, `EnemyID_KumaChappy`, `mObj` array |
| States | 9 (`Dead 0`, `Rebirth 1`, `Lost 2`, `Attack 3`, `Flick 4`, `Turn 5`, `TurnPath 6`, `Walk 7`, `WalkPath 8`; plus `NULL -1`, `StateCount 9`) |
| Animations | 9 distinct (`Attack 0`, `Dead 1`, `Flick 2`, `Move 3`, `Carry 4`, `Lost 5`, `Turn 6`, `Eat 7`, `Rebirth 8`; plus `AnimCount 9`) |
| Proper parms | `fp01` PoisonDamage 300.0, `fp11` HealthGaugeTimer 30.0, `fp12` RespawnRate 10.0 |
| Health | `mHealth`/`mMaxHealth` members; carcass revive loop (`doBecomeCarcass`, manager rebirth via `generalEnemyMgr->birth`) |
| Followers | `ChappyRelation` dwarf-follower relation on the actor |
| Identity (enemyInfo) | id 35, `EFlag_DayEndMax4 | EFlag_CanAppearDayEnd | EFlag_CanBeSpawned | 2 | EFlag_UseOwnID`, model bank `Chappy`, child -1/0, drop `BDT_Strong` |

Notable source mechanics: the Lost state runs a life-gauge revive timer
(`fp11`) and respawns through the manager (`fp12`), so death, corpse and
re-entry semantics differ from ordinary enemies; the actor also keeps
dwarf Bulborb followers via `ChappyRelation`.

Source hashes (sha256) are pinned in the adapter and asserted by the tests
for all seven inspected files, so drift fails loudly instead of silently
re-baselining: header `ac6df273...`, KumaChappy.cpp `961ba9bf...`,
KumaChappyMgr.cpp `66f2283f...`, KumaChappyState.cpp `2b1fe1fb...`,
KumaChappyAnimator.cpp `76772e3a...`, enemyInfo.cpp `305f8260...`,
enemyInfo.h `0e68be79...`.

## Reused framing (no forked parser)

Retail enemyparm text goes through
`experimental.pikmin2_engine_parms.parse_parm_text` when supplied, and
asset/model-bank facts are read, never restated.

## Exact P1 blockers

1. P1 actor birth: no host manager registers `EnemyID_KumaChappy`.
   Candidate host vehicle TEKI_Swallob 32 (the P1 Spotty Bulbear,
   native/include/teki.h) is UNVERIFIED for this role; provider shard
   actor-birth-projectiles owns the seam (#169/#186 coordination).
2. Mesh/bank: retail model bank `Chappy` plus anim bank not
   converted/installed (asset pipeline #128 / #613).
3. Receiver: `damageCallBack` and mouth-slot receivers need a live bound
   actor (#613 P1 actor acceptance).
4. Corpse/carry route: `BDT_Strong` drop and corpse corridor unproven on
   P1 (#613 / reward shard).

## Verification

`py -3.12 -m pytest tests/test_pikmin2_kumachappy35_audit.py -q` -> 13
passed (hash pins, enum decode, parm defaults, manager/actor identity,
packet shape, blockers, reused framing; plus malformed and
missing-source negatives).

All six runtime gates UNTESTED; fixture adoption N/A (P0 tooling handoff).
Next bounded scope: P1 actor birth for KumaChappy35 once provider shard
actor-birth-projectiles publishes its seam (report to integrator #437).
