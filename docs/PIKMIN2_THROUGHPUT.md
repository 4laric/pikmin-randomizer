# Throughput operations

Planning backpressure defaults to four waiting integration handoffs or an oldest
handoff age of one hour. A single fresh handoff does not pause planning when
workers are available and refill demand remains. `pause_integration_depth` and
`pause_integration_age_seconds` override these thresholds. The dashboard reports
the helper target reason; worker reservations and the bounded helper cap still apply.

Exact-pin handoffs isolated by a batch are a separate repair backlog, excluded
from actionable integration age/depth, oldest-handoff metrics and repeated
integration support reviews. The dashboard retains their age and isolation reason.
The controller resumes the existing stopped owner within its recorded scope,
at most twice, to prepare a self-contained replacement against the destination
pins. Live/unknown workers, protected resources and open integration claims remain
fenced. Binding rechecks isolation pins and archives the rejected handoff before
starting a new generation. Changed handoff pins return to normal validation;
exhausted repairs require explicit adjudication. A repair is never acceptance.

## Parallel planning pool (#581)

Planner intents waiting three minutes enter FIFO dispatch ahead of newer helpers,
regardless of discovery priority; execution and recovery work retain precedence.
`planner_fairness_seconds` on the controller config adjusts this threshold.

Accepted, hash-verified no-work reports suspend repeat discovery while their named
lane/issue inputs remain unchanged. Source pins, dependency lists and meaningful
completion/blockage transitions wake them; heartbeat, generation and revision
churn do not. Reports without named inputs use non-planner workflow state.
`planner_pool.no_work_recheck_seconds` defaults to one hour for changes recorded
only outside the local registry, such as GitHub issue updates. Active turns finish
normally. The dashboard lists sleeping scopes, dependencies and recheck times.
When a missing provider has been promoted into a concrete job, configure that
helper's `prerequisite_lanes` with its canonical lane IDs. These explicit links
supersede narrative inference and periodic retries: discovery waits until each
named job is done with integration or an accepted review disposition. Missing or
merely `done` lanes without acceptance remain blocked. The dashboard exposes each
job's owner, issue, state and next action. A newly completed prerequisite wakes
the partition even when its old no-work report never named that job.
Pending non-helper review reports also wake their registered integration owner
for an explicit evidence-based disposition; they no longer wait only for a source
handoff to trigger the owner. Review acceptance never substitutes for integration.
In parallel mode the publication coordinator waits for a new undispositioned
proposal in the configured inboxes, or a manifest error, instead of waking just
because the executable queue is empty.

Verified no-work reports without an unfinished linked producer also create durable
prerequisite requests automatically. These wake the same coordinator even without
a proposal. It handles at most three requests per turn: reuse an existing owner,
or create an assigned bounded issue and private source/launch proofs, publish via
`merge_proposals`, then record `linked` through `workflow.prerequisite_queue.resolve`.
Runtime links require no controller-config edit. Multiple partitions may share
one producer; normal ownership validation and dispatch still apply. This is a
narrow exception to the coordinator's publication-only role, authorizing provider
job preparation, not source implementation or independent worker launches.

Run the disposition CLI through the controller's checkout (the rendered instruction gives the absolute form):
`<python> <checkout>/scripts/workflow_module.py prerequisite_queue --root <canonical-root> --request <private-json>`.
The JSON contains `coordinator`, `generation`, `request_id`, `outcome` (`linked` or
`no_action`), `lanes`, `reason`, and hashed `evidence`. Only the live configured
coordinator may disposition a still-current report. A link must name an existing
non-planner lane or a published spec. `no_action` needs a concrete evidence-backed
reason, not an outside-my-partition deferral; changed inputs reopen consideration.
Two unanswered turns leave an explicit exhausted request in diagnostics instead
of silently spending on the same preparation forever. Existing active producers
are never duplicated. Requests and links survive controller restarts.

`throughput.autofill.planner_pool` configures bounded helper turns,
partitioned into enemy acceptance/provider gaps, dungeons, and overworld/challenge.
Each entry in `helpers` supplies a unique `scope`, private immutable autofill
`template` path and its `sha256`. Templates are issue-backed, non-heavy reviews
with private clean planning worktrees and no native implementation source.

The controller derives a helper target from ready-backlog deficit, available
approved stopped workers, `items_per_helper` (live: 3), `max_active` (live: 24), and
`reserve_workers` (2). Ready implementation consumes workers first. It provisions
at most one helper per tick through ordinary ownership/launch checks. Scopes cannot
overlap themselves; cycle IDs and stored specs make restart replay idempotent.
In deficit mode, a full ready backlog suppresses new helpers. Idle-capacity mode
instead grows planning to the lesser of the configured maximum, distinct demanded
partitions, and idle plus active helper capacity minus unclaimed ready work and
the execution reserve. There is no additional hard-coded three-helper ceiling.
For example, nine idle workers and three active helpers with a reserve of two
permit ten helpers. Eight newly ready unclaimed jobs lower that target to two.
Running bounded turns finish normally as the target shrinks.
Helper refill is paused when the integration queue has depth at least four or an
item older than one hour. A ready item with only one idle worker also pauses refill.
`cooldown_seconds` (live: 300) prevents immediate repeat planning of one partition.

Helpers stage immutable complete spec proposals in separate partition inboxes,
finish `review-ready` with a hashed report, and perform no source implementation,
build, dispatch, manifest publication or ADMIT. After the worker and protected
children stop, the controller acknowledges only the planning report; ordinary
pool completion returns the worker for implementation. This does not accept any
proposed slice or increment accepted implementation/gameplay metrics.

The existing planner remains the sole coordinator and manifest writer. It reads
helper proposals and calls canonical `workflow.planner_pool.merge_proposals(reg,
manifest_path, proposal_path)`. Publication verifies fresh issue assignment and
body hashes, private source/launch proofs, active ownership, and pending proposal
issue/lane/file/worktree/output collisions. Appends are serialized with registry
transactions, detect manifest changes, preserve a backup and replay unchanged
IDs without duplication. Invalid proposals remain unpublished. The coordinator
does not independently create scopes owned by helpers.

Dashboard helper counts are separate from active enemy implementation. Lease-only
build mode also applies at autofill readiness and provisioning, so preparation
cannot silently consume build slots before the ordinary scheduler sees it.

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
controller dispatch at <=87%. Fill available capacity with eligible work, following
**existing work > new content > idle**. New content jobs set `work_class: "expansion"`;
omitted fields and legacy/dependency/recovery intents default to `existing`.
Work class precedes role priority. Running or blocked existing work does not
prevent independent expansion from using spare capacity; live workers are not
preempted. See the [complete content lane plan](PIKMIN_CONTENT_IMPORT_LANES.md). Preserve
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

For a requested shared-file review, `dispose-review` records an authenticated
approvals-ledger row and applies a new validated handoff instead of leaving an
approval in a disconnected report:

```json
{"key":"cave-50","generation":1,"revision":8,"version":"shared-review-1","handoff_sha256":"<submitted-handoff-sha256>","file":"native/pc_port/example.cpp","status":"approved","reviewer":"species-integration-owner","reviewer_generation":42,"evidence":{"path":"output/reviews/cave-50-review.txt","sha256":"<review-evidence-sha256>"}}
```

`status` is `approved` or `rejected`; the file must identify exactly one existing
shared review. `reviewer`/`reviewer_generation` name the caller's own live
registered lane, and the command must run inside that lane's launch session; a
free-text reviewer is refused (see the Approvals ledger in PIKMIN2_WORKFLOW.md). The source handoff hash, lane generation/revision, and stopped-owner
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

The dashboard reports idle workers by role/capability and lists ready jobs with no
compatible idle worker. “Idle” without a compatible role is not available capacity;
resolve that mismatch before increasing planner fan-out. Blocked refill items
retain a category (`provider`, `integration_owner`, `worker_capacity`, or
`workflow`) and a first-blocked timestamp so repeated retries do not hide the
actual dependency age.

## 8. Keep acceptance work staffed without another approval round

The user has authorized ongoing paid worker reuse and available capacity. Within
that scope, the configured planner prepares the next concrete assignment;
ordinary bounded items do not need another per-item user approval. Issue-first
ownership, private worktrees, source review and the existing runtime acceptance
rules still apply. The controller remains the sole dispatcher.

The unattended order is **existing enemy acceptance work, existing content work,
then content expansion**. Use the explicit backlog priorities `enemy_acceptance`,
`existing_content`, and `expansion`. An enemy assignment must identify the exact
source identity and missing gates, such as transport/reward or cleanup/reentry.
An imported model, review acknowledgement, tooling test, or one admitted variant
cannot stand in for an entire family's gameplay completion. No automatic ADMIT
is granted by refill, pool completion, or integration metrics.

Enable the adapter inside the existing controller's `throughput` configuration:

```json
{
  "autofill": {
    "enabled": true,
    "manifest": "output/workflow/acceptance-backlog.json",
    "refill_cooldown_seconds": 900,
    "planner_lane": "acceptance-backlog-planner",
    "planner_cooldown_seconds": 900,
    "low_watermark": 4
  }
}
```

The path is illustrative; use the actual prepared manifest under the canonical
workspace's `output/`. The manifest envelope has `schema: 1`,
`repository: "4laric/pikmin-randomizer"`, `assignee: "4laric"`, and an `items` list.
Each item carries its stable `id`, priority, workstream, role/capabilities, heavy
flag, instruction, lane/source record, prepared launch inputs with brief/config
SHA-256 hashes, and hashed issue proof with the exact issue-body hash. Use the validator's current schema when
preparing inputs; unresolved validation is a visible blocker, not permission to
invent missing evidence. The configured refill cooldown defaults to 900 seconds
and is bounded below at 60 seconds. The registered acceptance backlog planner
(#570, `acceptance-backlog-planner`) supplies the next concrete scopes through the
same issue-first and sole-controller protocol. Its separate cooldown defaults to
900 seconds (minimum 300); `low_watermark` defaults to four. An enemy-work shortage
can request planning even when content expansion has a large remaining backlog.

The configured planner is the single writer of the autofill manifest, a queue
of prepared, issue-backed scopes. The integrator reviews source acceptance and
handoff proposals. If no planner is configured, designate the integrator as the
sole fallback writer; never run concurrent manifest writers. Before appending an
item, inspect the current handoff, open issue and existing ownership; continue existing useful work before
creating another slice. Each new scope needs an assigned GitHub issue, precise
owned paths and acceptance, an existing workstream integration owner, source
commit and dirty-state pins, an actual private worktree, a brief and provider
configuration, documented prerequisites, and explicit capabilities. Queue only
actionable scopes: resolve prerequisites first, or prepare a useful bounded
provider/consumer assignment that can proceed independently. Prepare those inputs
first; a title or a proposed issue alone is not dispatchable work. Preserve existing
manifest item identities and specifications; append a fresh item for a changed
scope so provisioning can be replayed without a duplicate lane or job.

On each controller pass, eligible entries can fill confirmed stopped, authorized
pool workers through their existing sessions. Live or unknown owners, conflicting
paths, unavailable integration owners, unprepared inputs, RAM hysteresis, and
heavy-build capacity remain hard constraints. A blocked enemy item does not
consume all spare capacity when an independent eligible content item is ready.
No second supervisor, fabricated process identity, or direct runtime launch is
part of this protocol.

When capacity has no eligible prepared scope, the controller records starvation.
With a configured planner it requests a planner wake; otherwise it emits a durable
refill request to the designated integrator. Requests repeat at the applicable
cooldown while the shortage persists; a previous notice is not permanent
suppression. The single manifest writer must append the next fully prepared scopes
or record the concrete blocking dependency and its owner. Completion reports
should include a bounded follow-on proposal grounded in observed remaining gates
and reusable evidence. Recheck ownership and prerequisite changes before planning;
do not repeatedly relaunch the same blocked work without a useful next action.
Only validated, assigned, prepared scopes enter the queue. The user has authorized
routine issue-backed follow-ons; enemy ADMIT retains its existing approval gate.

The dashboard's **Acceptance backlog** section reports the observed ready backlog,
running or resource-waiting enemy work, confirmed idle authorized workers, blocked
reasons, manifest errors and latest refill request. Queue starvation means eligible
capacity has waited for prepared work. Missing observations display `Unavailable`;
zero is displayed only when the controller actually reports zero. The item summary
shows at most ten blocked scopes plus the additional count; inspect the complete
JSON status for the full list. A disabled autofill adapter is identified explicitly.

**Integrated slices / hour** measures accepted implementation output from registry
integration records. It does not count review acknowledgements or enemy admissions.
The dashboard does not currently have an authoritative enemy-admission metric and
says so explicitly. Assess family progress using the source-identity admission
ledger and its gate evidence, independently of worker utilization or slice rate.
# Idle-capacity planning shards (#586)

Set `planner_pool.use_idle_capacity: true` to fill otherwise-idle eligible workers
up to `max_active` and the number of distinct helper templates. Unclaimed ready
implementation still reserves workers first; RAM, launch pacing and model cooldowns
continue to apply. `reserve_workers: 0` permits all remaining eligible capacity.
Untouched shards precede repeat turns. Turns are bounded and return workers after
a hashed review report; a planning report is not gameplay acceptance.

The deployed catalog under `output/workflow/autofill/planning-shards/catalog.json`
divides enemy identity groups, dungeon regions, overworld stages, challenge stages
and shared providers into 24 assigned issue-backed scopes. Old broad planners must
exit before activation (`wait_for_launches`). Only the coordinator publishes the
shared manifest using `merge_proposals`; helpers stage immutable proposals.

Before overlapping research or issue preparation, use `workflow.planner_claims`
against the canonical shared registry. Atomically claim `topic:<canonical-name>`,
`issue:<number>`, `provider:<catalog-name>` and `file:<repository-relative-path>`.
Case/slash aliases and file ancestor overlaps conflict. Claims require the current
live lane generation; batches are all-or-none. Claims never expire or transfer
automatically. This cooperative protocol complements actual implementation scope
checks and depends on using the catalog's common vocabulary.

CLI: `<python> <checkout>/scripts/workflow_module.py planner_claims --root ABS_ROOT --request ABS_JSON claim`
(worker instructions render the absolute form; `py -3.12 -m workflow.planner_claims` imports from the current directory)
(also `inspect` and `release`). Requests contain `lane`, `generation`, `resources`.
A live owner may release unused claims. Proposal claims remain until the registered
live `acceptance-backlog-planner` coordinator reviews them, records hashed disposition,
and confirms the owner and protected children stopped. Its release request adds
`coordinator: {lane: acceptance-backlog-planner, generation: N}` and
`disposition: {path: ABS_REPORT, sha256: HASH}`. Prefer disposition before rebinding. After automatic recovery, the coordinator may
explicitly dispose an older claim generation: pass the generation recorded on the
claim, and verify both the current terminal owner and original claim processes are
stopped. Worker release remains current-generation fenced. Unknown process state
or in-flight dispatch must not be bypassed.

## Parallel publication helpers (#617)

Idle worker capacity can review staged proposals before discovering new work.
Planner-pool helper entries with `kind: publication` and `review_inboxes` run only
while immutable `proposals-*.json` files contain unpublished or differing items.
They sort before discovery helpers. Discovery entries can set `defer_for_review`
to their inbox paths, suppressing repeat discovery until existing proposals publish.
Current bounded turns finish normally; ready implementation retains first call on
workers. The live pool has four review groups, issues #618–#621.

Publication helpers claim their review partition, validate complete source/issue/
ownership evidence, then call canonical `merge_proposals`. This supersedes the
older sole-coordinator publication restriction for these explicitly assigned helpers.
Only the actual append is serialized: SQLite protects the write, changed manifests
reject the stale attempt, and helpers reread/revalidate before bounded retry.
Identical published IDs replay safely. Raw manifest writes remain forbidden.
Helpers report hashed decisions and release their own claims. Coordinator #570
retains cross-shard arbitration, old inbox work and original planner-claim disposition.
Malformed/rejected proposals require explicit reasons; helpers cannot invent missing
specs, modify accepted scopes, integrate source or grant ADMIT.

## Review feedback routing (#622)

Reviewers record repair/dependency dispositions through canonical
`workflow.proposal_feedback.record(reg, lane, generation, proposal, sha256,
outcome, reason, evidence, wait_for_lanes=None)`. Evidence is a hashed report;
proposal bytes and registered reviewer generation are fenced. Completed reviewers
can import only the exact report already registered as their review evidence.

Unchanged rejected bytes no longer generate review demand. Repair feedback is
injected into the next shard planning turn, requiring a corrected uniquely named
proposal. Dependency feedback names actual registry lanes and suppresses review
until all reach done. New proposal bytes/files wake normal validation. Nothing
expires on a timer, grants acceptance or bypasses the publication validator.
Current queued turns may finish, but new identical review cycles are suppressed.

## Setup and claim maintenance (#623)

`setup_healing.enabled` adds bounded controller maintenance without replacing the
healthy coordinator. Stopped planner claims can be disposed automatically only
when every immutable proposal in that shard is identical to published specs or
has hashed explicit review feedback. The controller records a hashed disposition
and invokes the existing release API, retaining current/original process, child,
launch and generation checks. Undecided proposals remain protected.

Blocked runtime lanes whose recorded blocker explicitly identifies absent native
setup receive one ordinary same-owner recovery launch per source/blocker fingerprint.
The worker must recheck current source records (which may already be repaired),
preserve all work, and create a private native worktree from an integration-approved
pin only when actually missing. It checkpoints source identity and uses normal
private build leases and mandatory runtime fixtures. This does not bypass external
review, change acceptance, reset the coordinator or grant ADMIT.

## Queue-aware support (#624)

The dashboard Capacity panel includes worker spend over the last 60 minutes,
with a per-model breakdown under Inspect details. The read-only OpenCode database
query is restricted to this workflow's distinct registered/managed sessions and
completed messages within the window. It uses reported message costs, excludes
Codex and unrelated account use, and is an estimate rather than a billing statement.
Zero/missing prices are unpriced, not free. If the database is unavailable, the
existing event-log subtotal is labeled partial and never added to the database total.

With `queue_pressure.enabled`, the controller observes publication, integration and
runtime queues every tick, sampling arrivals/departures/completions at most once
per minute over one hour. Initial observations are a baseline, not arrivals.
Rates are marked warming up for five minutes. Departures are not acceptance;
completion counts require a done lane. Oldest age and explicit lane/issue dependency
fan-out contribute to a transparent pressure score (depth + age capped at 12 +
downstream + twice positive sampled growth). See dashboard Queue pressure and
controller/queue-pressure.json. Measurements guide staffing, not CPU utilization.

Idle support helpers rank by stage pressure ahead of discovery; ready implementation
still reserves workers first. Integration assistance has a separate concurrency
limit (`integration_support_max_active`, default 2). Integration depth/age pauses
discovery but does not pause assistance draining that queue. The execution reserve,
model pacing and RAM controls still apply; existing turns drain without preemption.
Registered planning-only discovery, publication and integration helpers in the autofill
pool can be admitted and dispatched while the integrator is unavailable; implementation jobs retain the
integration-owner availability gate.
Preparation (`planner_pool.provisions_per_tick`) and pool assignment
(`throughput.assignments_per_tick`) support bounded bursts of one to four jobs.
The live controller uses four, as does its existing dispatch burst. Each preparation
rechecks free workers and the execution reserve; each dispatch retains RAM and model
spacing controls. Pending helper records do not count as occupied worker capacity.
The dashboard reports integration assistance and its target separately.
Two issue-backed integration-support partitions prepare pinned packets for the integrator.
They review up to three targets per turn; completed report targets are remembered by
source/handoff fingerprint so unchanged packets do not consume repeat turns. Changed
pins or new handoffs create new demand. `mode: preparation` upgrades read-only review
to private integration rehearsal: helpers may resolve conflicts and test in exclusive
worktrees/`codex/` branches beneath their owned output directory. Heavy builds still
require registry leases and private build directories. Packets identify producer and
actual destination commits, handoff hash, resolution commits/patches, test evidence
and unresolved decisions. Changed pins require revalidation. A prior read-only report
does not suppress the first preparation turn; unchanged preparation is deduplicated.
Helpers never edit producer/shared worktrees, merge into the maintained line, export,
grant shared approval, issue integration receipts or admit enemies. The integrator
checks preparation packets in `output/deepseek-wave/inbox/integration-support-prep-*.md`
and retains final validation and acceptance. Existing read-only turns retain their scope.

Within existing enemy/content/expansion priority classes, autofill prefers prepared
providers with more explicit downstream dependents. Preflight now rejects missing
lane names and runtime proposals without a prepared private native source worktree;
review feedback routes these failures to preparation repair before assignment.

## Unbound dispatch recovery (#627)

Dispatch allows up to two seconds for a newly spawned local runner to register,
then binds and delivers its prompt in the same call. A model reservation and pacing
timestamp are persisted before spawn. Already-started unbound runners have priority
over fresh launches, and their reserved model can finish binding during its own
spacing window. This prevents long reconciliation ticks from consuming the runner
registration timeout. The existing three-retry bound remains; exhausted registration
is reported as recovery/inspection rather than ordinary queued work. The dashboard's
helper-session counts exclude implementation sessions, which appear in the worker roster.

An intent whose runner explicitly ended registration_timeout can be retried only
with null bound process, confirmed-dead runner, absent start.json/child.json and a
recovery-safe lane. Archive the exact launch directory inside its verified parent;
reuse the durable intent and session with at most three such retries. Never infer
safety from age alone. Non-progressing intents no longer monopolize dispatch.
Within existing/expansion priority, assigned implementation/recovery launches precede
planning/publication/integration-support helpers; RAM and model pacing still apply.

## Enemy activity classification (#628)

Dashboard active_enemy_lanes/count uses distinct running/waiting-resource
implementation lanes, excluding helpers. Scheduling priority is the legacy default;
registry settings.enemy_acceptance_lanes provides explicit audited semantic overrides
for immutable proposals mislabeled existing_content (Armor15 and Tadpole27).
The dashboard lists counted lane IDs. This does not alter scheduling, published
proposal bytes or family admission. Queued/blocked/done lanes are not counted.

## Shared-review decision routing (#629)

`shared_review_routing` maps exact shared files to registered decision owners.
Pending handoff reviews produce durable decision packets in the existing integrator
inbox; packet consumption is not approval. Unresolved consumed packets are reissued
after ten minutes, deduplicated by producer generation/file/source pins. Tasks resolve
only when an authenticated approvals-ledger decision exists at the producer's pins, or
the source is superseded. Unknown files receive no invented owner, and an owner that
cannot record the decision (does not own the producer's workstream or hold its exact
delegation) receives no packet: the route becomes `owner_cannot_decide` with an owner
notice. For #129/#132, #186 delegates focused file review to the existing species
integration lead, which must be the workstream owner; the reviewer must inspect
pins/tests and record approve/request-changes evidence through review_decisions or
dispose_review (authenticated, from its own launch session), retaining stopped-producer
fences. The healthy coordinator/integrator is not restarted or duplicated.
# Managed-session recovery and activity evidence

The controller checks process identity (PID, host and creation time), not PID
existence alone. A heartbeat is liveness bookkeeping, not proof of useful work.
The dashboard's Worker activity section reports observed session activity;
routine OpenCode cleanup lines do not reset the age. Ten minutes without session
activity creates an inspection notice. This is deliberately not permission to
kill an arbitrary live tool or build.

Quiet, session-specific balance, rate-limit and invalid-request failures are
eligible for bounded recovery. The controller checks the runner/child relationship,
descendant processes, leases, queued requests and ownership generation before
stopping only the stranded OpenCode child. The runner records its real exit.
Confirmed-dead runners with confirmed-dead children can also be resumed without
inventing successful results. Unknown process identities remain fenced.

Retries preserve the session, work and planning claims, use the current model
allowlist, and stop after their retry budget with an actionable notice. Recovery
does not mark slices completed, remove issue dependencies, or grant ADMIT.

Managed launches derive a private configuration granting access within the
canonical repository when no explicit external-directory policy exists. This
covers workflow scripts, registry/evidence and private worktrees; issue ownership
still controls edits. Explicit policies are preserved. An existing idle prompt
inside that repository can be recovered through the same process fences; paths
outside it require inspection. Permission repair has its own two-retry budget
and preserves provider retry counters. Every launch uses a private configuration
copy so OpenCode cannot mutate pinned source files. Legacy schema-hint insertion
is accepted only when removing that exact insertion reproduces the pinned hash;
all other configuration changes still fail validation.

New handoffs wake the existing stopped integration owner. Admission and worker
dispatch also recognize a stopped owner with a verified standby review report,
no open batch and no live/unknown protected process. This avoids a timing race
between a short standby turn and the scheduler. Actual batch integration still
requires the owner to run and claim the work; standby never accepts a slice.
A parked review report is archived when that same owner binds a new generation;
it is not discarded or treated as gameplay acceptance. A claimed batch is itself
wake demand: a confirmed stopped owner can resume in the same session, provided
its batch generation and registered workstream ownership still match. Binding
atomically advances the batch ownership generation/revision and records recovery
history, preserving all candidate pins, builds and isolation decisions. The owner
must reread revisions and resume existing batches before claiming new work.
Live/unknown owners or protected processes and stale/transferred ownership remain
fenced. Unchanged demand has at most two wakeups,
then produces an inspection notice instead of an endless model loop.

Blocked implementation consumers also receive one reassessment turn per exact
verified prerequisite receipt set. A newly integrated producer can match an issue
reference in the consumer dependencies, or a hashed coordinator prerequisite
disposition/report can explicitly connect it to that consumer. This covers issue
aliases that the versioned artifact wakeup cannot resolve. Receipt validation
evidence must still verify; review-only completion is not integrated source.
Live/unknown workers, protected children, in-flight launches and existing handoffs
remain fenced. Reassessment preserves original dependencies and source records:
the consumer must verify applicability, update its private worktree and record
remaining gates. It cannot infer shared approval or gameplay acceptance. An
unchanged receipt set does not restart a still-blocked consumer repeatedly.

Automatic batching excludes an isolated handoff while its generation, revision,
source and evidence pins match the recorded isolation. The controller emits a
deduplicated repair-needed notice containing the batch ID and reason, and does
not wake the integrator repeatedly for that unchanged input. Revised handoffs
are reconsidered through normal validation. Explicit batch operations remain
available for deliberate re-review.

Accepted review dispositions retain a verified copy under
`output/workflow/evidence/<sha256>`. Completion can use that copy after a temporary
worker inbox disappears; changed or corrupt evidence is never rehashed into
acceptance. Legacy accepted dispositions can archive their original verified
bytes through idempotent review-acceptance replay.

An interrupted planning-only cycle incorrectly left `done` without a disposition
can retire as `superseded` only after a later accepted cycle covers the identical
issue, scope and owned files. The original runner, child, leases and requests must
be stopped, with no in-flight dispatch or retained planning claims. The old
assignment releases its reservation without counting any accepted implementation
or inventing a report for the interrupted turn.

Autofill can adapt idle worker capabilities through the explicit
`throughput.autofill.worker_adaptation` policy. It requires `enabled`, an
`authorized_by` identity, and named `profiles` with `role`, `workstream`,
`requires` (existing capabilities), and `grants` (permitted capabilities).
For example, a content-import implementation profile can authorize
`runtime-import` for workers already holding `content-source-audit` and
`source-review`. Existing compatible workers are preferred. Roles are never
automatically promoted and only the missing capabilities required by the job
are added; this is dispatch authorization, not evidence of runtime acceptance.

Adaptation follows issue/source/launch validation and admission/conflict checks,
and commits atomically with the worker reservation. Every lane belonging to the
worker must be completed and safely stopped, with accepted completion or an
explicit cancellation/supersession. Open assignments, in-flight launches,
provisioning reservations and integration owners are excluded. The
`pool_worker_adapted` event records the policy, authorizer, job spec hash and
added capabilities. Private worktrees, build leases and runtime evidence remain
mandatory. Missing or disabled policy leaves unmatched work awaiting a worker.

Prerequisite resolution contract v3 re-audits verified no-work reports once under
its new rules. A linked disposition must include an outstanding producer; linking
only completed historical work cannot resolve a missing input. Genuine completed
partitions use an evidence-backed no_action disposition. The coordinator receives
cross-partition blocked consumers and their evidence/ownership, and must prepare
actual missing provider work or identify an exact external owner/input. Requests
referencing blocked runtime consumers take priority; the three-request turn bound
and two-attempt retry limit still apply. No planner is restarted merely to change
the waiting count.

A no_action report referencing blocked consumers must name an explicit user-owned
external_input (kind user_asset/user_decision, owner user, and exact detail).
Internal missing pins, fixture ownership or integration work require an executable
producer or bounded discovery job; referring them back to the controller cannot
close the request. This does not clear external asset or acceptance requirements.

The dashboard's prominent monster admission progress reads the configured
monster_admission.source maintained worktree through its canonical
load_and_validate/admission_contract functions in a read-only subprocess.
The denominator is playable source/variant identities (variants separate),
excluding plants/helpers/projectiles/non-spawnable bases. Names and counting
rules are expandable. Invalid/missing source displays Unavailable, never zero.

Linked prerequisite scopes are re-promoted when every outstanding linked producer
is blocked. A linked disposition must include an outstanding non-blocked producer
(or a published job awaiting admission); linking blocked consumers back to themselves
cannot establish progress. Re-promotion is deduplicated against the report and
stranded producer set, and existing retry bounds apply. Exhausted requests may retry
when semantic inputs change (source pins, dependencies or terminal state), never
merely because a heartbeat or progress timestamp moved.
# Prerequisite preparation fallback (#635)

An exhausted coordinator request (two unsuccessful turns), or a pending request
older than 15 minutes, can demand a bounded prerequisite-recovery turn from its
existing issue-backed planning partition. The ordinary idle-worker reserve,
private worktree, topic/file claims and publication validation still apply.
An outstanding nonblocked producer suppresses this recovery. The helper must
prepare concrete producer proposals (or a bounded pin-discovery proposal), verify
an actual live producer, or identify an exact user-owned external input; merely
referring work back to the coordinator is insufficient.

Recovery is recorded once per partition and semantic dependency snapshot, before
admission, so heartbeat changes and rewritten no-work reports cannot create an
unbounded retry loop. Changed source/dependency inputs can rearm it. Recovery
preparation does not imply implementation, integration or gameplay acceptance.

Shared-owner review routing (#635): explicit #186 review requests on stopped,
nonintegrated blocked producers or completed review-only producers are integration
owner demand, even before a valid handoff exists. The existing integrator must
inspect pinned source and record a review decision or prepare bounded shared work;
this never grants integration or gameplay acceptance. Each unchanged request/source
pin set receives at most two wakeups, independently of unrelated queue churn.
Live or unknown producer/owner processes retain the normal recovery fences.

Terminal lease cleanup (#635): a terminal managed session with a verified normal
exit-loop boundary and completed tools may clean up its idle CLI despite an
expired build lease owned by its exact current-generation runner. Fresh safe-tree
checks remain mandatory. Queue entries, live builds, unknown identities,
non-build leases, unexpired leases and provider-error paths remain protected.
The recovery does not delete leases or stop runners: real runner exit permits
normal dead-owner lease reclamation.

Build-resource wakeup (#635): after a newer build lease release/reap or capacity
increase, stopped blocked lanes explicitly reporting build contention can reassess
once per availability event. Fresh capacity sampling, ordinary process/ownership
fences and a two-launch per-tick limit apply. This reserves no lease and clears no
source, asset or shared-review dependencies; resumed workers must acquire normal
FIFO/exclusive leases and retain unresolved gates.

Pre-handoff shared decisions (#635): `<python> <checkout>/scripts/workflow_module.py shared_decisions
--root <canonical-root> --request <json>` records a substantive approved/rejected
file review for a safely stopped blocked producer. Fields: key, generation,
source_pins `{root,native}` matching current heads, exact owned file, status,
reviewer (your live registered lane) and reviewer_generation, scoped reason,
evidence `{path,sha256}`. Like every approvals-ledger writer it authenticates the
calling session and requires workstream ownership or the exact delegated
assignment; free-text reviewers are refused. The controller
verifies the evidence and pins again and wakes the same producer once. This does
not integrate source, clear unrelated dependencies, or grant gameplay acceptance.

Unclaimed prepared-spec repairs (#635): `<python> <checkout>/scripts/workflow_module.py prepared_repair
--root <canonical-root> --request <json>` accepts manifest_path, full replacement,
expected_hash (workflow.control.fingerprint of original spec), and evidence.
Fresh issue/launch/source proofs are mandatory. Issue/lane, source records,
workstream and owned files cannot change. Originals are archived; manifest writes
are fenced against concurrent changes. Registered/launched lanes are ineligible.
Use implementation/review roles for private candidate preparation; the existing
integrator retains shared destination writes. Update issue scope before repair.

### Abandoned build waiters and availability recovery

Normal-ended terminal sessions may be reclaimed when their only build reservation is a pre-exit queue entry owned by the exact current-generation runner. Existing terminal evidence, descendant safety and PID birth checks still apply. Recovery stops only the idle CLI child; canonical dead-owner queue reaping then removes the reservation. Queue reaping/cancellation carries the resource in its event and can wake blocked build consumers, including explicit FIFO-head/heavy-pool blockers. Live or unknown processes and unrelated review/runtime gates remain protected. Dashboard attention lists count every blocked item rather than silently capping the total at ten.

### Admission freshness and orphaned blocker follow-up

The sole controller runs a lightweight RAM observer every 15 seconds independently of scheduling, issue queries and dashboard publication. It only refreshes the RAM admission sample/hysteresis; it never dispatches work or acquires a build lease. Failed measurements leave the timestamp unchanged, so the 60-second stale-sample gate still fails closed. Staffing exposes both unoccupied capacity and the reason usable capacity is withheld (RAM pressure or expired observation).

A safely stopped runner with a missing terminal outcome gets one same-session artifact reconciliation per unchanged root/native head pair. It must inspect preserved changes and receipts first, and cannot infer acceptance from the previous exit code.

Blocked consumers with verified outcome evidence older than five minutes can generate prerequisite-preparation demand independently of helper no-work reports. The existing coordinator receives at most three consumers per turn and two attempts per unchanged evidence/source snapshot. An unstarted coordinator intent can receive this demand before any launch directory exists; a live or uncertain launch is never rewritten. Explicit active producer dependencies and in-flight consumer recovery are respected. This prepares real scoped proposals, not acceptance or automatic gate clearance.

Blocked-consumer links are recorded by the live registered coordinator with `<python> <checkout>/scripts/workflow_module.py blocked_followup --root <canonical> --request <json>`. Request fields: `coordinator`, `generation`, `consumer`, `consumer_generation`, nonempty `producers` lane IDs, `reason`, hashed `evidence`. The consumer must be safely stopped and blocked; producers must be active executable lanes, integrated source, or validated ready published specs. Completed review-only providers, blocked owners, helpers, self-links and transitive cycles are rejected. The link preserves all original gates and consumer source pins. Verified integration then wakes that exact consumer through the existing evidence-checked path.

Dashboard HTML replacement retries transient Windows reader locks for at most 1.55 seconds. A persistent lock preserves the last good HTML, records `dashboard-publish-error.json`, and retries next tick without aborting controller maintenance.
