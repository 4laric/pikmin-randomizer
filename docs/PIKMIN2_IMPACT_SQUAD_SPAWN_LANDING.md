# Impact squad-spawn landing (#733)

Lane `impact-squad-spawn-landing`, issue #733. Owner: Codex through shared
account `4laric`. This lane lands the done-but-unlanded #698 diagnosis via
handoff + integration packet. Owns only the landing validator, its tests and
this doc. The #698 diagnosis was taken read-only (no re-derivation, no
duplication, no family/shared/native edits, no runtime, no ADMIT).

## Pinned #698 evidence (re-verified hash-identical this turn)

- Root commit `b286da12` ("impact-squad-spawn-diagnosis: post-PARK stall
  classifier + fail-closed tests + diagnosis", base `36b86839`):
  `experimental/pikmin2_impact_squad_spawn_diagnosis.py` sha256
  `96d589a84c35e886024a09cdaf6ed1ce73072d7a55747ba5b6c1ff986f312177`,
  `tests/test_pikmin2_impact_squad_spawn_diagnosis.py` sha256
  `a797fd4acd93c6b50acafce2f1fc207007e110d1f4e9fda959ad8443dbfa2b00`
  (12 tests, re-run green read-only), `docs/PIKMIN2_IMPACT_SQUAD_SPAWN_DIAGNOSIS.md`
  sha256 `59afd3004a64b63848710d96d3a476f9c13f7256a3a38d149e633d2693444ae9`;
  outcome review-ready with checks evidence.
- Diagnosis verdict (read-only): the deterministic post-PARK stall is a
  fixture-observation freeze, not a proven engine spawn failure; the fix is
  per-gate diagnostic markers plus alivePikis counts in the #649 fixture
  idle(), owned by the #649 lane.
- Consumer runs re-verified in shape: 7 native.log files of 799 lines each
  with PARK plus 1 empty log, exactly as diagnosed.
- Guard reference: `scripts/p2_fixture_captain_guard.h` sha256
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`
  (no CAPTAIN_DOWN in any run; no runtime run exists here either).

## #649 fix location (validated read-only)

`tools/p2_challenge_guarded_boot_fixture.cpp` carries the exact gates the fix
must instrument: `alivePikis()` counter, `frames<20000` budget, navi gate,
captain guard, movie-skip gate, pause/UI gate, PARK at observed==1, squad at
60, boot at 120, PASS at 180. All eleven gate tokens present with mapped
lines; file sha256 recorded in the handoff.

## Arena sequencing (breaks the stall)

1. Land #698 now on diagnosis evidence (this packet; no runtime claim).
2. #649 owner adds the per-gate diagnostic markers plus alivePikis counts to
   the fixture idle() at the located gates.
3. #565 reruns its guarded chal0 boot; the markers separate
   squad-never-spawned from observation-frozen, and squad spawn is observed.

## Packet

The hashed integration-ready packet for the single-writer integrator and the
#649 owner names the exact commits/hashes above plus downstream consumer
`p1-challenge-impact-runtime-acceptance` (#565, blocked gen 2). No #698-file
duplication; owner review still applies to the fixture change itself.

## Gates

All six runtime gates UNTESTED (no boot executed here).
