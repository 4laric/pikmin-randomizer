# Two GL lanes on the shared Windows host

User-authorized 2026-09-14, tracking #462; coordination #186. Implementation owner:
Codex through shared account 4laric. This supersedes the blanket one-GL-process
rule for reviewed autonomous fixtures. It does not allow two desktop-input users.

| Lease | Work |
|---|---|
| A | One interactive gameplay/keyboard/controller/desktop screenshot run |
| B | One reviewed autonomous fixture that never consumes or injects desktop input, never changes focus, and renders in a hidden window |
| exclusive | Acquire both A and B for solo performance measurements, foreground/focus baseline checks, or a fixture whose isolation is unknown |

Coding and private builds remain independent. Concurrent timing is diagnostic,
never solo performance acceptance. Ordinary gameplay and family admission gates
are unchanged. Existing source/gameplay fixture requirements (fresh arena, live
squad, 960x540 sizing after settings) still apply. Hidden B framebuffer evidence
does not prove a visibly centred foreground window; collect that gate in A.

## Launch and inspect

From a root git worktree containing the runner:

```powershell
py -3.12 scripts/p2_gl_lane.py --status
py -3.12 scripts/p2_gl_lane.py --lane A --spec C:/absolute/private/run-a.json
py -3.12 scripts/p2_gl_lane.py --lane B --spec C:/absolute/private/run-b.json
py -3.12 scripts/p2_gl_lane.py --lane exclusive --spec C:/absolute/private/solo.json
```

Until integrated, the shared callable runner is:
`C:/Users/alari/pikmin-randomizer/output/p2-gl-lanes/scripts/p2_gl_lane.py`.
Run it with `py -3.12` from any root repository worktree. Its lease location is
derived from the git **common directory**, so private worktrees share the same
`C:/Users/alari/pikmin-randomizer/output/gl-lanes` locks. Do not run from a native
repository, which has a different common directory.

Each descriptor is JSON:

```json
{
  "executable": "C:/absolute/fixture.exe",
  "sha256": "REPLACE_WITH_REVIEWED_EXECUTABLE_SHA256",
  "cwd": "C:/Users/alari/pikmin-randomizer/output/my-fresh-arena",
  "args": ["--experimental-pikmin2-room"],
  "timeout_seconds": 120,
  "env": {"PATH": "C:/msys64/mingw64/bin;C:/Windows/System32;C:/Windows"},
  "no_input_review": {
    "source_commit": "REPLACE_WITH_REVIEWED_SOURCE_COMMIT",
    "reviewer": "REPLACE_WITH_REVIEWER_AND_ISSUE_EVIDENCE",
    "no_desktop_input": true,
    "no_focus_changes": true,
    "no_shared_writes": true,
    "autonomous_exit": true
  }
}
```

The no-input review is mandatory for B. It is an explicit review attestation,
not an OS security sandbox: do not set these fields merely to pass validation.
The runner hides the launch window and disables background joystick events,
but an application can still show its own SDL window or poll input. The fixture
itself must enforce the following contract:

- Hidden GL window from creation; no later show, activate, foreground, global
  capture, mouse grab, cursor warp or focus-dependent progress.
- No keyboard/mouse/controller polling or OS input injection. Process-local
  scripted simulation actions are allowed and must be labelled injected.
- No shared saves, settings, logs, ports, assets or output mutations. Use a
  unique private cwd; review any absolute paths and use unique ports if needed.
- Bounded autonomous completion, with meaningful failure exit codes. UI menus,
  human prompts and desktop automation belong in A.
- Pin the actual fixture executable. Interpreter/shell wrappers and unpinned
  code loaded at runtime do not qualify for B; build a reviewed direct fixture.

`PIKMIN_RANDOMIZER_TEST_BACKGROUND=1` alone does not qualify a game executable.
The current engine still has foreground-sensitive and hardware-input paths.
Existing fixtures remain A/exclusive until their owners review or port them.

## Queue and cleanup

Announce A, B or exclusive in #186 with issue, descriptor and expected duration.
The OS lease is authoritative among participating runners; comments are a human
queue, not a lock. One owner queues ready jobs per lane. A busy result should
retain the descriptor and identify the next job; do not leave unbounded polling
processes or start a bypass launch. Owners can continue source/test work.

Check for old unleased fixture/nectar processes during migration. Treat an
existing interactive run as occupying A; never launch another A alongside it.
A reviewed hidden B may coexist with that run. Unknown autonomous runs require
coordination before using B. All new launches should use this runner.

The runner acquires its lane and a cwd lease atomically by nonblocking OS locks
(releasing partial acquisition on failure). Exclusive requires both lanes. It
starts the child suspended, assigns a Windows job, then resumes it. Normal exit,
failure, timeout and runner termination terminate contained descendants and
release OS locks. Do not delete lock files: their presence does not mean busy.
Jobs cannot solve interference from a launcher that bypasses this protocol.

Each run writes stdout, stderr and `result.json` under shared `output/gl-lanes`.
The result pins the descriptor, process IDs, timestamps and exit code. A forced
runner kill can leave a historical `running` report; `--status` checks live OS
locks rather than trusting that report. Runner `passed` means exit zero only;
the fixture owner must inspect acceptance markers and evidence separately.

## Initial validation

Four focused Windows tests pass: cross-process lock exclusion and A/B coexistence,
exclusive rollback, B review/hash rejection, timeout descendant termination and
lease release, and nonzero-exit recording (several assertions share tests).

The infrastructure probe `scripts/p2_gl_lane_smoke.cpp` renders known colors into
a 960x540 GL buffer and validates readback. Hidden mode does not pump or inject
input and monitors foreground ownership. It exits autonomously. This is the
first reviewed B executable; it is not a game/20-Pikmin acceptance fixture.

Observed B runs alongside existing pinned-native `nectar.exe` PID 38088:

- Intel probe: 289 frames, correct readback, unchanged foreground, exit 0;
  `output/gl-lanes/run-1789415542492416200`.
- NVIDIA RTX 5070 Ti probe: 341 frames, correct readback, unchanged foreground,
  exit 0; `output/gl-lanes/run-1789415597619653300`.

The probes establish a functioning hidden second context and no observed focus
change. They do not establish every existing fixture's input isolation, game
state equivalence, or worst-case dual-game memory/frame-time budgets. Qualify
each game fixture before moving it to B; retain exclusive performance runs.

Occupancy correction, 2026-09-14 16:04 EDT: PID 38088 above was later identified
as an orphaned lane-33 QA run: its Python launcher 37132 survived a missing parent
39288. Following the user's report, those exact processes were stopped; all
session files and logs were preserved. Both leases were free and no fixture or
nectar process remained at verification. The PID references above are historical
probe evidence, not a current reservation. Audit:
`output/gl-lanes/orphan-lane33-38088.json`; interruption recorded in #444/#186.
