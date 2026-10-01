# Impact spawn-repair adoption rerun (#786)

Lane `p1-challenge-impact-spawn-repair-adoption-v2`, issue [#786](https://github.com/4laric/pikmin-randomizer/issues/786).
Fresh-issue restage of the cycle-41 adoption scope: adopt the proven
spawn-gate repair (#745, repaired native pin `8b9d8992`) into the impact
staged path with a leased rebuild, a headed rerun and a verdict for
downstream consumer `p1-challenge-impact-runtime-acceptance` (#565). Owns
only the three adoption files here; no native changes (runtime_check of the
repaired fixture, consumed read-only).

## Method

`experimental/pikmin2_impact_spawn_repair_adoption.py` verifies the headed
rerun log for the PARK -> SQUAD -> BOOT -> PASS grammar plus the centred
960x540 window and the captain-safety #632 contract. The original failing
consumer check 160cfb6f turns PASS when SQUAD/BOOT are observed past PARK
within 300 s with zero injections; anything else (including any
`P2_FIXTURE_CAPTAIN_DOWN`) fails closed with the exact next blocker.

## Guard

Captain safety #632 uses `scripts/p2_fixture_captain_guard.h` (sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`)
vendored in the repaired fixture; the guard runs first on every tick, the
captain is parked outside attack reach, and the negative test exits BLOCKED
(86) with no PASS. No blanket invincibility.

## Non-claims

#565 owns the acceptance verdict; this lane delivers rerun evidence only.
All six runtime gates stay UNTESTED unless genuinely observed. No ADMIT, no
ledger writes, no native changes.

## Reproduce

```
python -m pytest tests/test_pikmin2_impact_spawn_repair_adoption.py -q
python experimental/pikmin2_impact_spawn_repair_adoption.py --verify-log <headed-run.log>
```