# PC-BBFT follow-on anchor/ownership audit (lane `pc-bbft-followon-anchor-diagnosis`)

Lane `pc-bbft-followon-anchor-diagnosis` (attempt
`91dc1f3f406d8ba69de9f71cda4e50c54090e374c94a4dcfd99c865c28475ec7`,
generation 2) answers prerequisite recovery request
`2a21d6ed0bdeb96b071a67947b6a48536ec2a47b49737b845516ec6e393581f6` on
issue #775 for downstream `p2-challenge-ch-nari-03toy-p1` (#746).

Read-only diagnosis. No engine edits, no builds, no runtime launches, no
ADMIT. Nothing in this lane touches issues #755, #730, #769, or #775 via
`gh`; all findings live in the packet, this report, and workflow state.

## Method

`experimental/pc_bbft_followon_anchor_audit.py` verifies, fail-closed,
against explicit native revs:

- `symbol_in_blob(repo, rev, "pc_port/pc_bbft.cpp",
  "pc_p2_challenge_stage_lookup")` — the engine-table anchor #755 needs.
- `blob_present(repo, rev, <ext file>)` for
  `pc_port/pc_p2_challenge_stages_ext.h` and
  `pc_port/pc_p2_challenge_stages_ext.cpp` — the #730 files #755 needs.
- `anchor_status()` maps the two booleans to a resume disposition;
  `ownership_record()` records lane liveness; `packet()` hashes the result.
- Anything unverifiable is recorded ABSENT, never invented.

## Anchor verdicts (verified 2026-09-18)

1. Pinned base `a95040b66a0ffc9cdbfc649502569a29e66949a7`
   (`native/`): `pc_p2_challenge_stage_lookup` ABSENT under `pc_port/`,
   both ext files ABSENT. Disposition: **anchor-absent** — neither the
   lookup nor the ext files are on the pinned base.
2. Wave tip `codex/autofill-challenge-hostmode-engine-hook-native`
   (`db245877`): lookup PRESENT in `pc_port/pc_bbft.cpp`, ext files
   ABSENT. Disposition: **anchor-split** (lookup half only).
3. Extension files exist ONLY in the #730 private worktree branch
   `challenge-stage-table-extension-native` at `1bbf9eeb...`
   (`output/workflow/autofill/prerequisites/challenge-stage-table-extension-native-native`,
   `pc_port/pc_p2_challenge_stages_ext.{h,cpp}` present). #730 is `done`
   (gen 2, rev 4) but the files are unintegrated.

## #186 review state (verified 2026-09-18)

- #730 review packet ACCEPTED; the follow-on is APPROVED (2026-09-17):
  one-line `pc_bbft.cpp` fallthrough to the ext lookup on engine miss
  plus `CMakeLists` `pikmin_pc` membership for the ext TU, authored
  against the current line carrying the #718/#722/#728 seams, with a
  leased rebuild, a guarded run, then an implementation handoff.
  Decision: `output/workflow/integration-recovery/species-owner/stagetable730-186-decision.md`.
- #718 decision stands: `pc_bbft.cpp` is shared, so the additive call
  site and CMake membership need #186 review before any shared-line
  landing (already covered for the #730 follow-on by the approval above).

## Ownership (verified 2026-09-18)

- `challenge-pc-bbft-followon` (#755): `blocked`, gen 2 rev 3, worker
  `muse-l57`, PID 15336 DEAD. Not resumable in place.
- `nari-stage-table-rows-native` (#769): `blocked`, gen 2 rev 5, worker
  `muse-l56`, PID 16936 DEAD. Module + fixture are done/proven, but the
  lane is not resumable in place.
- `challenge-stage-table-extension-native` (#730): `done`; files exist
  only on its private branch, unintegrated.
- `p2-challenge-ch-nari-03toy-p1` (#746): `blocked`, gen 2 rev 4,
  waiting on the shared native row owner (#710) plus #186.

## Resume disposition for #746

No live resumable producer exists: both blocked prerequisite owners are
dead and no single line carries lookup + ext files. The exact
coordinator/integrator decision is:

1. Land the #730 ext files onto a lookup-carrying wave-tip line per the
   already-APPROVED #186 follow-on (one-line fallthrough + CMake
   membership, leased rebuild, guarded run).
2. Rebase `challenge-pc-bbft-followon` (#755) onto that line, then
   controller-recover it with a fresh worker (do not create a duplicate
   lane); same recovery for `nari-stage-table-rows-native` (#769), whose
   module + fixture need only the landing, not re-authorship.
3. Only then resume downstream `p2-challenge-ch-nari-03toy-p1` (#746).

The six challenge/flora gates remain UNTESTED and no flora engine/table
file was read or written. This lane stays inside its three owned files
and leaves issue #775 OPEN.
