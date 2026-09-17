# P2 cave guarded boot fixture (lane cave-guarded-runtime-fixture, #642)

Shared replacement-main cave boot fixture plus reproducible input package for
the blocked forest1 P1 (#154) and yakushima4 P1 (#161) runtime imports.

## What it is

- `native/tools/p2_cave_guarded_boot_fixture.cpp`: REAL game-linked
  replacement-main (scenario main instead of `pc_main.cpp`, mirroring
  `tools/p2_kurage_runtime.cpp`): 960x540 centred window,
  `--experimental-pikmin2-room` boot, then a guarded idle loop. The integrated
  cave entry path (`pc_p2_preview.cpp` -> `pc_p2_cave_setup`, #129 landing)
  applies `p2-cave-entry.txt`, emits `P2_CAVE_READY`, and runs the opt-in
  `p2-cave-generate.txt` sidecar. No new generator/save semantics: the fixture
  never parses manifests and never writes checkpoints.
- `experimental/pikmin2_cave_runtime_inputs.py`: builds/validates the input
  package (`p2-cave-entry.txt` + `p2-cave-generate.txt` +
  `p2-cave-runtime-inputs.json` provenance with sidecar SHA-256 pins).
- `tests/test_pikmin2_cave_runtime_inputs.py`: 9 focused tests (valid
  forest1/yakushima4 presets plus the full mismatch battery).
- `scripts/build_p2_cave_guarded_boot_fixture.py`: private build/run wrapper
  (configure, `pikmin_pc` tree-health build, `ninja -n` dry run, fixture TU
  compile with reference flags, link reuse, guard self-test, headed run).

## Readiness rule (corrected this lane against source evidence)

The fixture observes the ENGINE cave entry state (`pc_p2_cave_floor() > 0`
plus a live restored squad), NOT the room cargo mode. Non-beasts floor-1
imports (forest1/yakushima4) run treasure-driven previews where cargo-free is
false by design, and `p2CavePreviewReady` (non-beasts) requires the
treasure-driven `pc_p2_preview_ready()` state (legal model data). A cargo-free
gate would therefore refuse exactly the consumers this fixture serves; it is
deliberately not used. Without legal data the entry can never go active, so
the fixture correctly reports nothing (no false PASS).
  (configure, `pikmin_pc` tree-health build, `ninja -n` dry run, fixture TU
  compile with reference flags, link reuse, guard self-test, headed run).

## Ordering contract (#632)

The canonical captain guard runs on EVERY idle tick immediately after the base
engine idle and BEFORE any readiness observation or PASS. `CAPTAIN_DOWN`
(`P2_FIXTURE_CAPTAIN_DOWN`) exits BLOCKED (86) with no PASS. The guard never
changes game state.

- Canonical header (consumed read-only, never edited):
  `scripts/p2_fixture_captain_guard.h` sha256
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`.
- The fixture vendors that logic verbatim (a replacement-main TU cannot
  include a Python-tree script header at native build time); the vendored copy
  is covered by the `--guard-self-test` truth-table test plus the
  `P2_CAVE_GUARDED_BOOT_FORCE_CAPTAIN_DOWN=1` negative run (expects exit 86,
  `P2_FIXTURE_CAPTAIN_DOWN`, no PASS).

## Source pins (verified this lane)

- Root worktree HEAD `07e2126ff8c6dacd610958bcba117f3048dbd870` (integrated
  cave-generator-consumer-landing #129; receipt validation hash
  `e5d52f5d9199aa7ac5e98dbbf37a0f386440631a2e5bd283b058967847639c6f`).
- Native worktree HEAD `9688995e66614c13468c8decaab7567ee65f42c4`.
- Consumer lanes inspected read-only only: `shard-caves-forest-forest1-p1`
  (#154, blocked, owns `native/tools/p2_forest1_p1_fixture.cpp`) and
  `shard-caves-yakushima-yakushima4-p1` (#161, blocked, owns
  `native/tools/p2_yakushima4_p1_fixture.cpp`). Their files are untouched.

## Consumer commands

Build once (lane-private build dir; executable SHA-256 recorded in
`out/build-<ts>.json`):

    py -3.12 scripts/build_p2_cave_guarded_boot_fixture.py --configure --build

Guard logic without assets or a display (both exit-code asserted):

    <build>/p2_cave_guarded_boot.exe --guard-self-test       # exit 0, 7/7 rows
    <build>/p2_cave_guarded_boot.exe --guard-negative-test  # exit 86, CAPTAIN_DOWN, no PASS
    py -3.12 scripts/build_p2_cave_guarded_boot_fixture.py --verify-negative  # wrapper: exit 0 iff exit-86 + marker + no-PASS all hold

    <build>/p2_cave_guarded_boot.exe --guard-self-test

Forest1 floor-1 boot package, then headed run (private arena/current overlay,
live squad, real GL required; legal asset absence blocks observation only):

    py -3.12 experimental/pikmin2_cave_runtime_inputs.py build --cave forest1 --out <rundir> --pins <json>
    py -3.12 experimental/pikmin2_cave_runtime_inputs.py validate --dir <rundir>
    py -3.12 scripts/build_p2_cave_guarded_boot_fixture.py --run <rundir>

Same with `--cave yakushima4` for the #161 import.

## Headed evidence status (this lane, honest record)

- Private build green: `pikmin_pc` exit 0, fixture TU compiles warning-clean
  except pre-existing engine-header warnings, links 178 objects, exe SHA-256
  recorded in `out/build-<ts>.json`.
- Guard self-test (7/7) and negative interruption test (exit 86, no PASS) pass.
- Input packages build and validate (`INPUTS_PASS`); pytest 9/9.
- Headed boot: engine reaches window 960x540 centred, GL 3.3 context and
  audio init, then stalls pre-idle inside legal-data stage load (no WAIT
  heartbeat, no managers, process alive but silent). This is the documented
  legal-asset block, NOT a fixture defect: without `courses/pikmin2room`
  model data the preview (and therefore the cave entry) cannot go active.
  Runtime gates stay UNTESTED; no boot/PASS is claimed. Consumers run headed
  in a data-ready environment with the commands above. The run log must show
`P2_CAVE_READY`, `P2_CAVE_GENERATE_PASS` and `PASS CAVE_GUARDED_BOOT`; the
wrapper asserts all three. Pool/spawn names in the presets are schema-valid
harness placeholders; consumers substitute P0-derived manifests (validated by
the same checker before spending runtime).

## Shared-owner follow-up (not done here; needs integrator review)

Promotion to a first-class CMake target. Exact snippet (kurage precedent,
`native/CMakeLists.txt` lines 505-518):

    set(P2_CAVE_GUARDED_BOOT_SOURCES ${PC_PORT_SOURCES})
    list(REMOVE_ITEM P2_CAVE_GUARDED_BOOT_SOURCES pc_port/pc_main.cpp)
    list(APPEND P2_CAVE_GUARDED_BOOT_SOURCES tools/p2_cave_guarded_boot_fixture.cpp)
    add_executable(p2_cave_guarded_boot ${P2_CAVE_GUARDED_BOOT_SOURCES})
    target_include_directories(p2_cave_guarded_boot PRIVATE tools)
    target_compile_options(p2_cave_guarded_boot PRIVATE ${NATIVE_COMPILE_OPTIONS})
    target_link_libraries(p2_cave_guarded_boot PRIVATE pikmin_legacy)

`native/CMakeLists.txt` was deliberately NOT edited: it is outside this
lane owned files. The lane build script links the TU against the private
`pikmin_pc` graph instead, inside the lane build dir only.