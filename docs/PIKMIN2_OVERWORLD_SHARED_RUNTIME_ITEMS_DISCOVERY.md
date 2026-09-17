# Overworld shared runtime items: pin + scope the three unowned #132 items (#724)

Bounded source-pin/compatibility discovery for the three remaining generic
#132 native runtime items. Read-only inputs: the #658 save/session pin
registry, the #707 overworld surface boot-path registry, and the #151
surface-session handoff. No native/family/shared edits; no runtime; no ADMIT.

## Why

The accepted overworld-last cycle-18 report records that the `last` (#151) P1
surface session is blocked on the four generic #132 `MISSING_INTEGRATION`
items. A fresh scan found no non-done lane owning three of them. The save
serializer is covered by the published #712
`provider-save-serializer-conformance`, so this lane scopes the other three.

## Per-item verdict (exact pins, owner, #186 gate, scoping deliverable)

Pins are `src/plugProjectKandoU/...` in the read-only research tree; the
packet records the file SHA-256 and the exact line token per pin, fail-closed.

### 1. Native sunset driver -> owner #605 `provider-save-progression`

`singleGameSection.cpp`: `CaveDayEndState::init` (:183), `CaveDayEndState::exec`
(:209), `enableTimer` (:486), `disableTimer` (:500),
`saveMainMapSituation` (:660), `loadMainMapSituation` (:684).
Open sub-item: no sunset-named field-Pikmin loss driver exists in `src`; the
loss site must be pinned from the day-end flow, not assumed.
#186: day start/end and timer hooks sit on the shared section/FSM path.
Scoping deliverable: `experimental/pikmin2_sunset_driver_hook.py`,
`tests/test_pikmin2_sunset_driver_hook.py`, `docs/PIKMIN2_SUNSET_DRIVER_HOOK.md`;
acceptance: hook fires on the pinned day start/end + timer arm/disarm, the
sunset-loss sub-item resolved or recorded ABSENT, six gates honest.

### 2. Native receipt-ledger endpoint -> owner #606 `provider-treasure-receipts`

`onyonMgr.cpp`: `Onyon::isSuckReady` (:195), `InteractSuckDone::actOnyon`
(:403); `gamePlayData.cpp`: `PlayData::obtainPellet_Main` (:800) and the
ledger write `mPokoCount +=` (:832).
Open sub-item: no receipt/ledger-named source exists; these pins are the real
delivery path and are the binding surface.
#186: the surface delivery binding is unscoped.
Scoping deliverable: `experimental/pikmin2_receipt_ledger_binding.py`,
`tests/test_pikmin2_receipt_ledger_binding.py`,
`docs/PIKMIN2_RECEIPT_LEDGER_BINDING.md`; acceptance: delivery-to-ledger trace
on real callbacks, negatives refused, no receipt fabrication, six gates honest.

### 3. Native generator-cache restore -> owner #607 `provider-cave-generation`

`gameGeneratorCache.cpp`: `loadGenerators` (:203), `slideCache` (:281),
`beginSave` (:341), `write` (:504), `read` (:557), `CourseCache::read` (:665).
#186: restore extends the accepted generator pin.
Scoping deliverable: `experimental/pikmin2_generator_cache_restore.py`,
`tests/test_pikmin2_generator_cache_restore.py`,
`docs/PIKMIN2_GENERATOR_CACHE_RESTORE.md`; acceptance: cache write/read
round-trip equality and per-course restore on pinned fixtures with
overflow/negative paths, no generator-semantics change, six gates honest.

### Excluded

Native save serializer: `#712 provider-save-serializer-conformance`
(published); not re-scoped here.

## Method and fail-closed contract

`experimental/pikmin2_overworld_shared_runtime_items_discovery.py` encodes the
three items with their pins, owner, #186 gate and scoping deliverable, and
verifies every pin against the read-only research tree (`PIKMIN2_RESEARCH_ROOT`
or the canonical `native/pikmin2-research`): a missing file, an out-of-range
line, or a line whose token does not match makes the packet INVALID with a
specific reason; nothing is approved partially. `--out` writes the
machine-readable packet with the per-file SHA-256.

## Evidence

- Packet `out/items-packet.json` (ok=true, three items: 6/4/6 verified pins),
  CLI log `out/cli.log`, tests `out/pytest.log` (7 passed).
- Downstream consumers named: `last` (#151) surface session and #599; the #132
  contract `MISSING_INTEGRATION` remains the acceptance gate. All six runtime
  gates UNTESTED; no playability claim; no ADMIT.
