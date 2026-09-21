# Self-healing controller and OpenCode shepherd

Implementation #508; coordination #491/#186. Owner: Codex through shared account
4laric. This extends the existing single registry; it does not replace native
acceptance or grant ADMIT. The existing integrator remains the sole promotion owner:
it pushes line heads to the off-disk remotes after each receipt, and promotion
batches to the release target (`inspect promotion-plan`) become human-reviewed PRs;
the controller never merges, branches or pushes (docs/PIKMIN2_WORKFLOW.md, section 5).

## Responsibilities

The deterministic controller owns dispatch, dependency wakeups, provider cooldowns,
outcome reconciliation and delivery. It is also the only writer of review-packet
decisions: it evaluates at most one requested packet per 30 s at its audited pins and
refuses a request after drift or three failed attempts (docs/PIKMIN2_REVIEW_PACKETS.md). One smart OpenCode session reads changed-event
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
run the wrapper from a release worktree (see Deployment below). The wrapper restarts
a crashed controller with backoff; the registry rejects a second live controller.
This is a local background process, not a boot-persistent Windows service. Start
the wrapper again after reboot. Create `<controller output>/STOP` to stop future
ticks. Active workers finish independently; STOP does not kill builds or runtime
sessions.

## Deployment from a pinned release

Production runs from an immutable release worktree, never from the shared canonical
checkout: a branch switch, stash or half-finished edit there would otherwise change
the controller's and every worker's gate code at once. The controller imports its
runner from its own checkout and hands workers absolute commands into it
(`scripts/pikmin2_workflow.py`, and `scripts/workflow_module.py <module>` for the
module CLIs), while `--root` stays the canonical workspace and registry.

```powershell
py -3.12 scripts/workflow_module.py service status --root C:/Users/alari/pikmin-randomizer
py -3.12 scripts/workflow_module.py service prepare-release --root C:/Users/alari/pikmin-randomizer --ref <commit or branch> --config C:/Users/alari/pikmin-randomizer/output/workflow/controller/config.json --python <absolute python.exe>
```

`status` is read-only. It shows the controller identity from `control.controller`,
its liveness, the code revision recorded when that process claimed the registry
(`control.controller_code_revision`, trusted only when its `process` matches), the
on-disk revision of the controller's own checkout (the recorded path, else the
absolute `pikmin2_controller.py` in its command line; never the checkout running
`status`, which is shown separately), and whether its parent is the
`Start-Pikmin2Controller.ps1` wrapper (`unknown` when the process table cannot
tell). It warns, and exits 1, for dirty code, a running sha that differs from disk,
missing provenance, an undeterminable checkout or an unsupervised controller.

`prepare-release` resolves the ref to a commit (a worktree path is accepted only
when it has no uncommitted changes), refuses a commit of the canonical repository
that lacks `tests/workflow_release_tests.txt` before touching disk, and creates a
detached worktree at `<root>/output/workflow/release/<short-sha>`. The config must name `output` (the
wrapper has no default). An existing directory is reused only
if it is a clean worktree at exactly that commit; anything else is refused. It then
runs the pytest arguments listed in the release's `tests/workflow_release_tests.txt`
inside the worktree and refuses on any failure or if the tests dirty the tree. It
never signals the controller; a subprocess that cannot start or times out is
refused with its command. On success it prints the switch-over for the operator:

1. create `<controller output>/STOP` and wait for the controller PID and its wrapper
   PID to exit. A wrapper whose controller exited nonzero sleeps and relaunches the
   old code unless STOP still exists, so when the wrapper cannot be identified the
   plan prints a process query that must return nothing before step 2;
2. delete STOP, or the new wrapper exits immediately;
3. start `<release>/scripts/Start-Pikmin2Controller.ps1` hidden with
   `-WorkspaceRoot <canonical root> -Config <config> -Python <python>`;
4. run `service status` from the release and confirm the new sha, `dirty=False`
   and a wrapper parent.

`<release>/scripts/Deploy-WorkflowRelease.ps1` performs steps 1-4 for the release it
lives in: it waits for every `pikmin2_controller.py` and wrapper process to exit
(leaving STOP in place and exiting 1 after `-TimeoutSeconds`), then starts the
wrapper from its own folder and prints `service status`. Rolling back is running
the same script from an older release folder. Run it from an operator shell; agent
sessions must not restart production.

Crash forensics: an exception escaping the controller anywhere (startup, monitors,
shutdown; per-tick failures are still caught and written to `error.json`) writes its
traceback to `<controller output>/error.json` with `stage: fatal` and to stderr, then
exits 1. Because `Start-Process` truncates `controller.stdout.log` and
`controller.stderr.log` on every start, the wrapper moves a non-zero exit's logs to
`controller.<utc-stamp>.exit<code>.stdout.log`/`.stderr.log` (the newest
`-KeepCrashLogs`, default 20, per stream are kept) and writes `controller-exit.json`
(previous PID, exit code, saved log paths). The next controller records it as one
`controller_restarted_after_exit` event and renames the note to
`controller-exit.recorded.json`; a damaged note never blocks startup.
`-RestartDelaySeconds` (default 15) scales the restart backoff.

Running workers keep the CLI paths they were given; new launches get the release's.
Keep old release worktrees until no launch refers to them.

The tick interval is config `interval` (default 15 seconds, at most 30). A change to the config, WAKE, integrator
inbox or receipts ends the wait early, but a tick never starts sooner than
`min_tick_seconds` (default 5, from 0 to the interval) after the previous one
began. Registry events end the wait only with `wake_on_registry_events: true`
(default false): live events arrive about every 5 seconds, so turning it on
roughly triples the tick rate while the writer lock is saturated. A wait that
finds the registry locked past its 2-second read timeout keeps waiting instead of
raising, and any other wait failure is written to `error.json` and falls back to
the plain interval, so a wait can no longer end the service. New launches pause at `ram_high` and resume at
`ram_low` percent RAM (code defaults 77/72; the live config sets 95/90), one per
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

The controller verifies accepted candidate ancestry with Git in the given worktrees,
then `integrate` proves the landed bytes (docs/PIKMIN2_WORKFLOW.md section 5), the
existing handoff and validation/export hashes before marking completion. A receipt
may add `"lander":{"lane":...,"generation":...}`; config receipts run in the
controller, outside any launch session, so it stays an unauthenticated
`claimed_lander` and shared-file ports in them refuse.
Replaying the same receipt does not increment completion twice. Conflicting receipts
fail closed; a malformed receipt file is refused with a `receipt_rejected` notice and
never stalls the tick. Every native file the lane changed must be at `native_commit`:
leaving an auxiliary native fixture out needs a per-file port with `landed_blob` null,
a reason and hashed evidence, and leaving out an engine-path file (native `pc_port/`,
`src/`, `include/`, `cmake/`, `CMakeLists.txt`) needs an approved landing review and
an authenticated lander, so it refuses in a config receipt. Validation evidence alone no longer excludes a file. Receipt submission does
not run a merge/export.

Configure `publications` with `{producer,path,description}` for completed provider
contracts. The controller snapshots the evidence into immutable files, versions it
by hash, and publishes it only after the provider is `done`. Consumers blocked on
those lane IDs resume once per accepted dependency set. Their same session and
worktrees are preserved. Issue references such as `#437` never resolve merely
because an issue closes; the shepherd/integrator checks the evidence.

## No-progress parking

Every terminal outcome (`finish`, `submit_handoff`) records the lane's substantive
signal next to it as `progress_signal`: state, root/native heads, dependencies
(case, whitespace and `gen N` markers normalized), handoff sha and integration flag.
`stall_streak` counts consecutive generations whose signal equals the previous
generation's; it resets only when the signal changes, never at bind, and each stalled
generation emits `no_progress_generation`. Only generations bound by a guard-aware
controller (`bind_launch` stamps `lane.guarded_generation`) count, so outcomes that
worker CLIs record before the controller restarts onto this code build no streak.
A `reconcile` finish (the controller's "exited without terminal outcome") leaves
signal and streak unchanged: a runner crash is neither progress nor a stalled
generation. Lanes written before these fields read as streak 0, so nothing parks
until two further unchanged generations bound after the restart are observed. A
changed signal clears `parked`/`wake_after` even when it arrives without a launch
(a shepherd decision, a handoff) and emits `lane_unparked`.

`Registry.plan_launch` enforces the guard once, for wake reasons only:
`consumer-prerequisite`, `blocked-producer-followup`, `shared-preflight-decision`,
`shared-hook-decision` (approvals and review packets), `autofill-planner`,
`integration-demand`, `build-resource-available`, `outcome-reconcile` and
`handoff-representation`. Each wake passes the substantive inputs it carries
(producer receipts, decision keys, substantive demand items, planner input
fingerprint); integration demand leaves out queued-job and planning-row churn, as its
token does. Build-resource wakes pass none: a release is not evidence that this
lane's blocker changed, so a stalled lane waiting on a build slot relaunches only at
its `wake_after` recheck. At
`stall_streak >= 2` a wake is admitted only with an input the lane has not already
been offered since it last progressed, or once `wake_after` has passed (periodic
recheck). Otherwise it refuses with `Parked`, sets `lane.wake_after` (15 min doubling
per further stalled generation, capped at 4 h) and `lane.parked`, emits `lane_parked`
and one informational `no_progress_parked` notice (status `info`, never offered to the
shepherd, and the waking tick adds no notice of its own, so parking cannot invite a
model-directed resume); later refusals read committed rows and take no writer lock. Recovery continuations (`dead-runner`, `provider fallback`,
`provider-error`, `permission-repair`, `provider-stall`), operator/user reasons and
integration demand carrying `disposition_required` reviews are never parked, and any
bound launch unparks the lane. Parking only suppresses relaunch: it never clears a
dependency, infers resolution or records an approval. The dashboard counts parked
lanes; `<python> <checkout>/scripts/workflow_module.py no_progress --root <root>` lists streaks and parked lanes
read-only, and `--db <copy.sqlite3>` reads any registry copy (opened `mode=ro`, no
workspace checks) for a dry run of what would park.

Open notices collapse per (lane, kind, error): a repeat bumps `repeats`, `last_at` and
`last_detail` at most every ten minutes instead of adding a row, and the shepherd
packet omits those three fields so an unchanged event set keeps its packet ID. Only
a row still open absorbs repeats: after the shepherd resolves it, a repeat with the
same detail stays suppressed and a distinct detail (another path, generation or
decision) is a new pending notice. A notice naming a launch (`action`) stays one per
launch.

## Crash and provider recovery

Launch intent is committed before spawn. A unique launch directory holds an atomic
runner claim, process identity, start gate, actual child identity, JSON events and
result. No OpenCode work begins until ownership registration is written. A controller
restart reconnects to that directory. A bound runner without its start gate receives
the same gate on replay. An uncertain spawn without identifiable execution is
reported for reconciliation, never blindly repeated. A live or unknown child blocks
replacement even if its parent disappeared.

The runner owns its child's exit. OpenCode stays alive after its turn, so when the
turn ends (stdout `step_finish` with reason `stop`, or stderr `"exiting loop"` for
the launch's session) and neither stream has shown non-cleanup output for
`runner.exit_grace_seconds` (default 10), the runner re-checks the recorded child
identity and takes a Toolhelp process snapshot (no CIM or PowerShell): it stops the
child through its own Popen handle only when nothing but `conhost.exe` runs below
it, the same idle-tree fence the sweepers enforce. A tool's build, server or
detached shell (or an unavailable snapshot) defers the stop, recorded as
`turn_end_deferred` (reason, descendant names) in `activity.json` and the result,
and is rechecked every `runner.descendant_recheck_seconds` (default 30), so a stop never
orphans work in the lane's worktree. A stopped turn records `stopped_after_turn`
and `turn_end`, and completes like a natural exit, so the slot is free seconds
after the turn instead of after the cleanup sweepers. A turn end is withdrawn when
its stream shows the loop running again (a loop line or permission evaluation after
`"exiting loop"`, or a `tool_use` after `step_finish` `stop`); after a stderr
re-entry only stderr can end the turn. `terminal_idle_recovery` and
`terminal_cleanup` remain backstops.

OpenCode block-buffers stdout JSON on a pipe, so tool activity is read from both
streams: any `tool_use` event, any stderr `evaluated permission=` line, or a loop
step past 0. A rate-limit line stops the child only while no tool has started in the
turn, and only after the limit and stdout have both been quiet for
`runner.rate_limit_settle_seconds` (default 5), so buffered events are parsed first.
That pre-tool stop is the only `kind: rate_limit` result: it cools the failed model
and falls back through the configured chain in the same session. A mid-tool limit
never stops the session (`rate_limit_phase: mid_tool`); if the session then dies
without ending its turn the exit is a provider failure (provider-error retry), and
if it ends its turn normally it completes normally.

`complete_runs` plans a recovery continuation in the same transaction that marks the
stopped launch exited (`plan_launch(supersedes=...)`), so a refused plan leaves it
unexited. A refused or exhausted continuation falls through to `reconcile` with
hashed evidence, and only then is the launch marked exited; if reconciliation is
also refused the launch stays open with `completion_attempts` and backs off
(`completion_retry_after`, 1 minute doubling to 1 hour) behind a
`completion_deferred` notice. One launch's failure, including a failed session
adoption, never skips the rest of the sweep or the live runners' heartbeat; a busy
registry leaves the launch for the next sweep (`complete-runs-error.json`, with its
stage). Every retry counter (`dead_runner_retries`, `rate_limit_retries`,
`provider_failure_retries`, `permission_retries`) rides the whole chain and
`automatic_retries` caps it (`automatic_retry_limit`, default 8), so alternating
failure kinds cannot reset each other. Provider-stall recovery builds its
continuation with the same carry (`Controller.retry_carry`): counters, chain count,
obligations and session scope.

A `child.json` or `result.json` that parses to garbage (NUL bytes after a power
loss; `runner.write` fsyncs launch records before its atomic replace, while
advisory status files and writes under the registry writer lock pass
`durable=False`) is a crash once the
runner is dead and no child can survive: the runner started before the current boot
(its creation time predates the boot and the Windows `BootId` it recorded in
`boot.json` differs from the current one, so a clock correction proves nothing), or
the process table holds no process whose parent is the runner's PID and that
started after it. An unproven launch backs off (`completion_retry_after`, up to 10
minutes) instead of scanning the process table every tick. The launch then takes the normal dead-runner path with a
`crash.json` (reason, damaged record hashes, proof) as its evidence and an
informational `crashed_launch_recovered` notice; the damaged bytes stay in place. A
valid `result.json` already proves the child exited. Without a proof, a live runner,
or a locked file, the launch stays fenced with `completion_record_unreadable`. A
bound runner that died before writing `child.json` needs the same proof.

Every recovery continuation (dead runner, spawn error, provider
fallback, provider error, permission repair, provider stall) carries the failed
launch's obligations: consumer verification, delivery contracts, acceptance check,
review obligations and wake inputs. At bind, `bind_context` gives the new generation
its own pending check and names it in the instruction; when the producer receipts
drifted it instead tells the worker the old ID cannot be reported and emits
`consumer_verification_rebind_declined`. Attempt counters stay with the original
launch. Every attempted endpoint is tried at most once in that chain.

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
one active invocation; its `start.json` is written with the spawn. Its packet offers
the first 12 pending notices after stall collapse: only the newest pending
`progress_stale`, `session_activity_stalled`, `stopped_without_outcome`,
`outcome_missing` or `missing_runner_result` per (lane, kind) is offered and older
ones become `superseded`; the observer also keys `progress_stale` and
`stopped_without_outcome` per lane generation. Three failures of the same packet
(its notice-ID signature) write `shepherd-attention.json` and move those notices to
`escalated`, so the next packet offers the rest. Its session and decisions survive
controller restarts. Model-generated commands are validated; stale decisions cannot
overwrite newer lane progress.

Lanes without a controller launch config have no wake path. A stopped one in
`ready`, `running`, `reconciling` or `waiting_resource` raises one
`unsupervised_lane` notice; configure its launch or retire it. An integration
notice reports `integration_owner_not_alive` only when
`integration_owner_available` (the scheduler's predicate) is false, so a verified
parked owner is not a blocker, and owner liveness/state are left out of the notice
identity.

## Evidence, notifications and rollout

Inspect `status.json`, `error.json`, `shepherd-attention.json`, `attention-*.json`,
and `launches/` under controller output. Material notifications are delivered once
to the existing integrator inbox; unchanged ticks remain quiet. GitHub issue writes
use a durable marker: uncertain creation is searched/reconciled, not submitted twice.

Before live adoption, take a SQLite backup, preserve legacy sessions, and record
supervisor identities. Seed the already-consumed dependency versions when a manual
continuation has already consumed them. Do not run overlapping legacy and controller
recovery. Deploy through `service prepare-release` (above); the registry records
which revision claimed it (`controller_started` events) and stamps each launch.

Validation:

```powershell
py -3.12 -m unittest tests.test_pikmin2_workflow tests.test_pikmin2_controller tests.test_pikmin2_fixture_build tests.test_provider_recovery -q
```

Tests inject duplicate events, stale generations/decisions, missing terminal outcomes,
rate limits, uncertain spawn, crashes around registration, live children, immutable
publications and actual Git ancestry. They do not certify any native gameplay gate.

## Elastic build admission (#580)

Enable `build_capacity: {"enabled": true, "base": 2, "maximum": 4,
"ramp_seconds": 60}` in the controller configuration. The controller durably
enables lease-only admission: heavy assignments can prepare and dispatch while
actual build leases occupy the pool. All compilation/link jobs must still acquire
the canonical registry lease before starting. Directory exclusivity, FIFO,
process fencing, and maintained-build ownership remain enforced.

The controller raises the cap one slot per minute, up to four, when RAM is below
80% and builds are queued, or idle workers coexist with enough active heavy lanes.
At 87% RAM it pauses new build grants and lowers the target to two; grants resume
below or at 82%. Existing leases are never revoked. Samples older than 60 seconds
pause new heavy grants until the controller refreshes them. RAM is sampled while
the registry writer is held, and a write never replaces a newer stored observation,
so the 15-second monitor and the main tick cannot commit a stale clear over a
newer pause. Pool occupancy is read from a committed snapshot outside the writer;
only leases, queue, the meta row and the event tail are loaded under it. Lane
dispatch retains the separate 90% RAM ceiling. Low demand returns the target to two.

The dashboard separates leases held, preparing lanes, concurrency limit and
currently available grants. Historical utilization uses capacity-change events
and is capped at 100%.
The policy and lease-only mode persist in the registry; removing configuration
does not silently disable the stale-sample guard. Reconfiguration needs an explicit
reviewed migration. The cap is a cooperative limit, not an OS memory guarantee.

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
Exhausted exited-worker retries enter reconciliation with evidence; live post-tool recovery
retains its existing stricter per-head budget and completed-tool safety checks.

`model_launch_spacing` defaults to 15 seconds between new launches of each model,
persisted across controller restarts. Existing local tools/builds keep running.
This paces launches, not individual model requests inside an active worker.
Deployment must update pending intents as well as configuration; existing running
workers keep their current model until a safely fenced continuation.

## Headless worker recovery (#568)

The runner stops its own child after the turn (see Crash and provider recovery); `terminal_idle_recovery` is the backstop for runners that predate it or missed the boundary. Enable `terminal_idle_recovery: {"enabled": true, "quiet_seconds": 60}` in the local controller configuration to release managed CLI children that remain alive after their exact session reports `exiting loop`. Its journal records each attempt's own evidence (an aborted attempt's evidence is replaced), and `complete_runs` classifies an exit only from a journal in `child_stop_requested`. Recovery requires a quiet completed boundary, verified runner/child identities and ancestry, no active or unknown lease, and no tool descendants. It ignores only the known periodic cleanup message. Windows process creation times distinguish reused parent PIDs. The runner writes its real exit result; cleanup never creates an acceptance or terminal lane outcome.

Same-session recovery preserves the pool assignment and records its launch history after verifying the previous execution exited. `Registry.reconcile_pool_recovery(action_id)` can apply that same fenced link to an already-bound recovery during deployment. Completion uses valid recorded integration/review evidence before fallback evidence; changed hashes remain invalid.

Unattended worker configurations should deny unknown external directories immediately, explicitly allow their authorized private workspace and necessary application temporary directory, and retain edit exclusions for shared/original checkouts. Launches of an integration owner (a workstream `owner_lane`, or any `integration-demand:` wakeup) get per-launch OpenCode `permission.bash` deny rules after any catch-all (last match wins) for `git merge`/`pull` with `-X ours|theirs`, `-s ours` or a strategy option, `cherry-pick`/`rebase -X`, `reset --hard`, `clean -f*`, `checkout --ours|--theirs`, `checkout [<ref>] -- <path>`, `checkout .`, `restore` of the worktree or from a source, and force, mirror or `+refspec` pushes (`managed_config.INTEGRATOR_GIT_DENY`). An integrator config that cannot carry them (unparseable, a non-map `permission.bash`, or any `agent`/`mode` entry with its own `permission`, which OpenCode would apply instead) is refused with an `integrator_guard_refused` notice: before spawning, or, when ownership changed after spawning, before binding, so the runner is never started and times out through the normal no-start path while other launches keep dispatching. Wildcards match the command text, so this is a guard against accidents, not a sandbox. A permission-wait recovery requires independent idle-process verification; terminal-loop recovery does not treat a permission request as a completed loop.


Heavy assignment reservations pause only when a lane is `blocked`, `review_ready`, `handoff_ready`, or `done` and its worker and every protected lease process are confirmed stopped. This frees prospective build capacity for dependency producers; it does not release any actual resource lease, change worker ownership, complete an assignment, or accept evidence. Live or unknown workers and protected children retain their reservations. Actual build leases always count separately toward the shared cap, including multiple leases held by one lane, and resuming a heavy assignment must reserve capacity again.


### Prepared work and queued planner reservations (#630)

Ready backlog measures validated work independently of idle workers. The separate
Ready awaiting worker card counts prepared items awaiting compatible capacity.
The sole controller may yield a never-started planner reservation to prepared
implementation, in the existing implementation priority order. This is a recorded
cancellation before execution, not a completed plan or accepted slice. The helper
partition remains eligible for a later cycle after its normal cooldown.

Reclamation requires generation 1, ready state, confirmed stopped inherited
process, no execution evidence, no claims or leases, and compatible worker roles
and capabilities. Any launch attempt, binding, process or launch-directory artifact
prevents reclamation; normal recovery handles uncertain startup. Running helpers
finish normally. Implementation takes the released worker before helper refill.

### Terminal cleanup and capacity dispatch (#631)

With terminal_cleanup.enabled, completed review/handoff producers may have their
lingering OpenCode child retired after a five-minute grace period. The controller
requires the matching session exit-loop, no later activity except service cleanup,
valid immutable outcome evidence, matching generation and process identity, no
productive descendants, and no live or unknown independent resource owner. Only
that child is stopped; its runner records the actual exit. No acceptance or age
reset is synthesized. Unknown states remain protected. Windows termination checks
creation time and stops through the same process handle.

Dashboard helper reservations are split into running, queued, report-ready and
recovery counts. launches_per_tick may be raised from 1 to 2 (hard maximum 4)
to activate additional paid workers; model pacing and measured RAM admission are
rechecked. Existing implementation/recovery retains priority over helper discovery.
Prepared relative paths are resolved against the canonical workspace before the
runner changes directory, preventing failed starts such as PanModoki #220.
