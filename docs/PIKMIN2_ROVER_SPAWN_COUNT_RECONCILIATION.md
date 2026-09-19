# Rover spawn-count reconciliation (#699)

Lane `rover-spawn-count-reconciliation`, generation 2. Owner: Codex through
shared account `4laric`. Consumer: blocked
`p2-challenge-ch_mat_route_rover-p1` (#561, gen 6): with #695 integrated the
boot reaches P2_ROOM_READY, but the cave-entry spawn-count checkpoint rejects
the staged 60. Read-only analysis: no source/shared/native edits, no runtime,
no ADMIT. All six gates UNTESTED.

## 1. Staged intent (consistent; not the fault)

The staged count 60 is arithmetically consistent across every staged artifact:

- `p2-cave-entry.txt` (run-rover-10): `P2_CAVE_ENTRY_1 <32-hex> 1 1.0 60`
  plus 60 `species maturity` pairs (61 lines total), sha256
  `62323d7f5e15fe031da7786303ea9e3701e786a642ebc91802f0d1e6da4a4df0`.
- Arena override `arena-override.gen`: 60 `ikip` Pikmin records
  (20 Blue + 20 Red + 20 Yellow), sha256
  `8a5f18539202ca8939a36b095a93061cca756ecdf2c355fb8147522ffdd38a3d`.
- Lane marker template `markers.txt`: `P2_ROUTE_ROVER_SQUAD count=60`.
- Watcher `watch_boot.py` (`--expect-restores`, default 60): requires
  `restores >= 60` where a restore is one `P2_CAVE_RESTORE species=` line
  (file:24, file:52, file:62-64, file:72-74).

## 2. Engine checkpoint semantics (correct; not the fault)

Reference checkout is the consumer lane native tree at `8c7b97fd`
(read-only; family-owned, untouched):

- `pc_port/pc_p2_cave.cpp:92-93`: without the room preview, or without
  `p2-cave-entry.txt`, `pc_p2_cave_setup()` returns silently (no markers).
- `pc_port/pc_p2_cave.cpp:105`: `if(spawned.size()!=squad.size())invalid(
  "spawn count differs from checkpoint")` — the live `pikiMgr` alive count
  at setup time must equal the entry count, else abort. Called from
  `pc_port/pc_p2_preview.cpp:312` during preview setup.
- `pc_port/pc_p2_cave.cpp:114`: one `P2_CAVE_RESTORE` per squad member (a
  passing count-60 run emits exactly 60, matching the watcher).
- `pc_port/pc_p2_cave.cpp:144-145`: `P2_CAVE_READY` then
  `pc_p2_cave_generate_run()` (#129: `P2_CAVE_GENERATE_*` markers).

The checkpoint is correct restore-in-place design: it restores species/
maturity onto already-spawned Pikmin, it does not create them.

## 3. Observed failure (citations)

- run-rover-10 (entry staged): native.log sha256
  `908ea5f1b653e11c8cf4b50857821a4fef0ce13990617a91a272c105094cabfe`,
  line 819 `Invalid P2 cave entry: spawn count differs from checkpoint`
  (abort); 0 RESTORE, 0 GENERATE. Its `dataDir/stages/chal0/default.gen`
  is `arena-compact-nopr05.gen` (sha256
  `507120b371f0fc837423c324171c66c15b30b76c1c0baa3b5a5f1dfb9739cf62`),
  but the engine opened `dataDir/stages/chal0/default.gen` with size
  **14665** (log line 413), not the staged 23913: the DVD layer resolved
  the retail assets-tree file, so the run overlay was ineffective and the
  staged 60 Pikmin never spawned (no Piki squad markers in the log).
- run-rover-11 (entry deleted by `stage_run11.py:8`): native.log sha256
  `ece124c061dfb5a6e20045257b4cadf2300a062210503dc704737deb75c3a9c3`
  (the lane blocked-outcome evidence); 0 RESTORE, 0 GENERATE, 57 FPS,
  `P2_ROOM_READY`; setup returned silently, so the 60-restore checkpoint
  cannot pass by construction.
- Machine verdicts from the reserved checker: run-10
  `staging-path`, run-11 `entry-missing` (11 focused tests green).

## 4. Disposition: STAGING-PATH fault; exact correction

- The staged count 60 is right as roster intent; the engine checkpoint and
  the #129 generator are right as designed. The fault is the staged run
  composition: the arena overlay never reaches the engine (opened 14665 !=
  staged 23913), so at setup time live Pikmin (0) != entry (60) and the
  checkpoint aborts; deleting the entry only trades the abort for a silent
  skip with the same 0-restore outcome. Timing is secondary: setup snapshots
  live Pikmin at preview-init, before any post-setup spawn could help, and
  the #129 sidecar runs after the restore check by design.
- Exact correction (private candidate for owner review, no code change):
  restage the run so the engine loads the 60-Pikmin `arena-override.gen`
  (opened `default.gen` size must read 23913) AND restore
  `p2-cave-entry.txt` (count 60 + 60 pairs) into the run dir. Then the stage
  generator spawns 60 live Piki before setup, `spawned.size()==60` holds,
  60 RESTORE + `P2_CAVE_READY` + GENERATE markers emit, and the 60-restore
  watcher passes.
- Alternatives rejected: changing staged 60 (breaks the consistent intent);
  loosening the checkpoint bounds (bounds are correct); deleting the entry
  (already proven to yield 0 markers).
- Family-owner review: NO shared edit is needed or proposed. If the engine
  cannot be made to prefer the run overlay, the fallback is a #642-owner
  decision to defer the spawn-count check until post-generate — a shared-
  semantics change that must not be made by this lane.

## 5. Owner actions and packet

- #561 restage (consumer lane): effective overlay + entry restore; verify
  opened size 23913 and 60 RESTORE lines; resubmit the blocked outcome.
- #642/#129 owners: no code action required; review this candidate only.
- Downstream consumer: #561 (`p2-challenge-ch_mat_route_rover-p1`, gen 6).
- Lane commit (root base `36b86839`): checker + 11 tests + this doc.
  Guard reference only (no runtime): `scripts/p2_fixture_captain_guard.h`
  sha256 `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`.

## 6. Six-gate evidence (honest, review-only)

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED | cited, not claimed | natural (no claim) |
| 2. Autonomous movement and animation | UNTESTED | not in scope | natural (no claim) |
| 3. Attacks and receivers | UNTESTED | not in scope | natural (no claim) |
| 4. Death and corpse | UNTESTED | not in scope | natural (no claim) |
| 5. Actual transport and reward | UNTESTED | not in scope | natural (no claim) |
| 6. Cleanup and re-entry | UNTESTED | not in scope | natural (no claim) |
