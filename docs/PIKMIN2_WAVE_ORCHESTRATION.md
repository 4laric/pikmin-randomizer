# Pikmin 2 wave orchestration playbook (DeepSeek multi-lane fan-out)

Reusable recipe for running a large parallel implementation "wave": one
long-running **orchestrator** (lane 01) plus N **worker lanes**, all headless
DeepSeek opencode sessions, with review → fix → merge → ingest loops and a
watchdog that keeps the orchestrator alive.

Written 2026-09-15 after the 33-lane P2 enemy-roster wave. This documents the
process, not any single lane's findings. Companion docs:
`PIKMIN2_IMPLEMENTATION_FANOUT.md` (fixture baseline every lane must adopt),
`PIKMIN2_BATCH_RESOURCES.md` (build isolation), repo `AGENTS.md` (hard rules).

---

## 1. Topology

```
lane 01 orchestrator (1 long-running agent)  ── polls, reviews, merges, builds, reports
        │  launches/resumes via resume.ps1
        ├── lane 07 worker  (root worktree + native worktree + private build dir)
        ├── lane 12 worker
        └── … one opencode process per active lane
```

- **Workers** each own a lane: their own `output/dsw/lNN-root` (root repo) and
  `output/dsw/native-lNN` (engine repo) git worktrees, a private build dir
  `output/dsw/native-lNN-build`, and evidence under `output/dsw/lNN-out/`.
- **Orchestrator** owns the integration worktrees `output/dsw/wave-root`,
  `output/dsw/native-wave`, and `output/p2-main-review` (local `native` junction
  → `native-wave`). Workers never touch those.
- Exactly **one orchestrator**. A second one is the most common cause of "the
  launch went nowhere".

## 2. Layout (`output/deepseek-wave/` = the wave tooling, gitignored)

| Path | Purpose |
|---|---|
| `prompts/lNN-<tag>.md` | the brief a worker reads (slice / fix rounds) |
| `prompts/l01-orchestrator*.md` | orchestrator brief (+ addenda) |
| `prompts/subagent-addendum.md`, `prompts/gate-table-addendum.md` | appended to every code / every brief |
| `review-template.md` | the procedure handed to reviewer subagents |
| `handoffs/lNN.md` | worker handoff (copy of the lane's `docs/PIKMIN2_LANE…`) |
| `handoffs/lNN.status` | `DONE <tag>` / `BLOCKED <tag>: reason`; **absent while running** |
| `handoffs/reviews/lNN.md` | review verdict file (`LANE/TAG/VERDICT/ACTION/…`) |
| `handoffs/l01-report.md` | orchestrator's per-cycle report |
| `ledger.md` | append-only integration log (authoritative history) |
| `inbox/*.md` → `inbox/done/` | user → orchestrator directives (`ADMIT`, `PUSH`, `HOLD`, …) |
| `claims/lNN` | single source of truth for who may touch a lane |
| `logs/` | per-run `.log`/`.err`, `pids.txt`, watchdog + heartbeat |
| `sessions.txt` | `lNN ses_…` primary session per lane (l01 included) |
| `launch.ps1`, `resume.ps1`, `launch_orchestrator.ps1`, `watch_orchestrator.ps1` | lifecycle scripts |
| `status.py`, `claim.py`, `inbox.py`, `slot.py`, `build_lane.py` | tooling |

## 3. Hard rules (unchanged from AGENTS.md / the lane briefs)

- **Push policy (relaxed 2026-09-15).** Agents may commit freely and may
  `git push` on fix/feature work branches — `feature/**`, `fix/**`,
  `deepseek/**`, `claude/**`, `codex/**` — on the root and native remotes. Never
  push the default branch (`main`/`master`), tags, or force-pushes. GitHub issue
  writes are separate and still user-governed.
- **Never edit** the shared `native/` checkout, `native/build-randomizer`, or the
  main repo checkout. Work only in `output/dsw/**` and `output/p2-main-review`.
- **Honest six gates.** Natural evidence only is PASS; injected/forced/proxy is
  `UNTESTED (injected)`. A receipt never launders into a PASS.
- **Claims + inbox are authoritative.** Check `claim.py check lNN --owner
  orchestrator`; exit 3 = held by a user agent → skip the lane entirely.
- **Build isolation:** private build dirs, Ninja + `C:\msys64\mingw64\bin` g++.
  Only the integration lead builds the wave line, one build at a time.
- Some lanes belong to another agent (e.g. codex lanes 08/25/28/29/30): never
  launch, review, merge, or touch them.

## 4. Per-lane lifecycle

1. **Brief** — orchestrator writes `prompts/lNN-<tag>.md` (blocking items first,
   file:line, commit-message prefix, status contract, then appends
   `subagent-addendum.md` for code lanes and `gate-table-addendum.md` always).
2. **Launch / resume** — `launch.ps1` (new) or `resume.ps1` (existing primary
   session, from `sessions.txt`). Both acquire a claim and set the permission
   config (see §6). Only the **primary** session can delegate via `task`.
3. **Work** — worker edits its worktrees, builds privately, runs GL fixtures via
   `slot.py run gl lNN`, runs tests, commits on `deepseek/p2-lNN` +
   `deepseek/p2-lNN-native`, writes the handoff and `handoffs/lNN.status`.
4. **Review** — orchestrator spawns a `general` reviewer subagent (max 3, 10 s
   stagger) with `review-template.md`; the reviewer writes
   `handoffs/reviews/lNN.md`: `VERDICT: MERGE | MERGE-WITH-FIXES | BLOCK | REJECT`
   + `ACTION` (merge-now / hold-for-fix).
5. **Act** — MERGE / tiny-fix → integrator commits then `git merge --no-ff` into
   `wave-root` (+ `native-wave`); keep both sides in conflicts. Substantive fixes
   → write the next `prompts/lNN-<nexttag>.md`, delete `lNN.status`, `resume.ps1`.
6. **Integrate** — after native merges queue **one** wave build; then ingest the
   handoff (`check_p2_handoff_gates.py` → `ingest_p2_handoff_gates.py --apply` →
   `generate_p2_advance_report.py`); checkpoint (re-export `engine/`, merge into
   `p2-main-review`, sweep `pytest -k pikmin2`).
7. **Park** — scope complete → ledger note, no resume.

## 5. Tooling reference

```powershell
# status + claims
py -3.12 output/deepseek-wave/status.py
py -3.12 output/deepseek-wave/claim.py status
py -3.12 output/deepseek-wave/claim.py whose lNN
# user directives
py -3.12 output/deepseek-wave/inbox.py list
# launch/resume a worker
powershell -File output/deepseek-wave/launch.ps1  -Lanes 14,15,16
powershell -File output/deepseek-wave/resume.ps1 -Lane 07 -Session <ses_…> -Brief l07-fix2.md -Owner orchestrator
# orchestrator
powershell -File output/deepseek-wave/launch_orchestrator.ps1 -Session <ses_…> -Brief l01-orchestrator.md
```

Live-lane liveness (never parse `logs/pids.txt`; it is mixed UTF-16/UTF-8):

```powershell
Get-CimInstance Win32_Process -Filter "name='opencode.exe'" |
  ForEach-Object { ($_.CommandLine | Select-String 'dsw.(l[0-9][0-9])-root') -replace '.*dsw.(l[0-9][0-9])-root.*','$1' }
```

## 6. Reliability kit (the part that makes it survive unattended)

Headless `opencode run` **cannot answer an interactive prompt**. Two failure
modes were observed: (a) a run wedges forever on
`message=asking … permission=external_directory`; (b) a provider
`AI_APICallError: socket connection was closed unexpectedly` ends the run with no
notice. Fixes, all additive and applied to **new** launches only:

- **Permission allowlist** — `output/deepseek-wave/opencode.wave.json` sets
  `permission.external_directory` to `allow` for `pikmin-randomizer/**` and
  `bbft/**` (everything else stays `ask`). The three launch scripts set
  `$env:OPENCODE_CONFIG` to it, so workers and their subagents inherit it. A
  fresh orchestrator run showed **0 `asking` events** (previously 46).
- **Idempotent orchestrator launch** — `launch_orchestrator.ps1` refuses to start
  a second orchestrator on `wave-root` (use `-Force`), and writes
  `logs/orchestrator.pid`.
- **Heartbeat** — the orchestrator brief writes
  `logs/orchestrator-heartbeat.txt` at the top of each cycle.
- **Watchdog** — `watch_orchestrator.ps1` supervises the wave-root process:
  if it **dies**, it resumes the primary session from `sessions.txt` (`l01 …`);
  with `-KillStalled` it also kills a wedged run (heartbeat/run-log older than
  `-StaleMinutes`, default 12) and resumes it. `-Once` for a scheduler; a
  `logs/orchestrator-watchdog.stop` sentinel stops it. Cooldown 150 s prevents
  restart storms.

Start it detached (survives the launching agent):

```powershell
Start-Process powershell -ArgumentList '-NoProfile','-File',
  'C:\Users\alari\pikmin-randomizer\output\deepseek-wave\watch_orchestrator.ps1','-KillStalled' -WindowStyle Hidden
```

If the orchestrator is ever moved to a **new** session, update the `l01` line in
`sessions.txt` and restart the watchdog.

## 7. Review & fix loop contracts

- Reviewer verdict files (`handoffs/reviews/lNN.md`) are plain key/value blocks:
  `LANE / TAG / VERDICT / ACTION / ROOT_BRANCH / NATIVE_BRANCH /
  INTEGRATOR_NOTICES / BLOCKING / NOTE`. `BLOCKING: none` is explicit.
- Fix briefs restate the verified state, list blocking items first with
  file:line, name the exact acceptance evidence, the commit-message prefix, and
  end with `write handoffs/lNN.status as DONE <tag> or BLOCKED <tag>: <file:line>`.
- Re-review after every fix round; a lane stays `hold-for-fix` until its blocking
  list is empty. Doc-only notices (stale citations, wrong commit lists) are
  integrator fixes, not blockers.

## 8. Known pitfalls (learned the hard way)

- **Duplicate orchestrators** / relaunching on a fresh `--title` session instead
  of `--session` → two agents fighting. Launch is now idempotent.
- **Permission asks** wedge headless runs (fixed by §6 allowlist).
- **Provider socket drops** end a run silently → the watchdog resumes.
- **One wave build at a time**; never merge `native-wave` mid-build; a second
  concurrent build in the same dir fails with `File can't be removed`.
- **`git add -A` slip** once swept a lane's untracked tools into a commit — scope
  adds to intended paths.
- **Resume picked a child session** (alphabetically first) instead of the lane's
  primary → the child lacked the `task` tool. `sessions.txt` must map a lane to
  the FIRST `session.id=` in its `.err`, i.e. the primary.
- **`logs/pids.txt`** is mixed UTF-16/UTF-8 — do not parse it.
- Keep `windows` default `960x540` for the standard acceptance launch; record any
  override.

## 9. Admission (user-owned)

`ADMIT <id>` in the inbox only nominates and reports an `ADMISSION CANDIDATE`;
the actual write (`audit_pikmin2_roster.py --write-admission`, flipping the
deny-by-default tests, re-export, sweep) requires an explicit user approval in
the directive's `detail` line. The orchestrator never admits on its own.

## 10. Bootstrap checklist for a future wave

1. Create per-lane worktrees `output/dsw/lNN-root` + `output/dsw/native-lNN` and
   private build dirs; record the starting Pikmin overlay + 960×540 startup
   (see `PIKMIN2_IMPLEMENTATION_FANOUT.md`).
2. Populate `prompts/lNN.md` for each lane; append the subagent and gate-table
   addenda.
3. Ensure `opencode.wave.json` exists and the launch scripts set
   `OPENCODE_CONFIG`.
4. Add each lane's primary session to `sessions.txt` as
   `lNN ses_…` (including `l01`).
5. Launch the orchestrator: `launch_orchestrator.ps1 -Brief l01-orchestrator.md`.
6. Start the watchdog with `-KillStalled`, detached.
7. Drive with inbox directives; read `handoffs/l01-report.md` and `ledger.md`.
8. Push accepted work branches at green checkpoints (fix/feature patterns only;
   never the default branch, tags, or force-pushes), or on a `PUSH` directive.
