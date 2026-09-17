# Save-dayclock dependency-ready record for tutorial P1 consumers (#132)

Lane `caves-tutorial-save-dayclock-dependency-ready`, issue #132 (stays
OPEN). Implementation owner: Codex through shared account `4laric`.
Tooling-only publication: no native build, no shared edits, no ADMIT. All
six runtime gates UNTESTED; no playability is claimed.

## What this publishes

A machine-readable `dependency-ready.json` that tutorial P1 lanes
(`p2-cave-tutorial_2` #152, `p2-cave-tutorial_3` #153) can pin. Every value
is hash-verified at publish time against the DONE audit lane
`provider-save-dayclock-anchor-audit` (root commit `4fff74c7`) outputs; any
mismatch fails closed with the exact difference. Nothing is re-decoded or
invented.

Pinned contract inputs:
- Audit inventory (`out/inventory.json`, verdict `complete`): five required
  anchor groups (day_clock, sunset_loss, debt_equipment, louie_president,
  save_migration) plus the expected-absent sprout_regeneration record.
- Audit doc, adapter and tests (hash-pinned as files).
- Research source pins for the two cited files
  (`src/plugProjectKandoU/singleGameSection.cpp`, `gamePlayData.cpp`).

## Downstream consumers

- `p2-cave-tutorial_2` (#152) and `p2-cave-tutorial_3` (#153): pin this
  record's `inventory_sha256` + provider commit for their P1 save-semantics
  slices.

## Explicitly unevaluated (NOT covered by this record)

- Sprout-regeneration anchors (outside the audited pair; see audit notes).
- Treasure-ledger semantics (provider-treasure-receipts shard).
- Floor-generation semantics (provider-cave-generation shard).
- Durable-save write paths and restart identity (future provider work).
- Any runtime behavior, reward, revisit or restart observation.

## Validation evidence (this turn)

- `tests/test_pikmin2_save_dayclock_dependency_ready.py`: 9/9 pass
  (real-output positive plus tampered/truncated/corrupt/missing negatives).
- Publisher: `experimental/pikmin2_save_dayclock_dependency_ready.py`.