# Tutorial P1 native runtime fixture (lane p2-overworld-tutorial-p1-native-runtime)

Bounded P1-native producer for the Valley of Repose (course `tutorial`), issue
#696. Executes the tutorial surface session in the game engine through a
leased full native build plus a guarded fixture, consuming the integrated
`p2-surface-session-1` contract, the integrated overworld source locator and
the real-source tutorial manifest. Six-gate evidence carries honest
natural/injected labels. No ADMIT; consumer issue #148 stays OPEN.

## Owned files (exact, new files only)

- `native/tools/p2_tutorial_p1_runtime_fixture.cpp`: replacement-main harness
  (forest/kurage/cave-guard convention; 960x540 centred window;
  `--experimental-pikmin2-room` boot). Captain-safety guard #632 vendored
  verbatim and executed on EVERY idle tick before any observation;
  `CAPTAIN_DOWN` exits BLOCKED (86) with no PASS. `--guard-self-test`
  (7-row truth table, engine-independent) and `--guard-negative-test`
  (exact interruption call) flags.
- `experimental/pikmin2_tutorial_p1_runtime.py`: run-layout stager
  (`stage`: manifest + seed + pins with SHA-256 record, plus integrated
  contract/locator hash pins), layout validator (`validate`: hash re-check,
  tamper detection) and run-log verifier (`verify-log`): PASS only on full
  marker evidence with zero failure markers; otherwise per-boundary
  unsupported/unobserved verdicts.
- `tests/test_pikmin2_tutorial_p1_runtime.py`: focused tests (staging, tamper
  detection, integrated pin consumption, verifier truth table incl.
  captain-down-blocks-pass).
- This doc: pins, commands, evidence, missing pieces.

## Fail-closed boundary contract

The fixture checks each required surface-session boundary against actual
engine capability and reports `P2_TUTORIAL_P1_UNSUPPORTED boundary=<name>
reason=<no-...-in-port>` where the port lacks support, then exits
`FAIL TUTORIAL_P1_RUNTIME` with no PASS marker. Diagnostic engine facts
(`P2_TUTORIAL_P1_ENGINE_FACT ... diagnostic_only=1`) prove only that the
harness boots and observes a live room scene; they say nothing about the
tutorial surface, day, saves, receipts, or reentry.

## Consumed contracts (read-only, hash-pinned)

- `experimental/pikmin2_surface_session_contract.py` (schema
  `p2-surface-session-1`): the seed's schema and course are checked against it
  when importable; its hash is recorded in the staged run metadata.
- `experimental/pikmin2_overworld_source_locator.py`: the real-source locator
  that hash-pins `user/Abe/stages.txt`
  (`4de9008c99e799b99b2746c0156846eeb7ad50895ad110fc7f2070db6de1fff8`);
  its hash is recorded in the staged run metadata.
- Real-source tutorial manifest + session seed consumed read-only from the
  done lane `p2-overworld-tutorial-p1-surface-session` (#148) run layout
  (`prepared/tutorial-p1-surface-session-output/p1-run/run/`).
- Canonical guard `scripts/p2_fixture_captain_guard.h` consumed read-only
  (sha256 recorded in the handoff); vendored verbatim in the fixture. The
  header itself is never edited.

## Source pins (this lane)

- Root worktree HEAD `c86e4029` (codex/content-lanes-531 tip).
- Native worktree HEAD `b805d9c6` (codex/p2-main-review-native tip).

## Build / run (private, leased)

Build directory `output/tutorial-p1-native-runtime-build` (exclusive, lane
private). Lease the heavy-build slot through the canonical registry
(`build:output/tutorial-p1-native-runtime-build`) before ANY heavy job and
respect the live elastic cap; release afterward. Record the exact source
commit, executable SHA-256, and `ninja -n` result.

Promotion of the fixture to a first-class CMake target is a shared-owner
follow-up (forest/kurage precedent); the lane links the TU against the private
`pikmin_pc` graph without editing shared build files.

## Honest status / missing pieces

The port has no overworld course boot, no day-advance API, no save
serializer, no receipt ledger, and no exit/reentry path (verified against
`pc_main.cpp`/`pc_bbft.cpp` boot flags and the `pc_port/*.h` API surface; the
`p2-surface-session-1` contract declares the same set missing). Until a
native slice implements them (save serializer -> save-progression #132,
receipt ledger endpoint -> treasure-receipts, generator-cache restore ->
cave-generation/placement, sunset/day driver -> save-progression), every
surface-session boundary stays unsupported/unobserved, all six gates stay
UNTESTED or BLOCKED, and no playability is claimed. Protected observation (if
any) is labelled and never used to prove captain damage.
