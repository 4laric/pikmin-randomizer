# Bounded forest_1 cave (issue #930, draft)

Implementation owner: Codex through shared account `4laric`.

This is a developer package for an original engineered floor. It is not a retail
forest_1 reproduction or an accepted native campaign. The opt-in solo manifest
contains one canonical `forest1-bounded-v1` table, its stable location IDs and its
conservative Blue/Yellow Onion requirements. Physical layout salt changes spacing,
not the table or requirements. Capacity bonuses do not establish color supply.
Default generation remains unchanged. AP cave generation is rejected until a
supported authenticated check transport exists; no AP option is exposed.

## Build and launch

Use a private native worktree/build and the shared workflow build supervisor.
Compile `tools/p2_cave_generator_test.cpp` with
`pc_port/pc_p2_cave_generator.cpp` into a private generator executable.
Then invoke `scripts/stage_pikmin2_playable_cave.py` with `--assets` pointing to
the legal installed P1 asset directory, `--pod` to a locally extracted Pod bundle
containing `pod.mod`, `treasure.mod`, and `p2-pod.txt`, `--exe` to the completed
native build, `--generator` to the generator executable, and `--output` to a fresh
ignored directory. `--seed 930 --salt 0` reproduces the observed package.

The generated `Play.cmd` uses the source checkout's Python launcher. Local assets
and source checkout paths are prerequisites, so this is not a portable release.
The launcher uses separate session state, locks concurrent use of its session,
checks its packaged file hashes, discards inherited cave/P2 environment overrides,
and stages a new run directory. It refuses a seventh nectar process or low free
memory (below 4 GiB or 15%). This is a conservative operating policy, not a proven
machine safety threshold; coordinate staggered launches across lanes.

F6 near the far hole requests a floor-boundary checkpoint. Squad color/maturity,
captain health and consumed bud budgets restore together. Durable treasure
receipts suppress already-delivered native actors even after an unsaved crash.
The supervisor recovers a completed transfer if it crashed before recording the
checkpoint. Ordinary unsaved exits restore the last boundary squad; treasure
receipts remain collected. This package journals solo checks but does not apply
campaign item effects or connect to AP. Pending conversion outputs or live sprouts
block checkpointing rather than silently dropping them.

## Evidence and remaining acceptance

Local evidence is under `output/p2-playable-cave-930/` in the canonical workspace.
Native build `build-02` pins `d0379696093563ff5ccff9d7ca09f2e34338e6cc`, clean source,
executable SHA-256 `330cfd980a0140d4547b135289e328a0e07a4ac7ab9cb89f9ac6cedc052cc8d3`,
with a successful build and `ninja: no work to do.` dry run.

`package-03` was freshly staged from the current overlay with 20 red Pikmin and
native centered-window startup. A canonical 60-second bounded run observed active
gameplay, 20 live reds, Pod, original walls/floor and water-colored regions without
immediate extinction. The log records centered 960x540 startup and two native
treasure actors plus Blue/Yellow bud actors. The supervisor stopped only its own
PID 19736 on timeout. Its result is **not PASS**: no full acceptance marker was
expected or produced. Window capture was inspected through the computer-use tool;
the rendered window is DPI-scaled. No natural conversion/carry was demonstrated.

The headless receipt fixture validates actual ledger grant, close/reopen, duplicate,
foreign-seed, corrupt-file and unreadable-path behavior. Python checks cover default
generation, solo fills, conservative color logic, tampering, AP rejection, physical
mesh/water data, receipt validation and pending-checkpoint crash recovery.

Independent review confirmed the persistence and seed/AP fixes. The following gates
remain open and block promotion from draft:

- Electric volumes have radius 16 while corridors are 100 wide, permitting a
  walkable bypass. Close this coverage gap and prove mixed-squad carry denial.
- Natural thrown-Pikmin Blue/Yellow conversion and subsequent real transport,
  water immunity, electric opening, Pod reward and exit/re-entry need observation.
- Captain-down negative control and repeated runtime checkpoint/restart need the
  dedicated guarded fixture. Parser/headless success does not satisfy these gates.
- Bud visuals are colored floor markers; automatic ordinary plucking is provisional.
- Template cargo beside the Pod is scaffolding, not one of the two seed checks.
- AP transport, campaign item effects, full native campaign resume, retail geometry,
  and gameplay sign-off remain unimplemented or unaccepted.

All generated assets, extracted source data, logs, sessions and binaries stay local;
the PRs contain source only. Do not use the earlier `package-dev-02`, staged during
linking before the new executable-completeness guard, as a runnable deliverable.
