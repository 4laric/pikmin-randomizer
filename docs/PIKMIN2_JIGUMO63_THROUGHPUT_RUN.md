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
(14 tests), this doc.

## Evidence contract

The run passes its preparation bar iff the log shows: live baseline,
family bind (374003/source 63), natural P2_JIGUMO_DEAD, carcass present,
HP-per-lost-Pikmin strictly above 25, zero CAPTAIN_DOWN, zero injection
markers, 960x540 centered window. The observer adjudicates; the fixture only
records. Evidence is reported for #374 gate 4; gate claims belong to the
family lane.

## Run evidence (2026-09-17, generation 2)

Staged run fd633e8807f44d88abc8491428631483, fixture exit 0, observer
VERDICT EVIDENCE (no gate claimed here):

- `P2_JIGUMO573_BASELINE red=20 blue=0 live=20`; `WINDOW width=960 height=540
  centered_call=1`; `STAGE generator=374003 source_id=63 chain=family near=6
  far=14 staged=1`; engine `P2_JIGUMO_BIND generator=374003 source_id=63`;
  `CARRIER`, `CENSUS`, `SCENARIO latch_first`, `SQUAD` all present.
- Natural engine `P2_JIGUMO_DEAD generator=374003 source_id=63 health=0`;
  `P2_JIGUMO573_RESULT dead=1 carcass=1 lost=7 ratio=71.43 hp_drained=500.0`
  (500/7, strictly above 25).
- Combat observed: 2 bites, 1 eat (below pass1 bound of 7), 0 flicks,
  6 staged re-latches; zero `P2_FIXTURE_CAPTAIN_DOWN`, zero BLOCKED/REFUSED,
  zero injection markers, every staged line carries staged=1.
- native.log 66718 bytes sha256
  `88ee97daeecaf66a87ce9800b4f321e46ae30a09798c5da6b4aface0728b67ec`;
  result.json sha256
  `8c678156cb49f0625028e3945d8a448e481caa6c7381c2df735083d8398c8099`.
- Staged sidecars: actors sha256
  `874650bf4633785cc8b7a7cb23a0725e86ee215258911440d84dfe61d47dcb84`
  (`374003 Jigumo` only); bank sha256
  `36616de4470612a639a7e349a4aa8da9d421a03067bb141c6eb4337d071a79d9`
  (family manifest, read-only reuse); 101 Jigumo pose files combined sha256
  `3d0647f2475953c88ba16608cdc0632a90b0a7800b47dd16dd99e7481`.
- Build: native 859fe9bf9eb8dff029c5ecc1024f164e5fb4db6a (clean);
  `cmake --build --target pikmin_pc -- -n` -> `ninja: no work to do`;
  nectar.exe sha256
  `66ea163d03f3c4d8627ec6831783e5701692011550463c2fb1dba237d27a9f12`;
  fixture.exe sha256
  `64c13089758fe8ce669fccd877ebf987efdae8952cabc8db2439ee02b514bb48`.
- First staged attempt (run 698187b5) died at batch3 setup: the arena lacked
  `p2-aquatic-bank.txt` + pose bank (`P2_BATCH3 missing bank for present
  actor config`, exit 3). Fixed by staging the family bank/poses read-only;
  no fixture or engine change was needed.

## Remaining work

Family lane (#167/#374) adjudicates gate 4 from this evidence. Captain
safety #632 adopted (vendored guard sha256 d2f678c9..., called before
pause/movie returns; negative + self tests in the fixture binary).
