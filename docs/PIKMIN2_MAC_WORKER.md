# Optional Mac worker pilot

Preparation tracked in #512. Implementation owner: Codex through shared account
4laric. This is an opt-in worker path; the maintained Windows controller remains
the coordinator and sole integration owner. No Mac is enrolled by checking out
these files. Existing Windows lanes are not migrated.

## What the Mac can do

- Source investigation, bounded edits, reviews, and compatible Python tests.
- One job at a time, claimed only when its approved capabilities match.
- Native C++ source edits when the job includes a pinned native repository.
  The resulting candidate still needs Windows build/runtime validation.

Mac provisioning rejects `windows-build` and `windows-runtime` capabilities.
The Mac does not run the Windows controller, `/proc` process adapter, fixture
launchers, or maintained integration build. It talks only to the remote API.
OpenCode inference remains provider-side; provider limits can still be shared
with Windows. The pilot's local RAM ceiling is 75%, independent of the Windows
controller's configured limit.

## Architecture and limits

The SQLite registry stays on the Windows coordinator's local disk. Never sync it
with the Mac or put it on a network share. `pikmin2_coordinator.py serve` exposes
only registration, claims, heartbeats, artifact uploads and result submission.
It binds **127.0.0.1 only**. Use an authenticated SSH tunnel to reach it; SSH access
to Windows must already be configured. This preparation does not install an SSH
server, open firewall ports, start a public service, or distribute credentials.

The local administration CLI is the only way to provision/revoke workers, enqueue,
requeue or close jobs. Tokens are scoped to one preapproved worker. The remote
API cannot create jobs, change capabilities, merge source, mark local lanes done,
or grant ADMIT. Provisioning stores a token hash in the registry and writes the
secret only to ignored `output/workflow/remote/credentials/`. Keep that directory
private to your OS account; file mode 0600 applies on POSIX, while Windows relies
on the account's directory ACL. Revoke and provision a new worker ID to rotate.

Source commits and evidence are proposals. Server receipt checks hashes and
attempt ownership; it does **not** prove gameplay acceptance or that a pushed
commit contains what the contributor claims. The integrator must fetch and review
the exact commits and run required Windows checks.

## 1. Prepare Windows when the Mac is available

From the maintained project directory, with the registry initialized:

```powershell
py -3.12 scripts/pikmin2_coordinator.py --request examples/pikmin2-workflow/mac-worker.json provision
py -3.12 scripts/pikmin2_coordinator.py serve
```

The first command prints a credential **file path**, not the token. Transfer that
file privately to the Mac as `output/mac-credentials.json`. Do not put it in an
issue, commit or chat. Provision once; a duplicate command refuses to overwrite
the credential. The foreground server can be stopped with Ctrl+C. For unattended
use, launch it through an existing hidden supervisor; reboot persistence is not
installed by this preparation.

## 2. Bootstrap the Mac

Install Python 3.12+, Git, OpenCode and SSH; authenticate GitHub and the paid Muse
provider locally. An Apple Silicon or Intel Mac uses the same worker commands.
Clone the tooling branch, then:

```sh
git clone --branch codex/workflow-mac-worker https://github.com/4laric/pikmin-randomizer.git
cd pikmin-randomizer
python3 -m venv output/worker-venv
source output/worker-venv/bin/activate
python -m pip install -r requirements-worker.txt
python scripts/pikmin2_worker.py doctor
chmod 600 output/mac-credentials.json
```

The doctor checks the actual OS/architecture, Python version, Git/OpenCode paths
and portable RAM measurement. It does not certify provider authentication or
native game support. Keep the checkout in a normal local directory, outside a
cloud-synchronized folder. Do not copy Windows `output/`, OpenCode session stores,
build caches or controller configuration onto the Mac.

In another terminal, replace the SSH destination with the Windows host:

```sh
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:8791:127.0.0.1:8791 alari@WINDOWS_HOST
```

Then register without claiming work:

```sh
python scripts/pikmin2_worker.py register --credentials output/mac-credentials.json
```

Registration can be repeated. A different worker instance cannot replace a live
one; the old registration must expire first. Do not copy `output/remote-worker/`
between machines. Use a separate worker ID/credential for every machine.

## 3. Queue one issue-backed pilot from Windows

Copy `examples/pikmin2-workflow/remote-job.json` into ignored `output/` and replace
every placeholder. The issue must be open, assigned to 4laric, and already contain
the exact acceptance criteria in its body. Record Codex as the implementation
owner. Reserve specific file paths; overlapping local or remote ownership is
rejected in both directions, including parent-directory overlap with remote work.

The source URL must be the canonical network repository, and the full commit
must be published at the named branch tip when queueing. The existing Windows
native `origin` may point at a **local research directory**: that is not a source
the Mac can fetch. Publish the required feature branch to the approved native
GitHub fork first; this workflow does not remap or push existing remotes for you.

Optional native source entry:

```json
"native": {
  "url": "https://github.com/4laric/Open-Nectar---Pikmin-Native-PC-Port.git",
  "ref": "refs/heads/codex/YOUR_PUBLISHED_NATIVE_BRANCH",
  "commit": "FULL_40_CHARACTER_COMMIT"
}
```

```powershell
py -3.12 scripts/pikmin2_coordinator.py --request output/mac-pilot-job.json enqueue
py -3.12 scripts/pikmin2_coordinator.py status
```

Start with a small review or Python-only task whose files are not already owned.
Do not reserve an active Muse family again. The pilot is deliberately one job per
invocation, rather than a new unattended contributor fleet:

```sh
python scripts/pikmin2_worker.py work --credentials output/mac-credentials.json
```

Each attempt fetches pinned source into
`output/remote-worker/attempts/<job>/<attempt>/root`. Native, if supplied, is a
separate Git repository at `root/native`. Changes use
`codex/remote-<job>-<generation>`; only that feature branch may be pushed. The
contributor receives the assigned scope, acceptance criteria and Windows review
requirement. No default/integration branch, tag or force pushes are authorized.

## 4. Results and Windows validation

The contributor writes `output/remote-result.json` in its private root:

```json
{"outcome":"candidate","summary":"Changes, tests run, and remaining Windows validation"}
```

Outcomes are `candidate`, `review`, or `blocked`. Missing reports, dirty Git trees
or nonzero OpenCode exit codes require reconciliation. A clean candidate goes to
`awaiting_windows_validation`; other reports go to `awaiting_review`. Neither
state completes a local lane. Small evidence bundles are uploaded by SHA-256,
at most 1 MiB per artifact and 20 artifacts per attempt. Full logs, binaries and
assets remain on the Mac. The maintained controller routes result notifications
to the existing integrator inbox without requiring a smart-model decision.

The integrator reads `output/workflow/remote/results/`, fetches the reported root
and native commits, reviews diffs and issue evidence, and performs the required
Windows build/runtime checks. Before returning source ownership to a Windows lane,
close the remote reservation with a recorded disposition:

```json
{"job":"mac-pilot-review","summary":"Reviewed proposal; transferred exact commits to the named Windows validation issue/lane"}
```

```powershell
py -3.12 scripts/pikmin2_coordinator.py --request output/mac-pilot-disposition.json close
```

This releases the reservation; it does not merge or admit anything. Follow the
normal issue-first local lane registration and integration process afterward.

## Sleep, disconnect and retries

Workers renew a 180-second lease every 20 seconds. A disconnected Mac can finish
private work, but expired attempts cannot publish authoritative results. A lost
claim response retries the same durable request; a saved `launch.claim` prevents
running the same attempt twice. Losing a worker is never proof its processes died.

The coordinator does not automatically reassign expired jobs. Inspect the attempt
and choose whether to reconcile its output or explicitly requeue with
`{"job":"mac-pilot-review"}` and the local `requeue` command. A new attempt has a
new generation and directory; late old results are rejected. Ownership remains
reserved while the Mac is offline. To revoke access, use `{"worker":"mac-pilot"}`
with the local `revoke` command.

If only the submission response was lost, retry the saved result without rerunning
OpenCode:

```sh
python scripts/pikmin2_worker.py retry-result --credentials output/mac-credentials.json \
  --attempt output/remote-worker/attempts/JOB/ATTEMPT
```

Identical accepted results replay safely even after expiration. An expired,
unaccepted result needs integrator reconciliation. If a worker process crashed,
inspect surviving OpenCode/tool processes before removing `work.lock`; do not
delete its attempt directory or `launch.claim` to force a restart.

## Validation boundary

Protocol, registry and HTTP tests run on Windows, including a real local Git
checkout and stand-in child process through the upload/result path. This does not
constitute a real macOS/OpenCode pilot. Before expanding, verify Mac credentials,
claim/heartbeat, one review result, sleep/disconnect fencing and Windows receipt.
Keep the existing Windows worker fleet unchanged until that pilot passes.
