# Kusachi wired-squad extinction diagnosis (issue #787)

Lane kusachi-squad-extinction-diagnosis, gen 2. Fingerprint
`kusachi-wired-squad-extinction-after-boot`. Consumer kusachi-gameplay-obs gen 3
(#780, blocked): boot PASS (identity+movement, live 20 blue, exit 0), then
squad 20 -> 0 in ONE tick at ~12.5 s after boot (extinction_tick=90).
Read-only diagnosis; no engine/file edits, no duplication, no ADMIT.

## Evidence pins (all re-hashed MATCH)

- gen3 native.log `output/kusachi-gameplay-obs-run-gen3-v2/native.log` (1471
  lines) sha256 `bc2a4afc2f7b1ac0fb3a54108a9d33f13aa29db6b135217719a69775f143554b`
- gen3-report.json sha256 `2a500370ce3b644e471e5f7a3c48a7b2b9cdea3d05cc2a1aea0ffc337a2a2059`
  (re-emitted bytes; brief-era sha differs by formatting only - declared
  native.log/run-result shas verify, exe + pins match)
- run-result.json sha256 `071ca01ca9ddcc7fdc24b0970bc52a34bccc6bdc596675fb088b2b3a3a628e96`
- exe 1b13fb70354e0f32; root commit 618e75a9; native pin 68ac7496
- Analyzer `experimental/pikmin2_kusachi_squad_extinction_diagnosis.py`
  reproduces this verdict fail-closed; 6 tests green.

## Verdict: ENGINE manager-level squad removal (not hazards, not fixture)

1. Two independent readers agree on engine truth: `P2CHALLENGE_WIRING_TICK
   squad_alive` (pc_p2_challenge_runtime.cpp countSquad :53-64, iterates pikiMgr
   skipping dead) and `P2_CHALLENGE_CONTENT_WIRED wired=` (pc_p2_challenge_content.cpp
   countSquadByColor :38-49, same iteration). Ticks hold 20 for 89 ticks, then a
   SINGLE tick flips 20 -> 0 with zero intermediate counts (log:1170-1171).
2. Hazards ruled out: zero damage/death/drown/hazard/combat markers in all 1471
   lines (bomb/hit matches are asset loads; the one teki never engaged,
   teki_max=1, attacks UNTESTED). Incremental hazard kills cannot produce a
   silent single-tick 20 -> 0.
3. Fixture ruled out: the gameplay fixture only guards/polls/recolors
   (p2_kusachi_content_wiring_fixture.cpp, 228 lines, no squad-lifetime writes);
   the observer only samples positions; the driver only supervises. The wired
   count reflects engine pikiMgr truth, not fixture state.
4. Engine-side confirmation: immediately after the flip the engine plays the
   squad-extinction cinemas (demo46/demo47 loads + o_dead.stx at log:1178-1200,
   ship demo36 at :1303) - the engine itself concluded the squad is gone.
   time_left 167.5 (no timeout), floor 0, no transition markers.
5. `naviMgr dropped` is UNPROVEN from this log: zero navi markers after the flip
   (searched to end-of-log). The brief phrase is an inference, not evidence.
   The removal is manager-level (pikiMgr live set zeroed in one frame, no death
   trail); whether via navi-drop cascade or direct manager clear is
   undetermined - the discriminating probe below settles it.

## Fix / follow-on owner (files + lines)

Owner: consumer lane kusachi-gameplay-obs (#780, blocked gen 3) - instrument,
do not re-theorize. Exact follow-on probe in the extinction window (ticks
85-95): per-tick `naviMgr`/`getNavi()` null flags plus per-piki alive flags
(first 20 slots), emitted as parseable markers. Insertion points:
- `.../kusachi-gameplay-native/pc_port/pc_p2_challenge_runtime.cpp`
  countSquad() lines 53-64 (add navi-null + per-slot alive logging)
- `.../kusachi-gameplay-output/observer/p2_kusachi_gameplay_observer.cpp`
  extinction block lines ~263-271 (capture the same-tick snapshot)
- `.../kusachi-gameplay-native/pc_port/pc_p2_challenge_content.cpp`
  countSquadByColor() lines 38-49 (already the corroborating reader; keep)
If #780 cannot absorb it, a new bounded probe lane owning only those two
engine-adjacent files plus its own test/doc. No ADMIT; gates stay UNTESTED
until observed.

## Captain safety (#632)

No runtime run executed, launched, or proposed by this diagnosis (read-only log
+ source analysis). Guard standard for the follow-on run:
scripts/p2_fixture_captain_guard.h sha256
d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474
(orimaDead/NaviDead/HP<=1 -> CAPTAIN_DOWN + BLOCKED, parked captain).
Downstream consumer: kusachi-gameplay-obs (#780). Pins: root 618e75a9, exe
1b13fb70, native 68ac7496.