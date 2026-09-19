# Perplexing Pool (p2-overworld-yakushima) P1 surface-session import (#150)

Implementation owner: Codex through shared account `4laric`. Lane
`p2-overworld-yakushima-p1-surface-session` (root-only tooling). This extends
the P0 course-record boundary with a real-source decode path and a P1 import
path that stages the decoded manifest into a private run layout and drives
the integrated `p2-surface-session-1` checker (#132). No native build, no
runtime run, no playability claim, no ADMIT.

## Source correction (documented, not a fork)

The P0 strict record validator requires a `farm` key, but retail
`CourseInfo::read` treats EVERY key as optional
(`src/plugProjectKandoU/gameStages.cpp:207-260`; `farm` is skipped when
absent and `mFarmPath` stays null, guarded at :440-442). No shipped course
block carries `farm`, and the block headers (`LimitGenInfo`, `CaveOtakara`,
`Ground Otakara`) are `#` comments ? only the counts and rows are real
stream data. The strict `decode_course_pairs` entry is preserved bit-for-bit
for synthetic boundary tests; the real-source `decode_course_block` entry
applies the source-faithful positional/optional-key semantics through the
SAME field validators.

## Real yakushima record (observed, never invented)

`user/Abe/stages.txt` (3275 bytes, sha
`4de9008c99e799b99b2746c0156846eeb7ad50895ad110fc7f2070db6de1fff8`):
start (-369.326, 80.000, 974.444), startangle 99.695, 6+3 generator rows,
caves y_01(11), y_02(14), y_03(14), y_04(13), test(0), ground max 7.
Cave entries belong to sibling caves-yakushima lanes (#158-161); routed,
never duplicated.

## P1 path

- `load_surface_contract()` resolves the real checker from the live checkout
  or byte-exact from content pin `b08e3bdc` (blob `3ba71fe9?` verified);
  otherwise `P1GapError` names the exact gap.
- `stage_p1_run()` writes `course-record.json` + `session-seed.json`
  (checker `blank_session("yakushima", 1)`) + `boundaries.json` into a
  private run dir.
- `drive_session_boundaries()` runs day_transition (begin?sunset?save?
  reload?begin), receipt_replay (deliver twice; the duplicate is contract-
  rejected), and exit_reentry (exit-on-surface rejected, then
  exit/enter/exit/enter) against expected outcomes, records the four
  missing-native-integration requests, and reports wake flags
  (`course_record_decoded` + `cave_entrances_known` true).
- CLI `--p1-run DIR` writes `boundary-report.json`; all three boundaries
  report `pass` on the pinned checker.

## Validation

- `tests/content_lanes/test_p2_overworld_yakushima.py`: 13 green (strict
  pairs, real-shape block decode incl. farm-absent, staging/drive incl.
  gap paths, real ISO bytes pinned to hash/size/tags).
- No runtime, no playability claim. Remaining P1/P2 blockers: save/
  progression (#132), actor/asset closure (#128/#130/#131/#140/#144/#145/
  #146); captain safety #632 (`scripts/p2_fixture_captain_guard.h`) is
  mandatory before any runtime run.
