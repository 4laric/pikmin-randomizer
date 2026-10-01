# Restartable Beasts engineering supervisor (#314)

Owner: Codex using shared GitHub account 4laric. Depends on the
[#307 exit receiver](PIKMIN2_BEASTS_EXIT_RECEIVER.md). This is an opt-in Python
engineering API, not the player campaign launcher.

`experimental.pikmin2_beasts_supervisor.supervise(ledger, root=..., assets=...,
exe=..., output=..., timeout=240)` reads the active floor-2 ledger and starts the
existing exit42 fixture with that boundary token and generation population.
The fixture currently supports only health 1, twenty leaf Reds, and both Violet
flowers. Other parties and suppressed generation are rejected before an intent
is written. This prevents quietly replacing a persisted party with fixture defaults.

The fixed `ledger.directory/beasts-supervisor/runner.lock` serializes callers.
Before staging, an atomic `request.json` records the original launch state. The
runtime's `prepared` callback records the exact absolute stage directory before
native process creation. The request remains as a fence against another launch;
it is recovery metadata, not a second authoritative campaign save.

Call `supervise(ledger)` after reopening the ledger to recover. An existing
request always takes precedence over launch arguments. With no completed
`acceptance.json`, the result is `pending_or_uncertain` and no process starts.
This covers crashes before staging, between staging and launch, during execution,
and before the final report. A failed or changed acceptance raises an error and
does not advance the ledger. There is deliberately no automatic reset/relaunch:
inspect the original run and process before deciding how to recover a failed
engineering attempt. Deleting the request defeats this fence.

With valid evidence, the existing hash-checking receiver applies the transfer
through the single authoritative `surface-ledger.json`. Recovery after a lost
post-commit response replays the same event, preserving revision and surface.
The result is `floor3_stopped`, with `native_floor3_ready=false`. The floor-3
assembly survey in #311 is a party-only engineering preview and does not grant
campaign-entry capability.

This lock coordinates this supervisor only. Other ledger writers retain their
own OS lock and revision/token checks; a conflicting mutation rejects receipt.
Evidence is hash-correlated, not cryptographically authenticated. Disk loss,
manual request removal, arbitrary file tampering and full campaign resume are
outside this guarantee. The runtime writes acceptance with the existing atomic
write helper so recovery cannot mistake a partially written report for success.

## Validation

Focused tests cover first start/reopen, pre-stage and post-stage interruption,
incomplete and failed evidence, a lost post-commit response, concurrent start,
and rejection of an unsupported incoming party. The wider receiver, boundary,
transfer, party, generation, reference-checkpoint and surface suites are run too.

The actual native smoke is stored locally in `output/beasts314-final` under the
private cave worktree. It creates an engineering ledger from the reference test
audit (placeholder content/campaign identities), advances its reference floor 1
to floor 2, and calls the supervisor against the frozen #307 native executable.
It does not represent a native floor-1 playthrough or a full campaign content
manifest. The smoke then reopens the ledger, verifies exact replay and unchanged
suspended surface, and writes `supervisor.json`. No disc assets, executable,
generated overlay or runtime save are committed.

Results: **83 tests and 143 subtests passed** across those suites. Independent
read-only review found no blocker within this one-attempt scope and separately
ran the supervisor/receiver tests (12 tests, 7 subtests).

Actual run `runs/ff2d80e0b86f4aeb8572ab10ea6e10e5` passed with native exit **42**;
the ledger stopped at floor 3/revision 3 and a reopened supervisor returned the
same result without changing ledger bytes. Native source remains frozen at
`e23986231d81b6f275d9fd900610c1bd82105b31`.

| Artifact | SHA256 |
|---|---|
| Frozen #307 executable | `fc7723b48e7396d97da2da24c4256ad0f3361dd33aeb62152a94b93ed2e8ff12` |
| Native log | `9d7efa92ee763adf8d1effb044885e82e199e7749f82b6b609981e3a9df29370` |
| Native transfer | `dfa79eae0ad72a30879d1d1d0f65cc1a662580459f6647785bb337c1ad96a42f` |
