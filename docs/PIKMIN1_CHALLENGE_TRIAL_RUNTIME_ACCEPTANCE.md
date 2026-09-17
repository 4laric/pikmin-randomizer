# P1 Challenge Trial (chal4) runtime acceptance (lane p1-challenge-trial-runtime-acceptance, #567)

Consumer acceptance over the landed #649 guarded runtime fixture, its
machine-readable input package, and the #52 campaign contract - all consumed
read-only, never duplicated or edited. No shared/native/maintained edits, no
CMakeLists edits, no ADMIT. Issue #567 stays OPEN until the integrator lands
this handoff; trial is the last remaining P1 challenge runtime slice after
forest (chal1, done), navel (chal2, done), impact (chal0, blocked on #698) and
spring (chal3, running).

## Stage contract (exact source key, not the display title)

- level_key `challenge:trial`
- native_area_id 4
- stage_info_index 20
- source `stages/chal4.ini`
- slot `chal4`, challenge level 4

## Consumed pins (read-only)

- #649 fixture fragment + builder + inputs module + guard record: root
  worktree `.../p1-challenge-guarded-runtime-root`, native worktree
  `.../p1-challenge-guarded-runtime-native` (commit hashes re-verified at run
  time; never edited).
- #52 campaign contract `experimental/pikmin1_challenge_campaign_contract.py`
  on `codex/content-lanes-531` (loaded by the #649 inputs builder via a
  git-show snapshot; never vendored here).
- Canonical assets `C:/Users/alari/bbft/dist/cohesion/pikmin/assets` (audited
  read-only; staged into the rundir as a directory junction, never copied or
  modified).
- Captain guard `scripts/p2_fixture_captain_guard.h` sha256
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`, recorded
  in every acceptance record. The fixture runs this guard FIRST on every idle
  tick; CAPTAIN_DOWN exits BLOCKED and can never substantiate a PASS. Captain
  parked far outside attack reach (`P2_CHALLENGE_PARK`); no blanket
  invincibility; no fake guard provider.

## Commands (all write under the lane output dir only)

- Build inputs:
  `py scripts/p1_challenge_trial_runtime_acceptance.py --canonical <root> --root649 <r> --native649 <n> --assets <a> --out <o> build-inputs --head649 <h>`
- Private leased build:
  `... build --build-dir <o/build> --head649 <h>` (acquires the heavy-build
  lease, builds via the #649 build script, records exe sha + `ninja -n`,
  releases)
- Headed run:
  `... run --timeout 1200` (executes `fixture.exe --experimental-challenge-level 4`
  in `out/run-chal4` with the package env, captures `native.log`)
- Acceptance record:
  `... accept --log <native.log> --record-out <acceptance.json>`

## Gate outcomes (honest labels)

- `identity_spawn`: PASS only when the stage identity row, generator
  recognition/spawn counts, and a live starting squad are all observed in one
  uninterrupted run (no CAPTAIN_DOWN, fixture PASS marker present).
- `movement_animation`, `attacks_receivers`, `death_corpse`,
  `transport_reward`, `cleanup_reentry`: UNTESTED - a boot-only observation
  cannot exercise combat, death, haul, or reentry; nothing inferred.

## Pre-existing PIKI BIRTH limitation (recorded exactly if it blocks the run)

Trial is known to hit a pre-existing PIKI BIRTH limitation. When the engine
reaches its window/init but no `P2_CHALLENGE_SQUAD`/`P2_CHALLENGE_BOOT` marker
appears, the driver sets `birth_limitation_suspected` and the acceptance record
carries a `blocked_reason` of kind `piki_birth_limitation` with the exact log
lines and the named shared owner:

- owner: Piki birth path owner (`src/plugPikiColin/newPikiGame.cpp`; shared
  hook review #186, campaign contract #52).
- blocks: promotion (an unresolved engine limitation), not preparatory work.

An unresolved engine limitation blocks promotion; it never turns an unobserved
gate into a PASS.

## Not observed / not claimed

No movement, attacks, deaths, transports, rewards, reentries, timers, scoring,
or retry semantics. No playability claim. Protected observation is labelled as
such where it occurs and never proves captain damage.

## Remaining scope (not this lane)

Trial runtime acceptance closure after the PIKI BIRTH limitation is resolved
(shared owner), plus #52 timed/scored campaign follow-on scope 1. Native
CMake/CTest first-class targets remain a shared-owner follow-up.
