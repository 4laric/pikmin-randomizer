# Overworld surface save/progression boundary contract (#132)

Lane `overworld-save-progression-contract`, issue #132 (OPEN, reused; no
duplicate issue). Implementation owner: Codex through shared account 4laric.
P0 tooling only: no native build/runtime/ADMIT; all six runtime gates
UNTESTED; fixture adoption N/A.

## Scope

Audit the surface save/progression boundary for the four P2 overworld lanes
(148 Valley of Repose, 149 Awakening Wood, 150 Perplexing Pool, 151 Wistful
Wild) by read-only inspection of the six existing surface modules
(`pikmin2_surface_identity/ledger/physics/pocket/runner/topology.py`) against
the decoded overworld surface tables
(`docs/PIKMIN2_CONTENT_INVENTORY.json`, source `user/Abe/stages.txt`).
Publish an isolated contract adapter so the four lanes share one validated
boundary instead of re-deriving it.

## Reserved files (only these; all new)

- `experimental/content_lanes/p2-overworld-save-progression.py` - contract adapter.
- `tests/content_lanes/test_p2_overworld_save_progression.py` - 21 focused tests.
- `docs/content_lanes/p2-overworld-save-progression.md` - this document.

No shared surface module, manifest or other lane file was edited. If a shared
surface module must change, that change is NOT included here and goes through
existing-owner review (#186) first.

## What the boundary covers (host side)

- Per-area registry: the four overworld ids bound to issues 148/149/150/151 and
  the single decoded source `user/Abe/stages.txt`; unknown/duplicate/mismatched
  rows are refused.
- Surface snapshot schema persisted by `SurfaceLedger`: `region, day, time,
  position, squad, health, receipts` (region token `[a-z0-9_-]{1,100}`, day
  1..1000000, time 0..24, finite position within 100000).
- Ledger envelope: `schema(=1), campaign(32-hex), content(64-hex),
  origin(64-hex), revision(=len(events)), phase(surface|cave|return_ready|
  failed), surface, trip, events`; event keys `enter:|floor:|return:<32-hex>`
  with 64-hex digests.
- Content identity shape (64-hex) consumed by `surface_identity(...)`.

## What the boundary does NOT cover (exact unsupported references)

The four native integration items resolved by pin-discovery #658, recorded as
references only (not re-derived, nothing invented):

| Item | Native pins (verbatim) |
|---|---|
| sunset driver | singleGameSection.cpp:183,209,660,684,486,500 |
| save serializer | gamePlayDataMemCard.cpp:39,707,1372,1411,1346,1360 |
| receipt ledger endpoint | onyonMgr.cpp:403, gamePlayData.cpp:800, onyonMgr.cpp:195 |
| generator-cache restore | gameGeneratorCache.cpp:557,504,203,281,341,665 |

Provenance: `shard-overworld-last-save-session-pin-discovery` (#658). Missing
local disc stage-table bytes (`user/Abe/stages.txt`) stay missing; the adapter
never fabricates a stage row.

## P1 activation prerequisites

1. The four #658 native items each need a bounded implementation lane plus the
   #186 shared-semantics decision where the item touches a shared path.
2. P1 runtime import per area additionally needs the per-area content lane's
   stage bytes and the #132 surface-session contract runtime binding.
3. Then P2 persistence acceptance (per-area saves, day/sunset losses, receipt
   ledger) can be staged with #632 captain-guard adoption.

## Verification

`py -3.12 -m pytest tests/content_lanes/test_p2_overworld_save_progression.py -q`
-> 21 passed (synthetic fixtures; the adapter also loads the real committed
inventory and asserts the four-area registry).