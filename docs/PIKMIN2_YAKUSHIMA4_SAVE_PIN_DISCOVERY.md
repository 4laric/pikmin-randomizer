# Yakushima4 save/persistence pin-discovery (issue #779)

Lane yakushima4-save-pin-discovery, generation 2. Diagnosis only: read-only
source mapping, no engine/file edits, no runtime, no ADMIT, no ledger writes.
Downstream consumer: shard-caves-yakushima-yakushima4-p1 (#161, blocked).
Machine-readable record: experimental/pikmin2_yakushima4_save_pin_discovery.py
(--emit / --check); all six runtime gates UNTESTED.

## Floor-1 evidence (#161)

- Lane shard-caves-yakushima-yakushima4-p1, blocked gen12 rev31.
- Validation: .../caves-yakushima/prepared/yakushima4-p1/out/validation-gen12.log
  sha256 43675548da11239f1f4f737cae12951735fcd529d18315984b72668e5d5d9e91.
- Pins: root f446faee63cc8c48da8d141aff3fdf953f4cb2b4, native
  88188a1e3d687132baf4c2ab7c01b3c752ef4500.
- Holds: real guarded boot (960x540, live 20, unit staging), authored route
  topology (36 NAV rows), walk-inside collision samples
  (P2_YAKUSHIMA4_TRAVERSAL_PASS rooms=8 links=36).
- Remaining gaps: higher floors 2-5, save/persistence, species admission.

## Landed #132 contracts (read-only sources)

1. Cave save: .../planning/dungeons/prepared/cave-save-contract-review-root/
   docs/PIKMIN2_CAVE_SAVE_PROVIDER_REVIEW.md (worktree commit 8aaf6cf6).
   Artifacts: native/pc_port/pc_p2_cave.cpp:123-169 pc_p2_cave_checkpoint
   write sequence; engine/pc_port/pc_p2_cave_transfer.h:17-121 wire format;
   engine/tools/test_p2_cave_transfer.cpp schema asserts.
2. Dayclock anchors: .../provider-save-progression/prepared/save-anchor-audit-root/
   docs/PIKMIN2_SAVE_DAYCLOCK_ANCHOR_AUDIT.md (worktree commit 4fff74c7).
   Artifacts: singleGameSection.cpp:216 advanceDayCount, :183/:209
   CaveDayEndState init/exec, mCaveSaveData/mCurrentCaveID/mCurrentFloor.
   Inventory: .../save-anchor-audit/out/inventory.json.
3. Surface session: .../prerequisites/surface-session-provider-contract/root/
   docs/PIKMIN2_SURFACE_SESSION_CONTRACT.md (worktree commit 7b6d25df).
   Artifacts: schema p2-surface-session-1 checker; save-after-sunset and
   course-matched reload rules.

## Needed slice for yakushima4 floor-1+

- Checkpoint write/read/validate at floor boundaries per the cave-save contract.
- Persisted floor/roster state: floor id, living-squad census, NAV topology ref.
- Day/progression anchors: CaveDayEndState, mCurrentCaveID/mCurrentFloor, day count.

## Owner + first bounded slice

No live provider-save-progression implementation lane exists (only done
planning cycles on #605), so the owner is a NEW bounded lane
yakushima4-save-persistence-slice. First slice owns exactly:
- experimental/pikmin2_yakushima4_save_persistence.py
- tests/test_pikmin2_yakushima4_save_persistence.py
- docs/PIKMIN2_YAKUSHIMA4_SAVE_PERSISTENCE.md
Pins: root base 36b868391e62cccf37d992aa2f796f3cc9c6dc31 (read contracts
read-only), native base 88188a1e3d687132baf4c2ab7c01b3c752ef4500 (the
#161 floor-1 pin). Downstream consumer #161. Higher floors and species
admission are out of scope for that slice.

## Method and safety

- Adapter validates the pin record fail-closed (valid/invalid pins, hash
  mismatch, missing contract sections, absent provider, malformed input).
- 9 focused tests green. No invented providers or callsites: every citation
  above was read from the pinned sources.
- No runtime run (tooling pin-discovery); captain safety #632 engages nothing.
