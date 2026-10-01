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


## Run evidence (gen 2 smoke run, 2026-09-17)

- Fixture exe `p2_muki_houdai_p1.exe` sha256
  `bd3d1b6777c36e5e83592dcddf519527b4ea483bd539e597b593b6071b60effe`,
  built from the committed guarded fixture plus the leased `pikmin_pc` link
  (empty-arg link fix applied to the split LINK_LIBRARIES).
- Arena `p1-muki-houdai-out/run-smoke/` (preview-room assets reused read-only
  from the cave-boot baseline run; `run.json` + `p2-session.json` recorded).
- Exit code 3 with `BLOCKED MUKI_HOUDAI_P1_BOOT engine-table-row-pending
  stage=ch_MUKI_houdai` in `run-smoke/native.log` (utf-16). No
  `P2_FIXTURE_CAPTAIN_DOWN`, no stage entry, no injected state.

### Six-gate table (all rows cite run-smoke/native.log via evaluate_gates)

- window-960x540-centred: PASS (`P2_MUKI_HOUDAI_P1_WINDOW width=960 height=540 centered=1`)
- captain-guard-silent: PASS (guard silent during observed run)
- squad-ready: PASS (`P2_ROOM_READY treasure=bolt carry=5 repairs=1`)
- stage-boot: BLOCKED (`BLOCKED MUKI_HOUDAI_P1_BOOT engine-table-row-pending`)
- challenge-arena: UNTESTED (stage never entered)
- exit-status: BLOCKED (exit 3 with BLOCKED marker)

Remaining blockers: legal `ch_MUKI_houdai.txt` source bytes and the shared
#710 `engine-table-row-pending` row. No ADMIT. No playability claim.



## Gen-4 evidence (row resolution via pinned MUKI rows)

- Fixture resolves ch_MUKI_houdai through p2challenge::muki::selectMukiByUiIndex(8), linked read-only from the #748 producer tree; miss stays BLOCKED.
- Guard runs on EVERY tick including movie ticks (moved before the movie early-return).
- Headed runs: P2CHALLENGE_STAGE_ENTRY stage=ch_MUKI_houdai table=0 tick=1, P2_ROOM_READY squad=20, no CAPTAIN_DOWN. Forced-down negative exits 86 with DOWN marker on tick 0; missing-flag exits 1.
- Sustained observation unreachable: the preview boot plays day-end/result loops (demo32/56 tables) that requestSkip refuses by engine design, so observed ticks freeze (movie=1, 117 ticks) and no PASS is emitted. Fail-closed holds; remaining gap is the movie stall, not the table.

