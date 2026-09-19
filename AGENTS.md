# Muse admission wave: current execution policy (2026-09-15, #491)

This section supersedes historical conflicting workflow details below. Read the
maintained C:/Users/alari/pikmin-randomizer/AGENTS.md and docs/PIKMIN2_WORKFLOW.md.
Use the SINGLE C:/Users/alari/pikmin-randomizer/output/workflow/registry.sqlite3
through the maintained CLI with --root C:/Users/alari/pikmin-randomizer.
Native origin pushes are allowed on work branches, never default/main/master or
p2-integration or */p2-integration; never tags/force. Private runtime is exempt
from GL reservation. All heavy builds use the Muse wave leased runner and private
build directory. Keep one primary contributor per lane; no nested subagents in
this bounded ten-contributor launch. Do not edit the maintained root/native,
legacy worker worktrees, research checkouts, admission allowlists or seed defaults.
The live existing integrator owns promotion; submit candidate commits/evidence.
For ADMIT candidate evidence, natural gameplay is required; injected state/health,
forced transport and synthetic markers cannot close a natural admission gate.
The assigned brief names exact files and the workflow generation. Register before
edits, maintain meaningful checkpoints, validate handoffs, and stop at one ready
handoff or a documented dependency. King WarCry has passed; do not redo it.

## Historical wave notes (read as history where they conflict above)

# Pikmin Randomizer track

For P2 parallel work, follow [the current workflow](docs/PIKMIN2_WORKFLOW.md). Family owners implement and validate end-to-end in private worktrees, including routine additive native hooks and private builds. Earlier blanket requirements to stop for integration permission after each batch are superseded. Coordinate changes to shared semantics with the affected owner; serialize only maintained checkout/build/export writes and final integration.

Lane execution, resource leases, watchdog recovery and handoff validation follow
[the workflow operating contract](docs/PIKMIN2_WORKFLOW.md). Use one shared local
registry under `output/workflow/` across participating worktrees. Private runtime
launches are exempt from shared-runtime reservations; private build directories
still require exclusive ownership and respect the aggregate heavy-build budget.

P2 implementation agents must read [the fan-out and mandatory fixture baseline guide](docs/PIKMIN2_IMPLEMENTATION_FANOUT.md) before claiming or resuming work. Before the next runtime acceptance run, adopt the current starting-Pikmin overlay and 960×540 centred-window native startup, regenerate stale arenas, and record per-lane adoption evidence as required there. Existing active lanes are included.

Before starting any implementation, ensure its scope and acceptance criteria are written in a GitHub issue in 4laric/pikmin-randomizer and assign that issue to the authenticated account (currently 4laric). Record Codex as the implementation owner when using that shared account; do not imply a separate Codex GitHub identity. Update the issue with progress, commits, validation evidence and remaining work. Assignment indicates ownership, not that every backlog item is actively underway. This issue-first requirement also applies to work inside native/ and bbft/.

Work in this directory's native/ and bbft/ repositories. Original BBFT and decomp/pikmin-research checkouts belong to parallel work; do not edit them for this task. Read README.md for the snapshot boundary and next milestone. Keep builds, saves, generated seeds, logs and runtime state local and separate. Inspect inherited scripts for original absolute paths before executing. Do not relink the shared Archipelago installation. The source split and standalone seed/session foundation are implemented. Read DEVELOPMENT.md for build/test evidence and current limitations. Physical placement is still pinned; slot/carry-route audit, relocation, full native campaign resume and gameplay sign-off remain open.

## Headless opencode worker fan-out (lessons, 2026-09-14)

An orchestrating session (Claude) drove 19 DeepSeek V4 Pro workers, one per P2 family lane, through headless `opencode run --dir <root worktree> -m opencode/deepseek-v4-pro --auto`. Tooling lives in ignored `output/deepseek-wave/` (launcher, per-lane briefs, `status.py`, `slot.py` semaphores, `build_lane.py`). What we learned:

- **One root + one native worktree per lane, both branched from the integration pair** (`codex/p2-main-review` / `codex/p2-main-review-native`), not from whatever branch the orchestrator happens to be on. Native worktrees must be created with an absolute target path; a relative path from `git -C native` lands them inside `native/output/`.
- **Stagger launches.** Eighteen opencode instances booted at once all hung at `init` indefinitely; the same instances relaunched 25 s apart all came up. Treat opencode startup as a serialized resource.
- **Pass the brief by file path in the message**, not with `-f`: `run`'s `-f` is an array option and swallows the trailing message text. Tell the worker to read `prompts/lNN.md` with its file tool and follow it.
- **Workers run unattended, so the brief must pre-answer everything**: exact worktree paths, base commits, the single bounded slice, the six-gate reporting rule, absolute asset paths, the build/GL wrappers, and where to write the handoff plus a `DONE`/`BLOCKED` status file the orchestrator can poll.
- **Enforce host capacity with lock files, not prose.** `slot.py` limits native builds to 2 concurrent, integration to 1, and real-GL fixture runs to 2; workers build only through `build_lane.py`, which queues, configures Ninja + MinGW, runs `ninja -n`, and records the exe SHA-256 as evidence.
- **Workers commit on their lane branches and may push them; they do not file GitHub issues.** Push policy: fix/feature work branches only (`feature/**`, `fix/**`, `deepseek/**`, `claude/**`, `codex/**`) on the root and native remotes; never the default branch, tags, or force-pushes. The orchestrator reviews each handoff (diff + rebuild + focused tests), fixes small review findings directly on the lane branch, merges accepted slices with `--no-ff` onto a wave branch (`claude/p2-deepseek-wave` + `-native`), and only then hands to lane 01 / records evidence.
- **Review catches lane-local leakage.** The first handoff hardcoded its `native-l14` worktree path into a test destined for the integration line and included a tautological assertion; expect this class of defect and check for it.
- **Provider stream errors are transient.** A burst of `Endpoint is unavailable` hit 15 lanes within a minute; opencode retried and every session continued. Do not restart a worker on a stream error; only resume (`opencode run --session <id>`) if its process actually exits before writing a status file.
- **Detect liveness from process command lines** (`Win32_Process` filtered on `opencode.exe`, matching `--dir .../lNN-root`), not from a pid file: PowerShell `Tee-Object` and shell redirects mix UTF-16 and UTF-8 in the same file.
- **Resume, don't relaunch, for follow-on slices.** Keeping the session (`--session ses_...`) preserves the worker's context of its own diff and review feedback.

Idea to try next: have each opencode worker orchestrate its own 2–3 subagents (opencode's `@general`/subagent support) for the read-heavy phases (source audit, existing-candidate inventory, test writing) while keeping one primary session per lane for the native edit/build/handoff. This should cut per-lane wall-clock and let the expensive model spend tokens on the slice instead of on reading docs, at the cost of more concurrent startup and API load; stagger subagent spawns as well.

Subagent trial results (2026-09-14, lanes 02–33 follow-on slices): read-only `explore` delegations (source audit, candidate inventory) were adopted as-is in nearly every lane and cut per-slice wall-clock by an estimated 20–40 minutes. Delegated `general` test scaffolds were the weak spot: first-round outputs repeatedly injected state where it passed trivially, hardcoded lane paths, or asserted on a parallel function nobody calls; after one correction round the quality matched solo work. Two more lessons: (1) a worker session started from a pre-addendum prompt may not have the `task` tool at all (lane 02 reported it absent twice) — check the tool list before requiring delegation; (2) one delegated audit conclusion ("min-uid dwarf slot") was the direct cause of a later stage-mismatch bug, so treat subagent audit conclusions as claims to verify, not facts. Merge order matters with many lanes touching the same host seams: keep both sides on conflicts in `pc_p2_batch2.cpp` / `pc_p2_projectiles.cpp` include-and-clip chains, and compile the single object before committing the merge.

Resume pitfall (2026-09-14): an opencode worker that spawned subagents leaves several `session.id=ses_...` values in its log. Only the FIRST one is the primary session; the others are child sessions with no `task` tool and a narrower constraint prompt. Resuming a child looks like it works (it reads the brief and edits files) but it cannot delegate and may refuse builds/commits. Record the primary id at launch (`session.id=` first occurrence) and resume only that.

Gate evidence contract (2026-09-14): `docs/PIKMIN2_ENEMY_ROSTER.md` §"Gate table format" is the contract lane 02's ingestion (`scripts/ingest_p2_handoff_gates.py`) reads; `scripts/check_p2_handoff_gates.py <handoff>` tells a lane which PASS rows would be refused (uncited, injected, wrong token order). Roster admission stays at zero until family handoffs cite real log files in that format, so every worker brief now appends `prompts/gate-table-addendum.md` and the integrator regenerates `docs/PIKMIN2_ROSTER_ADVANCE_REPORT.md` after merges.

Lessons (2026-09-15/16, DeepSeek integrator v2 + paid Muse wave): a single opencode session held the lane-01 integrator role for ~8 h and drove 17 merges (P2 lane 19 + Muse lanes 52–67) plus six review-lane acceptances through the serialized loop — merge under the `slot.py integrate` lock, one `build_lane.py wave`, checker→ingest→advance-report, engine re-export, `codex/p2-main-review` checkpoint, MinGW sweep. What worked: the lock kept one writer on the wave; `--no-ff` merges of dependency-consuming branches were conflict-free because git de-dupes identical cherry-picks; the checker/ingest contract cleanly separated accepted PASS rows from refused/injected ones. What bit: (1) the controller's `receipt()` requires the lane's *current* registry generation; two receipts written with the handoff's generation (1 vs 2) were refused as stale ownership and the LLM shepherd misdiagnosed the same failures as a "non-existent output/dsw" — verify the generation before believing a receipt diagnosis. (2) Receipt ancestry is directional: the lane head must be an ancestor of the integrated wave commit, so producer-head substitution is wrong. (3) Hand-editing `transport_reward`/`delivery_receipt` for a natural receipt made 54/57/78 admission candidates and correctly turned the deny-by-default suite red (19 failures) — that red is the intended signal, not a regression. (4) Muse workers on the free `muse-spark-1.3-contributor-free` provider wedged on rate limits with uncommitted work; moving sessions to `opencode-go/muse-spark-1.3-contributor` resumed them, so commit early per checkpoint. (5) The cave wave (l42–l51) is a separate divergent line (163 files/19.4k insertions since the fork at `64d6adef`); merging it into the P2 wave would revert work — keep separate integrators. (6) Roster `admit-check` marks every PASS `<gate>:injected` when the entry's notes contain a `NONNATURAL_MARKERS` word ("vehicle"/"host"/"proxy"), even for otherwise-natural evidence; wording hygiene gates admission as much as evidence does.

## Build isolation (required)

`native/build-randomizer` is a single shared resource. Do **not** run your regular builds in it — agents queuing on the one maintained build dir is the pipeline's main bottleneck. Build in your own environment so lanes can compile in parallel.

- Work in your own `native/` git worktree/branch (e.g. `output/native-<lane>` switched to a `opencode/*` branch). Keep uncommitted build work out of the shared `native/` checkout, which the integration lead also uses.
- Configure a private build directory under ignored `output/`, matching the maintained generator and toolchain, then build there:
  ```powershell
  $env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
  cmake -S output/native-<lane> -B output/native-<lane>-build -G Ninja -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++
  cmake --build output/native-<lane>-build --target pikmin_pc -j 6
  cmake --build output/native-<lane>-build --target pikmin_pc -- -n   # expect: ninja: no work to do.
  ```
  Generator is Ninja (the Python-bundled `ninja.exe`); compiler is `C:/msys64/mingw64/bin/g++.exe`. See `docs/PIKMIN2_BATCH_RESOURCES.md` §2.
- Never run two heavy build/link jobs in the same build directory, and never check a build directory in.
- Only the integration lead builds `native/build-randomizer` for the maintained line, after a fast-forward/merge, and then runs `py -3.12 scripts/export_native_source.py`. Do not hold that directory for exploratory builds.
- Record build evidence per attempt: pinned commit, private build dir, executable SHA-256, and the `ninja -n` dry-run result.

Keep private build dirs, builds, saves, generated seeds, logs and runtime state under ignored `output/`.

## Git push policy

Agents may commit freely on their work branches and **may `git push` to root `origin` on fix/feature branches** — `feature/**`, `fix/**`, and the wave work branches `deepseek/**`, `claude/**`, `codex/**`. **Native work branches may be pushed to native `origin`**, including existing lane branch names. Never push the default branch (`main`/`master`), `p2-integration`, or a namespaced branch ending in `/p2-integration`; never push tags or force-push. Verify the remote rather than guessing it. Record what was pushed (branch + commit) in the handoff or report. Issue-first tracking still governs GitHub issue writes.

## Export does not wait on a clean shared `native/`

The shared `native/` checkout normally carries a recorded dirty baseline from other lanes (for example `src/plugPikiKando/creatureCollision.cpp` and `goalItem.cpp`, plus occasional transient merge/untracked files from parallel workers). That baseline is expected and is part of the exported source. Do **not** block on, wait for, or attempt to clean the shared checkout before exporting, and do not treat its dirty state as a precondition for integration.

- The maintained export runs from the integration line after its fast-forward/merge and copies the recorded working-tree state as-is:
  ```powershell
  py -3.12 scripts/export_native_source.py
  # or export directly from a private native worktree, never touching the shared checkout:
  py -3.12 scripts/export_native_source.py --source output/native-<lane>
  ```
- Only the integration lead runs the maintained export; lanes keep their own uncommitted work out of the shared checkout by using private `native/` worktrees (§Build isolation) and commit native changes on their own branch.
- Record the native commit **and** dirty state with any export evidence. Native work branches may be pushed to origin under the Git push policy above; never push default/p2-integration branches, tags, or force-pushes.

## Stock asset sources (check before asking the user)

- Pikmin 1 engine stock assets (dataDir, stages, courses/pikmin2room): `C:/Users/alari/bbft/dist/cohesion/pikmin/assets`
  (e.g. `dataDir/stages/chal0/default.gen`, sha256 eeb58bacfb1dc7235a99c95ac6d5e019ed09547aab066cf8f9132edc43ff9972).
- Pikmin 2 retail disc: `C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso`
  (sha256 5388b54a9c2d156c94bcfa80acd53b513288dc17e88c97a1edfb57ad25db661a). Extract with the
  experimental/pikmin2_* tools (e.g. `pikmin2_white.py --iso` for white_* room models).
- Recorded user answers with hashes: `output/workflow/user-answers/`.

## Integration lines (canonical)

Land root work only on `codex/p2-main-review` and native work only on `claude/p2-deepseek-wave-native`
(declared as `integration_lines` in the controller config). `codex/content-lanes-531` and
`claude/p2-deepseek-wave` are merged and closed: never land or push to them.
