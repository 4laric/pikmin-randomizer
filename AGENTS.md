# Pikmin Randomizer track

P2 implementation agents must read [the fan-out and mandatory fixture baseline guide](docs/PIKMIN2_IMPLEMENTATION_FANOUT.md) before claiming or resuming work. Before the next runtime acceptance run, adopt the current starting-Pikmin overlay and 960×540 centred-window native startup, regenerate stale arenas, and record per-lane adoption evidence as required there. Existing active lanes are included.

Before starting any implementation, ensure its scope and acceptance criteria are written in a GitHub issue in 4laric/pikmin-randomizer and assign that issue to the authenticated account (currently 4laric). Record Codex as the implementation owner when using that shared account; do not imply a separate Codex GitHub identity. Update the issue with progress, commits, validation evidence and remaining work. Assignment indicates ownership, not that every backlog item is actively underway. This issue-first requirement also applies to work inside native/ and bbft/.

Work in this directory's native/ and bbft/ repositories. Original BBFT and decomp/pikmin-research checkouts belong to parallel work; do not edit them for this task. Read README.md for the snapshot boundary and next milestone. Keep builds, saves, generated seeds, logs and runtime state local and separate. Inspect inherited scripts for original absolute paths before executing. Do not relink the shared Archipelago installation. The source split and standalone seed/session foundation are implemented. Read DEVELOPMENT.md for build/test evidence and current limitations. Physical placement is still pinned; slot/carry-route audit, relocation, full native campaign resume and gameplay sign-off remain open.

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

Keep private build dirs, builds, saves, generated seeds, logs and runtime state under ignored `output/`. Never push native origin.
