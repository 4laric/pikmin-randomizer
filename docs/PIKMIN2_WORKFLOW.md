# Lane, orchestrator and watchdog operating contract

Current workflow, 2026-09-15. Implementation: #490; coordination: #186.

Build-capacity update (#580): the live controller enables lease-only heavy-build
admission. Preparing lanes do not reserve build slots. Actual private and maintained
builds still acquire exclusive directory/resource leases and share the current
registry cap. The controller scales that cap from 2 to 4 with demand and RAM
headroom; see `docs/PIKMIN2_CONTROLLER.md`. This supersedes fixed two-slot
assignment reservations in historical runbooks. Existing-work priority is unchanged.
The controller's independent 15-second capacity monitor applies the same policy
even during slow scheduler cycles: growth requires RAM below the configured
threshold (currently 90%), increases one
slot per configured ramp interval (normally 60 seconds), and stops at four.
The user-approved ceiling is 95% RAM, with admission resuming at 90% or below.
The controller config sets ram_high/ram_low and build_capacity ram_high/ram_low/
ram_growth; worker/planner admission and dashboard use the same configured ceiling.
Monitor and main
tick share the transactional ramp timestamp; neither bypasses resource leases.
Owner: Codex through shared GitHub account `4laric`.

Build queue FIFO reserves one free aggregate slot per distinct earlier unleased
build directory. Later independent requests may use remaining capacity; a live
waiter that stops polling cannot idle the entire pool. Same-directory FIFO,
exclusive leases, RAM admission and the aggregate cap still apply. A reservation
is not a lease and never authorizes a build until acquire returns success.
Acquisition reclaims leases whose exact protected process is confirmed dead,
even before TTL expiry. Expired live or unknown identities remain protected.

Throughput extension (#524): [worker pool, frozen delivery, batching and dashboard](PIKMIN2_THROUGHPUT.md).

Self-healing execution extension (#508): [controller and smart shepherd](PIKMIN2_CONTROLLER.md).
It adds terminal `finish` outcomes, review-only evidence, durable integration receipts,
versioned dependency wakeups, fenced OpenCode dispatch and provider fallback. Use the
controller as the sole automatic dispatcher after legacy supervisor adoption.

This is the execution-state entrypoint. [AGENTS.md](../AGENTS.md) governs repository
policy; [fan-out](PIKMIN2_IMPLEMENTATION_FANOUT.md) governs fixture adoption and
acceptance. GitHub child issues hold scope, assignment, acceptance and handoffs.
The local registry holds execution, resource reservations and recovery actions.
Historical family reports are evidence references, not a work queue.

For a compact live action list, run `py -3.12 -m workflow.operator` from the
canonical root (add `--json` for pins and blocker evidence). See the
[operator quickstart](PIKMIN2_WORKFLOW_OPERATOR.md) for feeding work, completing
receipts and checking real progress.

## Roles and current policy

Shared-file review delegation (#635): the controller may grant a new
integration-support cycle `shared-files-v1` authority over its frozen assignment.
This supersedes older preparation-only shared-approval restrictions for that
assignment. A live reviewer submits decisions through `workflow.review_decisions`;
the registry fences producer generation, source pins, handoff and cycle completion.
Dynamic allocation uses existing idle workers and distinct handoffs. Final merges,
exports, integration receipts and gameplay admission retain the integration owner.
See the operator quickstart for configuration and capacity bounds.

### Prerequisite delivery requires consumer verification (#635)

Integration remains an immutable source-delivery receipt, not proof that a blocked
consumer can proceed. Each prerequisite wakeup now records producer commit and
validation pins plus a consumer verification ID. The consumer must reproduce its
original failure and submit a concrete command, expected result, observed result,
and independent hashed evidence while its current generation is running:

```powershell
py -3.12 -m workflow.consumer_verification --root C:/Users/alari/pikmin-randomizer --request output/consumer-check.json
```

The request contains `verification`, `consumer`, `generation`, boolean `passed`,
boolean `prerequisite_resolved`,
`check: {command, expected, observed}`, and `evidence: {path, sha256}`. Run the CLI
from the canonical checkout. Submit before `finish`. A probe, contract or simulated
hook cannot pass a check requiring a compiled consumer or real engine behavior.
When that exact check passes but unrelated work remains, report it passed and
finish blocked on the remaining dependency. This does not grant gameplay acceptance.
Successful reports require `prerequisite_resolved: true`: the original required
consumer behavior must now work. A diagnostic exiting zero because it reproduced
the original defect must report `passed: false, prerequisite_resolved: false`.
Legacy success reports without this explicit resolution attestation are retained
as unverified, preserving their original checks/evidence and bounded repair demand.

Unreported terminal outcomes count as unverified, including integration-ready
outcomes. Failed or unverified blocked consumers feed repair demand grouped by
the exact producer receipt set. The coordinator must inspect the consumer evidence,
reuse active owners, or prepare a private implementation repair with the actual
consumer check as acceptance. Do not reopen or rewrite an immutable integration
receipt. At most two repair referrals are made for unchanged producer pins; no
unlimited no-work loop. The dashboard reports verified consumer unblocks separately
from integrated slices. Historical work is never retroactively counted as success.

| Role | Responsibility |
|---|---|
| Lane | One bounded slice; private source/build; heartbeat, progress checkpoint and hashed handoff |
| Orchestrator | Assign issues; resolve dependencies; inspect dispatch guidance; claim recovery actions; review/integrate/export |
| Watchdog | Classify stalled execution; persist a bounded, deduplicated action; never independently launch, kill, merge or push |

Native work branches may be pushed to **native `origin`**. Do not push `main`,
`master`/another default branch, `p2-integration` or a namespaced branch ending in
`/p2-integration`; never force-push or push tags. Verify the remote; do not guess it.
Private runtime launches are **exempt** from shared-runtime reservations.
The maintained build/export and shared runtime fixtures remain exclusive resources.
Private build directories are exclusive individually and share a heavy-build cap.
King WarCry is passed. The old blanket blockers list is historical and must not
be used to dispatch duplicate cleanup/FSM/WarCry work.

## 1. Initialize one registry per host workspace

Python 3.12 standard library only. Run from the checkout containing the tooling:

```powershell
py -3.12 scripts/pikmin2_workflow.py --root C:/Users/alari/pikmin-randomizer init
py -3.12 scripts/pikmin2_workflow.py --root C:/Users/alari/pikmin-randomizer status
```

Default database: `<root>/output/workflow/registry.sqlite3`. Every participating
lane must use this **same absolute root and database**, even from another worktree.
`--db` may override the path within that root's `output/`. Never create a separate
production registry per lane: that defeats exclusivity. SQLite transactions
serialize mutations across processes; no daemon or third-party service is required.
Do not put the database on a network share. Do not delete/reinitialize it as recovery.

All mutation arguments come from UTF-8 JSON: add `--request <file>` before the
command. Request paths are relative to the shell; paths *inside* requests are
relative to `--root` unless absolute. Evidence/worktrees must resolve within root.
Source templates: [lane](../examples/pikmin2-workflow/lane.json) and
[handoff](../examples/pikmin2-workflow/handoff.json). Replace placeholders and write
working copies under `output/`; templates intentionally cannot validate unchanged.

Optional `init` request:

```json
{"settings":{"max_heavy_builds":2,"heartbeat_seconds":300,"progress_seconds":1800,"failure_limit":3,"handoff_limit":2,"handoff_age_seconds":3600}}
```

These are initial operating budgets, not measured hardware capacity. A later budget
change requires a reviewed migration; `init` refuses to overwrite existing state.

## 2. Claim and checkpoint a lane

Create/assign the scoped child issue first. `register` records the issue, actual
owner, stable worker/lane IDs, actual task ID, exact owned files, acceptance,
milestone, root/native source identities and a **long-lived worker/supervisor PID**.
Use root-relative semantic file names (`native/pc_port/...` for native ownership),
not private-worktree-prefixed names that conceal an overlap. `native: null` is
allowed for tooling-only work. Shared `4laric` assignment does not activate a lane.

Do not use the short-lived CLI PID. The PID must identify this lane's execution;
a shared app-host PID cannot establish that one task has stopped. If a dedicated
process is unavailable, use the shared host only as a conservative liveness signal:
automatic recovery remains unavailable while it is alive. The orchestrator must
reconcile actual task status; do not fabricate a dead process.

`register` captures PID creation time and host identity. It rejects duplicate lane
IDs, unfinished duplicate issue claims, overlapping exact owned files, and more
than one active slice per worker. Use explicit child issues for disjoint scopes.
File ownership is a coordination contract, not a filesystem permission mechanism.

Execution states:

```text
ready -> running -> waiting_resource / blocked -> running
running -> handoff_ready -> integrating -> done
handoff_ready / integrating -> running (implementation needs revision)
```

`handoff` enters `handoff_ready`; `integrate` alone enters `done`. A worker may
have one active slice plus one handoff awaiting/in integration. Returning an older
handoff to implementation must satisfy the same WIP limit.

Heartbeat request (no progress/revision advancement):

```json
{"key":"species-receivers","generation":1}
```

Checkpoint request:

```json
{"key":"species-receivers","generation":1,"revision":1,"changes":{"state":"running","next_action":"Run receiver matrix","dependencies":[]}}
```

Every checkpoint must use the current revision from `status`; a stale update fails
instead of overwriting another update. Source changes use complete `root`/`native`
records: `base`, ordered `commits`, final `head`, `dirty`, `worktree`. Record dirty
state honestly; empty string means clean. These fields describe the observed source,
not a historical build certificate.

Meaningful progress requires an additional `progress` object with `summary`, local
`path` and `sha256` of an artifact/log. It advances `progress_at` and resets repeated
failure/recovery budgets. Reusing the previous evidence hash is rejected. A
heartbeat, “still working”, or state change does not reset those budgets.
`blocked` requires dependency lane IDs or issue references such as `#128`.
`waiting_resource` requires an actual queued resource request. External issue
dependencies are deliberately unresolved until the orchestrator clears them after
checking evidence; local dependencies resolve when that lane reaches `done`.

## 3. Resource leases

| Resource | Use |
|---|---|
| `maintained-build-export` | Integration lead's maintained build, verification and export sequence |
| `shared-runtime` | Shared runtime fixture/input session |
| `build:output/native-species-build` | One private build directory, canonicalized before locking |
| Private runtime launch | No lease required; use private output/saves and preserve user input/QA sessions |

Acquire request:

```json
{"key":"species-receivers","generation":1,"resource":"build:output/native-species-build","pid":12345,"ttl":300}
```

The process must exist **before work begins** and remain responsible for all work
using that resource. A practical protocol is a dedicated idle supervisor that
requests the lease, waits for `acquired:true`, runs and waits for its build/link
children, then exits. The orchestrator releases its lease afterward. Do not launch
the heavy build first and reserve afterward. Never use a shell that exits while
its child build/fixture continues. The CLI itself does not wrap existing launchers;
unmodified launchers do not acquire leases automatically.

Successful acquisition returns a random `token`; a busy resource returns an
`acquired:false` queued request. Poll acquisition on an ordinary orchestration
tick, not a tight loop. `renew` takes `key`, `generation`, `resource`, `token`,
optional `ttl`; renewal requires a live matching process. `release` takes the same
fields except `ttl` and requires the protected process to have stopped.

FIFO applies to eligible waiters for each exclusive resource and the shared
heavy-build pool; a waiter for a still-held directory does not block a free slot. The
default cap is two heavy jobs, including the maintained build. An expired lease
remains held while its process is alive or uninspectable. An expired lease with a
confirmed-dead owner is reclaimed on acquisition. The controller also releases
current-generation private build leases for terminal lanes through the normal
dead-owner release API without waiting for expiry. A verified completed managed
session with an idle process tree may retire its lingering CLI despite an unexpired
runner-owned build lease acquired before the final exit-loop; all session, process
identity, tool-completion and activity fences still apply. Live/unknown build
children remain protected. Dead queued waiters are removed
after the heartbeat budget; unknown/live waiters retain their place. Cancel abandoned
requests explicitly with `cancel-request` and `{key,generation,request_id}`.
Record cancellation rather than allowing an abandoned waiter to block the queue.

Leases are cooperative, local to this registry, and not a substitute for an OS
process supervisor that waits for children. They do not impose a shared-runtime
reservation on private launches.

## 4. Watchdog and recovery

Run `watchdog` once per monitoring tick. It returns durable actions, including
previously returned ones; notify only for new actionable IDs or status changes.
Stay quiet on unchanged state. This command does not install/change a scheduled
automation, send task messages or make GitHub writes.

| Observation | Action |
|---|---|
| Alive, fresh heartbeat, progressing | None |
| Missing heartbeat, live/unknown process | Request checkpoint; retain ownership |
| No meaningful progress | Request bounded diagnosis/checkpoint |
| Still no progress after twice the progress budget | Escalate for orchestrator diagnosis; do not restart blindly |
| Blocked/resource-waiting beyond budget | Check dependency/queue; do not restart |
| Worker and every protected process confirmed stopped | Offer recovery from recorded checkpoint |
| Three identical recorded failures, or three recoveries without progress | Escalate; no further recovery |

Use `failure` with `{key,generation,attempt_id,fingerprint,evidence:{path,sha256}}`.
An attempt ID is idempotent; replay does not inflate failure counts. Reusing one
for different evidence fails. The fingerprint identifies the underlying failure,
not a timestamped log. New meaningful evidence resets the budget; routine updates
do not.

Dispatch protocol:

1. Inspect the persisted action, lane checkpoint and actual task/process state.
2. `claim-action` with `{action_id,consumer}`. Exactly one claimant succeeds.
   Even that claimant cannot claim again. Recovery safety/budget is checked again.
3. For recovery, resume/create execution through the authorized task adapter and
   record the action ID in that request. Keep replacement work paused until its
   new ownership generation is recorded. The watchdog itself has no task adapter.
4. `complete-action` with `{action_id,consumer,outcome,replacement:{task_id,pid}}`.
   Recovery increments the ownership generation. Previous-generation registry
   writes/lease renewals fail. Non-recovery actions omit `replacement`.
5. Replaying the exact completion is harmless. A conflicting replay is rejected.

**Uncertain dispatch:** if the dispatcher crashes or times out after claiming,
leave the action claimed. Locate the already-created/resumed task using its action
ID and complete the same action. Never unclaim or blindly launch a replacement.
If it cannot be reconciled, escalate to the orchestrator with that ID. There is no
timeout that silently resets a claimed dispatch. Generation fencing applies to
registry writes; it does not revoke filesystem access from arbitrary processes.

## 5. Reviewable handoffs and integration

`validate-handoff` request: `{"path":"output/species/handoff.json"}`. This is
read-only and works without an initialized registry. `handoff` additionally takes
`key`, `generation`, `revision`, and matches the document against the lane claim.

Validation requires:

- Issue/owner/task/generation/scope, owned and changed files, exact source records.
- Source mappings and test commands/results linked to hash-checked evidence files.
- Shared-file review records; changes outside ownership require an explicit review.
- Every assigned slice criterion classified, and all six arena gates classified
  `PASS / FAIL / BLOCKED / UNTESTED / N/A` with explanatory detail.
- Natural versus injected evidence explicitly labeled. N/A is source-backed.
- Runtime: current fixture adoption evidence, successful private build/no-work
  dry run, executable hash; replacement-main fixtures also require `built`
  provenance matching the native source, build directory and executable hash.
- Tooling-only: explicit fixture non-applicability; no runtime PASS claims.

`reviewable:true` never means gameplay accepted. A slice can pass while unrelated
family gates remain untested. The assigned criteria must pass before entering the
handoff queue. Shared review may still be pending at that point; it must be approved
before integration completion. The tool checks declared reviews, not the semantic
content of a diff; integration still reviews saves, damage, IDs and actor lifetime.

Submitted handoff/evidence hashes are rechecked when beginning and completing
integration. To add review evidence, submit a new handoff file from `handoff_ready`
or `integrating` using the current revision; it returns to `handoff_ready` and
preserves original queue age. Do not silently edit submitted evidence in place.

Start integration with a checkpoint to `integrating`. Finish with `integrate`:

```json
{"key":"species-receivers","generation":1,"revision":5,"record":{"root_commit":"FULL_INTEGRATED_ROOT_COMMIT","native_commit":"FULL_INTEGRATED_NATIVE_COMMIT","native_dirty":"RECORDED_DIRTY_STATE","export_evidence":"output/integration/export.json","export_sha256":"SHA256","validation_path":"output/integration/checks.log","validation_sha256":"SHA256"}}
```

Tooling-only integration omits native/export fields. Completion records evidence;
the command never merges, builds or exports. Existing fixture provenance limitations
still apply: hashes cannot establish natural play or certify historical source
identity of reused objects. A human/focused integration review remains necessary.

## 6. Throughput and dispatch

`status` reports current lane records, leases, requests, actions and:

- Current handoff queue ages and resource wait ages; completed wait durations.
- Unique failed attempts and per-lane repeated failure/recovery counts.
- Completed slice count and start-to-integrated lead times.
- Outstanding gates grouped by milestone, explicitly `not_reported` before evidence.

Dispatch guidance ranks ready lanes by downstream lanes unblocked, then declared
`closes_gates`, then age. It excludes unresolved dependencies. Gate priorities are
planning declarations, not evidence of completion. If two handoffs accumulate or
one waits an hour (configurable at initialization), it recommends pausing new slices
and clearing integration. This is guidance, not cancellation of existing work.

Use accepted integrated slices and closed milestone gates to assess throughput.
Heartbeats and commits are not completion. Continue enforcing one active slice
and one ready/integrating handoff per worker.

## Adoption and validation

Existing lanes are not imported from historical prose or assignment. On their next
resume, the orchestrator reconciles their latest issue/handoff and registers each
actual worker once. Adopt leases in the launcher/supervisor before relying on their
exclusivity. Keep fixed QA bundles unchanged. Publish material checkpoints,
integration commits and remaining work to the child issue; do not post every tick.

```powershell
py -3.12 -m unittest tests.test_pikmin2_workflow tests.test_pikmin2_fixture_build -v
```

Tests use isolated temporary state, concurrent connections, real process identity
and synthetic handoff artifacts. They do not build/run native gameplay, activate
existing lanes or prove external scheduler/task-adapter integration.

Implementation validation (#490, 2026-09-15): 30 workflow tests plus 12 existing
fixture-build tests pass. A separate Windows smoke completed 21 CLI operations,
including live/dead lease release, handoff-to-integration, duplicate recovery claims,
idempotent recovery completion and stale-generation rejection. Local evidence:
`output/workflow-coordination/cli-smoke/commands.json` and `status.json`.
# Optional additional Mac worker

See [Mac worker onboarding and fenced remote jobs](PIKMIN2_MAC_WORKER.md) for the
opt-in worker path. It keeps the registry and native validation on Windows, adds
capability-aware issue-backed jobs, and does not migrate active lanes.
### Runtime consumer proof (#635)

A runtime consumer may report passed=true only with `runtime` containing
`kind: game_runtime`, its current `native_head`, and distinct hashed `executable`,
`log`, and `result` artifacts (each `{path, sha256}`). The result is the bounded
supervisor JSON: absolute executable in `argv[0]`, `passed: true`, `exit_code: 0`,
`timed_out: false`, and nonempty `markers` mapping observed markers to true.
The independently hashed log must contain those markers and no captain-down.
Use the actual consuming game path and markers proving the missing behavior;
a fixture-only call or successful diagnosis does not establish engine wiring.
The canonical fixture launcher can supervise an already staged game executable.

Existing latest blocked runtime reports lacking this proof become unverified,
preserving their old checks and source-delivery receipts. Policy-versioned repair
demand grants one new bounded referral budget, not unlimited retries. Prepared
repairs must include real call sites and build membership when those are missing,
with ordinary shared review and consumer revalidation after integration.

### Blocked work and worker capacity

The controller parks a blocked execution after verifying its outcome evidence,
stopped worker/resource identities, matching assignment generation, and absence
of an in-flight launch. Its assignment/job becomes `parked`, never `completed`.
The lane remains blocked with its source ownership, dependencies and evidence
intact. Integration owners and the backlog coordinator are excluded.

A generation-fenced parked lane permits compatible authorized worker reuse.
Launch intents and binding enforce one active slice per worker, so an old lane
cannot resume while that worker has another active task. Live or unknown process
identities and pending launches prevent reuse. Parking runs before autonomous
refill on each pool tick. The dashboard counts blocked lanes and parked lanes
separately from worker availability; parking does not claim acceptance or ADMIT.

### Bounded launch bursts

The sole controller has one independent five-second dispatch loop, handling
stopped-run completion and ready intents with a `launches_per_tick` budget
(maximum four per pass). Main scheduler ticks do not also dispatch. Lifecycle
recovery and dispatch share a lock; slow planning stays outside that lock.
One-shot runs retain bounded synchronous dispatch.
`model_launch_burst` permits up to four starts per model during each
`model_launch_spacing` window; the default burst is one. Live policy is four
starts per 30-second window. Reservations are durable and charged once per
launch/model, including crash replay. Provider/model cooldowns, allowed models,
RAM hysteresis, ownership fencing and build leases still apply. This removes
artificial spacing within a bounded burst without granting extra build slots.

Dashboard publication runs in one independent thread inside the sole controller,
normally every 15 seconds, rather than waiting for scheduler maintenance. Main
ticks skip publication while this publisher owns it. Dashboard observations use
read snapshots; publication failures are recorded and retried on the next refresh.
The publisher never dispatches workers or grants leases. One-shot controller
runs retain synchronous publication.

The first Muse rate-limit or verified provider failure pins that retry chain to
the authorized DeepSeek model via `provider_fallbacks`. If DeepSeek is cooling
down, the retry waits rather than reverting to Muse. Existing queued provider
retries follow the same policy. Permission repairs and task failures do not
trigger provider failover. Same-session identity and stopped-process gates remain.

Helper preparation has one independent five-second loop in the controller. Each
pass retains the bounded provision limit (live: four), current demand, sleeping
scope/cooldown checks, execution reserve, and immutable issue/template/source
proofs. Main autofill skips the helper phase while that loop owns it. Prepared
job assignment runs in the sole fast dispatch loop, before launching, rather
than waiting for slow pool maintenance. Dashboard reservation totals derive from
current unfinished scope lanes; completed lanes no longer inflate the count.

Verified terminal cleanup and completed pool-assignment release run in the sole
five-second dispatch lifecycle loop. Live terminal exit-loop grace is 30 seconds;
the exact session, validated report/handoff, unchanged terminal log, no active
child work, and no live/unknown resource owner remain mandatory. This grace is
not permission to terminate an active or uncertain turn. Helper reservations
are shown as one total with running/queued/report-ready/recovery components.

Prepared implementation admission has one independent bounded pass (live: up to
four per pass), using the same immutable manifest, issue/source proof, worker
reservation and ownership validation. Main maintenance still audits readiness
but does not compete for admission. Completed history is skipped before writer
transactions; controller/scheduler status reads use snapshots. Slow transactions
are recorded locally in slow-transactions.jsonl for contention diagnosis; nested
write transactions fail immediately instead of waiting on their own SQLite lock.
Concrete prerequisite recovery outranks general discovery, with live referral
age five minutes; one-attempt-per-input and producer ownership fences remain.

Concurrent admission publishes new launch specifications while observers run.
Cost capture and provider-recovery scans iterate a copied lane configuration,
so additions cannot abort maintenance. Helper report reception accepts a racing
existing disposition only for the same generation already marked done, with
verified stored evidence; it never replaces the winning acceptance receipt.

A managed session proven idle at exit-loop or a recognized provider failure may
retire its CLI child even when its same-generation waiting runner owns a build
lease acquired before that boundary. Running lanes require acquisition/request
timestamps; expiry alone is insufficient. Active descendants, other live/unknown
owners, runtime leases, changed logs and generation/session mismatches still
block recovery. No lease is deleted by this exception: the runner records its
real exit, then ordinary reconciliation/failover and lease reclamation proceed.

### Throughput feedback and proactive repair (#635)

Explicit `dispose-review` rejections now feed the same bounded owner repair path
as batch isolation. The controller verifies the immutable handoff and attributed
review evidence, pins generation/revision/source/handoff, and retains the old
candidate in repair history. Claimed integration batches, live/unknown processes,
worker WIP and the two-repair budget remain fences. Reviewers must record a real
rejected disposition with actionable evidence; prose-only HELD is not a decision.
No pending review is inferred to be rejected or approved. The fast dispatch loop
owns repair routing; main maintenance does not race it.

Stage timing observes preparation, assignment, launch, execution, build, resource
wait, review, integration, dependency and consumer verification. Initial ages are
lower bounds from first observation. Reason-text updates do not reset residence
time; generation or stage changes do. Completed stage durations cover the last
hour. Age flags are diagnostic, never permission to kill a worker. The dashboard
shows verified consumer unblocks/hour alongside integrated slices/hour.

Newly published native implementation, repair and QA proposals require an explicit
`producer_contract`: `kind` (`engine_change`, `diagnosis`, `runtime_check`), concrete
`deliverable`, `callsites: [{file,symbol}]`, `build_membership: [file]`, and
`consumers: [{lane,command,expected}]`. Engine-change callsite/build paths must be
in owned_files. Diagnosis can omit callsites/membership but cannot claim an engine
unblock. Existing published immutable specs remain readable. Publication validates
scope completeness; independent review and consumer evidence establish behavior.

Use `py -3.12 scripts/workflow_native_build.py --root <canonical> --request <json>`
for configured private native builds. Request fields are `lane`, `generation`,
`source`, `build`, `expected_head`, `executable`, fresh `output`, optional `jobs`
(1-6) and `wait_seconds` (0-3600). It resolves actual compiler/Ninja paths from
CMakeCache, verifies source ownership and pins, waits for a canonical build lease,
and records build log, executable hash and no-work dry-run. Its process waits for
the build; normal dead-owner reclamation releases the lease after it exits.
Missing configuration fails preflight rather than guessing a Ninja location.
Use `scripts/run_pikmin2_fixture.py` for staged runtime checks: boot assets, runtime
DLLs, 960x540 startup, explicit markers and bounded timeout remain mandatory.

Proposal observations parse only changed inputs, with a bounded cache and full
five-minute reread backstop. Publication and launch still independently hash bytes;
the observation cache never authorizes mutations. Unchanged active execution
records skip redundant readiness writes, while ready work retains liveness checks.

Repeated `failure` records with the exact diagnostic fingerprint produce one
bounded shared repair demand across affected blocked consumers. Meaningful progress
invalidates old failures. Hashed evidence, existing-owner checks and at most two
referrals per unchanged pattern/source set remain required. The coordinator must
verify a shared cause, publish one appropriately scoped fix and record producer
links for each consumer. Existing integration wakeups then require independent
consumer verification; a shared repair receipt cannot itself count as an unblock.

The controller cancels an abandoned queued private-build request only when its
owner is an exact-identity Python helper executing solely `import time;
time.sleep(integer)`, with no children or leases, and its producer has a hashed
blocked outcome plus a quiet, exact-session exit-loop. Request/launch/generation,
process tree, log and identity are rechecked before cancellation. The sleep helper
is not terminated. Arbitrary commands, active/unknown owners, changed logs and
real build waiters remain protected. Verified blocked terminal turns can then
retire their lingering CLI through normal cleanup; ordinary resource-availability
wakeups may resume them under fresh lease admission.
Resource-availability wakeups run in the sole fast dispatch lifecycle after
stopped-run completion, rather than waiting for slow planner maintenance.


### Integration assistance and queued review decisions

The controller can allocate up to eight integration preparation slots from the
existing authorized worker pool, retaining the configured two-worker execution
reserve. Each free slot receives one distinct outstanding handoff; in-flight
assignments retain their ownership. Already prepared snapshots are excluded.
Changed handoff inputs bypass the helper cooldown. This expands task capacity,
not the number of worker identities; helpers prepare private integration work
and never replace the sole integration writer or grant ADMIT.

The dashboard prominently distinguishes integration helpers actually running
from their demand-based target, with reserved/queued/report/recovery details and
the handoffs assigned to each worker.

A live registered integration owner records explicit shared-file decisions with
`python -m workflow.review_decisions --root <canonical-root> --request <json>`.
The request contains `reviewer`, reviewer `generation`, producer `key`,
`producer_generation`, current `handoff_sha256`, and `decisions` entries with
`file`, `status` (`approved` or `rejected`), and hashed `evidence` (`path`, `sha256`).
The controller applies queued decisions through the existing immutable handoff
API once producer/child stop fences pass. Source or handoff drift invalidates the
request, and evidence is rehashed on application. The registry mutation and
receipt advance atomically. Prose approval alone is insufficient; an approved
handoff must not be handed back to a stopped producer merely to flip statuses.
All build, integration receipt, runtime acceptance and admission gates remain.
