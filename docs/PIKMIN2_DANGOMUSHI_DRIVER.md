# DangoMushi fixture-side driver (issue #667)

Implementation owner: Codex through shared account `4laric`. Lane
`dangomushi94-fixture-driver` (fixture-side tooling only). Implements the
5-step driver specified by the #664 contract against the validated observer
legs, with zero observer changes, closing consumer
`dangomushi94-death-cleanup-observer` (#376) gates 4/6 at runtime.

## Driver procedure (`plan` + `drive`)

For one generator id, `plan()` emits the ordered fixture action script and
`drive()` verifies each step against run-log text in order:

1. **bind** ? run `pc_p2_dangomushi_setup()`; require TEKI vehicle plus
   `P2_DANGOMUSHI_BIND generator=<id> source_id=94`.
2. **damage** ? real free-squad Attack orders during accepted windows only;
   proceed on `P2_DANGOMUSHI_DAMAGE_ACCEPTED`. `DAMAGE_REJECTED` outside the
   window is expected and never proceeds or fails. No `mHealth`/Transport
   writes, ever (plan forbids both tokens).
3. **death** ? await `P2_DANGOMUSHI_DEAD ... health=0` after the damage step;
   this is the natural-death leg (the family guard only fires at real
   zero health through the dead-clip path).
4. **corpse** ? locate the engine corpse pellet via `mPelletView`; require
   `P2_BATCH3_DRAW corpse=1 key=DangoMushi` after death.
5. **reset** ? `pc_p2_dangomushi_forget` + reset, generator re-init, `setup`;
   require a second same-generator `P2_DANGOMUSHI_BIND` (stale/fresh proof:
   a re-bind on any other id fails the step).

Fail-closed: any missing leg, id mismatch, wrong order, injected marker
(`P2_MUSE_DANGOMUSHI_INJECT`, `P2_DANGOMUSHI_DEATH_INJECT`,
`injected_health`, `not_natural_combat=1`, `mHealth=`) or captain-down
token fails the drive (captain-down exits BLOCKED, never PASS).

## Observer alignment (verified, not duplicated)

`check_observer()` loads the REAL validated observer
(`.../enemies-5/prepared/dangomushi94-observer/experimental/pikmin2_muse_dangomushi.py`,
13 green tests + standalone checker) read-only and runs its `parse()`:
`gate_ok` agrees on the driver's good/bad logs (proven in-test, skipped
only if the file is absent). The four contract legs
(bind ? death ? corpse ? re-bind, same generator) match the observer's
four legs token-for-token.

## Captain safety #632

Guard `scripts/p2_fixture_captain_guard.h`
(sha256 `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`)
adopted before any observed tick; verified byte-identical in-test. Captain
parked outside attack reach when captain hits are not the subject; no
blanket invincibility; protected observation labelled and cannot prove
captain damage.

## Validation

- `tests/test_pikmin2_dangomushi_driver.py`: 14 green (plan shape/write
  forbiddance, full-sequence drive, missing/wrong-order/rejection-only
  negatives, injected + health-write + captain-down rejection, cross-id
  re-bind rejection, real-observer agreement, guard-hash match).
- No runtime run here; downstream #376 gates 4/6 close on a real run of
  this driver. No family/shared edits, no ADMIT.
