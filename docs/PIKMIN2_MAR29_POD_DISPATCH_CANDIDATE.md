# Mar29 Pod dispatch candidate (#665)

Lane `mar29-pod-dispatch-candidate`, generation 2. Owner: Codex through
shared account `4laric`. Coordinator follow-up for stopped consumer
`shard-enemies-2-mar29-observer` (#375): transport_reward is blocked because
TEKI_Mar has no receipt hook in the shared Pod/preview dispatch chain.
Producer `enemies-2-mar29-receipt-provider` (#650) delivered
`pc_p2_mar_receipt.{h,cpp}` and filed the exact shared dispatch-arm patch;
this lane prepares the private scoped candidate and the integration-ready
packet for the single-writer integrator. No ADMIT.

## What this lane owns (new root files only)

- `experimental/pikmin2_mar29_pod_dispatch_candidate.py`: stdlib helper that
  applies the filed 5-line arm onto a PRIVATE copy of `pc_p2_preview.cpp`,
  verifies hook-registration grammar (include, arm, receipt string, call,
  order, existing arms intact), and emits a hashed packet. Fail-closed;
  writes nothing on any drift.
- `tests/test_pikmin2_mar29_pod_dispatch_candidate.py`: 9 focused tests
  (clean apply + verify, order, existing intact, double-apply refused,
  missing anchors refused, empty refused, no-write on failure, overwrite
  refused, real pinned base applies). All pass.
- This file.

No maintained/shared/family edits committed by this lane; no native edits at
all. No runtime, no builds.

## Reused #650 inputs (read-only, not re-derived)

- Dispatch patch: `p2-preview-mar-dispatch-186-request.md` (5 added lines on
  `pc_p2_preview.cpp` at native base `7b9ecaa6`, sha prefix `14607674`).
- Adapter `pc_p2_mar_receipt.{h,cpp}` + fixture (hashes recorded in the
  packet; verified present, not modified).

## Candidate evidence (private out/candidate)

- `pc_p2_preview.cpp.candidate`: base preview + the 5-line arm, nothing
  else. SHA-256 recorded in the packet.
- `mar29-pod-dispatch-packet.json`: exact base/patch/adapter hashes, hook
  findings, the #186 owner decision still needed, downstream #375, all six
  gates UNTESTED.

## Owner decision needed (#186)

Apply the 5 added lines verbatim to `pc_port/pc_p2_preview.cpp`, or amend
with exact replacement text, or decline with reason. On approval the
integrator lands it (single writer), rebuilds under lease, and the #375
consumer proceeds. This packet does not grant approval and changes no shared
file.

## Checks

- `py -3.12 -m pytest tests/test_pikmin2_mar29_pod_dispatch_candidate.py -q`
  -> 9 passed + 5 subtests.
- Real pinned base applies cleanly with hook findings all true.
