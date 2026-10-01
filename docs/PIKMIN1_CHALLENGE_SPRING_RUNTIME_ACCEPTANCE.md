# P1 Challenge Spring (chal3) runtime acceptance (lane p1-challenge-spring-runtime-acceptance, #566)

Consumer acceptance over the landed #649 guarded runtime fixture, its
machine-readable input package, and the #52 campaign contract - all consumed
read-only from the maintained integration lines, never duplicated or edited.
No shared/native/maintained edits, no CMakeLists edits, no ADMIT. Issue #566
stays OPEN until the integrator lands this handoff; Trial (chal4) stays
blocked on the pre-existing PIKI BIRTH panic and the #52 follow-on scope 1
stays next scope.

## Consumed pins (read-only)

- #649 fixture package at the maintained wave tips (verified at run time,
  fail-closed on drift): root `claude/p2-deepseek-wave`
  `347526301a4a91df673a631c7d7ab0579e5823a9` (helper `27b7abb1...`, inputs
  module `8dde9bbf...`) and native `claude/p2-deepseek-wave-native`
  `58df488eb1d9582b0ef625d46874f3427c18628d` (fixture fragment
  `950c9222...`, byte-identical to the landed #649 fragment).
- #52 campaign contract: pin `9aa6faad` (loaded by the inputs builder via
  git-show snapshot; content sha256
  `21e1caf02eda06acd9f686bf1b72bce2d6ea3bf366594bb2e8cb416c3aff1b87`,
  also present verbatim on `codex/content-lanes-531` at
  `3eb8806997ec3d9cdf72a9fb3f93b0461045a956`; never vendored here).
- Canonical assets audited read-only by the inputs builder and staged into
  the rundir as a directory junction (symlink-or-copy fallback), never
  copied or modified.
- Captain guard `scripts/p2_fixture_captain_guard.h` sha256
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`,
  recorded in every acceptance record. The fixture runs this guard FIRST on
  every idle tick; CAPTAIN_DOWN exits BLOCKED and can never substantiate a
  PASS. Captain parked far outside attack reach (P2_CHALLENGE_PARK); no
  blanket invincibility; no fake guard provider.

## Commands (all write under the lane output dir only)

- Verify pins:
  `py scripts/p1_challenge_spring_runtime_acceptance.py ... verify-pins`
- Build inputs:
  `... build-inputs --head649 <wave-native-tip> --inputs-root <lane-root>`
  (module code runs from the wave-root checkout; `--inputs-root` supplies
  the canonical guard file plus the contract pin object, both hash-pinned).
- Private leased build:
  `... build --build-dir <build> --head649 <tip>` (acquires the heavy-build
  lease under the live elastic cap, builds via the #649 build script,
  records exe sha + `ninja -n`, releases; short build dir plus a lane
  response-file fallback keep the fixture link under the Windows
  CreateProcess limit - bit-identical argv transport, recorded in
  build-provenance).
- Headed run:
  `... run --timeout 1200` (executes `fixture.exe --experimental-challenge-level 3`
  in `out/run-chal3` with the package env, captures `native.log`)
- Acceptance record:
  `... accept --log <native.log> --record-out <acceptance.json>`

## Observed facts (chal3 headed run)

- Centred 960x540 window (SDL init line + preview centered line).
- `CHALLENGE_LAYOUT_READY id=challenge-3` with stage file and story flag.
- Generator recognition and spawn counts per pool (default 87/111, plant 38/38).
- `P2_CHALLENGE_PARK` captain coordinates (parked outside attack reach).
- `P2_CHALLENGE_SQUAD pikis=20` live starting squad.
- `P2_CHALLENGE_BOOT level=3 slot=chal3` and `PASS P2_CHALLENGE_GUARDED_BOOT`.
- No `CAPTAIN_DOWN` marker anywhere in the run log.
## Gate outcomes (honest labels)

- `identity_spawn`: PASS only when the stage identity row, generator
  recognition/spawn counts, and a live starting squad are all observed in one
  uninterrupted run (no CAPTAIN_DOWN, fixture PASS marker present).
- `movement_animation`, `attacks_receivers`, `death_corpse`,
  `transport_reward`, `cleanup_reentry`: UNTESTED - a boot-only observation
  cannot exercise combat, death, haul, or reentry; nothing inferred.

## Not observed / not claimed

No movement, attacks, deaths, transports, rewards, reentries, timers,
scoring, or retry semantics. No playability claim. Protected observation is
labelled as such where it occurs and never proves captain damage.

## Remaining scope (not this lane)

Trial (chal4) runtime acceptance (blocked on the pre-existing PIKI BIRTH
panic) and #52 follow-on scope 1. Native CMake/CTest first-class targets
remain a shared-owner follow-up.
