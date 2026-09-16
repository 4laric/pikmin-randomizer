# Lane, orchestrator and watchdog operating contract

Current workflow, 2026-09-15. Implementation: #490; coordination: #186.
Owner: Codex through shared GitHub account `4laric`.

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

## Roles and current policy

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
confirmed-dead owner is reclaimed on acquisition. Dead queued waiters are removed
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
