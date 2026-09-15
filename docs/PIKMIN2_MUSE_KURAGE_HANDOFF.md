# Muse l58 — Kurage57 correlated natural generated birth (#498)

Parent #243; wave #491; integration #437/#186. Implementation owner: Codex
through shared account 4laric; executing contributor Muse Spark 1.3 via
OpenCode (lane muse-kurage, l58).

## Scope

Close gate 1 with the SAME real generated slot/generator appearing in
placement, source-ID resolve, and Kurage binding. Additive observer and
negative tests land now while the placement/packaging blockers progress;
reviewed candidate commits from muse-placement (l52/#492) and
muse-packaging (l53/#493) are consumed only after their dependency-ready
records appear. The old 201001 sidecar auto-bind is never passed off as a
generated identity. Legacy l29 claim and capture/ingestion modules are
read-only; accepted gates 2-6 are unchanged.

## What was added (reserved files only)

- `experimental/pikmin2_muse_kurage.py` (new): read-only log observer
  `validate_generated_birth()` correlating `P2_SEED_RESOLVE source_id=57`,
  `P2_GENERATED_PLACEMENT source_id=57 bound=1`, `P2_KURAGE_TEKI_READY` and
  `P2_KURAGE_CORPSE_READY` on one slot/generator; fail-closed on any missing
  marker, mismatch, `bound=0`, or injected/health_zero taint. Legacy 201001
  auto-bind without generated markers is an explicit named FAIL.
- `tests/test_pikmin2_muse_kurage.py` (new): 12 tests — correlated PASS plus
  negatives for auto-bind, missing placement/resolve, slot/generator
  disagreement, `bound=0`, wrong source ID, injected taint, corpse-receipt
  mismatch, and empty log.
- `native/tools/p2_muse_kurage_fixture.cpp` (new): dependency-free C++
  twin of the observer (reads a native.log path or stdin, exit 0 PASS /
  exit 1 FAIL). Links against nothing; NOT registered as an engine
  replacement-main target — CMake registration waits for the l52 case-57
  bind (shared hook request to #491 before any CMakeLists edit).

## Ordered commits

Root branch `codex/muse-l58-kurage` (base `72a2c450d7b9040545de4a440c2c32e2173ea6fa`):

1. `l58: Kurage57 generated-birth observer + negative tests (#498)` —
   experimental module, pytest suite, this handoff.

Native branch `codex/muse-l58-kurage-native` (base `7b9ecaa668fd55332073446cdbdaf6424b209ea7`):

1. `l58: additive Kurage generated-birth log observer fixture (#498)` —
   `tools/p2_muse_kurage_fixture.cpp` only; no engine linkage, no CMake edit.

## Interfaces / hooks touched

None. No shared file edited. Requested future hook (filed with #491 when
l52 lands, not now): register `tools/p2_muse_kurage_fixture.cpp` as a
standalone (non-engine) CMake target, or consume the l52
`pc_p2_generated_placement_bind` case-57 marker contract as-is.

## Build / test evidence

- `py -3.12 -m pytest tests/test_pikmin2_muse_kurage.py -q` -> **12 passed**.
- Native fixture: `g++ -fsyntax-only -std=gnu++17 -fpermissive
  tools/p2_muse_kurage_fixture.cpp` -> EXIT 0; linked standalone and ran
  against a correlated sample (exit 0,
  `KURAGE_GENERATED_BIRTH_PASS slot/generator=349001`) and a legacy-201001
  auto-bind sample (exit 1, named auto-bind FAIL).
- No heavy engine build this slice: no engine source changed, so no rebuild
  was required; fixture provenance for a runtime claim remains future work
  after the l52 bind lands.

## Dependency / blocker record (exact)

Gate 1 is BLOCKED on two named providers, both without `dependency-ready.json`
at handoff time:

- muse-placement l52/#492: `native/pc_port/pc_p2_generated_placement.cpp`
  has bind cases only for source IDs 23/59-62; no case 57, so
  `P2_GENERATED_PLACEMENT source_id=57 bound=1` can never be emitted.
  No legal-slot profile for Kurage57 exists in
  `randomizer/p2_placement_catalog.py` (cohort covers lanes 13/14/16/19/22/30).
- muse-packaging l53/#493: no candidate staging path for identity 57, so a
  generated session cannot stage Kurage assets/sidecars.

Seed-layer check passes already: 57 is in `randomizerP2SourceIds`
(`native/pc_port/pc_randomizer_p2_roster.h`), so `ENEMY_P2` can carry it and
`P2_SEED_RESOLVE source_id=57` is emittable once a seed targets a slot.

## Concrete source ID

- Source ID: 57 `Kurage`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED | tests/test_pikmin2_muse_kurage.py observer ready (12 passed); live bind waits on muse-placement l52/#492 case-57 `P2_GENERATED_PLACEMENT` and muse-packaging l53/#493 candidate staging; legacy 201001 auto-bind explicitly refused | blocked on named providers |
| 2. Autonomous movement and animation | PASS (natural, inherited) | docs/PIKMIN2_LANE29_DEEPSEEK_HANDOFF.md slice 4; output/dsw/l29-out/kurage-arena/b7439430e78b48b6ad2c9400f50f4b02/run.log:764 P2_KURAGE_MOVE 136 samples states 1/2/4/9 | natural source FSM; body stand-in labelled in l29 |
| 3. Attacks and receivers | PASS (natural, inherited) | docs/PIKMIN2_LANE29_DEEPSEEK_HANDOFF.md slice 4; output/dsw/l29-out/kurage-arena/b7439430e78b48b6ad2c9400f50f4b02/run.log:793 P2_KURAGE_RECEIVER_HIT, :794 ATTACH stick_before=0 stick_after=1, :852 KILL alive_after=0 | natural receiver on live Pikmin |
| 4. Death and corpse | PASS (natural, inherited) | docs/PIKMIN2_LANE29_DEEPSEEK_HANDOFF.md slice 3; output/dsw/l29-out/kurage-arena/f4b1b0a27e8f4c85b906c04b249b3618/run.log:808 P2_KURAGE_TEKI_DEAD, :813 CORPSE_CONFIG | natural |
| 5. Actual transport and reward | PASS (natural, inherited) | docs/PIKMIN2_LANE29_DEEPSEEK_HANDOFF.md slice 3; output/dsw/l29-out/kurage-arena/f4b1b0a27e8f4c85b906c04b249b3618/run.log:855 P2_POD_RECEIPT id=corpse:kurage:201001 value=2 new=1 pokos=2 seeds=0 | natural |
| 6. Cleanup and re-entry | PASS (natural, inherited) | docs/PIKMIN2_LANE29_DEEPSEEK_HANDOFF.md slice 4; output/dsw/l29-out/kurage-reentry-run/stdout.log:766 FORGET, :770 RESET, :774 REENTRY_PASS stale_bound=0 rebound=1 | natural forget/reset seam |

Gates 2-6 are inherited unchanged from the read-only l29 slices (no
re-observation, no relabelling), including l29's labelled concessions (P1
type-0 stand-in body, FreeMode haul 426.8u with 18 carriers, corpse credit as
a stand-in for the source number-pellet reward); only gate 1 carries new l58
evidence, and that evidence is the observer plus an honest BLOCKED record,
not a PASS.

## Reproduction

```
py -3.12 -m pytest -q tests/test_pikmin2_muse_kurage.py
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_MUSE_KURAGE_HANDOFF.md
```

## Remaining work

1. Consume reviewed l52 case-57 bind + slot profile and l53 candidate
   staging after their dependency-ready records; cherry-pick into the
   private worktree preserving this observer.
2. Run a real generated session (ENEMY_P2 seed targeting the l52 slot),
   capture native.log, and validate with both observers.
3. Register the C++ observer in CMake (hook request to #491) once the
   marker contract is final.
