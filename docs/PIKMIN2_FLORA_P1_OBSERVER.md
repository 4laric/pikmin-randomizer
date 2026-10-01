# Flora P1 observer (#737)

Lane `flora-p1-observer`, issue #737. Owner: Codex through shared account
`4laric`. Bounded P1 observer for the enemies-1 flora gate (47 Clover, 80
Tukushi, 89 Chiyogami) through the landed #697/#723 flora hookup, consumed
read-only and never duplicated. Owns only the observer, its tests, this doc
and the guarded fixture. No shared edits, no ledger writes, no ADMIT.

## Consumed pins (read-only)

- Hookup root `8c535f8a` (driver, observer, tests, doc) and native
  `3e52765b` (converter, bridge, hookup fixture): converter blobs
  `b73cfe49...`/`59b3f4f4...`, bridge + fixture.
- Campaign contract pin `9aa6faad` (module content sha256
  `21e1caf02eda06acd9f686bf1b72bce2d6ea3bf366594bb2e8cb416c3aff1b87`).
- Captain guard `scripts/p2_fixture_captain_guard.h` sha256
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`,
  recorded in every acceptance record. The fixture runs this guard FIRST in
  its guard modes; CAPTAIN_DOWN exits BLOCKED and can never substantiate a
  PASS. Captain parked far outside attack reach; no blanket invincibility;
  no fake guard provider.

## Observation design

A live starting squad (20 Pikmin) is staged and presented at the mouths.
Three flora sessions (Clover/Tukushi/Chiyogami) bind the identity through
the M2 scenery path and drive naturalistic conversions (ordinary bud plus
Pelplant serving). Every swallowed Pikmin is absorbed into a counted sprout;
the session records converted/received/hauled with hauled always 0
(absorb-never-haul invariant: received == converted, nothing hauled off,
nothing vanished unobserved). Fresh private arena per run; centred 960x540
window; active observation loop. Receipt-parseable `P2_FLORA_P1_*` markers
plus `PASS P2_FLORA_P1_RUN sessions=3`.

## Gate outcomes (honest labels)

- Gates PASS only on genuinely observed evidence with an uninterrupted run.
  Boot-level observation cannot exercise combat, death, haul, or reentry;
  nothing is inferred. Protected observation is labelled as such where it
  occurs and never proves captain damage.

## Not observed / not claimed

No movement, attacks, deaths, transports, rewards beyond absorbed sprouts,
reentries, timers, scoring, or retry semantics. No playability claim.

## Remaining scope (not this lane)

Shared-engine per-tick hookup call plus CMake membership (serialized
follow-on under #723 mechanics with #171 owner + #186 review); later flora
content and persistence. Downstream: #171 flora backlog.
