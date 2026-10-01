# Impact squad-spawn stall diagnosis (#698)

Coordinator follow-up for the stopped consumer
p1-challenge-impact-runtime-acceptance (#565): headed chal0 runs stall
deterministically post-PARK with no squad spawn across controlled runs.
Implementation owner: Codex through shared account 4laric; executing
contributor Muse Spark 1.3 (worker muse-l58). No source/shared edits,
no runtime by this lane, no ADMIT. All six runtime gates UNTESTED.

## Verdict

The stall as observed is a fixture-observation freeze, not a proven
engine spawn failure: the RoomApp observer parks the captain
(P2_CHALLENGE_PARK at observed==1) and then its observed counter
never reaches the squad count at observed==60, while the engine keeps
rendering frames. Whether a squad spawned is unknowable from these
logs -- the fixture never gets far enough to count it. The precise
missing piece is per-gate instrumentation in the fixture, owned by
#649 (exact fix location below).

## Evidence inventory (read-only)

Consumer output
output/workflow/autofill/planning-shards/p1-challenge/prepared/p1-challenge-impact-runtime-output/acceptance/runs/:
8 run dirs; 7 native.log files of 799 lines each with PARK at :797
and 2 tolerated DVD failures at :404-405, differing only in session
IDs and asset-timing noise (pairwise diff verified); 1 empty log
(c150a1c77, 0 bytes -- startup produced no output, separate anomaly).
Consumer lane is blocked gen 2 with driver/tests/doc committed and
build evidence recorded; no gates claimed.

## Code citations

Fixture
(p1-challenge-impact-runtime-native/tools/p2_challenge_guarded_boot_fixture.cpp,
#649 lane): alivePikis counter :57; frame budget :59
(
equire(++frames<20000) -- at ~30fps the 600 s runs end near frame
18000, so no timeout abort fires); navi gate :61; captain guard :62
(vendored #632, no CAPTAIN_DOWN in any run); movie-skip gate :63;
pause/UI gate :64; PARK at observed==1 :68-74; squad count at
observed==60 :75; boot at observed>=120 :76-78; PASS at
observed>=180 :79-81.

## Mechanism (exact)

After PARK (:797) the log shows only engine heartbeat
(:798 [PC Port] FPS: 29.6..., Textures 511 live). For observed to
freeze between 1 and 60 with frames advancing, exactly one of these
holds every tick (fixture :61-64): 
aviMgr->getNavi() null, a movie
player active (with 
equestSkip() ineffective), mPauseAll on, or
mIsUIOverlayActive on. Movie-subsystem heap lines bracket PARK
(:738-739 resetHeap, :796 clearing top heap) but state no marker for
active/inactive, pause, UI or navi -- so the four candidates are
indistinguishable from current markers. The two DVD FAILED reads
(:404-405 chal0/1.gen, init.gen) are tolerated: boot continues 400
more lines through generator init (:635-636, 95 + 30 creatures), so
they are explicitly NOT the cause. No CAPTAIN_DOWN fired, so the
captain neither died nor interrupted in any run.

Ruled out: asset condition (all post-audio reads succeed; failure set
is fixed and tolerated), environment (7/7 deterministic shape on a
quiet host with a live renderer), captain death (guard silent).

## Attribution and fix location

- Primary, fixture-side: the #649 fixture cannot distinguish its own
  gates. Owner: p1-challenge-guarded-runtime-fixture lane. Fix: emit
  one diagnostic line naming the blocking gate (movie/pause/UI/navi)
  plus the alivePikis count at PARK time and every N stuck ticks in
  tools/p2_challenge_guarded_boot_fixture.cpp idle(). That single
  change converts the next stalled run from silent to attributed, and
  separates squad-never-spawned from observation-frozen.
- Secondary, engine-side conditional: if the diagnostic shows a stuck
  movie, pause or UI state, ownership goes to the engine
  movie/pause/UI paths (not named here -- no evidence yet); if it
  shows navi-null with a live captain, ownership goes to squad/captain
  spawn handling. Do not pre-assign either.
- The empty c150a1c7 log (startup produced nothing) is a separate
  anomaly for the runner owner, not this spawn path.

## Packet

- Lane commit for the three owned files (branch
  codex/autofill-impact-squad-spawn-diagnosis).
- Failing condition: deterministic post-PARK observer freeze across
  7 shaped runs + 1 empty run; consumer #565 blocked gen 2.
- Downstream: fixture owner (#649 lane) for the diagnostic markers;
  engine spawn-path owners only if the markers implicate them.

## Captain safety

No runtime by this lane; log-only observation. The #649 fixture
already vendors the #632 guard (captain check every tick, exit 86)
and no run shows CAPTAIN_DOWN -- captains were alive throughout.
Guard header scripts/p2_fixture_captain_guard.h recorded as reference;
no blanket invincibility exists anywhere in this evidence.

## Reproduction

    py -3.12 -m pytest -q tests/test_pikmin2_impact_squad_spawn_diagnosis.py
    py -3.12 -m experimental.pikmin2_impact_squad_spawn_diagnosis --log <native.log>
