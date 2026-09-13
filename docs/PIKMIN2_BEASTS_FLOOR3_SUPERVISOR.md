# Restartable floor3 terminal supervisor (#329)

Owner: Codex using shared4laric account. Requires host #326 and native/runtime
#328. This is an explicit engineering API that intentionally induces a terminal
fixture condition; it is not the player launcher or a natural combat test.

Prepare a fresh checkpoint-bound stage with `stage_checkpoint`, then select
`extinction` or `knockout` with `pikmin2_beasts_floor3_failure_runtime.arm`.
Call `pikmin2_beasts_floor3_supervisor.supervise(ledger, stage=stage, exe=exe)`.
It verifies the original checkpoint/token and encoded party, rejects an already
used stage, and records the exact stage, executable, hashes and original ledger
state before invoking native. Both supervisors share the existing fixed
`beasts-supervisor/runner.lock`; floor3 keeps `floor3-request.json` beside the
floor2 request. The request is recovery metadata, not a second campaign save.

Reopen using `supervise(ledger)` alone. Existing requests take precedence over
new arguments. Missing acceptance reports `pending_or_uncertain` and never starts
another process. A valid exit42 report goes through the #323 receiver and locked
ledger transition. Exact replay after a lost commit response returns the terminal
state without changing its bytes. Changed pinned stage/executable data is rejected.
There is no automatic launch retry or reset of an uncertain attempt.

The native fixture runtime now atomically publishes `acceptance.json`, using the
existing host write helper. The older floor2 supervisor also reports `failed`
when an exact replay observes a later terminal floor3 checkpoint; it previously
labelled that latest state `floor3_stopped`. No additional event or reward is
created by either replay.

## Validation

**105 tests, 210 subtests passed** across the new supervisor and affected cave
boundary, ledger, party, reference, entry and native-runtime evidence suites.
New cases cover launch-once/reopen, conflicting reentry arguments, interrupted
process, lost post-commit response, stage mismatch, shared lock contention and
the older supervisor's downstream failure report.
Independent read-only review found no blocker in the one-attempt, per-ledger
scope and separately ran 20 tests/29 subtests.

Two fresh native runs were launched by the supervisor itself from separate
private copies of the actual #314 floor3 checkpoint:

| Reason | Run under output/beasts329 |
|---|---|
| Extinction | `extinction/runs/ea1e810cd93a49c499262e74658bb316` |
| Knockout | `knockout/runs/4a824e984b234ac29b048eed7d20025c` |

Both returned exit42 and committed failed floor3, with unchanged suspended
surface and original source ledger. Reopening each supervisor produced an equal
result and byte-identical ledger. Each reason directory contains `supervisor.json`
and its pinned request; run `acceptance.json` contains full input/log/transfer
hashes. The source checkpoint uses the documented engineering reference audit
and placeholder identities, not a complete playable campaign content manifest.

Both use the frozen #324 native candidate `a9627bebf79445dfff0253992a1f72e0926d955a`,
fixture SHA256 `5767229bc44683ec20e294ff791e61ee99d625f40817a7c24061b928298f7a79`.
No native source or executable was changed by this supervisor implementation.
The private root combines #326 and #328; the inherited cave.cpp conflict was
resolved to the complete frozen #328 version. Integration should merge those
parents before reviewing this supervisor delta.

Still open: general floor3 player supervision, natural failure/retreat recovery,
successful floor4 descent, full roster/treasure hauling and complete cave resume.
The evidence remains unsigned hash correlation; deleting the intent or manually
launching another writer bypasses this API's one-attempt fence.
