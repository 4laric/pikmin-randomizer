# Last daylight/receipt/cache pin discovery (#151)

Lane `shard-overworld-last-daylight-receipt-cache-discovery`, issue #151 (OPEN,
4laric-assigned; Wistful Wild, course last). Implementation owner: Codex through
shared account `4laric`. This is a **tooling diagnosis** (never an engine
unblock): it pins and names ownership for the three remaining #132
MISSING_INTEGRATION items gating course-last runtime observation. The sibling
save-serializer boundary is consumable via #736 and is NOT re-derived here. No
shared/family/native edits, no builds, no runtime runs, no ADMIT. All six gates
UNTESTED.

## Verdicts (research pins re-verified read-only; port checked at native pin `b805d9c6`)

Research tree `native/pikmin2-research` (files under
`src/plugProjectKandoU/`; all symbols confirmed present this turn):

1. **Sunset/day driver: ABSENT in port.** Research pins
   (`singleGameSection.cpp`: `CaveDayEndState`, `saveMainMapSituation`,
   `loadMainMapSituation`, `enableTimer`, `disableTimer`) hold. Port has no
   `SunsetDriver`/surface day driver (only stubs + cave `day_end`); the field-
   Pikmin sunset-loss enumeration has no sunset-named driver. Owning lane: none.
   Contract: #186 shared review (day hooks on the shared section/FSM path).
2. **Receipt ledger endpoint: ABSENT in port for surfaces.** Research pins
   (`onyonMgr.cpp`: `actOnyon`, `isSuckReady`; `gamePlayData.cpp`:
   `obtainPellet_Main`) hold. Port has NO `obtainPellet`/`actOnyon` surface
   binding. Nuance: the port DOES contain a `ReceiptLedger` vocabulary
   (`pc_p2_receipt.h`, lane-06 cargo/contest provider), which is explicitly NOT
   the #132 surface delivery endpoint and is excluded by the adapter (negative
   test). Owning lane for the surface endpoint: none. Contract: #606 (ledger
   concept) + #186 (surface binding unscoped).
3. **Generator-cache restore: ABSENT in port.** Research pins
   (`gameGeneratorCache.cpp`: `GeneratorCache::read/write/loadGenerators/
   slideCache`, `CourseCache::read`) hold. Port has validation helpers but no
   `GeneratorCache::read`/`slideCache` restore path. Owning lane: none.
   Contract: #607 cave generation + #186.

## Downstream consumers (last P1 runtime fixture; fixture does not exist yet)

Canonical command shape (contract, not a run claim):
`scripts/run_pikmin2_fixture.py --arena <last-arena> --fixture <last-p1-fixture.exe> --seconds <budget>`.
Expected per-boundary behavior: boot emits `P2_LAST_BOOT course=last` (unknown
refused); day shows start/end + timer markers with losses enumerated or ABSENT;
save uses the #736 boundary round-trips; receipt traces delivery callbacks with
no fabrication; exit shows anchor + restore markers. The pinned registry names
these commands per item.

## Owned files (all new)

- `experimental/pikmin2_last_daylight_receipt_cache_discovery.py`: research-pin
  verifier + port checker + pinned-registry emitter; fail-closed on drift.
- `tests/test_pikmin2_last_daylight_receipt_cache_discovery.py`: 13 focused
  tests (pins, ABSENT verdicts, cargo-ledger exclusion, contracts, consumer
  shape, no-write, stdlib-only). All pass.
- This file.

## Six-gate status (tooling; all UNTESTED, no runtime claim)

| Gate | Status | Evidence | Method |
|---|---|---|---|
| 1-6. all gates | UNTESTED | n/a (diagnosis only) | unobserved |

## Captain safety (#632)

N/A (no runtime run). Any future last-P1 runtime must adopt
`scripts/p2_fixture_captain_guard.h` with orimaDead/NaviDead/HP<=1 checks,
CAPTAIN_DOWN + BLOCKED exit, and a parked captain; guard/source hashes recorded
at adoption.