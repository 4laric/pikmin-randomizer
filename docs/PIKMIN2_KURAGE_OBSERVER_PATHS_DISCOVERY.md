# Kurage57 observer-paths discovery (#753)

Coordinator prerequisite promotion for the enemies-4 Kurage gap: the Kurage57
observer is unstageable on precedent paths (all owned by done #498); no live
owner exists for the designation.

## Ownership (read-only)

Done `muse-kurage` (#498, gen 5) owns `experimental/pikmin2_muse_kurage.py`,
`tests/test_pikmin2_muse_kurage.py`, `docs/PIKMIN2_MUSE_KURAGE_HANDOFF.md`,
`native/tools/p2_muse_kurage_fixture.cpp` (gate 1 closed there; files unlanded
but ownership-retained). Precedent observer shape: armor15/mar29 published items.

## Designation (zero overlap, verified free)

- `experimental/pikmin2_kurage57_observer.py`
- `tests/test_pikmin2_kurage57_observer.py`
- `docs/PIKMIN2_KURAGE57_OBSERVER.md`
- `native/tools/p2_kurage57_observer_fixture.cpp`

Verified free of manifest owners, planner claims, and existing files. Consumer
pins: #498 files (gate-1 baseline, read-only), armor15 shape (read-only).

## Observer scope (downstream)

Kurage57 death/transport/re-entry observer on the designated paths; gate 1 taken
as-is from #498; natural death + corpse, transport/reward with stale/fresh proof,
honest six-gate handoff, focused tests, no ADMIT.

## Verification

`py -3.12 -m pytest tests/test_pikmin2_kurage_observer_paths_discovery.py -q`
-> 8 passed. All gates UNTESTED; no family/shared/native edits, no runtime.