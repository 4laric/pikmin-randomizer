# P1 Challenge Forest (chal1) runtime acceptance (lane p1-challenge-forest-runtime-acceptance, #564)

Consumer acceptance over the landed #649 guarded runtime fixture, its
machine-readable input package, and the #52 campaign contract - all consumed
read-only, never duplicated or edited. No shared/native/maintained edits, no
CMakeLists edits, no ADMIT. Issue #564 stays OPEN until the integrator lands
this handoff; chal3-chal4 and #52 follow-on scope 1 are next scope.

## Consumed pins (read-only)

- #649 fixture fragment + builder + inputs module + guard record: root
  worktree `.../p1-challenge-guarded-runtime-root` @ `a1d72cf0` (commit hash
  re-verified at run time), native worktree @ `c549997e`.
- #52 campaign contract: pin `9aa6faad` (loaded by #649 builder via git-show
  snapshot; never vendored here).
- Canonical assets: `C:/Users/alari/bbft/dist/cohesion/pikmin/assets`
  (audited read-only by the inputs builder; staged into the rundir as a
  directory junction, never copied or modified).
- Captain guard `scripts/p2_fixture_captain_guard.h` sha256
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`,
  recorded in every acceptance record. The fixture runs this guard FIRST on
  every idle tick; CAPTAIN_DOWN exits BLOCKED and can never substantiate a
  PASS. Captain parked far outside attack reach (P2_CHALLENGE_PARK); no
  blanket invincibility; no fake guard provider.

## Commands (all write under the lane output dir only)

- Build inputs:
  `py scripts/p1_challenge_forest_runtime_acceptance.py --canonical <root> --root649 <r> --native649 <n> --assets <a> --out <o> build-inputs --head649 <h>`
- Private leased build:
  `... build --build-dir <o/build> --head649 <h>` (acquires the heavy-build
  lease, builds via #649 build script, records exe sha + `ninja -n`, releases)
- Headed run:
  `... run --timeout 1200` (executes `fixture.exe --experimental-challenge-level 1`
  in `out/run-chal1` with the package env, captures `native.log`)
- Acceptance record:
  `... accept --log <native.log> --record-out <acceptance.json>`

## Observed facts (chal1 headed run)

- Centred 960x540 window (SDL init line + preview centered line).
- `CHALLENGE_LAYOUT_READY id=challenge-1` with stage file and story flag.
- Generator recognition and spawn counts per pool (default + plant).
- `P2_CHALLENGE_PARK` captain coordinates (parked outside attack reach).
- `P2_CHALLENGE_SQUAD pikis=20` live starting squad.
- `P2_CHALLENGE_BOOT level=1 slot=chal1` and `PASS P2_CHALLENGE_GUARDED_BOOT`.
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

chal3-chal4 runtime acceptance and #52 follow-on scope 1. Native
CMake/CTest first-class targets remain a shared-owner follow-up.
