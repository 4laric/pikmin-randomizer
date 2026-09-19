# P2 Challenge host-mode consumer (#651)

Cross-partition prerequisite for challenge-0/1/2/3 P1 scopes. Implementation
owner: Codex through shared GitHub account 4laric; contributor Muse Spark 1.3.
Private worktrees: `.../prepared/challenge-host-mode-root` (root) and
`.../prepared/challenge-host-mode-native` (native).

## Corrections from the pinned #651/#186 review

Review evidence: `output/workflow/challenge-host-review.md` sha256
`fc3901adbc11d221343bba546b94e3af63bd8c7b5bd7b61a0822341bc3f0ef19` (status
`rejected`). The following corrections are applied in this generation:

1. **Fixture reclassified.** `native/tools/p2_challenge_mode_fixture.cpp` is
   explicitly a **host-state unit test**, not a game-linked guarded boot
   fixture. It links only the host-state module plus a standalone main and
   cannot prove real captain health, window adoption, engine stage selection
   or engine boot. Its own banner and the `P2_CHALLENGE_HOSTSTATE_KIND
   unit_test guard_inputs=SIMULATED` marker state this.
2. **Stage selection exposed honestly.** Selection is driven by
   `--ui-index` over a labelled SAMPLE table (two contract-shaped entries);
   unknown indices exit 2. Captain inputs are simulated CLI values
   (`--captain-hp`, `--orima-dead`, `--navi-dead`, `--captain-down`), never
   engine health.
3. **Guard include path resolved without vendoring.** The CMake registration
   block now uses a validated cache variable
   `P2_CHALLENGE_GUARD_INCLUDE_DIR` (default `${CMAKE_SOURCE_DIR}/../scripts`,
   `FATAL_ERROR` if the header is missing); private builds pass the canonical
   scripts path. No drifting vendored copy.

## What this consumes (never forks)

The DONE framework contract `experimental/pikmin2_challenge_framework_contract.py`
(producer `b9bb55f0`, cherry-picked as `728e7492`) is consumed as an artifact;
scoring is delegated to `compute_score` and the stage-table parser is never
reimplemented. The #661 registration packet (`5c22074d`, cherry-picked as
`ad1d1c2c`) is consumed for its registration guidance.

## Host-mode semantics implemented (root consumer)

`experimental/pikmin2_challenge_mode.py`: `stage_select` by `ui_index`,
`starting_state` (contract squad/sprays/timer), `tick` (`mTimeLimit`
countdown), `descend` (per-floor extension), `check_end`
(captain_down/give_up/extinction), `result` (ordinary vs deathless + contract
score), `retry` (attempt-local reset, persistent clear/high-score preserved).
Unsupported semantics stay explicit: `coop_2p`, `key_completion`,
`result_screen`.

## Verification (this generation)

- `tests/test_pikmin2_challenge_mode.py` + the packet's tests: 26 passed,
  5 subtests.
- Host-state unit test built clean (`-Wall -Wextra -Werror`) and run:
  `--ui-index 3` selects `ch_NARI_01kusachi` and emits the full chain;
  `--captain-down` exits **86** with `P2_FIXTURE_CAPTAIN_DOWN ... outcome=BLOCKED`
  before any observed TICK; unknown `--ui-index 9` exits 2.
- Captain-safety #632 guard adopted: `scripts/p2_fixture_captain_guard.h`
  sha256 `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`.

## Bounded engine-registration / boot-hook patch and required ownership

The REAL stage-selectable runtime fixture lies outside this lane's owned
files; the exact patch and its required owner are:

1. **CMake/CTest registration** (maintained `native/CMakeLists.txt`, owned by
   the maintained build owner / #186 review): the validated block above
   (`P2_CHALLENGE_GUARD_INCLUDE_DIR` + `add_executable`/`add_test` for
   `p2_challenge_mode_fixture`). Apply privately today; maintained merge needs
   the build owner.
2. **Engine boot hook** (game startup / challenge section entry, shared native
   files, owned by the native framework maintainer): on challenge stage
   start, call `p2challenge::start` with the entry selected from the contract
   stage table by `ui_index`, then drive `tick`/`descend` from the engine
   frame loop and apply the squad/sprays through the engine's PikiContainer
   and `setDopeCount`. This hook is required before any real captain health,
   window adoption or engine boot can be observed.
3. **Coordination:** the existing #656 harness owns build tooling; coordinate
   by evidence (fixture target name, include dir, CTest name) rather than
   duplicating harness code.

Real runtime checks additionally require actual engine state and a negative
captain-down observation; both remain gates. All six runtime arena gates are
UNTESTED and no playability is claimed.

## Downstream consumers

challenge-0 (#600), challenge-1 (#601), challenge-2 (#602), challenge-3
(#603) P1 scopes.