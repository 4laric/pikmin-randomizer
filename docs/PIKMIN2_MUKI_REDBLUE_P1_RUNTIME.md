# ch_MUKI_redblue P1 runtime acceptance (#744, P2 Challenge 19)

Lane p2-challenge-ch-muki-redblue-p1. Implementation owner: Codex through
shared account 4laric. Reuses the done+integrated P0 import base for
ch_MUKI_redblue read-only; follows the accepted houdai/damagumo P1 shape.
No engine/family/shared edits. No ADMIT. No ledger writes.

## Scope

Stage a fresh ch_MUKI_redblue arena (practice overlay, chal0 slot) with a
live red squad, the #743 staged boot-request, and a session record; build
the private guarded fixture under lease; adopt the starting-Pikmin overlay
and 960x540 centred-window fixture; adopt scripts/p2_fixture_captain_guard.h
(#632, vendored semantics, sha256 d2f678c9...); run natural gameplay with
receipt-parseable markers plus a dependency-free run-log reader and negative
tests; publish a six-gate handoff with honest disposition.

## Stage-boot path

- Selector: adopted #743 `select_stage_extended("ch_MUKI_redblue")` ->
  gap provenance record (ui_index 18, table_order 17, 2 floors) rendered to
  `p2-challenge-boot-request.txt` (`P2_CHALLENGE_STAGE_SELECT_1`); unknown
  keys refused fail-closed. Staged boot-request validated by the fixture
  (SELECT_RESOLVED) but never trusted as boot proof.
- Control: "chal0" always resolves in the fixture probe (CONTROL_OK proves
  the probe works).
- Native rows: ch_MUKI_redblue resolves ONLY with #748
  (`pc_p2_challenge_muki_stages`) landed. Until then the fixture exits
  BLOCKED engine-table-row-pending (exit 3), mirroring houdai.

## Owned files (this slice only)

Root: experimental/pikmin2_muki_redblue_p1_runtime.py (stage + observer),
tests/test_pikmin2_muki_redblue_p1_runtime.py (6 tests),
docs/PIKMIN2_MUKI_REDBLUE_P1_RUNTIME.md (this file).
Native: tools/p2_muki_redblue_p1_fixture.cpp (guarded boot probe).

## Marker contract

P2_MUKI_REDBLUE_P1_BASELINE / _WINDOW / _NAVI_PARKED / _CONTROL_OK /
_SELECT_RESOLVED / _ROW_RESOLVED / BLOCKED ..._BOOT engine-table-row-pending
/ PASS ..._BOOT / P2_MUKI_REDBLUE_P1_REFUSED / FAIL ... / P2_FIXTURE_CAPTAIN_DOWN.
Six gates UNTESTED unless observed; the observer reports, never claims.

## Generation-3 status

#743 landed and adopted (selector resolves redblue, unknown refused).
Boot still pending #748 native rows. See generation notes in the lane
output dir for run evidence.
