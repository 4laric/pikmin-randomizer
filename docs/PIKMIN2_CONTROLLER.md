# Self-healing controller and OpenCode shepherd

Implementation #508; coordination #491/#186. Owner: Codex through shared account
4laric. This extends the existing single registry; it does not replace native
acceptance or grant ADMIT. The existing integrator remains the sole promotion owner.

## Responsibilities

The deterministic controller owns dispatch, dependency wakeups, provider cooldowns,
outcome reconciliation and delivery. One smart OpenCode session reads changed-event
packets and emits bounded decisions as JSON in its final response. The runner saves
the response: the model has no edit permission, shell, builds or nested agents.

The shepherd can resume a stopped contributor with a revised instruction, record
a supported blocked/review outcome, notify the integrator, or request a bounded
issue-first slice. The controller validates generations, progress, old process
death, legacy supervisor death, evidence and retry budgets before acting. New slice
requests create assigned GitHub issues; the integrator reserves ownership/worktrees
before starting implementation. Decisions cannot grant ADMIT or merge source.

## Running it

Copy `examples/pikmin2-workflow/controller.json` to ignored output and fill `lanes`:

```json
{"muse-example":{"root":"C:/workspace/output/example-root",
 "output":"C:/workspace/output/example",
 "brief":"C:/workspace/output/example/brief.md",
 "config":"C:/workspace/output/example/opencode.json",
 "legacy_supervisors":[]}}
```

Every lane must already be registered with a known `opencode:<session>` task ID.
Use actual process identities from `workflow process` for legacy supervisors. They
must stop before adoption; timeout is not permission to overlap an existing owner.
Set `repo` and `assignee` for issue-first requests. Enable `shepherd.enabled` only
with an authorized configured model/provider. Model names are local configuration,
not a guarantee of access. The shipped example is disabled by default.

```powershell
py -3.12 scripts/pikmin2_controller.py --root C:/Users/alari/pikmin-randomizer --config output/workflow/controller/config.json --once
```

`--once` performs a real tick, including permitted dispatch. For ongoing operation,
launch `scripts/Start-Pikmin2Controller.ps1` hidden with `-WorkspaceRoot`, `-Config`
and an absolute `-Python` executable. The wrapper restarts a crashed controller
with backoff; the registry rejects a second live controller. This is a local
background process, not a boot-persistent Windows service. Start the wrapper again
after reboot. Create `<controller output>/STOP` to stop future ticks. Active workers
finish independently; STOP does not kill builds or runtime sessions.

The standard interval is 30 seconds. A 72–77% RAM band limits new launches, one per
tick. Do not invent tasks to fill RAM. Existing jobs are not killed when memory
rises. The common two-heavy-build pool remains authoritative. Live build processes
with recently changing build logs suppress false model-progress alarms.

## Terminal outcomes

Agents no longer need to construct all terminal metadata manually:

```json
{"key":"muse-example","generation":2,"outcome":"blocked",
 "summary":"Need the reviewed placement contract",
 "evidence":{"path":"output/example/status.md","sha256":"SHA256"},
 "dependencies":["muse-placement"]}
```

Pass this as `--request <file> finish` to `scripts/pikmin2_workflow.py` with the
canonical `--root`. Supported outcomes:

| Outcome | Meaning |
|---|---|
| `blocked` | Exact dependencies remain; no repeat work until evidence changes |
| `review-ready` | Review of existing evidence complete; controller captures reviewer/session metadata |
| `implementation-ready` | Requires `path` to a fully validated runtime/tooling handoff |
| `reconcile` | Worker stopped but actual outcome needs diagnosis |

Review records have `kind: review`, hashed source evidence, and `fresh_runtime:false`.
They do not declare new gameplay gates, executable provenance or build acceptance.
A review can assess historical evidence in its conclusion without pretending to
have launched a new fixture. `review_ready` and `reconciling` do not trigger the
old watchdog restart recommendation. Runtime handoff requirements remain intact.
The integrator closes a reviewed slice with `accept-review` and JSON fields
`key`, `generation`, `summary`, `evidence`. This disposition is idempotent and does
not count as source integration or permit publication of an integrated dependency.

A clean OpenCode exit without a terminal outcome is reconciliation, not a crash.
The shepherd inspects preserved work before offering a continuation. Two unsuccessful
shepherd-directed attempts against an unchanged source head require attention.

## Integration receipts and artifact versions

The integration lead writes a receipt after its existing merge/build/export/checks.
Configure the path in `receipts`. It contains the arguments to `workflow receipt`:

```json
{"key":"muse-example","generation":2,
 "root_worktree":"output/integration-root",
 "native_worktree":"output/integration-native",
 "record":{"root_commit":"FULL_SHA","native_commit":"FULL_SHA",
 "native_dirty":"","export_evidence":"output/integration/export.json",
 "export_sha256":"SHA256","validation_path":"output/integration/checks.log",
 "validation_sha256":"SHA256"}}
```

The controller verifies accepted candidate ancestry with Git, the existing handoff,
and validation/export hashes before marking completion. Replaying the same receipt
does not increment completion twice. Conflicting receipts fail closed. A root-only
accepted handoff can exclude an auxiliary native fixture; record that exclusion
explicitly in validation evidence. Receipt submission does not run a merge/export.

Configure `publications` with `{producer,path,description}` for completed provider
contracts. The controller snapshots the evidence into immutable files, versions it
by hash, and publishes it only after the provider is `done`. Consumers blocked on
those lane IDs resume once per accepted dependency set. Their same session and
worktrees are preserved. Issue references such as `#437` never resolve merely
because an issue closes; the shepherd/integrator checks the evidence.

## Crash and provider recovery

Launch intent is committed before spawn. A unique launch directory holds an atomic
runner claim, process identity, start gate, actual child identity, JSON events and
result. No OpenCode work begins until ownership registration is written. A controller
restart reconnects to that directory. A bound runner without its start gate receives
the same gate on replay. An uncertain spawn without identifiable execution is
reported for reconciliation, never blindly repeated. A live or unknown child blocks
replacement even if its parent disappeared.

Pre-tool rate limiting cools down the provider globally (default 15 minutes) and
falls back through the configured model chain in the same session after the old
process stops. Once tools have run, the controller does not kill the process to
switch providers unless the guarded idle-provider recovery below is enabled.
Every attempted endpoint is tried at most once in that chain.

### Provider stalls after completed tools (#510)

Enable this Windows controller policy to recover the idle-after-rate-limit case:

```json
"provider_stall_recovery": {
  "enabled": true,
  "quiet_seconds": 180,
  "max_attempts_per_head": 2,
  "models": ["opencode-go/muse-spark-1.3-contributor"]
}
```

The controller requires a timestamped rate-limit error newer than the last JSON
event, a completed step and completed/error tool records, and at least three
minutes without new events. It verifies exact process identities, enumerates
descendants, and refuses to stop any owner with a live/unknown resource lease or
any child other than the known supervisor/worker and console hosts. It repeats
activity and descendant checks before each stop. Unknown inspection fails closed.
This is recovery at an observed idle boundary, not permission to interrupt tools.

The policy covers both registered legacy supervisors and managed runner children.
It journals intent before stopping supervisors and then the worker, verifies their
death on a later tick, and queues the same OpenCode session and private worktrees
on the configured paid endpoint. Windows termination validates creation time on
the same process handle used for termination. Controller restarts replay the
journal; the shepherd cannot override an in-progress recovery. Two automatic
recoveries per recorded source head exhaust the budget and leave an attention
notice. Handoffs, completed lanes, and blocked review outcomes are never restarted.
Inspect `control.provider_recoveries` for the evidence, identities and replacement
launch. This policy is Windows-specific; other hosts require a process adapter.

The smart shepherd wakes for changed notices, at most once every two minutes, with
one active invocation. Three failed calls for an unchanged event set open a circuit
and leave an attention record rather than spending indefinitely. Its session and
decisions survive controller restarts. Model-generated commands are validated;
stale decisions cannot overwrite newer lane progress.

## Evidence, notifications and rollout

Inspect `status.json`, `error.json`, `shepherd-attention.json`, `attention-*.json`,
and `launches/` under controller output. Material notifications are delivered once
to the existing integrator inbox; unchanged ticks remain quiet. GitHub issue writes
use a durable marker: uncertain creation is searched/reconciled, not submitted twice.

Before live adoption, take a SQLite backup, preserve legacy sessions, and record
supervisor identities. Seed the already-consumed dependency versions when a manual
continuation has already consumed them. Do not run overlapping legacy and controller
recovery. Deployment can use a pinned tooling checkout against the canonical registry.

Validation:

```powershell
py -3.12 -m unittest tests.test_pikmin2_workflow tests.test_pikmin2_controller tests.test_pikmin2_fixture_build tests.test_provider_recovery -q
```

Tests inject duplicate events, stale generations/decisions, missing terminal outcomes,
rate limits, uncertain spawn, crashes around registration, live children, immutable
publications and actual Git ancestry. They do not certify any native gameplay gate.

## Headless worker recovery (#568)

## Model throttling and fallback (#579)

Configure the authorized ordered `models` chain, for example Muse followed by
`opencode-go/deepseek-v4.1-flash`, and the same chain in `provider_stall_recovery.models`.
Observed worker rate limits cool only the failed model. Explicit provider-wide
cooldowns remain supported for confirmed provider-wide incidents. A model switch
does not guarantee a separate upstream quota; if both models throttle, both wait.

`model_rate_limit` defaults to `initial_seconds: 30`, `max_seconds: 300`,
`reset_after_seconds: 1800`, and `max_retries: 8`. Consecutive throttles double
the delay to the cap; a 30-minute quiet period resets escalation. Attempt IDs
make penalties replay-safe. Retries preserve sessions, instructions and dispatch
priority, prefer another authorized model, and retain cooled models for later.
Exhausted pre-tool retries enter reconciliation with evidence; post-tool recovery
retains its existing stricter per-head budget and completed-tool safety checks.

`model_launch_spacing` defaults to 15 seconds between new launches of each model,
persisted across controller restarts. Existing local tools/builds keep running.
This paces launches, not individual model requests inside an active worker.
Deployment must update pending intents as well as configuration; existing running
workers keep their current model until a safely fenced continuation.

## Headless worker recovery details

Enable `terminal_idle_recovery: {"enabled": true, "quiet_seconds": 60}` in the local controller configuration to release managed CLI children that remain alive after their exact session reports `exiting loop`. Recovery requires a quiet completed boundary, verified runner/child identities and ancestry, no active or unknown lease, and no tool descendants. It ignores only the known periodic cleanup message. Windows process creation times distinguish reused parent PIDs. The runner writes its real exit result; cleanup never creates an acceptance or terminal lane outcome.

Same-session recovery preserves the pool assignment and records its launch history after verifying the previous execution exited. `Registry.reconcile_pool_recovery(action_id)` can apply that same fenced link to an already-bound recovery during deployment. Completion uses valid recorded integration/review evidence before fallback evidence; changed hashes remain invalid.

Unattended worker configurations should deny unknown external directories immediately, explicitly allow their authorized private workspace and necessary application temporary directory, and retain edit exclusions for shared/original checkouts. A permission-wait recovery requires independent idle-process verification; terminal-loop recovery does not treat a permission request as a completed loop.


Heavy assignment reservations pause only when a lane is `blocked`, `review_ready`, `handoff_ready`, or `done` and its worker and every protected lease process are confirmed stopped. This frees prospective build capacity for dependency producers; it does not release any actual resource lease, change worker ownership, complete an assignment, or accept evidence. Live or unknown workers and protected children retain their reservations. Actual build leases always count separately toward the shared cap, including multiple leases held by one lane, and resuming a heavy assignment must reserve capacity again.
