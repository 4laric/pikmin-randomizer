# ch_MUKI_houdai P1 runtime (lane p2-challenge-ch-muki-houdai-p1, #735)

Parent: #541 (P0 import, done+integrated). Follows the accepted #537
ch_NARI_02tile P1 shape. Implementation owner: Codex through shared account
`4laric`. Bounded P1 runtime slice for P2 Challenge 09. No ADMIT. No ledger
writes. Issue #735 stays OPEN.

## What this slice delivers

- `experimental/pikmin2_muki_houdai_p1_runtime.py`: validates stage records
  against the catalogued P0 pin (2 floors, order 24, UI 8, timers
  100.0/150.0 s, sprays 1/1, 5x10 leaf, treasure 0), stages a hashed
  private run layout (stage-manifest + input package + run plan), and reads
  guarded boot logs with a dependency-free marker reader
  (`P2CHALLENGE_STAGE_ENTRY` / `P2_ROOM_READY` / `P2_FIXTURE_CAPTAIN_DOWN`).
- `native/tools/p2_muki_houdai_p1_fixture.cpp`: guarded challenge
  stage-boot fixture source (960x540 centred window, captain guard #632
  with orimaDead/NaviDead/HP<=1 checks, `CAPTAIN_DOWN` + BLOCKED exit,
  parked captain, receipt-parseable markers). Engine/family/shared edits
  require existing-owner review and are NOT included.

## Honest scope and remaining blockers

- Legal source bytes for `ch_MUKI_houdai.txt` are UNAVAILABLE (P0 missing
  prerequisite); the staged plan records this instead of inventing values,
  so no natural houdai gameplay can be observed yet. All six arena gates
  remain UNTESTED.
- The #537-pattern engine-table blocker (follow-on #710) applies to the
  shared stage-boot path; a houdai boot attempt must expect the same
  `engine-table-row-pending` BLOCKED outcome until #710 lands.
- Remaining: legal disc bytes, #710 stage-boot table row, leased heavy
  build + fixture provenance, fresh arena + live squad + 960x540 boot,
  captain-guard negative test. Floors beyond the slice and persistence
  remain OPEN. No playability claim is made.
