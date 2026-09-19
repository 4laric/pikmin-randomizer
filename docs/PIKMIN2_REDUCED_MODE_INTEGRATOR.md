# Reduced-mode integrator handbook

This is the handover for whoever runs planning and integration for the Pikmin 2 pipeline in
reduced mode. It covers what that job is, the standing decisions, where the state lives, and every
command, in order. The toolkit is in `ops/reduced-mode/` of each release worktree. This document ships
next to it.

## 1. What reduced mode is

On 2026-09-19 the pipeline was cut back to what produced code. The full pipeline had made about 5
real landings in 12 hours from about 300 launches, and 87% of its "done" lanes had no code.

What changed:
- **Turned off:** throughput, autofill, the planner pool, shepherd, setup healing, queue pressure and
  shared-review routing (`reduced-mode.patch.json`). `integrator_inbox` stays on.
- **Retired:** all 2344 old launch specs (`retire_old_lanes.py`). The only lanes that can launch are
  the `rd-*` lanes you register.
- **One integrator:** a single strong integrator (this role) writes the briefs, merge-tests handoffs
  and lands them.
- **The metric:** code commits landed per day on the two lines.

Lane workers are OpenCode sessions on `muse-l*` pool workers. Each gets one written brief with a
definition of done, works in its own worktree, and finishes with a validated handoff
(`handoff_ready`). Workers never push to or merge into the lines.

## 2. Standing decisions (from the user)

- **Canonical root line:** `codex/p2-main-review`. Its worktree is `output/p2-main-review` and its
  remote is `origin`.
- **Canonical native line:** `claude/p2-deepseek-wave-native`. Its worktree is
  `output/dsw/native-wave`, its repo is `native/`, and its remote is `fork`.
- Both are declared in `output/workflow/controller/config.json` under `integration_lines`. The
  `release_target` is `origin/main` and `fork/main`.
- **Pushing:** the line heads are pushed after every landing. Native work branches may also be
  pushed.
- **White Pikmin** are allowed in version-1 cave checkpoints.
- **Assets** (`output/workflow/user-answers/`):
  - P1: `C:/Users/alari/bbft/dist/cohesion/pikmin/assets`
  - P2 ISO: `C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso`
- **Line writes need the user.** An integrator running in Claude Code auto mode cannot commit to,
  fast-forward or push the lines, cannot write to GitHub, and cannot create STOP or restart the
  controller; the classifier blocks all of these. The user runs one pasted command per step. Always
  give copy-paste commands with absolute paths, and never assume a working directory.
- **What the integrator can do alone:** commits and merges on scratch branches in scratch worktrees,
  building, testing, and reading the registry.

## 3. Where things live

| What | Where |
|---|---|
| Toolkit (versioned with the release) | `<release>/ops/reduced-mode/` |
| Current release | the path shown by `service status` ("Running code ... at <path>") |
| Lane manifest (issue, branch, kind, owned_files per lane) | `output/reduced/lanes.json` |
| Lane briefs (source copies) | `output/reduced/briefs/brief-<lane without rd->.md` |
| Per-lane workspace | `output/reduced/<lane>/`: `root/` and `native/` worktrees, `brief.md`, `opencode.json`, `run/`, `nbuild/`, and the handoff files |
| Registry | `output/workflow/registry.sqlite3` (WAL). Pre-reduced backup: `registry.before-reduced-mode.sqlite3` |
| Controller config | `output/workflow/controller/config.json`. Backups: `config.before-reduced-mode.json`, `config.before-reduced-lanes.json` |
| Retire undo record | `output/workflow/reduced-mode-retire-undo-<stamp>.json` |

In PowerShell, set these first:

```powershell
$WS='C:\Users\alari\pikmin-randomizer'; $REL='<release path from service status>'; $RM="$REL\ops\reduced-mode"
$PY=(py -3.12 -c "import sys;print(sys.executable)")
```

## 4. Status: what is running

```powershell
cd $REL; py -3.12 -m workflow.service status --root $WS            # controller alive, parent wrapper, running code
cd $REL; py -3.12 -m workflow.inspect --root $WS lane rd-<name>    # state, gen, worker, process, next action
cd $REL; py -3.12 -m workflow.inspect --root $WS stuck             # anything waiting on a person
```

The lane states that matter:
- `running`: the worker is alive.
- `handoff_ready`: the lane is finished and waiting for you.
- `review_ready`: the lane is finished, but its outcome needs a decision.
- `blocked`: the lane named exactly what stops it.
- `done`: a receipt has been recorded.

A lane keeps its pool worker until it is `done`.

## 5. The loop

1. **Pick the work.**
   - Old backlog: `py -3.12 $RM\triage.py <out.json>` lists branches whose commits are not on the
     lines (clean, conflict or report-only). It is read-only.
   - As of 2026-09-19 the native backlog is used up. New lanes come from open GitHub issues.
2. **Write a brief.** Copy an existing brief from `output/reduced/briefs/`. The native template is
   `brief-snakecrow-gate.md`; the root template is `brief-p2ap-installers.md`. Keep these sections:
   - Task.
   - Files.
   - Definition of done. Each bullet becomes a registered acceptance string, and the handoff must
     repeat each one exactly.
   - Rules: worktree and branch, never touch the lines, the build helper and ctest, ownership and
     shared reviews, finish or blocked.

   Allow a zero-commit outcome whenever the work may already be on the line. Several lanes correctly
   ended that way (demon-chain-a, bomb-arm, onikurage-policy).
3. **Add the lane to `lanes.json`.**
   - Fields: `kind` (`native` or `root`), `branch` (`reduced/native-<x>` or `reduced/root-<x>`),
     `issue`, `scope` and `owned_files`.
   - The issue must be open, distinct from the others, and not held by any unfinished lane.
   - No owned file may be held by an unfinished lane.
   - `CMakeLists.txt` is shared and owned by no lane; lanes declare their edits to it as a shared
     review.

   Check before registering:
   ```powershell
   py -3.12 "$RM\check_lanes.py" --root $WS rd-a rd-b
   ```
4. **Register and start (the user pastes this).** Setup needs the controller stopped. The deploy
   removes STOP and restarts it. Running lanes survive a restart.
   ```powershell
   $L=@('rd-a','rd-b')
   New-Item -ItemType File -Force "$WS\output\workflow\controller\STOP" | Out-Null
   & "$RM\setup-lanes.ps1" -Root $WS -Lanes $L          # in-process &, NOT powershell -File
   & $PY "$RM\reduced_setup.py" kickoff --root $WS --lanes $L
   & "$REL\scripts\Deploy-WorkflowRelease.ps1" -WorkspaceRoot $WS -Python $PY
   ```
   Then confirm each lane is `running` with `inspect lane`. If a lane shows "Unknown lane", its setup
   refused; the usual causes are in section 8.
5. **Merge-test a finished batch** (integrator, in a scratch worktree):
   - Read `output/reduced/<lane>/run/finish-request.json` (its summary), and `handoff.json`,
     `decision.md` or `conflicts.md` where they exist.
   - `git -C <repo> worktree add -b scratch/land-<n> <scratch> <line>`, then
     `git merge --no-ff` each lane branch in turn.
   - Resolve conflicts. The common one is two lanes appending to the same `foreach(policy ...)` test
     list in `CMakeLists.txt`; keep both entries.
   - **Native build:**
     ```bash
     PATH=/c/msys64/mingw64/bin:$PATH
     cmake -S <scratch> -B <build> -G Ninja -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ \
       -DCMAKE_MAKE_PROGRAM=C:/Users/alari/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0/LocalCache/local-packages/Python312/Scripts/ninja.exe \
       -DP2_CHALLENGE_GUARD_INCLUDE_DIR=C:/Users/alari/pikmin-randomizer/output/p2-main-review/scripts
     cmake --build <build> -j 8
     ctest --test-dir <build> -j 8
     ```
     The test count must not fall, and nothing may fail. On 9b0c63d3 it was 124/124; after a4cc188f,
     127/127.
   - **Root tests:**
     ```powershell
     py -3.12 -m pytest -q -p no:cacheprovider --continue-on-collection-errors tests/ -k "seed or p2 or apworld or randomizer"
     ```
     Run it on the scratch branch and on the line, and compare the FAILED lists; the branch must add
     none. The line had 4 failures here before your change. Collection errors in a scratch worktree
     come from the `native/` folder being absent.
6. **Land (the user pastes this).** It fast-forwards the line worktree and pushes. It refuses if the
   line is dirty or has moved.
   ```powershell
   & "$RM\land-batch.ps1" native <sha>     # or: root <sha>
   ```
7. **Record receipts (integrator or user).** Receipts mark the lanes `done` and free their workers.
   Check first:
   ```powershell
   py -3.12 "$RM\record_landing.py" --root $WS --lane rd-x --dry-run
   ```
   Then record:
   ```powershell
   py -3.12 "$RM\record_landing.py" --root $WS --lane rd-x --validation <merge-test ctest/pytest log>
   ```
   - A lane with zero commits needs `--already-landed`.
   - "Does not contain the reviewed bytes" means the landing changed a lane file after the lane did
     (a merge resolution). Pass `--port FILE`; that requires the lane's shared review to be approved.
8. **Update the counts** of commits landed today, and pick the next work.

## 6. Deploying workflow code changes

Workflow code lives on branch `workflow-hardening`. Never edit the live checkout: the controller
imports the release worktree.

1. Commit on `workflow-hardening` and test it (`py -3.12 -m pytest -q tests/test_runner_*.py`, etc.).
2. The user builds the release:
   ```powershell
   cd <current release>; py -3.12 -m workflow.service prepare-release --root C:/Users/alari/pikmin-randomizer --ref <sha> --config C:/Users/alari/pikmin-randomizer/output/workflow/controller/config.json
   ```
   The entry point is `workflow.service`, not `pikmin2_controller.py`.
3. The user deploys it: create STOP, then run
   `& <new release>\scripts\Deploy-WorkflowRelease.ps1 -WorkspaceRoot $WS -Python $PY`.
4. Check that `service status` shows the new commit.

## 7. Undo

To go back to full mode, see `ops/reduced-mode/revert-reduced-mode.ps1` (restores the config) and
`retire_old_lanes.py --undo <undo json>` (restores the 2344 specs). Registered `rd-*` lanes stay in the
registry. The last resort, with the controller stopped, is to copy `registry.before-reduced-mode.sqlite3`
back over the registry; that drops every write made since.

## 8. Known problems and fixes

- **Lane missing after setup ("Unknown lane"):**
  - Its issue or files are held by an unfinished lane: pick another issue, or trim `owned_files`.
  - Or no worker was free: add more `muse-l*` ids to `worker_preference` in `lanes.json`. Landed lanes
    hold their workers until their receipts are recorded (step 7).
- **`powershell -File setup-lanes.ps1 -Lanes a,b`** passes the array wrongly and can start the
  controller with no lanes. Always call it with `&` in the same session.
- **Missing-DLL popups** (`libstdc++-6.dll`, `libgcc_s_seh-1.dll`) from worker test executables:
  fixed in release 812c2ccb, where the runner puts `C:\msys64\mingw64\bin` on the worker PATH and
  turns off error dialogs.
- **Scratch CMake configure fails:**
  - "unable to find Ninja": pass `CMAKE_MAKE_PROGRAM` (the pip ninja path above).
  - "p2_fixture_captain_guard.h not found": pass `P2_CHALLENGE_GUARD_INCLUDE_DIR` pointing at the root
    line's `scripts/`.
- **`No module named workflow.service`:** `-m` puts the current directory first on the path, and the live
  checkout's older `workflow/` package shadows the release. Run `-m workflow.*` commands from inside the
  release folder.
- **The `prepare-release` "unrecognized arguments" error:** you called `pikmin2_controller.py`. Use
  `-m workflow.service`.
- **An issue held by an old lane:** old non-`rd` lanes still hold issues and files. `check_lanes.py`
  names the holder.
- **rd-root-held-a/b:** these stay blocked until mar-corpse-emission-native,
  shard-enemies-5-catfish26-observer and shard-enemies-4-jigumo63-observer finish.

## 9. Current work (2026-09-19)

- **Landed on native:** 9b0c63d3 (SnakeCrow, Sarai capture, Mamuta poses, BigTreasure elements) and
  a4cc188f (Onikurage suite registration).
- **Landed on root:** a18e4ebf (the playable P2 enemy pool: `--p2-species playable` and the AP option
  `p2_enemy_pool`).
- **Zero-commit outcomes:** demon-chain-a and bomb-arm.
- **Running:**
  - rd-demon-chain-b (#242), rd-kabuto-host (#424) and rd-captain-kurage (#130).
  - The P2-in-P1 batch: rd-p2ap-installers (#442), rd-p2ap-content (#643), rd-p2ap-kill-checks
    (#134), rd-p2ap-sarai (#439) and rd-p2ap-failsafe (#440).
- **P2-in-P1 goal:** a full P1 Archipelago seed with admitted P2 enemies.
  - The generation side works.
  - The runtime needs a content root staged from the ISO (rd-p2ap-content). After that: a headless
    session acceptance, then a real play-through.
  - Background: `docs/PIKMIN2_AP_PLAYTEST.md` on the root line.
