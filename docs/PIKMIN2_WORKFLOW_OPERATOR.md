# Operating the workflow

Current-state guide for the person running the Pikmin 2 workflow. Contracts live in
[PIKMIN2_WORKFLOW.md](PIKMIN2_WORKFLOW.md) (lanes, registry, handoffs, approvals),
[PIKMIN2_CONTROLLER.md](PIKMIN2_CONTROLLER.md) (controller, deployment, wakes) and
[PIKMIN2_THROUGHPUT.md](PIKMIN2_THROUGHPUT.md) (pool, batching, dashboard). Native work
also follows [PIKMIN2_IMPLEMENTATION_FANOUT.md](PIKMIN2_IMPLEMENTATION_FANOUT.md).
Commands below run from the canonical root, `C:/Users/alari/pikmin-randomizer`.

## Start here: read-only commands

| Question | Command |
|---|---|
| What is stuck, why, and what only I can do? | `py -3.12 scripts/workflow_module.py inspect stuck` |
| Only the asks waiting on me | `py -3.12 scripts/workflow_module.py inspect needs-you` |
| Why is this lane where it is; why is it not being woken? | `py -3.12 scripts/workflow_module.py inspect lane <key>` |
| Its launches (reason, exit code, tools started) | `py -3.12 scripts/workflow_module.py inspect launches <key> [--limit N]` |
| A helper lane's open planner assignment | `py -3.12 scripts/workflow_module.py inspect assignment <lane>` |
| Config, heads of every checkout, controller release | `py -3.12 scripts/workflow_module.py inspect config` |
| Receipt, admission and batch actions | `py -3.12 -m workflow.operator [--json]` |
| Is the controller alive, supervised and on clean code? | `py -3.12 scripts/workflow_module.py service status --root <root>` |
| Stall streaks and parked lanes | `py -3.12 scripts/workflow_module.py no_progress --root <root>` |
| Audit integration receipts / approvals | `py -3.12 scripts/workflow_module.py landing_audit --root <root> [--approvals]` |
| Evaluate a committed review packet | `py -3.12 scripts/workflow_module.py review_packet verify --root <root> --packet <path>` |

`inspect` defaults to `--root .`, reads with SQLite `mode=ro` and `PRAGMA query_only`,
decodes only the sections a verb needs, never imports `workflow.registry` and never
calls a write path (it shares pure helpers with modules that also write; its registry
view refuses every write), and works on the live WAL registry while the writer is
contended. `--db <file>` reads a backup copy without the workspace check, with the
config of the copy's own root unless `--root` or `--config` is given; when no config
is found, a machine-wide `config_unread` item says so and nothing config-derived is
claimed. `--json` gives everything; text output is UTF-8 whatever the console code
page. `lane`, `launches` and `assignment` refuse an unknown lane key; `lane` and
`launches` include launches moved to the registry archive (`archived`). `stuck`
probes worker processes for the available-worker count (several seconds);
`needs-you` does not. `workflow.operator` prints the same Needs-you and blocker
sections above its receipt actions and folds done-lane export-evidence audit rows
into one count line. The dashboard, output/workflow/controller/throughput.html, shows
Needs you and the blocker groups at the top with every list capped (20 items, 12
groups, 10 lanes per item, 400 characters of text). If the view cannot be built, the
dashboard and `workflow.operator` say "Needs you unavailable" with the error, never
an empty list.
Workers are told to read state with the same `inspect` command (the release's
absolute path) instead of writing Registry or sqlite scripts.

## Reading `inspect stuck`

**Needs you** comes first, oldest and widest first:

| Kind | Meaning | What to do |
|---|---|---|
| `user_decision` | A lane recorded a user-owned decision (support_actions `external`) and still waits at the generation it was asked about (a relaunched lane's older asks drop out). One row per lane and kind with how often it was asked, first-ask age, up to three distinct wordings and how many blocked lanes wait on it (transitively) | Decide. There is no operator write command yet: give the answer as hashed evidence the lane or a reviewer lane can cite, or retire the lane if the answer is no |
| `user_asset` | A lane needs an asset only you can supply (same openness rule) | Put it at a stable path and record its path and sha256 where the lane can cite it |
| `toolchain` | A `user_asset` ask naming the compiler/toolchain (decisions never count): listed while its lane still waits on it, and for 72 h after the ask once that lane moved on | Fix the machine; native builds and fixture reruns fail until then |
| `prerequisite_needs_human` | A prerequisite request was offered to the coordinator twice without a disposition | Link a producer (`prerequisite_queue` resolve) or record the user-owned `external_input` |
| `unsupervised_lane` | A stopped lane has no launch config, so nothing wakes it (dropped once the lane is launch-configured or done) | `configure-lane-launch`, or retire it |
| `shared_review_target_dead` | A routed shared-review owner is stopped and unsupervised; its packet is held (dropped once the owner is configured, alive or done) | Supervise the owner or fix `shared_review_routing.files` |
| `shepherd_escalation` | Three failed shepherd calls for one packet, or an uncertain shepherd launch | Read output/workflow/controller/shepherd-attention.json and the escalated notices |
| `packet_refused` | A recorded review packet request was refused for lack of `integration_lines.root` (only when the line was removed between request and decision) | Declare the line, land the packet there, re-request |

**Machine-wide** lists the controller down (or no claim), a RAM launch pause, a
build-admission pause, `config_unread`, and `integration_lines_undeclared` (review
packets cannot be re-pinned, requested or decided; landings are checked against any
branch; the item counts open lanes holding shared hooks). `review_packet request`
refuses before recording anything while the line is undeclared, so that item, not
`packet_refused`, is where those refusals show.

**Blocked lanes by structured blocker.** Each blocked or waiting lane's references
come from its dependency text (`#N` and `4laric/pikmin-randomizer#N` become `#N`;
another repository's `owner/repo#N` stays external and no local lane owns it; lane
names become lanes), its producer link at current pins, the classification of its
current snapshot, its structured `shared_hooks`, and open user asks. A lane's own
issue and name are dropped; `#632` (captain safety policy) is never a blocker. Each
reference resolves to its owner lane, and groups key on that owner: `#730` and
`challenge-stage-table-extension-native` form one group labelled with both. References
no lane owns (a decision issue, a user ask, an unowned or external issue) group on
the reference. A lane with several owners appears in each group. Owner states:

| Owner state | Meaning | Accountable / next action |
|---|---|---|
| `decision` | `#186` (config `consumer_wakeup.umbrella_issues`): no lane owns it | reviewer: record the shared-hook decision (`approvals shared-hook` from a reviewer lane, or `review_packet request`) |
| `missing` | No lane has that issue | planner: publish or link a producer |
| `live` | Owner ready, running, waiting or reconciling | producer: nothing unless it stalls |
| `handoff` | Owner holds a handoff or review-ready report | integrator: land it |
| `done_unlanded` | Owner done without an integration receipt | integrator: land its commits and record the receipt |
| `landed` | Owner integrated | the consumer verifies it on a prerequisite wake or holds on its own gap; `inspect lane` says which |
| `blocked` | Owner is itself blocked | unblock the owner first; `roots` follows blocked owners to the end of the chain |

Circular waits (A waits on B waits on A) are listed separately; break them by hand.
Lanes whose dependencies name nothing structured are listed as prose only. **Parked,
no progress** lists lanes the no-progress guard parked, with what they wait for and
`wake_after`. **Acceptance criteria only another owner can satisfy** lists blocked
lanes whose criteria require a `#186` decision, an integrator landing or the
maintained export: such a slice can never pass, so it can never hand off. Move the
criterion to the handoff's `shared_reviews` or `remaining_work` in a replacement
spec; `autofill.validate_spec` flags these (advisory, never refused) and records
them on the autofill item as `acceptance_lint`.

`throughput_runtime.autofill.clustered_blockers` is the same grouping restricted to
two or more lanes (field `covered` when the owner is live or holds a handoff); lanes
with no structured reference still cluster on identical normalized text. An empty
`consumer_wakeup.umbrella_issues` means no decision issues here, in `inspect` and in
the wake gate alike. On the live registry of 2026-09-19 it found 10 clusters: the
`#186` decision (15 lanes) and nine owner lanes.

## Lane states

`registry.TRANSITIONS` is authoritative:

| State | Meaning | Operator concern |
|---|---|---|
| `ready` | Waiting to launch | The controller dispatches it |
| `running` | A worker session owns it | Check progress, not liveness |
| `waiting_resource` | Waiting for a build lease | Leases and RAM admission decide |
| `blocked` | Terminal blocked outcome with dependencies | `inspect stuck` / `inspect lane` |
| `reconciling` | A stopped launch's outcome is being reconciled | Automatic; persistent means inspect the launch |
| `handoff_ready` / `integrating` | Handoff awaiting / in integration | The sole integrator acts |
| `review_ready` | Review-only report awaiting disposition | The integration owner accepts or rejects it |
| `done` | Integrated or reviewed | Receipts audit through `landing_audit` |

Two markers on blocked lanes: `capacity_parked` releases the lane's worker for other
work while the lane keeps its dependencies; `parked` (no-progress guard) means two
relaunches brought nothing new, so wakes wait for an unseen input or `wake_after`.
Neither clears a dependency. A worker runs one active slice at a time; a blocked
lane whose worker is busy elsewhere waits, and a due prerequisite wake reserves
that worker (`inspect lane` shows `worker_busy`).

## What to do

- **Answer asks** from Needs you first; they gate the most lanes.
- **Shared-hook (#186) decisions**: approvals are ledger rows written only by an
  authenticated reviewer lane from its own launch session; a handoff's own
  `approved` never counts and there is no operator approval command. A reviewer lane
  may cite your statement as hashed evidence. Out-of-band decisions on files a
  blocked lane does not own: `approvals shared-hook`; on ported landed bytes:
  `approvals landing-review`. Review packets are committed under
  `tools/review_packets/` ([PIKMIN2_REVIEW_PACKETS.md](PIKMIN2_REVIEW_PACKETS.md));
  `review_packet verify` is read-only, lanes ask with `review_packet request`, pins
  change only through `review_packet repin --show-diff`. Packets need
  `integration_lines.root` declared and the packet landed on that line.
- **Deliveries**: a closed batch is not a lane completion. Only `Registry.integrate`
  records integration, and only when the receipt commits provably contain the
  reviewed bytes (identical blobs, ancestry or a declared port). A port of a shared
  or engine file also needs an approved landing review by another lane, and the
  lander is the integrator's own launch session. Native lanes need actual export
  evidence; a file saying no export was performed is not evidence. Never cherry-pick
  a landed change again, rewrite hashes or reset a handoff's age.
- **Feeding workers**: pending specs are in output/workflow/autofill/manifest.json;
  planners publish through `planner_pool.merge_proposals`. A capability mismatch
  needs an authorized worker adaptation profile. Helper ceilings
  (`max_active`, `backpressure_planning_limit`, `integration_support_max_active`)
  may be JSON `null`; demand, workers, the execution reserve and RAM still bound
  concurrency.
- **Progress**: verify a current-generation tool result, source or evidence change,
  receipt or consumer check; running is not progress. Windows PIDs are identified by
  host and creation time; never kill a numeric PID from an old report.
- **Config**: output/workflow/controller/config.json; runtime launch specs live in
  `throughput_runtime.launch_specs`. Read current state before any mutation. Record
  scope, validation and remaining blockers on the assigned issue.

## Deploy and roll back

Production runs from an immutable release worktree under
`output/workflow/release/<short-sha>`, never from the canonical checkout.

1. `py -3.12 scripts/workflow_module.py service prepare-release --root <root> --ref <commit> --config <root>/output/workflow/controller/config.json --python <absolute python.exe>`
   creates the clean detached worktree and runs `tests/workflow_release_tests.txt`
   in it; it never touches the running controller.
2. From an operator shell (never an agent session):
   `& <root>\output\workflow\release\<sha>\scripts\Deploy-WorkflowRelease.ps1`.
   It creates STOP, waits for every controller and restart wrapper to exit (workers
   keep running; after `-TimeoutSeconds` it exits 1 leaving STOP), removes STOP,
   starts that release's `Start-Pikmin2Controller.ps1` hidden and prints
   `service status`.
3. Confirm `service status --root <root>`: the new sha, `dirty=False`, a wrapper parent; then
   `inspect stuck`.
4. Roll back by running `Deploy-WorkflowRelease.ps1` from the older release folder.
   Keep old release worktrees while any launch still names their CLI paths.

The controller reads config.json at start, so a config change takes effect on the next
deploy (rerun the running release's Deploy-WorkflowRelease.ps1). `integration_lines` is
the exception: landing and review-packet checks read it from the canonical config file
on every use, and the controller refuses to start with `integration_lines` from any
other config path. Details: [controller guide](PIKMIN2_CONTROLLER.md#deployment-from-a-pinned-release).

## Registry maintenance

The registry is output/workflow/registry.sqlite3 in documents-v1 storage and WAL
journal mode (`-wal` and `-shm` beside it). Readers use snapshots or `mode=ro`; do not
open it with `immutable=1`, SELECT body JSON by hand or write with UPDATE scripts.
Both commands below report only unless `--apply` is given, and `--apply` needs a
quiesced registry: stop the controller and its wrapper (STOP) and let worker CLIs
finish first.

- WAL: `py -3.12 scripts/workflow_module.py registry_wal --root <root> [--mode wal|delete] [--apply]`.
  It refuses unless the recorded controller is stopped and no connection holds the
  file, verifies an unchanged snapshot, a `mode=ro` reader, the wake waiter and
  `quick_check`, and restores the previous mode on failure. The mode lives in the
  file, so older releases use it too.
- Archive: `py -3.12 scripts/workflow_module.py registry_archive --root <root> --done-days N [--apply]`
  moves events, launches and actions of lanes done for more than N >= 1 days into
  output/workflow/registry-archive.sqlite3 and VACUUMs. Exit 2: refused, nothing
  removed. Exit 3: records moved but marking or VACUUM failed; rerun the same
  `--apply`. Lanes themselves never move; `registry_archive.history()` and `merged()`
  give full history. Anything reading older events of done lanes uses `merged()`.
- Storage migration (`workflow.storage --migrate`) is complete on the live registry;
  its backup is migration-time history, not a rollback image.

## Workspace topology

| Path | What it is |
|---|---|
| `C:/Users/alari/pikmin-randomizer` | Canonical root: the repository humans run commands from, and the workspace every `--root` names. Never deploy by editing it |
| `native/` | Maintained native tree, its own git repository (the `native` side of landings and exports) |
| `native/pikmin2-research/` | Nested research repository inside the native tree; not an integration line |
| config `integration_lines` | `{root: {repo, ref}, native: {repo, ref}}`: the reviewed lines landings and review packets are checked against; undeclared today |
| `output/workflow/registry.sqlite3` (+ `-wal`, `-shm`), `registry-archive.sqlite3` | Registry and its archive |
| `output/workflow/controller/` | Controller config, throughput.json/html, `*-stage-health.json`, error.json, shepherd-attention.json, `launches/<id>/` |
| `output/workflow/release/<short-sha>/` | Release worktrees; the controller and worker CLIs run from one |
| `output/workflow/autofill/` | Manifest, planning shards, `planning-shards/<scope>/prepared/<lane>-root|-native|-out` lane worktrees |
| `output/dsw/`, other `output/<lane>-*` | Older lane worktrees and build directories |

`inspect config` prints the heads of the root, native and research checkouts, the
declared integration lines, the controller's recorded release and the release
folders; `inspect lane <key>` compares a lane's worktree heads with the canonical
ones.

## Suggested Claude Code allowlist (read-only commands only)

Nothing writes this for you; add it to a settings file yourself if you want these
reads to run without prompts. Every entry below is read-only for all arguments.
Do not allowlist `scripts/pikmin2_workflow.py`, `workflow_module.py` as a whole,
`registry_wal`, `registry_archive`, `landing_audit` (its `--out` writes a file),
`review_packet` beyond `verify`, `delivery_contracts` (`--request` writes),
`Deploy-WorkflowRelease.ps1`, or `git diff`/`git log` (`--output=<file>` writes;
Claude Code already treats their plain forms as read-only).

```json
{
  "permissions": {
    "allow": [
      "Bash(py -3.12 scripts/workflow_module.py inspect:*)",
      "Bash(py -3.12 -m workflow.inspect:*)",
      "Bash(py -3.12 -m workflow.operator:*)",
      "Bash(py -3.12 scripts/workflow_module.py service status:*)",
      "Bash(py -3.12 scripts/workflow_module.py no_progress:*)",
      "Bash(py -3.12 scripts/workflow_module.py review_packet verify:*)",
      "Bash(git worktree list:*)",
      "Bash(git rev-parse:*)"
    ]
  }
}
```

## How the automation behaves (reference)

- **Dispatch.** The controller is the sole dispatcher, with separate launch,
  assignment and maintenance loops; a stage that raises is recorded in
  `dispatch-stage-health.json`, `launcher-stage-health.json` or
  `assignment-stage-health.json` and retried next pass. Prompts are written to the
  launch directory's prompt.txt; spawn failures leave a `spawn_error` result.
  Capacity checks skip the writer while the RAM pause state is unchanged and
  telemetry is under 15 s old.
- **Worker exits.** Runners stop their own child a few seconds after its turn ends
  and never stop a session for a rate limit once a tool started. An initial stream
  with no events after `terminal_idle_recovery.first_response_seconds` (default 300)
  is stopped after rechecking identities, logs, descendants and resources; bounded
  provider fallback follows. An unreadable child.json/result.json affects only its
  launch; with a dead runner and a proof that no child survives it becomes a crash
  (`crash.json`), otherwise it stays protected with `completion_record_unreadable`.
- **Process checks.** Exact identities (host, PID, creation time) that are dead are
  cached as dead; unknown results are cached for 5 seconds and only ever protect,
  never authorize recovery; alive is always rechecked.
- **Blocked work.** A blocked lane with hashed evidence and dead processes is
  capacity-parked in the assignment loop, releasing its worker. Consumers wake on
  new verified integration receipts of mapped producers (`consumer_wakeup`, see
  [throughput guide](PIKMIN2_THROUGHPUT.md)); `inspect lane` names the gate holding
  one. Repair planning gets one turn per unchanged blocked chain; dependency
  classification helpers record every dependency through
  `workflow.dependency_classification` as a typed contract, a support action or an
  `internal_blocker`, and never clear blocked state. Classified `owner_blocked`
  findings resume the owner once per snapshot; integration-review findings go to the
  sole integrator.
- **Support helpers.** `workflow.support_actions` records integration packets (wake
  the integrator), independently diagnosed repairs (one per source heads), verified
  producers, exact user-owned external inputs and stale dispositions, all with
  archived hashed evidence. Export preparation helpers rehearse minimal patches
  against the pinned destination; only the integrator exports and writes receipts.
  Stopped blocked planning helpers retire as unresolved (`review_disposition.resolved
  = false`).
- **Handoffs.** `freeze_handoffs_on_submit` preserves new handoffs in immutable
  bundles. A blocked producer with a valid exact-source export packet, or with every
  owned file approved in the ledger plus a current packet, gets one handoff
  re-presentation per source heads, and a validated pending resumption reserves its
  worker for 120 seconds. Aging review reports put obligations on new integration
  launches until accepted, resumed or deferred with `review_followup`.
- **Admission reconciliation.** Admitted families with open lanes are audited on
  each dashboard publication; the integration owner disposes them with
  `admission_reconciliation` (`retain` with a next action, or `superseded` with
  `no_remaining_delivery: true` and `covered_criteria`).
- **Typed delivery contracts.** `py -3.12 -m workflow.delivery_contracts --root <root>`
  prints grouped chains and unclassified dependencies; `--request` registers a
  contract (consumer, generation, producer, kind `review_artifact` /
  `source_integration` / `consumer_behavior`, requirement, acceptance_check, owner,
  evidence). Existing prose dependencies are never assumed satisfied.
- **Build leases.** The build-capacity monitor reaps confirmed-dead build lease
  owners every 15 seconds (`lease_reaped` events); live or unknown owners stay
  protected and no process is terminated.
- **Registry contention.** Writes take a FIFO in-process gate, then SQLite's
  writer lock; BEGIN, COMMIT and reads retry `database is locked` three times within
  about 28 s, then raise `RegistryBusy`; `scripts/pikmin2_workflow.py` exits 75 with
  `"busy": true`, so rerun the same command.
