# Landing decision: #730 ext table + #755 follow-on (recovery 8c2b7615)

Bounded decision packet for the coordinator/integrator: exact producer pins,
conflict pre-analysis and destination for landing the challenge stage-table
extension that unblocks #537 P1 boot. No merge performed here; no shared or
native files touched; no runtime; no ADMIT. All six arena gates UNTESTED.

## Producer pins (verified read-only against the native repo)

- Ext commit `5e871f88b0493d79d0ed800d923fec84367fe056`
  (branch `codex/autofill-challenge-stage-table-extension-native`): 3 pure-add
  files, 372 insertions, 0 deletions:
  - `pc_port/pc_p2_challenge_stages_ext.h` (blob `6d47f50987be`)
  - `pc_port/pc_p2_challenge_stages_ext.cpp` (blob `ca117202380e`)
  - `tools/p2_challenge_stage_table_ext_fixture.cpp` (blob `9b8aaebbd4d6`)
- Follow-on lane `challenge-pc-bbft-followon` (#755, blocked gen 2 rev 3):
  owns `native/pc_port/pc_bbft.cpp` + `native/CMakeLists.txt` for the fallthrough +
  membership. No commits yet (blocked on rebase + ext presence + #186).

## Conflict pre-analysis (vs current wave-native tip)

- The three ext files are pure adds: they do not exist at the destination
  tip, and no live lane owns those paths. Landing = `cherry-pick -x
  5e871f88` (or equivalent single-commit port).
- `native/pc_port/pc_bbft.cpp` + `native/CMakeLists.txt` are held by the live
  blocked #755 lane: do NOT touch; the fallthrough + membership change stays
  with that owner after the coordinator rebase + #186 review.
- The ext commit is NOT an ancestor of the wave-native tip (verified
  `merge-base --is-ancestor` nonzero): genuinely unlanded, not a no-op.

## Ordered landing steps (for the coordinator/integrator)

1. Land the ext commit onto the destination line (pure-add port of the 3
   files above).
2. Resolve the #755 follow-on via its owner: coordinator rebase + #186
   shared-hook review, then the pc_bbft.cpp fallthrough + CMakeLists
   membership change.
3. Re-run the #711 record fixture: 02tile must resolve TABLE (not
   ENGINE_ROW_PENDING) and boot READY; kusachi must stay READY.

## Downstream consumers

#537 P1 boot (blocked on the engine table row), recovery `8c2b7615` +
publication reviewer, #575/#576 placement providers (unaffected).

## Tests

`experimental/pikmin2_challenge_ext_landing_decision.py` exposes the pin
record, conflict matrix, ancestry check and packet assembler, all fail-closed.
`tests/test_pikmin2_challenge_ext_landing_decision.py`: shape/malformed
checks (synthetic) plus live read-only pin re-verification (no writes, no
builds, no merges).
