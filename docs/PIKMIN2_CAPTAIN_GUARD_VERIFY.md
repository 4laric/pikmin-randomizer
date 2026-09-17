# Captain-guard adoption verifier (#731)

Additive, fail-closed, engine-free checker: given a fixture C++ source and a native
run log, it asserts the #632 contract without running anything.

## Contract checked

- Source includes `scripts/p2_fixture_captain_guard.h` (sha256 `d2f678c9...`), or a
  tested inline equivalent is labelled: same predicate (`orimaDead || deadState ||
  !isfinite(hp) || hp <= 1.0`) plus the require/exit-86 path.
- `p2_fixture_require_captain(...)` is actually called (guard runs before observation).
- Log grammar: `P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%f orima_dead=%d dead_state=%d
  outcome=BLOCKED`; `PASS <name>` lines collected. NaN/unparseable HP counts as down.
- Any run containing CAPTAIN_DOWN must exit non-zero with no PASS line; a live-reading
  marker is itself a violation.
- `fixture_adoption.captain_safety` carries a known policy (`unprotected` |
  `protected_observation`) plus evidence keys present in the hashed evidence map; a
  `protected_observation` policy never yields `attacks_receivers` PASS.

## Fail-closed

Missing inputs, non-int exit codes, unknown marker grammar and unparseable HP raise
`VerifyGapError` (CLI exit 4) before any verdict. The tool writes nothing but its report.

## Evidence

- `tests/test_pikmin2_captain_guard_verify.py`: source adoption (header/inline/
  unguarded/missing-call), log dynamics (clean/down/zero-exit/down-plus-PASS/NaN/
  grammar/exit-type), adoption maps (policies, missing keys, damage claim, full
  verdict), CLI round-trip.
- No engine, family, shared or gameplay edits. No ADMIT, builds or runtime runs.