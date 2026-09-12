# Reproducible fixture builds (#135)

Implementation owner: Codex through shared account `4laric`. The standalone
`scripts/build_pikmin2_fixture.py` builds a private fixture from a completed
Windows MinGW CMake/Ninja `pikmin_pc` target. It never requests a production
rebuild and never overwrites an existing output directory. Existing fixture
builders and runtime interfaces are unchanged.

The earlier verifier extracted compiler/linker commands without checking the
dependency state. A directory named `build-stats` or `build-randomizer` is not
proof of compatibility: stale objects previously produced the wrong Snow
fixture behavior. This tool checks actual inputs and preserves original flags,
including LTO settings, instead of stripping/replacing them.

## Usage

Coordinate with the integration lead before using a production build. Wait
until their build has completed; a pending source edit intentionally rejects it.

```powershell
py -3.12 scripts/build_pikmin2_fixture.py --source <native-checkout> --build <completed-Ninja-build> --fixture <fixture.cpp> --expected-native-head <full-40-character-commit> --output <new-private-directory>
```

Use `--check-only` to inspect native inputs without compiling the fixture.
This mode reports `checked_not_built`; it does not check fixture-specific header
dependencies or produce an executable. A full build performs that extra check.

Suitable sources include `native/tools/preview_p2_room.cpp`, or the root
`scripts/pikmin2_entrance_fixture.cpp` and `scripts/pikmin2_surface_handoff_fixture.cpp`
when their interfaces match the selected build. Each source has its own runtime
requirements. A successful link does not establish that its gameplay assertions
pass. The builder does not launch the executable, copy assets, install DLLs, or
touch saves. Use the relevant fixture runner with isolated assets and saves.

The output must be outside the native source/build directories. A successful
run writes `fixture.exe`, `fixture.obj`, private `link-inputs/`, dependency files,
compiler/linker logs, and `provenance.json`. A rejected attempt also writes its
reason and any evidence collected before failure. **Use an executable only when
that attempt's provenance status is `built`.** A compiler may have produced a
file before a later input-change check rejects the attempt.

## Checks and evidence

- CMake must name the supplied source checkout, Ninja generator and the same
  compiler as the actual Ninja compile/link commands. Observed Git HEAD must
  equal the explicitly supplied full commit.
- `ninja -n -d explain pikmin_pc` must report no pending work. A dry-run line
  saying `Re-running CMake...` is a rejection, not permission to regenerate it.
  Neither a compiler nor a production build command is run on that path.
- The tool identifies exactly one `pc_main.cpp` compile and one link using its
  object. It supports the observed CMake `cmd /C "cd . && ... && cd ."` wrapper
  without executing a shell. Response files, unexpected pipelines and selected
  side-output/library-mode flags fail closed rather than being guessed.
- It records declared Ninja inputs, compiler dependency records, all compiled
  objects, explicit archives/import libraries, resolved `-l` libraries, build
  graph/cache/log/dependency files and the existing production executable.
  Compiler, Ninja, and compiler helper executables are hashed; compiler/Ninja
  versions and the derived argument arrays are retained.
- The native source record contains observed HEAD, porcelain status and a hash
  of the tracked binary diff. Dependency source/header hashes cover actual
  recorded inputs, including untracked headers that the compiler uses. Unrelated
  untracked directory contents are not recursively hashed.
- A compiler dependency-only scan discovers fixture headers before building.
  Explicit link inputs are copied and hash-checked into the private directory;
  only the main object and output paths are replaced. Import-library output is
  redirected into that directory too. Source/config/toolchain/input hashes,
  fixture dependencies, Git state and Ninja freshness are checked again after
  compilation/linking. Changed or missing inputs invalidate the result even if
  the compiler exited successfully.

## Important limits

`historical_build_certified` is always false. A current HEAD plus Ninja's
timestamp/command/dependency checks cannot prove that old object bytes were
historically built from that commit. Restored timestamps, a deliberately
modified dependency database, or undocumented earlier builds cannot be repaired
by observation. The report records the exact objects reused and the source state
observed now; it must not be relabeled a historical build certificate.

Before/after observations detect changes but do not lock the shared build or
prove that inputs remained unchanged at every instant. Do not run it concurrently
with a production rebuild. Implicit compiler startup/runtime libraries and
runtime DLLs are not copied into the private link snapshot, so this is not a
self-contained reproducible toolchain or portable player package. The supported
command grammar is deliberately limited to the project's observed Windows
MinGW/Ninja build, not arbitrary CMake generators or compiler wrappers.

## Validation

Run `py -3.12 -m unittest tests.test_pikmin2_fixture_build -v`.
Twelve synthetic tests cover a full fake compiler/link workflow, paths with spaces and
backslashes, preserved LTO flags, missing/stale inputs, wrong source/HEAD,
concurrent library replacement, check-only behavior and output preservation.
They do not claim a real native compile or runtime pass.

A separate two-source C++ project was configured and built locally with the
installed GCC 16.2.0 and Ninja 1.13.2 toolchain, using source/build/output paths
containing spaces. The new tool compiled and linked its replacement fixture;
that executable returned zero. An intentional subsequent source edit was rejected
before compilation, with the original target executable unchanged. This is a
real toolchain smoke test using synthetic code, **not** a Pikmin fixture pass.
Evidence is under `output/p2-fixture-builds/output/real-toolchain-proof/`.

An isolated Ninja generator-edge check also confirmed that `-n` can print
`Re-running ...` without executing the command: the marker was absent and the
build-file hash unchanged. Planned regeneration remains an immediate rejection.

The active native tree at observed HEAD
`3cc4a5326a8e8d83dd98b20888479caab00b305c` was correctly rejected because its
changed CMakeLists required regeneration. No compile command was issued. Local
evidence: `output/p2-fixture-builds/output/reject-active-tree/provenance.json`.
Read-only parsing of that build's commands/dependency records found 479 compiler
objects and 1,497 distinct source/header dependencies.

After the lead completed native build `606c0c1763073aa9576c08455b42fa548f59b4f7`
and held source edits, the actual `native/tools/preview_p2_room.cpp` fixture
compiled and linked successfully. Both Ninja checks reported no work. All 2,009
build inputs and 573 fixture dependencies passed the before/after checks, and
the observed Git state stayed unchanged. Existing dirty status for
`creatureCollision.cpp`, `goalItem.cpp`, and the untracked research directory
was recorded rather than rewritten or called clean.

Evidence: `output/p2-fixture-builds/output/native-room-606c0c17/provenance.json`.
Fixture executable SHA256:
`3ab25db6b06ce489b9eff87c304b1f358fde48f228cb15f388a2a4d93a1e3e7b`.
The shared source window was released immediately after those checks completed.
This is actual native compile/link evidence; the resulting fixture was not run
for gameplay acceptance in this batch.

Keep #135 open: clean-machine extraction/build installation, packaged runtime
dependencies, manual gameplay and full-content release acceptance remain work
beyond this bounded build-tooling patch. Generated binaries/reports stay local.
