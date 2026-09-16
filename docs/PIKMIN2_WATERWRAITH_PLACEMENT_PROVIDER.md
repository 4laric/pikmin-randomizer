# Waterwraith99 generated-placement provider (#575, consumer #572)

Provider slice for source 99 `BlackMan` (Waterwraith). Candidate-only: no
admission, no ledger writes, no runtime claim. Family files and the natural
gate-1 run stay with consumer #572.

## Verified gap and fix

At integration pins root `5486ae84` / native `ce89a039` the catalog had no
`BlackMan`/99 entry and the native candidate predicate/slots covered only
41/57/58/78. This slice adds a parallel, candidate-only source99 contract
without touching the #492 muse table.

## Slot choice (one defensible real production slot)

`568677317` = `navel_0-29_645`, stage-2 Navel water-cavern generator, ground
cohort, unprotected, renewable (`respawn_days` 5), corpse route, radius 100.

Rationale (from production campaign evidence, never a fixed-encounter UID):
Waterwraith is the water-cavern boss, and this is the lowest-UID unused ground
slot in the water-themed Navel cohort that already satisfies the ground +
corpse-route constraints. The #492 cohort uses 1254096625 (Hope),
689702860 (Navel mixed), 1787125272 (Spring) and 328297937 (Navel), so this
slot is distinct from all four.

Vehicle / terrain / route requirements:

- Vehicle: the lane-31 Waterwraith register seam (`pc_p2_waterwraith_register`)
  owns behavior; this native arm only records placement acceptance.
- Terrain: `ground` (actor walks the map graph; `burrow_ground` true).
- Route: `corpse_route` required (the profile sets `requires_corpse_route`).
- Helper: Tyre98 is the BlackMan manager child (`enemyInfo.cpp` child_count 1).
  It is never an independently seeded identity; `helper_budget` stays 0 and
  `WATERWRAITH_HELPER_IDS = {98}` records the exclusion.

## Contract

Root (`randomizer/p2_placement_catalog.py`, additive):

- `WATERWRAITH_CANDIDATE_SPEC` / `WATERWRAITH_GENERATED_SLOTS` /
  `WATERWRAITH_CANDIDATE_IDS` / `WATERWRAITH_HELPER_IDS`
- `waterwraith_candidate_profile()` (empty `accepted_gates`, one
  `accepted_slot_uids`, `is_boss` false, `helper_budget` 0)
- `waterwraith_candidate_source_ids()`, `waterwraith_accepted_slot()`,
  `build_waterwraith_document()`, `binding_targets_for_waterwraith()`
- `waterwraith_generated_triple(log_text)` - the generation-to-seed
  source99-to-bind correlation API: requires `P2_SEED_RESOLVE source_id=99`
  and a matching `P2_GENERATED_PLACEMENT source_id=99 ... bound=1` on the SAME
  target uid; reports `bind-refused:<reason>`, `resolve-bind-uid-mismatch`,
  `missing-seed-resolve`, `missing-generated-placement` or `no-source99-legs`.

`MUSE_GENERATED_SLOTS`, `MUSE_CANDIDATE_IDS`, `build_muse_document()` and the
ordinary candidate pools are unchanged, so all 41/57/58/78 behavior and the
`p2_muse_placement_fixture` reject-99 assertion are preserved.

Native (`pc_p2_generated_placement.{h,cpp}`, additive):

- `WATERWRAITH_GENERATED_SLOT_BLACKMAN99 = 568677317u`
- `pc_p2_generated_placement_is_waterwraith_candidate(unsigned)` (99 only)
- `pc_p2_generated_placement_waterwraith_slot(unsigned)` (99 -> slot, else 0)
- `case 99` in `pc_p2_generated_placement_bind` routes through a shared
  `recordBind` helper that emits the same `P2_GENERATED_PLACEMENT ... bound=1`
  marker (and `reason=bad-request|slot-rejected|registry-full` refusals) and
  returns false: placement accepted only, no family FSM claim. `is_bound` /
  `bound_count` / `forget` / `reset` cover the new arm because it reuses the
  existing registry.

No `CMakeLists.txt`, engine registry, `pc_main.cpp`, generic receiver or
`pc_p2_bombsarai_*` edit is included; none is needed for this contract.

## Evidence

- Standalone native test `native/tools/p2_waterwraith_placement_provider_test.cpp`
  (engine-free, `-Ipc_port` only): 32/32 PASS, including the static_assert
  slot sync, the preserved muse table (`!is_muse_candidate(99)`), the
  Waterwraith predicate/slot, the Tyre98 exclusion and table disjointness.
- Python `tests/test_pikmin2_waterwraith_placement_provider.py`: 20/20 PASS
  (native slot sync, preserved muse contract, candidate-only profile,
  default-deny `evaluate`, mismatched-slot denial, unsupported-id raise,
  correlation positives/negatives).
- Preserved regressions: `tests/test_pikmin2_muse_placement.py` 16/16,
  plus `test_p2_placement`, `test_p2_placement_audit`, `test_p2_seed_placement`
  (100 passed together; the two muse sync tests need `native/` reachable, which
  is a worktree-link artifact, not a behavioral change).
- Leased private build: `pikmin_pc` 617/617 linked, exit 0, `ninja: no work to
  do.` dry run; executable SHA-256 pinned in the handoff.

## Remaining work (#572)

Consume this API, run the real generated session and require the correlated
triple before any gate-1 claim. Shared semantics still need #186/integrator
review before publication. No ADMIT.
