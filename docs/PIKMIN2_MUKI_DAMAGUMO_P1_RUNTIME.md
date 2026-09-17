# ch_MUKI_damagumo P1 runtime observer - handoff (#740)

Lane `p2-challenge-ch-muki-damagumo-p1`, issue #740 (OPEN, 4laric-assigned).
Implementation owner: Codex through shared account `4laric`. Outcome: **BLOCKED**
on the stage-boot dependency; the observer scaffolding (module + reader + tests
+ guarded fixture) is implemented and committed, but no runtime run was
attempted because the stage-boot path cannot resolve `ch_MUKI_damagumo`. No
ADMIT, no ledger writes.

## Scope

P1 runtime acceptance for P2 Challenge 08 `ch_MUKI_damagumo` (1 floor, 150 s,
decoded starting roster, spicy 1), reusing the done+integrated P0 import base
read-only and following the accepted houdai P1 shape (#735, running).

## Stage-boot dependency (hard blocker)

The challenge stage-boot table (the #705 landing, which resolves only
`ch_NARI_01kusachi` and `ch_NARI_02tile`) does not name `ch_MUKI_damagumo`. A
run would hit `SelectionError: unknown P2 challenge stage`. Extending the table
is owned by the #705/#669 stage-boot owners, not this lane (no engine/family/
shared edits without existing-owner review). The fixture therefore fails closed
(`BLOCKED stage_boot_unresolved`, exit 1) instead of misbinding or injecting.

## Owned files (all new, committed)

- `experimental/pikmin2_muki_damagumo_p1_runtime.py`: arena-staging contract +
  dependency-free `validate()` run-log reader; rejects injected runs and
  unresolved stages.
- `tests/test_pikmin2_muki_damagumo_p1_runtime.py`: 8 tests (valid run,
  unresolved stage, injected, wrong stage, captain down, missing receipt,
  nonzero exit, dependency-free). All pass.
- `native/tools/p2_muki_damagumo_p1_fixture.cpp`: guarded `RoomApp` (UNBUILT;
  adopts #632, no health/transport writes, fail-closed on unresolved stage).
- This file.

## Six-gate status (all UNTESTED; no runtime claim)

| Gate | Status | Evidence | Method |
|---|---|---|---|
| 1. playable_boot | UNTESTED (blocked) | stage-boot table lacks `ch_MUKI_damagumo` | dependency |
| 2. combat_receipt | UNTESTED | n/a | - |
| 3. exit_cleanup | UNTESTED | n/a | - |
| 4. death_corpse | UNTESTED | n/a | - |
| 5. transport_reward | UNTESTED | n/a | - |
| 6. cleanup_reentry | UNTESTED | n/a | - |

Gates use the P1 challenge shape (boot/receipt/exit + death/corpse/transport);
none is claimed without a real run.

## Build / run provenance

No build or runtime run was performed: the stage cannot boot, so a leased build
would only reproduce the unresolved-stage exit. The fixture is committed
unbuilt and clearly marked. `fixture_adoption.captain_safety` is specified
(policy unprotected, guard adopted in source) but unexercised.

## Captain safety (#632)

The fixture includes and calls `p2_fixture_require_captain(orimaDead, NaviDead,
hp, tick)` before observation ticks, emitting `P2_FIXTURE_CAPTAIN_DOWN ...
outcome=BLOCKED` and exiting 86. No blanket invincibility is used.

## Residual / next

1. Stage-boot owners (#705/#669) extend the table to resolve `ch_MUKI_damagumo`
   (or the integrator directs an accepted alternative boot path).
2. Re-run this lane: leased build + guarded run to boot/combat/receipt/exit,
   then claim gates with the reader and checker.