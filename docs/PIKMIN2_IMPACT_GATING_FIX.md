# Impact fixture gating fix (lane impact-fixture-gating-fix-native, #739)

Bounded native producer implementing the exact #698 per-gate instrumentation
fix for the #649 fixture's post-PARK observer freeze. Downstream:
`p1-challenge-impact-runtime-acceptance` (#565) squad spawn observed, then gate
evidence. No other family/shared edits; no ADMIT.

## Traced gap (#698 diagnosis, read-only)

Headed chal0 runs stall deterministically post-PARK: the observed counter never
reaches squad count while the engine renders. Exactly one gate holds every tick
(fixture idle): managers null, navi null, movie active (skip ineffective),
pause on, or UI active — but the fixture emitted no marker naming which, so the
four candidates were indistinguishable. Raw assets, environment and captain
death were all ruled out.

## Fix (owned file, #649 done so free)

`native/tools/p2_challenge_guarded_boot_fixture.cpp` only:

- A `gateDiag(gate)` helper printing
  `P2_CHALLENGE_GATE_DIAG gate=<managers|navi|movie|pause|ui>
  observed=<n> alive=<c> frames=<f>` on every 300th stuck frame (capped),
  called from each early-return path that freezes `observed` (managers, navi,
  movie before its skip, pause/UI distinguished).
- At PARK time (`observed==1`), an additional
  `P2_CHALLENGE_PARK_ALIVE pikis=<n>` line records the live baseline, so a
  later freeze separates never-spawned from observation-frozen.

No behavior change besides the markers; the frame budget, guard, PARK, squad,
boot and PASS thresholds are untouched.

## Companion files (owned, new)

- `native/tools/p2_impact_gating_fix_probe.cpp`: standalone engine-free probe
  asserting the gate-decision truth table and that the fixture source carries
  the required markers. Exit 0 only on all.
- `scripts/build_p2_impact_gating_fix.py`: private leased build/run helper
  (splice + build + probe + headed run from a staged asset root).
- `experimental/pikmin2_impact_gating_fix.py` + `tests/...`: fail-closed
  verifier over the headed log (attributed stall vs squad spawn).

## Build / run (private, leased)

Build dir `output/impact-fixture-gating-fix-build` (exclusive, lane-private).
Lease via the canonical registry; live elastic cap; release after. Record
configure/build/test exits, executable SHA-256, run-log SHA-256 and `ninja -n`.
Runs use a staged asset root so the boot reaches idle.

## Captain safety #632

Guard vendored verbatim from `scripts/p2_fixture_captain_guard.h` (sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`),
checked first after idle; the fixture's self/negative paths are unchanged.
The headed run adopts it with no captain-down expected. All six gameplay gates
UNTESTED; no acceptance claimed beyond observed markers.
