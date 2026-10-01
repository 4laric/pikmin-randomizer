# UmiMushi 71/100/101 aquatic pin-discovery audit (#648)

Read-only verdict for stranded `shard-enemies-6-umimushi71-observer` (#374, BLOCKED gen 4).
Planning-only: no runtime, no family edits, all six gates UNTESTED, no ADMIT.

## Identities (enemyInfo, GPVE01 rev 0)

- 71 UmiMushi / Ranging Bloyster — spawnable, `UmiMushi::Mgr`.
- 100 UmiMushiBase / Bloyster base (crashes) — `EFlag_UseOwnID` without
  `EFlag_CanBeSpawned`; direct generation excluded.
- 101 UmiMushiBlind / Toady Bloyster — spawnable, shared FSM + Blind parms.

## Anchors (decomp rev `632af937...`, spot-checked this turn)

- Identity/birth: `generalEnemyMgr.cpp:450` (Base only), `genEnemy.cpp:495-573,591`,
  `enemyInfo.cpp:102-104`, `umiMushiMgr.cpp:86`, `umiMushi.cpp:94`.
- Attack/receiver: `umiMushiState.cpp:510` (tongue key 3, Navi key 5, flick key 6),
  `:606` (swallow at end), `umiMushi.cpp:467` (damageCallBack routing, no tail-ID rule),
  `:493,512,531` (Purple scaling), `:552` (seven mouth slots 30/25), `:843` (isChangeNavi).
- Death: `umiMushiState.cpp:634,649` (deathProcedure, kill at end; no loot/reset).
- Cleanup/re-entry: ABSENT in reviewed functions (no generator-rebirth, day-end or
  persistence anchor). Port has `pc_p2_umimushi_forget`/reset hooks; re-entry unobserved.

## Blocked-lane evidence consumed (read-only)

`death-run1/pass1`: 102 throws, hp 1500.0->1485.0, 12 swallows; captain dragged ~270u,
dead tick 1273, `P2_FIXTURE_CAPTAIN_DOWN` exit 86. Runtime evidence:
`natural_death=false, corpse_recorded=false, passed=false`.

## Verdict (consumable by #374)

1. Captain-alive death + corpse run — producer: the blocked lane itself (owns
   module+fixture+arena). Prescription: park captain out of tongue/attack reach,
   thrown-Pikmin latch, extended window. No new lane.
2. Cleanup/re-entry run — producer: same owner (tadpole stage-reset precedent).
3. Family receiver review (latch-vs-routing 71/101) — producer: NONE live; recommend a
   new bounded review lane modeled on #641 (Catfish26, done kind=tooling). No duplicate.
4. #167 wake NOT satisfied (checklist unchecked; #641 is a different family).

## Verification

`py -3.12 -m pytest tests/test_pikmin2_umimushi_aquatic_pin_audit.py -q` -> 9 passed.