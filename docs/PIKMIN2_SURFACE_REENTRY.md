# Repeated bounded entrance visits (#114 / #132)

`scripts/play_pikmin2_surface_loop.py` is a separate opt-in launcher. It preserves
the existing one-trip launcher and its QA bundle. Use a fresh output directory;
one-trip outputs are explicitly rejected. The separate entrance App needs the
new `repeat` mode. Older App binaries reject that mode rather than silently
disabling subsequent entry.

The player can return from Emergence Cave, walk within the original bounded
entrance pocket, and press F6 at the source marker to begin another visit.
The host uses the same SurfaceRunner and normal cave executable on every visit.
Closing a cave still resumes its latest floor entry. Closing a surface reuses
that surface launch command; this is boundary persistence, not a mid-day save.

## Authoritative transaction

`SurfaceLedger.enter_cave(revision, trip_id, native_entry=...)` accepts an optional
payload containing native transfer text, actual captain position, and receipts.
The native transfer token must equal the new trip ID. Thus the existing
`enter:<trip_id>` event binds the entire native entry exactly once, including
its expected revision. A successful transaction simultaneously updates current
surface position, squad/maturity, captain health and unchanged receipts, then
creates a new cave floor1 checkpoint and fresh cave token.

The existing floor1 transfer validator prevents population/species inflation.
Surface receipt acquisition is not supported; keys and values must equal the
authoritative surface receipt map. The host validates the source-pocket position;
the ledger also validates finite snapshot coordinates. Host region/day/time are
retained unchanged because native surface clock/world restoration is unfinished.

Extinction/knockout commits an authoritative failed trip with no living squad.
Only that failure may omit position, because the native extinction path exits
before the manual App can capture it. A failed trip cannot return or revive.
Living entries without a valid position fail without committing.

`pending-surface-entry.json` is a replayable command, not a second state writer.
It is stored before launching the surface, augmented with native output before
the ledger transaction, and removed afterward. If cleanup is interrupted, exact
replay returns the current state. Reusing its token with a new revision or changed
payload fails. Old exact replay after a later trip cannot move progress backward.
The ledger format and original no-payload entry request digests remain unchanged.

Receipts retain their existing identities across visits; repeated delivery does
not add duplicate Pokos. The existing native economy/receipt mechanism remains
responsible for in-game collection behavior; host regression tests do not claim
native repeat-visit playtesting.

## Remaining gates

- The entrance still has the engineered radius60 fence and original source floor.
- All source water metadata remains staged, with no native surface-water gameplay.
- The current staging limit is20 survivors; larger parties remain saved and are
  refused explicitly, never truncated.
- No production native source or shared build is needed for the ledger/host work.
  The separate App's opt-in mode must be privately rebuilt before manual use.
- Native physical F6 and complete repeated visits require manual acceptance.

Focused tests exercise two complete host visits through SurfaceRunner, changed
position and party, preserved receipt totals, stale/replayed entries, foreign
commands, interrupted ledger writes and command cleanup, native failure, and
rejected population/receipt inflation. Existing one-trip and ledger tests remain
part of the regression set.
