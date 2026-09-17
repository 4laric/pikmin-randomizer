# Registration packet: #651 host-mode guarded fixture in maintained CMake/CTest (#661)

Producer lane `challenge-host-mode-registration-packet` (#661); owner Codex
through shared account 4laric. This is a planning-only registration packet for
the #186 shared build review: no maintained/shared edits, no builds, no
runtime, no ADMIT. All six runtime gates UNTESTED.

## Why this packet exists

`challenge-host-mode` (#651) implemented the host-mode consumer and its #632
guarded fixture, then stopped: registering the fixture in the maintained
CMake/CTest is a shared edit requiring #186 review. The stranded challenge-3
and p1-challenge requests both trace to this single registration. This packet
provides the exact, review-ready change so #186 can decide it, after which
#651 can build/run and P1 stage lanes follow.

## Exact anchors (pinned tree `native/CMakeLists.txt` @ native HEAD `a95040b6`)

- `enable_testing()` — line 552 (CTest already enabled).
- Insertion anchor: after line 608
  `add_test(NAME pc_menu_repeat_test COMMAND pc_menu_repeat_test)`, before
  line 610 `# Host software DSP test (not linked into main game)`. The two are
  separated by one blank line (line 609).
- Pattern to mirror (lines 604-608): `add_executable` + `add_test` with
  `target_compile_options(... PRIVATE ${NATIVE_COMPILE_OPTIONS})`.

Pre-apply `native/CMakeLists.txt` sha256
`077809d202211aeb97eb136f6d4269b2098607b9a7a4d81d2b067c86e04a86d0`.

## The change (review-ready patch, dry-applied privately)

Patch file `output/workflow/autofill/prerequisites/hostmode-registration/patch/registration.patch`
sha256 `3c2cf41c4ce9183aadc8b7740e77642c323a745342c43a2ae30878ffc1f8989c`:

```cmake
add_executable(p2_challenge_mode_fixture
    tools/p2_challenge_mode_fixture.cpp
    pc_port/pc_p2_challenge_mode.cpp)
target_include_directories(p2_challenge_mode_fixture PRIVATE
    pc_port
    ${CMAKE_SOURCE_DIR}/../scripts)
target_compile_options(p2_challenge_mode_fixture PRIVATE ${NATIVE_COMPILE_OPTIONS})
add_test(NAME p2_challenge_mode_fixture COMMAND p2_challenge_mode_fixture)
```

Rationale for each line:
- `tools/p2_challenge_mode_fixture.cpp` is the #651 replacement-main fixture
  (includes `pc_p2_challenge_mode.h` and `p2_fixture_captain_guard.h`).
- `pc_port/pc_p2_challenge_mode.cpp` is the host state machine it links.
- `${CMAKE_SOURCE_DIR}/../scripts` is required because the canonical #632
  guard header `scripts/p2_fixture_captain_guard.h` lives outside the native
  include tree. The alternative (vendoring the header under `native/tools/`)
  would duplicate a canonical file; this packet prefers the read-only parent
  include and flags the choice for #186.
- No generator, save, scoring or gameplay semantics are registered; the target
  is a fixture executable plus its CTest entry only.

Post-apply `native/CMakeLists.txt` sha256
`ec901b4071100b8dafb9727a280165c6664dcfdb41aa1a11377300b03d3c2e51`
(private rehearsal worktree only; the maintained tree was not touched).

## Guard / safety references

- Guard header `scripts/p2_fixture_captain_guard.h` sha256
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`
  (read-only; the fixture runs the guard before every observed tick and exits
  86/BLOCKED on captain-down).
- Fixture source pins (from the #651 native worktree, read-only):
  `tools/p2_challenge_mode_fixture.cpp`, `pc_port/pc_p2_challenge_mode.h`,
  `pc_port/pc_p2_challenge_mode.cpp`; plus root state machine
  `experimental/pikmin2_challenge_mode.py` and `tests/test_pikmin2_challenge_mode.py`.
- Existing build harness reference (no shared CMake edit there):
  `scripts/build_p2_challenge_mode_fixture.py` (#656 harness) already builds the
  fixture out-of-tree via `scripts/build_pikmin2_fixture.py`, proving the
  source compiles and the guarded chain runs; this packet only adds the
  maintained registration.

## Validation commands (for #186 / integrator, after their review)

```powershell
git -C <private-native> apply --check output/workflow/autofill/prerequisites/hostmode-registration/patch/registration.patch
git -C <private-native> apply output/workflow/autofill/prerequisites/hostmode-registration/patch/registration.patch
cmake --build <private-build> --target p2_challenge_mode_fixture -j 6
ctest --test-dir <private-build> -R p2_challenge_mode_fixture --output-on-failure
```

Heavy build jobs require canonical registry leases and an exclusive private
build directory; none was run for this packet.

## Downstream consumers (for the publication reviewer)

- #651 `challenge-host-mode` (blocked on this registration), then #656
  host-mode build harness.
- P1 challenge stage runtime slices (#563/#564/#565/#566/#567) gated behind
  #651.
- Stranded challenge-3 and p1-challenge requests that named #661.

## Boundaries

No maintained/shared edits, no builds, no runtime runs, no manifest writes, no
ADMIT. The patch was dry-applied only against the private native rehearsal
worktree `output/workflow/autofill/prerequisites/hostmode-registration/native-dryrun`
at `a95040b6`; the canonical `native/` checkout was never modified.
