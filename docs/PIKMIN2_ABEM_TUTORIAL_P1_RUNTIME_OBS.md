# ch_ABEM_tutorial P1 runtime observation (#534)

Bounded runtime-observation slice for P2 Challenge 01, reusing the done P1
import base read-only. No engine/family/shared edits, no ADMIT, no ledger
writes; #534 stays OPEN.

## Owned files (NEW)

- `experimental/pikmin2_abem_tutorial_p1_runtime_obs.py` - fresh arena staging
  (live squad + ordinary control) plus a dependency-free run-log reader and
  honest six-gate classifier.
- `tests/test_pikmin2_abem_tutorial_p1_runtime_obs.py` - focused tests.
- `docs/PIKMIN2_ABEM_TUTORIAL_P1_RUNTIME_OBS.md` - this doc.

## What it does

The adapter consumes the DONE P1 import manifest read-only and stages a fresh
observation arena from the legal assets with the canonical starting-Pikmin
overlay (20-squad baseline, hash-pinned). It records every staged generator
id/position plus the untouched plants.gen set as the ordinary control, and
carries the floor-1 challenge roster (Clover, Tukushi, Ooinu_s, KareOoinu_s;
treasures key, gold_medal, silver_medal, wadou_kaichin; pool
1_units_cent3_tsuchi.txt) as observation targets, never placed actors.

The reader parses natural gameplay markers dependency-free: centred 960x540
window, live squad counts, spawn reports, cave/generate markers, boot PASS
and captain-down. The classifier passes identity_spawn only on a live squad
with no captain-down; every other gate stays UNTESTED unless genuinely
observed.

## Boundaries and honest status

- The engine P2 stage table available to this lane resolves only
  ch_NARI_01kusachi; ch_ABEM_tutorial has no engine row, so no stage-boot
  path can resolve it here. That is recorded as a BLOCKED prerequisite
  (provider row plus #186 wiring), never simulated.
- Runtime runs reuse existing fixtures/runners read-only (guarded cave boot
  fixture #642 pattern, canonical #671 runner); this lane owns no native
  files and edits none.
- Captain guard (#632) is adopted with hashes and a negative test; the
  captain is parked outside attack reach; no blanket invincibility.
- All six gates start UNTESTED; only genuinely observed facts flip a gate.

## Verification

`py -3.12 -m unittest tests.test_pikmin2_abem_tutorial_p1_runtime_obs` -> 8 passed.
