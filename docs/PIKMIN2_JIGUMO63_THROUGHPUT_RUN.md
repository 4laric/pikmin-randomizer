# Jigumo63 latch-first damage-throughput run (#167, family #167)

Lane shard-enemies-4-jigumo63-throughput-run. Executes the accepted #729
technique in a fresh private fixture+arena and reports evidence for #374
gate 4 (death + corpse) WITHOUT claiming any gate. No gates 1-3/5/6 work,
no family FSM edits, no ledger writes, no ADMIT.

## Technique consumed (read-only, #729)

Pass1 (#374 death-run1) failed on throughput: 117 throws drained 500 -> 380
(~1.03/throw); 9 bites, 7 eats, squad 20 -> 0, timeout, HP floor 380. A kill
needs strictly more than 500/20 = 25 HP drained per Pikmin lost. This run
uses latch-first sustained blows inside the 200-unit sweep (ATTACK key event
2 / frame 26 capture zone), keeps non-attackers out of the sweep (EAT-rate
bound), and re-latches promptly after flicks (radius 25, shake 100).
Anchors: LIFE 500.0 (pc_p2_jigumo.cpp:88), bite/swallow/flick keys, Dead on
mHealth<=0; source part rule; nest unrepresentable (home point stands in).

## Staged vs natural (labeled in the log)

STAGED (staged=1): squad deployment (6 near + 14 far), ring/re-latch
repositioning (AttackMode Pikmin never disturbed), reinforcement from the
far reserve. NATURAL (only observed): all damage, bites/eats/flicks, death
and the corpse. No sidecar/injection profile exists for this fixture, so no
stub marker can appear.

## Owned files (this slice only)

Native: tools/p2_jigumo63_throughput_run_fixture.cpp (guarded
replacement-main fixture; captain guard vendored, captain parked, 600-tick
squad evidence). Root: experimental/pikmin2_jigumo63_throughput_run.py
(stage + launch + validate), tests/test_pikmin2_jigumo63_throughput_run.py
(10 tests), this doc.

## Evidence contract

The run passes its preparation bar iff the log shows: live baseline,
family bind (374003/source 63), natural P2_JIGUMO_DEAD, carcass present,
HP-per-lost-Pikmin strictly above 25, zero CAPTAIN_DOWN, zero injection
markers, 960x540 centered window. The observer adjudicates; the fixture only
records. Evidence is reported for #374 gate 4; gate claims belong to the
family lane.

## Remaining work

Family lane (#167/#374) adjudicates gate 4 from this evidence. Captain
safety #632 adopted (vendored guard sha256 d2f678c9..., called before
pause/movie returns; negative + self tests in the fixture binary).
