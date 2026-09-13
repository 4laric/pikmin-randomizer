# Native diagnostic boundary correlation (#294)

Owner: Codex using shared 4laric account. This is the save/handoff track paired
with the independent floor3 track #295.

The host writes `P2_BEASTS_BOUNDARY_1` and a 64-hex token into the hashed private
input `p2-beasts-boundary.txt`. The native fixture validates that input and emits
matching begin/end markers around readiness, conversions and the final party
snapshot. The host requires exactly those two markers, in order, with the
evidence between them and the final PASS afterward.

Pass `--boundary-token` from the persisted active floor2 checkpoint. Without
that option, the runner generates a fresh diagnostic-only token. The new
`bound_checkpoint_witnesses` bridge verifies the native markers against the
reference checkpoint token before mapping any events. The historical unbound
bridge remains available for old logs and must not substitute for this check.

This prevents accidentally committing a different run's diagnostics against a
checkpoint. It does not authenticate logs cryptographically: the host supplies
the token and a caller could fabricate matching text. Reports distinguish
`native_boundary_correlated=true` from `native_handoff_authenticated=false`.
No native production transfer format, actual cave-exit action or automatic
launcher has been added. Save/engine review remains required before integration.

Native fixture candidate: `5ffc1071b8f1fa7719dea1c337eefbef82877f7f`.
Private link completed with no pending production build work before/after.
Executable SHA256:
`a9bf055832936810221658c02012fe2c2390a00e6d42825abb49f57eff14b955`.

Fresh native run:
`output/beasts294-final/runs/7d9cc4642b014397a6a4e282c7fe4e5b`.
Token `7176b14098dc689a33705a8851472974da35affdec8c867bd8cb4508726d0d63`
was read from the persisted floor2 ledger before launch. Native conversion and
party evidence passed, then the bound bridge advanced that ledger to floor3.
Reopening and exact replay preserved the committed state. The initial floor1
boundary remains declared engineering input, not an actual native descent.

Log SHA256:
`dfa022a07b117becd26128452282b609bf5ef9f815997faed68db5cf548cd87f`.
Commit/replay report: `output/beasts294-final/replay.json`.
The runner checks unchanged input/executable hashes, zero rewards and unchanged
repairs. Focused boundary, ledger, surface/campaign, reference, runtime and party
suites passed 74 tests and 122 subtests, including wrong/missing/duplicate and
out-of-order markers. Actual exit interaction, native attestation and playable
floor3 remain open.
