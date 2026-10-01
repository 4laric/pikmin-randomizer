# Jigumo63 throughput-run landing (#759, downstream #374 gate 4)

Coordinator prerequisite promotion: the #167 PASS run (natural DEAD +
carcass, ratio 71.43, 1 eat below the pass1 bound of 7, zero
captain-down/injections) was never handed off/integrated (owner gone).
This slice lands it read-only for the single-writer integrator.

Implementation owner: Codex through shared account 4laric.

## Method (no re-derivation, no duplication)

`experimental/pikmin2_jigumo_throughput_run_landing.py` re-verifies the
three run artifacts hash-identical against the pins recorded when the run
passed, then validates the recorded supervisor verdict. No family/shared/
native edits, no runtime, no ADMIT.

## Evidence pins (re-verified this turn)

- Run `.../shard-enemies-4-jigumo63-throughput-run/out/jigumo573/fd633e88`:
  native.log sha256 `88ee97da...67ec`, result.json `8c678156...8089`.
- Fixture `fixture-build/fixture.exe` sha256 `64c13089758f...bb48`;
  production nectar.exe `66ea163d...a0018` (leased build, ninja no-work).
- Native `859fe9bf...` (clean); root `975a9713...75797053` (5 commits);
  observer suite 14 green.
- Verdict: exit 0, dead + carcass, lost 7, ratio 71.43, bites 2, eats 1,
  flicks 0, zero captain-down, zero injections.

## Owned files (this slice only)

- experimental/pikmin2_jigumo_throughput_run_landing.py
- tests/test_pikmin2_jigumo_throughput_run_landing.py (4 tests)
- docs/PIKMIN2_JIGUMO_THROUGHPUT_RUN_LANDING.md (this file)

## Gates

All six runtime gates UNTESTED (tooling landing; the run evidence itself
is reported for #374 gate 4 with no gate claimed here). Captain safety
#632 was adopted by the run (vendored guard, parked captain); this slice
performs no runtime observation.
