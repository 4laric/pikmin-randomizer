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
- P2_WATERWRAITH_GENERATED_BIND generator slot source=99 (family
  claim arm in pc_p2_waterwraith_encounter.cpp: the encounter verifies
  the live seeded Teki -- alive, placement-bound, seed source 99 on
  the staged slot -- and owns it; the fixed P2_WATERWRAITH_BIRTH
  phase=fall attached=1 id=99 helper=98 proves the family is alive but
  never satisfies the verdict alone),
- P2_WATERWRAITH_GENERATED_FORGET generator reason (claim loss:
  dead, unbound, changed or gone; any later FORGET fails the verdict).

PASS requires resolve/placement agreement on the accepted slot
568677317, a BIND naming the same generator and slot, the family
birth naming id 99 with helper 98 attached, no later FORGET for that
generator, and no injected-birth taint. Tyre98 is attached evidence,
never the identity: no gate table is produced for 98.

native/tools/p2_muse_waterwraith_fixture.cpp gains an opt-in
--generated mode with the same triple logic (default invocation is
byte-identical to the l63 fixed-encounter contract). Both observers
plus the #575 waterwraith_generated_triple API agree on every sample
and on the live runs below (cross-tested).

## Gen4 validation runs (claim arm live)

Consumed reviewed prerequisites: root 7a21ce6a + native e2aa476e
(#575). Family claim arm implemented in owned
pc_p2_waterwraith_encounter.cpp (sidecar read, tekiMgr scan with
liveness + placement + seed-source verification, per-tick
revalidation, forget on loss; fixed rig/markers untouched).
Rebuilt privately via the leased runner (build log
output/workflow/autofill/enemy-waterwraith99-generated/build-1789622574745944800.log:
configure + pikmin_pc link + ninja no-work dry run, exit 0).

Happy run output/workflow/autofill/enemy-waterwraith99-generated/ww-genesis-g4/f7b255aef52c401abb3bf7125bae9735
(fresh arena, current overlay, staged Frog0 record id 568677317,
fixed family sidecar, generated sidecar naming 568677317,
placement slot join, minimal ENEMY_P2 seed to 99, cargo Pod, #576
candidate sidecars staged read-only into the run dir). Launch:
nectar.exe --experimental-pikmin2-room --randomizer-seed,
PIKMIN_P2_ROOM_WINDOW 960x540, 150 s harness deadline. Log run.log
sha256 dff6717257560378317120caa40a0333e3791e73a51ad2698d47ffcee2aa050b.

- :14 960x540 windowed and centered; :248 live 20-red squad.
- :591 P2_SEED_RESOLVE source_id=99 target=568677317.
- :592 P2_GENERATED_PLACEMENT source_id=99 target=568677317
  generator=568677317 bound=1.
- :593 P2_PLACEMENT_SLOT terrain=ground route=1 for the slot.
- :741 register profile binds the fixed placement (preserved).
- :763 P2_WATERWRAITH_GENERATED_BIND generator=568677317
  slot=568677317 source=99 type=0 (claim verified live Teki).
- :764 P2_WATERWRAITH_BIRTH phase=fall attached=1 id=99 helper=98.
- No FORGET, no taint, no staged-only tie: the generator was read
  from the live actor, never injected.
- Verdicts: Python PASS; C++ fixture generated_ok=1 (exit 1 only
  because the birth-focused run staged no visual profile and no
  chase leg ran: fixed visual/chase legs absent by run design,
  gates 2-6 preserved from l63, not re-proven); #575 triple API
  correlated=true. Captain-safety scan: clean.

Stale negative run ww-genesis-g4-stale (sidecar naming nonexistent
generator 999999001, same slot/seed): resolve :592 and placement
:593 fire, fixed BIRTH fires, NO bind is emitted, observer FAILs
with the exact missing-claim reason. The claim arm does not fire
spuriously.

Captain safety (#632): policy unprotected (production preview cannot
take the guard header without shared edits; canonical header
scripts/p2_fixture_captain_guard.h recorded as reference). Captain
left at squad spawn, birth-focused runs, post-run scans clean
(captain_safety_scan, tested incl. negative death-marker test).
Guard/source hashes: header 813 bytes at maintained scripts path;
observer scan in this lane's reserved module with tests.

## Packaging consumption (#576)

#576 (registry done) published BlackMan99 + owned-Tyre98 hash-verified
staging on branch codex/autofill-576, NOT integrated at this pin.
Its module was used read-only to stage candidate sidecars into both
gen4 run dirs (identity + actors files for 99/98, receipt with helper
owner linkage); no packaging code was committed to this lane. Live
two-way validation awaits #576 integration plus the generated
session above.

## Concrete source ID

- Source ID: 99 BlackMan (Waterwraith); 98 Tyre is the helper roller
  (no independent gate table, not seeded).

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/workflow/autofill/enemy-waterwraith99-generated/ww-genesis-g4/f7b255aef52c401abb3bf7125bae9735/run.log:591 resolve 99, :592 placement bound=1 slot 568677317, :593 probe terrain/route, :763 GENERATED_BIND generator=568677317 slot=568677317 source=99, :764 BIRTH id=99 helper=98 | natural |
| 2. Autonomous movement and animation | PASS (natural, inherited) | output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:897 actor-owned route leg; stdout.log:959 captain chase walk; stdout.log:972 chase travel accumulates | natural |
| 3. Attacks and receivers | PASS (natural, inherited) | output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:1153 stuns=1 hits=55 crushes=18 damage=3300.0; lane-31 family evidence preserved | natural |
| 4. Death and corpse | PASS (natural, inherited) | output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:977 body zero; stdout.log:980 corpse registered; stdout.log:982 teardown | natural |
| 5. Actual transport and reward | PASS (natural, inherited) | output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:1147 receipt generator=0 deliveries=1; corpse:waterwraith:0 value=2 | natural |
| 6. Cleanup and re-entry | PASS (natural, inherited) | output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:1152 re-entry ready=1 attached=1 | natural |

Gate 1 is this lane's fresh natural evidence (live family bind on the
generated actor). Gates 2-6 are preserved exactly from the read-only
l63 slice (family actor/encounter behavior modules untouched except
the additive claim arm, which does not alter fixed-rig behavior).

## Tests run

- tests/test_pikmin2_waterwraith_generated_acceptance.py: observer
  triple/slot/bind/forget/taint/captain-scan tests + fixture
  compile/run/agreement tests pass (27 with mingw g++ on PATH;
  fixture subset skips honestly without it).
- Adjacent waterwraith + placement suites re-run (see checks.log);
  l52 muse sync tests pass via the private native junction.
- scripts/check_p2_handoff_gates.py on this doc: 98 helper-ignored,
  gate1 accepted PASS, gates 2-6 accepted, no refusals.

## Follow-on proposals (exact, for integrator #437)

1. Packaging integration: land codex/autofill-576 (#576 done) so
   candidate sidecars ride a current pin.
2. Behavior routing (future, out of scope): drive rig visuals from
   the claimed Teki; needs its own design slice adjacent to
   preserved gates.
3. Then: ordinary generated session under the strict observer for
   full admission review.

## Reproduction

Run the observer suite, then the gate-table check:

    py -3.12 -m pytest -q tests/test_pikmin2_waterwraith_generated_acceptance.py
    py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_WATERWRAITH_GENERATED_ACCEPTANCE.md
