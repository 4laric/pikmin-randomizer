# Throughput operations

Implementation: #524–#527. Owner: Codex through shared GitHub account `4laric`.
This extends [the workflow operating contract](PIKMIN2_WORKFLOW.md) and
[controller contract](PIKMIN2_CONTROLLER.md); it does not replace their fencing,
issue-first ownership, resource leases, or gameplay acceptance checks.

Use the one canonical registry at `C:/Users/alari/pikmin-randomizer/output/workflow/registry.sqlite3`.
Keep the existing controller as the **sole automatic dispatcher**. These APIs
record assignments and launch intents; they do not authorize another supervisor.
Reused workers resume their existing registered OpenCode sessions. Never invent a
session, PID, issue, observed result, or source hash to make a request succeed.

## CLI and operating limits

Commands take keyword arguments from a UTF-8 JSON object. Save each request under
ignored `output/`, then invoke, for example:

```powershell
py -3.12 scripts/pikmin2_workflow.py --root C:/Users/alari/pikmin-randomizer --request output/workflow/requests/request.json set-workstream
py -3.12 scripts/pikmin2_workflow.py --root C:/Users/alari/pikmin-randomizer status
```

Request paths are relative to the calling shell; paths inside requests resolve
against `--root`. Examples below are schemas with illustrative values: replace
lane IDs, issues, revisions, paths, SHA-256 hashes, and full source commits with
fresh verified values. Do not replay placeholder requests against production.
Read current generation/revision before each fenced mutation.

The controller configuration enables the adapter with this fragment; retain the
rest of the existing configuration and its configured paid Muse model identifiers:

```json
{
  "interval": 15,
  "ram_high": 90,
  "ram_low": 87,
  "throughput": {
    "enabled": true,
    "provisional_qa": true,
    "capture_costs": true
  }
}
```

Pool assignment independently refuses new work at RAM >=90%. Hysteresis resumes
controller dispatch at <=87%. RAM is a ceiling, not a utilization target. Preserve
the registry's **two heavy-build slots**; assigning a heavy job reserves capacity
but does not replace the actual exclusive build lease. Private runtimes remain
exempt from shared-runtime reservations. The existing fenced runner dispatches
at most one runner per tick; ready capacity is filled over successive ticks.
Configuration is read when the controller starts; coordinate any configuration
restart with its existing owner. Per-lane launch specifications below are stored
in the registry and do not need a service restart.

## 1. Name an integration owner for each workstream

Keep cave and species integration independently owned. `set-workstream` requires
an existing, unfinished, confirmed-live owner lane. Replacing another owner is
refused while its recorded process is live or uninspectable.

```json
{"name":"caves","owner_lane":"cave-integrator","lanes":["cave-48","cave-49","cave-50"]}
```

Create a corresponding `species` workstream with its actual integrator and
members. Explicit membership makes batching ownership checkable. Repeating the
same owner can update membership; it does not transfer source ownership or start
workers. A pool job cannot be assigned while its workstream owner is stopped.

## 2. Reuse a pool of paid review and repair workers

First create an issue with exact scope and acceptance, assign it to `4laric`, and
record Codex as implementation owner. Existing lane claims still govern file
ownership. Authorize the roles/capabilities of a worker that already owns a
registered lane using `register-pool-worker`:

```json
{"worker_id":"paid-reviewer-1","roles":["review","repair"],"capabilities":["shared-review","evidence-repair"],"authorized_by":"User-approved throughput implementation; Codex through 4laric"}
```

Roles are `implementation`, `review`, `repair`, `integration`, and `qa`.
Capabilities are explicit matching strings. Registration alone does not dispatch.

After the old slice is done, has an applied integration/review disposition, its
assignment is completed, and its worker/resources/launch are stopped, use
`provision-pool-lane` to create a bounded next slice in the **same session**:

```json
{
  "previous_lane":"completed-review-1",
  "record":{
    "lane":"review-next-1","issue":999,
    "owner":"Codex through 4laric","scope":"Review the named shared-file handoff",
    "target_level":"review","next_action":"Apply the source-bound review disposition",
    "milestone":"throughput","owned_files":["output/review-next-1/report.md"],
    "acceptance":["Review disposition applied to the exact submitted handoff"],
    "root":{"base":"<40-hex>","commits":[],"head":"<same-40-hex>","dirty":"","worktree":"output/review-next-1"},
    "native":null
  }
}
```

This API inherits the historical worker, session, and process identity; do not
supply `pid`, `task_id`, or `worker_id`. Its source record is the actual prepared
worktree, and acceptance/owned files must match the issue. Native work includes
a complete native source record and the usual private build/worktree isolation.

Prepare the worktree, brief, and provider configuration, then call
`configure-lane-launch`:

```json
{"key":"review-next-1","root":"output/review-next-1","output":"output/review-next-1-run","brief":"output/review-next-1-brief.md","config":"output/paid-worker-config.json","legacy_supervisors":[]}
```

The launch root must match the lane's recorded root worktree. Brief/config must
exist. Record real legacy supervisor identities when applicable; a live supervisor
continues to block dispatch. Enqueue the scoped work with `enqueue-job`:

```json
{"record":{"id":"review-next-1-v1","lane":"review-next-1","issue":999,"workstream":"caves","role":"review","instruction":"Review the pinned shared-file change and apply its validated disposition. Report evidence and remaining work in the issue.","capabilities":["shared-review"],"heavy":false}}
```

The existing controller selects eligible jobs, persists a launch intent, and
resumes the same session. Jobs target the registered worker; this is not arbitrary
work stealing. Selection prioritizes repair, review, integration, QA, then
implementation and respects dependencies, live owners, and heavy reservations.
Manual API equivalents are `assign_job(worker_id, ram_percent)` and
`plan_assignment(assignment_id, models, ram_percent)`; the latter atomically
validates and records an intent, not a process launch. Use fresh measured RAM.

## 3. Complete work by applying its disposition

A review report alone does not complete a pool assignment. Review-only lanes use
the existing `finish` review-ready and `accept-review` flow; implementation lanes
need a validated handoff and normal integration receipt. Once the runner stops,
the controller can complete its assignment using hashed evidence. The manual API
is `complete_assignment(assignment_id, evidence)`, where evidence has `path` and
`sha256`. It refuses completion without a done lane, applied disposition, matching
bound execution generation, and stopped worker/protected resources.

For a requested shared-file review, `dispose-review` applies a new validated
handoff instead of leaving an approval in a disconnected report:

```json
{"key":"cave-50","generation":1,"revision":8,"version":"shared-review-1","handoff_sha256":"<submitted-handoff-sha256>","file":"native/pc_port/example.cpp","status":"approved","reviewer":"Codex through 4laric; focused reviewer","evidence":{"path":"output/reviews/cave-50-review.txt","sha256":"<review-evidence-sha256>"}}
```

`status` is `approved` or `rejected`; the file must identify exactly one existing
shared review. The source handoff hash, lane generation/revision, and stopped-owner
checks fence the operation. Blocked lanes require supported reconciliation first.
The resulting handoff is revalidated with all original slice/gate checks and stays
`handoff_ready`; rejection remains a pending integration review. Replay of an
identical current disposition is idempotent; conflicting or superseded replay is
refused. Subsequent review requests use the **new** handoff hash and revision.

## 4. Wake on changes, with a 15-second fallback

The controller waits for meaningful registry changes and configured receipt,
mailbox, configuration, or WAKE-file changes rather than a fixed five-minute sleep.
The bounded waiter observes change tokens at up to half-second intervals; the
default fallback is 15 seconds. It is not an OS notification service and does not
wake from its own read-only polling.

An integrator may use `wait-events` with this request:

```json
{"timeout":15,"paths":["output/deepseek-wave/inbox"],"cursor":"<cursor-from-previous-response>"}
```

Omit `cursor` for the initial wait. Responses contain `reason` (`changed`,
`timeout`, or `stopped`) and the next `cursor`. Timeout is 0–60 seconds. Inspect
fresh state after a change and retain the cursor for the next wait. This command
only waits; it does not dispatch or claim integration ownership.

## 5. Run provisional QA against frozen candidates

A completed implementation handoff can publish a runtime build before integration
bookkeeping is finished. `publish-candidate` requires a fully validated runtime
handoff, exact root/native source records, successful private build and no-work
Ninja evidence, executable hash, and applicable fixture provenance/adoption:

```json
{"key":"cave-50","generation":1,"revision":9,"version":"cave-candidate-v1"}
```

The returned candidate contains a `pin` and a `snapshot` of source/build/evidence
records. Subscribe the parked QA lane with `subscribe-candidate-qa`:

```json
{"key":"cave-51","generation":1,"revision":4,"producer":"cave-50","session_id":"<existing-session-id-without-opencode-prefix>"}
```

The session must match the registered `opencode:<session>` task. The controller
uses `candidate-qa-ready` and atomic
`queue_candidate_qa(key, generation, revision, pin, instruction, models)` to commit
one claim and one launch intent per pin. Instructions must identify the pin.
Unbound claims can be recovered; linked intents use the existing runner. Do not
add a parallel QA dispatcher or clear the lane's real integration dependencies.

The resumed lane reports `record-candidate-qa` with its **current bound generation**:

```json
{"key":"cave-51","generation":2,"pin":"<published-candidate-pin>","result":"PASS","evidence":{"path":"output/cave-51-run/qa.txt","sha256":"<qa-evidence-sha256>"}}
```

Results are `PASS`, `FAIL`, or `BLOCKED`. They are explicitly **provisional**, cannot
ADMIT an identity, cannot grant integration, and do not satisfy the real dependency.
Publishing a superseding candidate invalidates previous results; stale-pin results
are refused. Fresh runtime work still adopts the current starting-Pikmin overlay,
new private arena, and 960×540 centred-window fixture baseline. A copied certificate
is not fresh observed gameplay.

## 6. Freeze evidence once; refuse silent drift

`snapshot-handoff` archives a validated handoff and all referenced evidence:

```json
{"key":"cave-50","generation":1,"revision":9,"version":"handoff-v1"}
```

Bundles live under `output/workflow/delivery/` and use content-addressed filenames.
Existing bytes are checked rather than overwritten. The original fixture
certificate is retained; a marked derivative adds the copied executable's path
with the same hash, so full provenance validation still applies. Snapshot replay
checks every retained file hash. Original log rotation does not destroy the frozen
evidence. Changed frozen bytes, conflicting versions, and stale ownership fail
closed. New evidence requires a new handoff/version, never an edited old bundle.

To make normal integration validate the frozen copy, the lane owner/integrator
submits the returned `handoff.path` through the existing `handoff` command with
the current generation/revision. Do this while the slice is `handoff_ready` or
`integrating`, after coordinating with its stopped producer; do not reopen done
lanes. Archiving alone leaves the original submission pointer unchanged.

```json
{"key":"cave-50","generation":1,"revision":9,"path":"output/workflow/delivery/<content-hash>/handoff.json"}
```

The normal validator then consumes the copied evidence and still checks the
same source identity, shared reviews, fixture provenance and slice criteria.

## 7. Batch compatible integrations and measure useful output

A named live integrator may claim up to 16 fully reviewed `handoff_ready` slices
from its own workstream with `batch-claim`:

```json
{"batch_id":"caves-batch-1","workstream":"caves","integrator":"cave-integrator","generation":1,"revision":5,"candidates":[{"key":"cave-48","generation":1,"revision":7},{"key":"cave-50","generation":1,"revision":9}]}
```

The claim refuses overlapping changed files (including directory prefixes), other
batch claims, unresolved reviews, and stale ownership. It records immutable source
and handoff pins. It does not merge files or perform a build. The integrator still
holds the appropriate build/export lease and follows the normal integration policy.

Record a common verified build with `batch-record-build`:

```json
{"batch_id":"caves-batch-1","integrator":"cave-integrator","generation":1,"revision":1,"sources":{"root":{"base":"<40-hex>","commits":[],"head":"<same-40-hex>","dirty":"","worktree":"output/cave-integration"},"native":{"base":"<40-hex>","commits":[],"head":"<same-40-hex>","dirty":"","worktree":"output/native-cave-integration"}},"evidence":{"build":{"path":"output/cave-integration-build/build.log","sha256":"<sha256>"},"dry_run":{"path":"output/cave-integration-build/dry-run.log","sha256":"<sha256>"}}}
```

After claim, `revision` refers to the **batch revision**, not integrator lane
revision. If a candidate fails, `batch-isolate` takes `batch_id`, `integrator`,
`generation`, current batch `revision`, `candidate` lane ID, and `reason`. This
supersedes shared builds containing that candidate; record a fresh build of the
remaining pins. `batch-close` takes the same ownership fields without candidate or
reason. Closing does not grant per-lane integration or ADMIT: normal validated
receipts remain necessary.

`throughput-status` accepts `window_seconds` (default 3600) and optional fresh
`ram_percent`. The controller writes `throughput.json` and `throughput.html` in its
configured controller directory; the HTML view refreshes every 15 seconds. Metrics
include integrated implementation slices/hour, oldest ready/review/integrating
handoff, dependency-ready waiting time, heavy-slot lease utilization, staffing
recommendations, and reported cost per accepted slice. Acknowledged reviews are
not counted as accepted implementation. Build utilization measures lease time,
not CPU activity; missing history and prices remain unknown.

Positive provider-reported `step_finish` cost estimates are ingested from known
run logs when available. Manual `report-cost` uses:

```json
{"event_id":"provider-invoice-event-unique-id","lane":"cave-50","amount":0.42,"currency":"USD"}
```

An optional `at` is an epoch timestamp. `report-cost-batch` takes `{"events":[...]}`
and ingests atomically; reuse stable IDs to prevent duplicates. Currency totals
remain separate. Missing accepted-lane costs make the cost-per-slice value unknown,
not zero. Provider estimates are not reconciled billing totals.

Use queue age and role demand to add authorized workers where ready work is
accumulating. Add implementation, review, repair, integration, and QA capacity as
appropriate while respecting each workstream's one integration writer, 90% RAM
ceiling, and two shared heavy-build slots.
