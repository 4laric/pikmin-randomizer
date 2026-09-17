# Yakushima P1 native runtime fixture (lane p2-overworld-yakushima-p1-native-runtime)

Bounded P1-native producer for Perplexing Pool (course `yakushima`), Executes the yakushima surface session in the game engine
through a leased full native build plus a guarded fixture, consuming the
integrated `p2-surface-session-1` contract and the real-source yakushima
manifest. Six-gate evidence carries honest natural/injected labels. No ADMIT;
consumer issue #150 stays OPEN.

## Owned files (exact, new files only)

- `native/tools/p2_yakushima_p1_runtime_fixture.cpp`: replacement-main harness
  (kurage/cave-guard convention; 960x540 centred window;
  `--experimental-pikmin2-room` boot). Captain-safety guard #632 vendored
  verbatim and executed on EVERY idle tick before any observation;
  `CAPTAIN_DOWN` exits BLOCKED (86) with no PASS. `--guard-self-test`
  (7-row truth table, engine-independent) and `--guard-negative-test`
  (exact interruption call) flags.
- `experimental/pikmin2_yakushima_p1_runtime.py`: run-layout stager
  (`stage`: manifest + seed + pins with SHA-256 record), layout validator
  (`validate`: hash re-check, tamper detection), and run-log verifier
  (`verify-log`): PASS only on full marker evidence with zero failure
  markers; otherwise per-boundary unsupported/unobserved verdicts.
- `tests/test_pikmin2_yakushima_p1_runtime.py`: 12 focused tests (staging,
  tamper detection, verifier truth table incl. captain-down-blocks-pass).
- This doc: pins, commands, evidence, missing pieces.

## Fail-closed boundary contract

The fixture checks each required surface-session boundary against actual
engine capability and reports `P2_YAKUSHIMA_P1_UNSUPPORTED boundary=<name>
reason=<no-...-in-port>` where the port lacks support, then exits
`FAIL YAKUSHIMA_P1_RUNTIME` with no PASS marker. Diagnostic engine facts
(`P2_YAKUSHIMA_P1_ENGINE_FACT ... diagnostic_only=1`) prove only that the
harness boots and observes a live room scene; they say nothing about the
yakushima surface, day, saves, receipts, or reentry.

## Source pins (verified this lane)

- Root worktree base `c20a22ec` (this lane's prepared private worktree).
- Native worktree base `58d18dc9` (this lane's prepared private worktree).
- P1 yakushima manifest (real-source: stages.txt sha `4de9008c99e799b99b2746c0156846eeb7ad50895ad110fc7f2070db6de1fff8`, 4 cave links y_01..y_04, 8 provider blockers) built by this lane at `out/p1-run/manifest.json`; session seed copied read-only from the done lane `p2-overworld-yakushima-p1-surface-session` (#150).
- Canonical guard `scripts/p2_fixture_captain_guard.h` consumed read-only
  (sha256 recorded in the handoff); vendored verbatim in the fixture. The
  header itself is never edited.

## Build / run (private, leased)

Build directory `output/workflow/autofill/planning-shards/overworld-yakushima/prepared/yakushima-p1-native-runtime-build` (exclusive, lane private). Lease the heavy-build slot through the canonical registry
(`build:output/workflow/autofill/planning-shards/overworld-yakushima/prepared/yakushima-p1-native-runtime-build`) before ANY heavy job and
respect the live elastic cap; release afterward. Record the exact source
commit, executable SHA-256, and `ninja -n` result.

Promotion of the fixture to a first-class CMake target is a shared-owner
follow-up (kurage precedent); the lane links the TU against the private
`pikmin_pc` graph without editing shared build files.

## Honest status / missing pieces

The port has no overworld course boot, no day-advance API, no save
serializer, no receipt ledger, and no exit/reentry path (verified against
`pc_main.cpp`/`pc_bbft.cpp` boot flags and the `pc_port/*.h` API surface;
the `p2-surface-session-1` contract declares the same set missing). Until a
native slice implements them, every surface-session boundary stays
unsupported/unobserved, all six gates stay UNTESTED or BLOCKED, and no
playability is claimed. Protected observation (if any) is labelled and never
used to prove captain damage.
