# Challenge host-mode private build/run harness (#656)

Owner: Codex through shared account `4laric`. Lane
`p2-challenge-host-mode-build-harness`, issue #656. Produces the missing
buildable artifact for the stranded #651 host-mode consumer (recovery
`67d71db2`, challenge-1): a private leased game-linked build/run harness for
`native/tools/p2_challenge_mode_fixture.cpp` following the #642/#649
replacement-main pattern. Tooling only; no runtime acceptance claim, no ADMIT.

## Source pins (read-only consumption)

- Root: #651 state machine + tests + doc on `codex/challenge-host-mode`
  @ `b65ff8a024e18e39025b6501b66c5fe1645b68c3`
  (`experimental/pikmin2_challenge_mode.py`,
  `tests/test_pikmin2_challenge_mode.py`, `docs/PIKMIN2_CHALLENGE_MODE.md`).
- Native: #651 module + guarded fixture on
  `codex/challenge-host-mode-native` @ `f698955aa8c3bd32b18c0b638cca3e805a16bc7f`
  (`pc_port/pc_p2_challenge_mode.{cpp,h}`,
  `tools/p2_challenge_mode_fixture.cpp`).
- Captain guard: canonical `scripts/p2_fixture_captain_guard.h`,
  sha256 `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`,
  consumed read-only via `CPLUS_INCLUDE_PATH` (never copied or edited); the
  fixture builder pins it in the fixture-input snapshot automatically.

Neither #651's module/fixture nor any consumer lane is edited here, and no
shared `CMakeLists.txt`/CTest file is touched.

## Why this harness exists

Registering the fixture in maintained CMake/CTest is a shared edit that
requires #186 review, so #651 is blocked on a buildable artifact. This lane
links the replacement-main TU against the private `pikmin_pc` object graph
(reusing exact `build.ninja` compile/link edges, swapping only the
`pc_main` object), records provenance + exe SHA-256, and runs the guarded
chain. The #186 registration request stays open; this harness does not
preempt it.

## Consumer commands

All commands run from the lane root worktree with Python 3.12:

```powershell
# Full headed chain (leased configure + build + fixture + guardcheck + run):
py -3.12 scripts/build_p2_challenge_mode_fixture.py --native <native-worktree> --build <private-build-dir> --output <private-output-dir> --expected-native-head <40-hex> --guard-dir C:/Users/alari/pikmin-randomizer/scripts all

# Focused unit tests (no build, no ISO, no registry):
py -3.12 -m unittest tests.test_p2_challenge_mode_build -v
```

Private build/output directories must live under ignored `output/` and must
never be the shared `native/build-randomizer`. The harness holds the
`build:<dir>` registry lease while its child builds, renews it, and releases
only after the child exits.

## Evidence produced (per run, under the private output dir)

- `configure.log`, `build.log` (ends with `ninja: no work to do.`),
  `fixture.json` (exe SHA-256 + provenance path),
  `fixture-<stamp>/provenance.json` (`status: built`, exact native head),
  `fixture-<stamp>/fixture.exe`,
  `guardcheck.log` (live self-test exit 0 + negative exit 86, no PASS),
  `run.log` (ordered `BOOT..TICK(x3)..DONE` chain, exit 0).

## Downstream consumers

- challenge-1 stages #534/#545/#548/#552/#557/#560 (P1 runtime import).
- challenge-0 crawler P1 #562.
- #651 itself (blocked on the CMake/CTest #186 review, not on this artifact).

## Captain safety (#632)

The guard runs before every observed fixture tick; captain-down exits 86
(BLOCKED) with `P2_FIXTURE_CAPTAIN_DOWN` and is never recorded as a live
tick. The negative path (dead captain, hp 0) is compiled from the same
header and must exit 86 with no PASS marker. Protected observation cannot
prove captain damage. Adoption and hashes are recorded per run.