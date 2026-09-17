# Waterwraith99 generated acceptance: family consumer boundary (#572)

Consumer scope for the BlackMan99 generated identity gate. Implementation
owner: Codex through shared account 4laric; executing contributor Muse
Spark 1.3 (worker muse-l58). No ADMIT, no gate relabelling, no generated
markers fabricated anywhere in this slice.

## What this boundary does

experimental/pikmin2_waterwraith_generated_acceptance.py correlates the
generated birth triple for source 99 with its attached helper 98:

- P2_SEED_RESOLVE source_id=99 target (ENEMY_P2 seed bridge),
- P2_GENERATED_PLACEMENT source_id=99 target generator bound=1
  (narrow native bind path; placement99 provider #575, accepted slot
  568677317),
- P2_WATERWRAITH_BIRTH phase=fall attached=1 id=99 helper=98 generator
  (family register claim on the spawned actor; the generator field does
  not exist yet -- parsed when present, see follow-ons).

PASS requires resolve/placement agreement on the accepted slot
568677317, the family birth naming id 99 with helper 98 attached, a
present birth generator field equal to the placement generator
(numeric register tie -- staged-only ties never pass), and no
injected-birth taint. Tyre98 is attached evidence, never the
identity: no gate table is produced for 98.

native/tools/p2_muse_waterwraith_fixture.cpp gains an opt-in
--generated mode with the same triple logic (default invocation is
byte-identical to the l63 fixed-encounter contract). Both observers
plus the #575 waterwraith_generated_triple API agree on every sample
and on the live run below (cross-tested).

## Gen3 validation run (placement99 arm live; family claim missing)

Consumed reviewed prerequisites: root 7a21ce6a + native e2aa476e
(#575). Rebuilt privately via the leased runner (build log
output/workflow/autofill/enemy-waterwraith99-generated/build-1789604912903013700.log:
configure + pikmin_pc link + ninja no-work dry run, exit 0).

Fresh arena output/workflow/autofill/enemy-waterwraith99-generated/ww-genesis/992d26a345af482089eba8f7e4ab6564
(current overlay, staged Frog0 record id 568677317, fixed family
sidecar, placement slot join, minimal ENEMY_P2 seed 568677317 to 99,
cargo Pod, #576 candidate sidecars staged read-only into the run dir).
Launch: nectar.exe --experimental-pikmin2-room --randomizer-seed,
PIKMIN_P2_ROOM_WINDOW 960x540, 150 s harness deadline. Log run.log
sha256 0a810a3f2ea8bf081f55501dd63849cefaa89c3d9c162d3ddc02f5ea480581ee.

- :14 960x540 windowed and centered; :249 live 20-red squad.
- :592 P2_SEED_RESOLVE source_id=99 target=568677317.
- :593 P2_GENERATED_PLACEMENT source_id=99 target=568677317
  generator=568677317 bound=1 (placement99 arm fires live).
- :594 P2_PLACEMENT_SLOT terrain=ground route=1 for the slot.
- :766 P2_WATERWRAITH_BIRTH phase=fall attached=1 id=99 helper=98
  with NO generator field; register profile :742 binds the fixed
  placement (0,30,0), not the generated actor.
- Verdicts on the real log: Python FAIL register-tie-not-numeric;
  C++ fixture exit 1 (resolve=1 placement=1, generated_ok=0, same
  reason); #575 triple API correlated=true on the accepted slot.
  Captain-safety scan: clean (no down/extinction markers).
- Conclusion: the placement contract is live end to end; the
  remaining gap is exactly the family generated-actor claim path
  (register constructs its own fixed actor and never binds the
  seeded Teki) plus the BIRTH generator field. No staged tie was
  passed off as generated.

Captain safety (#632): policy unprotected (production preview cannot
take the guard header without shared edits; canonical header
scripts/p2_fixture_captain_guard.h recorded as reference). Captain
left at squad spawn, short birth-focused run, post-run scan clean
(captain_safety_scan, tested). Guard/source hashes: header 813 bytes
at maintained scripts path; observer scan in this lane's reserved
module with negative tests.

## Packaging consumption (#576)

#576 (registry done) published BlackMan99 + owned-Tyre98 hash-verified
staging on branch codex/autofill-576, NOT integrated at this pin.
Its module was used read-only to stage candidate sidecars into the
gen3 run dir (identity + actors files for 99/98, receipt with helper
owner linkage); no packaging code was committed to this lane. Live
two-way validation awaits #576 integration plus the generated
session above.

## Concrete source ID

- Source ID: 99 BlackMan (Waterwraith); 98 Tyre is the helper roller
  (no independent gate table, not seeded).

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED | gen3 run output/workflow/autofill/enemy-waterwraith99-generated/ww-genesis/992d26a345af482089eba8f7e4ab6564/run.log:592 resolve 99, :593 placement bound=1 slot 568677317, :594 probe terrain/route, :766 fixed BIRTH untied (no generator field); placement99 arm live, family generated-actor claim missing | natural markers; no staged tie passed |
| 2. Autonomous movement and animation | PASS (natural, inherited) | output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:897 actor-owned route leg; stdout.log:959 captain chase walk; stdout.log:972 chase travel accumulates | natural |
| 3. Attacks and receivers | PASS (natural, inherited) | output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:1153 stuns=1 hits=55 crushes=18 damage=3300.0; lane-31 family evidence preserved | natural |
| 4. Death and corpse | PASS (natural, inherited) | output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:977 body zero; stdout.log:980 corpse registered; stdout.log:982 teardown | natural |
| 5. Actual transport and reward | PASS (natural, inherited) | output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:1147 receipt generator=0 deliveries=1; corpse:waterwraith:0 value=2 | natural |
| 6. Cleanup and re-entry | PASS (natural, inherited) | output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:1152 re-entry ready=1 attached=1 | natural |

Gates 2-6 are preserved exactly from the read-only l63 slice (family
actor/encounter modules untouched this lane); only gate 1 carries new
#572 evidence: the placement99 arm proven live plus an honest BLOCKED
record on the family-claim gap, not a PASS.

## Tests run

- tests/test_pikmin2_waterwraith_generated_acceptance.py: observer
  triple/slot/tie/taint/captain-scan tests + fixture compile/run/agreement
  tests pass (24 with mingw g++ on PATH; fixture subset skips honestly
  without it).
- Adjacent waterwraith + placement suites re-run (see checks.log);
  l52 muse sync tests pass via the private native junction.
- scripts/check_p2_handoff_gates.py on this doc: 98 helper-ignored,
  gate1 BLOCKED, gates 2-6 accepted, no refusals.

## Follow-on proposals (exact, for integrator #437)

1. Family generated-claim arm (this lane owns pc_p2_waterwraith_actor /
   encounter files): bind the placement-bound seeded Teki as the rig
   owner and log its generator on P2_WATERWRAITH_BIRTH; needs its own
   design slice plus runtime validation adjacent to preserved gates.
2. Packaging integration: land codex/autofill-576 (#576 done) so
   candidate sidecars ride a current pin.
3. Then: generated session under this lane's strict observer for the
   gate1 PASS attempt.

## Reproduction

Run the observer suite, then the gate-table check:

    py -3.12 -m pytest -q tests/test_pikmin2_waterwraith_generated_acceptance.py
    py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_WATERWRAITH_GENERATED_ACCEPTANCE.md
