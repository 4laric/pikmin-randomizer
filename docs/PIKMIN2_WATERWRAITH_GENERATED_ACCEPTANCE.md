# Waterwraith99 generated acceptance: family consumer boundary (#572)

Consumer scope for the BlackMan99 generated identity gate. Implementation
owner: Codex through shared account 4laric; executing contributor Muse
Spark 1.3 (worker muse-l58). No ADMIT, no gate relabelling, no generated
markers fabricated anywhere in this slice.

## What this boundary does

experimental/pikmin2_waterwraith_generated_acceptance.py correlates the
generated birth triple for source 99 with its attached helper 98:

- P2_SEED_RESOLVE source_id=99 target (ENEMY_P2 seed bridge),
- P2_GENERATED_PLACEMENT source_id=99 target [generator] bound=1
  (reviewed l52 marker grammar),
- P2_WATERWRAITH_BIRTH phase=fall attached=1 id=99 helper=98
  [generator] (family register claim; the generator field does not exist
  yet -- parsed when present, see follow-ons).

PASS requires resolve/placement agreement on one target, the family
birth naming id 99 with helper 98 attached, generator tie when logged,
and no injected-birth taint. Tyre98 is attached evidence, never the
identity: no gate table is produced for 98.

native/tools/p2_muse_waterwraith_fixture.cpp gains an opt-in
--generated mode with the same triple logic (default invocation is
byte-identical to the l63 fixed-encounter contract). Both observers
agree on every sample (cross-tested).

## Live verification state (exact)

Placement99 support is ABSENT at this pin: pc_p2_generated_placement
has no case-99 arm (only 41/57/58/78) and no accepted slot UID for 99
exists, so no engine build can emit the placement marker and the
generated triple cannot complete. The observer therefore reports
BLOCKED naming the placement99 provider on any log with resolve but no
placement marker, and fixed-encounter (never generated) on the legacy
sidecar birth alone. Verified against the real historical l63 log
(encounter-run-2 stdout.log:892 BIRTH, no resolve/placement markers):
Python FAIL fixed-encounter; fixture default exit 0 (contract
preserved); fixture --generated exit 1 naming the missing resolve.

No generated slot UID is prescribed here (planner warning honored).

## Packaging consumption (#576)

#576 (registry done) published BlackMan99 + owned-Tyre98 hash-verified
staging on branch codex/autofill-576, NOT integrated at this pin
(5486ae84 still stages only 41/57/58/78). The family runner consumes
its receipt/sidecar contract (generators, actors/identity files and
hashes, helper owner linkage) once integrated; this boundary validates
log markers only and duplicates no packaging code.

## Concrete source ID

- Source ID: 99 BlackMan (Waterwraith); 98 Tyre is the helper roller
  (no independent gate table, not seeded).

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED | placement99 provider unpublished: no case-99 arm in pc_p2_generated_placement at native ce89a039, no accepted slot UID; l63 fixed-encounter birth (output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:892) is not a generated identity | natural fixed birth; generated triple open |
| 2. Autonomous movement and animation | PASS (natural, inherited) | output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:897 actor-owned route leg; stdout.log:959 captain chase walk; stdout.log:972 chase travel accumulates | natural |
| 3. Attacks and receivers | PASS (natural, inherited) | output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:1153 stuns=1 hits=55 crushes=18 damage=3300.0; lane-31 family evidence preserved | natural |
| 4. Death and corpse | PASS (natural, inherited) | output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:977 body zero; stdout.log:980 corpse registered; stdout.log:982 teardown | natural |
| 5. Actual transport and reward | PASS (natural, inherited) | output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:1147 receipt generator=0 deliveries=1; corpse:waterwraith:0 value=2 | natural |
| 6. Cleanup and re-entry | PASS (natural, inherited) | output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:1152 re-entry ready=1 attached=1 | natural |

Gates 2-6 are preserved exactly from the read-only l63 slice (family
actor/encounter modules untouched this lane); only gate 1 carries new
#572 evidence, and that evidence is the consumer boundary plus an
honest BLOCKED record, not a PASS.

## Tests run

- tests/test_pikmin2_waterwraith_generated_acceptance.py: 11 Python
  observer tests + 4 fixture tests (compile -Wall -Wextra -Werror, both
  modes, cross-observer agreement) pass; fixture tests skip honestly
  without g++.
- Adjacent waterwraith suites re-run for regressions (see checks.log).

## Follow-on proposals (exact, for integrator #437)

1. Placement99 provider (new bounded scope, shared owner #186 review
   required before publication): randomizer/p2_placement_catalog.py
   candidate-only BlackMan99 profile with one defensible real native
   slot/generator mapping; native/pc_port/pc_p2_generated_placement.h
   accepted-slot mirror + .cpp case-99 arm recording the triple and
   emitting the reviewed marker; root/native slot-sync test;
   negative unsupported/mismatched/stale-actor tests; helper98 never
   independently seeded; reset/forget clears stale bindings; new files
   tests/test_pikmin2_waterwraith_placement_provider.py,
   native/tools/p2_waterwraith_placement_provider_test.cpp,
   docs/PIKMIN2_WATERWRAITH_PLACEMENT_PROVIDER.md. No UID prescribed
   here; the provider must inspect production slot evidence.
2. Family marker follow-on (this lane owns the files): log the engine
   generator on the P2_WATERWRAITH_BIRTH line once the bind path lands,
   so the register tie is numeric rather than sidecar-staged.
3. Packaging integration: land codex/autofill-576 (#576 done) so the
   runner stages 99/98 sidecars; then a generated session correlating
   seed source99, bind marker, register claim and packaged sidecars.

## Reproduction

Run the observer suite, then the gate-table check:

    py -3.12 -m pytest -q tests/test_pikmin2_waterwraith_generated_acceptance.py
    py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_WATERWRAITH_GENERATED_ACCEPTANCE.md
