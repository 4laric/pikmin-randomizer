# Save/session pin-discovery review: four P1-blocking #132 native items (#658)

Lane `shard-overworld-last-save-session-pin-discovery`, issue #658 (OPEN).
Implementation owner: Codex through shared account 4laric. BOUNDED
pin-discovery/ownership only: no source edits, no shared-file changes, no
runtime runs, no ADMIT. All six runtime gates UNTESTED. Research tree
`native/pikmin2-research` used read-only; line numbers below are from that
tree as inspected this turn.

## 1. Native sunset driver (day start/end, sunset losses, surface time)

No lane owns it. Verified pins (`singleGameSection.cpp`):

| Line | Symbol | Role |
|---|---|---|
| 183 | `SingleGame::CaveDayEndState::init` | cave day-end entry |
| 209 | `SingleGame::CaveDayEndState::exec` | cave day-end tick |
| 660 | `SingleGameSection::saveMainMapSituation` | surface time capture |
| 684 | `SingleGameSection::loadMainMapSituation` | time restore on re-entry |
| 486 | `SingleGameSection::enableTimer` | day timer arming hook |
| 500 | `SingleGameSection::disableTimer` | day timer disarm hook |

Open sub-item: field-Pikmin sunset-loss enumeration has no sunset-named
driver in `src` (only UI counters in `hurryUp2D.cpp`/menus); the loss site
must be pinned from the day-end flow, not assumed. Shared review: #186
(day hooks sit on the shared section/FSM path).

Downstream spec outline (bounded): hook-declaration adapter + focused tests
for day start/end + timer arm/disarm on a private fixture; owned files
`experimental/pikmin2_sunset_driver_hook.py`,
`tests/test_pikmin2_sunset_driver_hook.py`,
`docs/PIKMIN2_SUNSET_DRIVER_HOOK.md`; acceptance: hook fires on the pinned
transitions, loss enumeration resolved or recorded ABSENT, six gates honest.

## 2. Save serializer (durable independent saves)

No lane owns it. Verified pins (`gamePlayDataMemCard.cpp`):

| Line | Symbol | Role |
|---|---|---|
| 39 | `PlayData::write` | durable save entry |
| 707 | `PlayData::read` | restore entry |
| 1372 | `CaveSaveData::write` | cave payload write |
| 1411 | `CaveSaveData::read` | cave payload restore (size-guarded) |
| 1346 | `OlimarData::write` | captain block write |
| 1360 | `OlimarData::read` | captain block restore |

Shared review: #132 saves/progression + #186 (independent per-area/squad/
captain semantics extend the audited card format).

Downstream spec outline (bounded): serializer-conformance adapter + tests for
per-area/squad/captain save/restore round-trips on pinned fixtures; owned
files `experimental/pikmin2_save_serializer_conformance.py`,
`tests/test_pikmin2_save_serializer_conformance.py`,
`docs/PIKMIN2_SAVE_SERIALIZER_CONFORMANCE.md`; acceptance: round-trip
equality on the pinned blocks, size-guard negatives, no save-format change.

## 3. Receipt ledger endpoint (surface/area treasure receipt binding)

No lane owns it. Verified pins:

| File:line | Symbol | Role |
|---|---|---|
| onyonMgr.cpp:403 | `InteractSuckDone::actOnyon` | pellet-to-poko delivery endpoint |
| gamePlayData.cpp:800 | `PlayData::obtainPellet_Main` | ledger accumulation (:832) |
| onyonMgr.cpp:195 | `Onyon::isSuckReady` | delivery readiness gate |

No receipt/ledger-named source exists in research; the endpoint above is the
real delivery path. Shared review: #606 (owns the ledger concept) + #186
(the surface binding is unscoped).

Downstream spec outline (bounded): receipt-binding observer + tests proving
delivered-treasure accounting on a pinned fixture; owned files
`experimental/pikmin2_receipt_ledger_binding.py`,
`tests/test_pikmin2_receipt_ledger_binding.py`,
`docs/PIKMIN2_RECEIPT_LEDGER_BINDING.md`; acceptance: delivery-to-ledger
trace on real callbacks, negatives refused, no receipt fabrication.

## 4. Generator-cache restore (cave/actor regeneration restore)

No lane owns it. Verified pins (`gameGeneratorCache.cpp`):

| Line | Symbol | Role |
|---|---|---|
| 557 | `GeneratorCache::read` | cache restore entry |
| 504 | `GeneratorCache::write` | cache persist entry |
| 203 | `GeneratorCache::loadGenerators` | course generator load |
| 281 | `GeneratorCache::slideCache` | cache slide/rotation |
| 341 | `GeneratorCache::beginSave` | save framing entry |
| 665 | `CourseCache::read` | per-course restore |

Shared review: #607 cave generation + #186 (restore extends the accepted
generator pin).

Downstream spec outline (bounded): restore-conformance adapter + tests for
cache write/read round-trips and per-course restore on pinned fixtures; owned
files `experimental/pikmin2_generator_cache_restore.py`,
`tests/test_pikmin2_generator_cache_restore.py`,
`docs/PIKMIN2_GENERATOR_CACHE_RESTORE.md`; acceptance: round-trip equality,
overflow/negative paths, no generator-semantics change.

## Cross-cutting

- Upstream evidence consumed read-only: #132 dayclock-anchor-audit, #132
  surface-session contract, #606/#607 provider scopes. Nothing duplicated.
- Shared-semantics needs route to #570/#186, never silent edits.
- Consumers: overworld-last P1 runtime, caves P1 (forest/yakushima),
  challenge P1 slices gated on save/session; recovery `18d253f1`.
- Captain safety #632: N/A (no runtime run). Any future runtime must adopt
  `scripts/p2_fixture_captain_guard.h` (sha256
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`).
