# P1 Challenge Impact runtime acceptance (#565)

Lane p1-challenge-impact-runtime-acceptance. Consumes the landed #649 guarded
boot fixture read-only (fixture TU, harness build(), input package
validate_run_log, boot evidence) plus the #52 campaign contract. Owns only the
acceptance driver, its tests and this doc. No shared/maintained/native edits,
no harness duplication, no ADMIT.

## Pins

- Fixture source: #649 native worktree at its pinned head (recorded in the
  handoff root/native records); guard vendored in the fixture, canonical
  scripts/p2_fixture_captain_guard.h sha recorded at runtime by guard_record.
- Input package: experimental/pikmin2_challenge_runtime_inputs.py
  validate_run_log reused for the observed/blocked verdict.
- Contract: p1-challenge-campaign-contract lane (#52, done).
- Assets: user-owned dataDir with stages/chal0.ini and
  stages/chal0/default.gen; per-run fresh directory with assets junction.

## Consumption command

Run the driver phases from the lane root worktree:

    py scripts/p1_challenge_stage_runtime_acceptance.py --native <649-native>
      --build <private-build> --output <out> --assets <assets>
      --expected-native-head <sha> build run observe

The build phase configures the private dir, builds pikmin_pc, links the fixture
via the #649 harness build(), and records the ninja dry run. The run phase
launches the headed boot with a fresh assets junction and stops the checklist
once layout, generator output, squad, window and frames are all observed.
The observe phase maps the log to facts plus gate verdicts.

## Observed vs not observed

Observed on a clean run: CHALLENGE_LAYOUT_READY id=challenge-0 stage_index 16
file=stages/chal0.ini story=1; 80 recognised generators with 95 spawned
creatures (plus 30 plant generators/creatures); 20-piki squad; 960x540
centred-window log lines; FPS frames; PASS P2_CHALLENGE_GUARDED_BOOT; exit 0
with no CAPTAIN_DOWN. Gate identity_spawn PASS (natural); gates 2-6 UNTESTED
(boot-only observation proves no movement, combat, death, transport,
cleanup or reentry).

Not observed: autonomous movement, attacks/receivers, death/corpse,
transport/reward, cleanup/reentry, save/reload, day advance, scoring,
retry, or any chal1-chal4 content.

## Blockers and next scope

Remaining stages chal1-chal4 and the #52 follow-on scope 1 (resource/timing
audit) stay next scope. A captain-down run can never substantiate PASS.
Issue #565 stays OPEN.

