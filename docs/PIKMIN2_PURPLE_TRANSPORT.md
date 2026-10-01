# Purple native approach and Onion delivery

Tracking: [#1071](https://github.com/4laric/pikmin-randomizer/issues/1071).
Owner: Codex through shared account `4laric`.
Native candidate: [PR91](https://github.com/4laric/Open-Nectar---Pikmin-Native-PC-Port/pull/91).

This slice extends the existing `purple_combat` fixture with
`P2_PURPLE_COMBAT_MODE=transport_delivery`. It tests an acquired Leaf Purple
approaching a standard weight-10 Red pellet, attaching through native transport,
carrying it to the Red Onion, and producing the configured population reward.
The candidate changes fixture code only. Integration and the maintained source
export remain the integration owner's work.

## Acceptance contract

1. Begin with the ordinary campaign's 20 Reds. Script a native throw into the
   bound Violet Candypop, observe conversion, and use the captain's native pluck.
   The fixture stages the captain beside the resulting sprout; it does not
   inject Purple identity, maturity or population.
2. Spawn one standard Red number-10 pellet on terrain near the active Red Onion.
   Read its actual carry minimum and matching Onion yield from native config.
   Let it settle before recording the baseline. No subsequent cargo teleport.
3. Assign one Red the native Transport action. Let the action choose a free slot,
   walk and attach. Require 90 attached observations at strength one, less than
   two units of cargo displacement, and no reward.
4. Release that control through native action abandonment and formation. Assign
   the acquired Purple Transport, without setting a slot or forcing attachment.
   Require one attached carrier, strength ten, native approach displacement,
   and more than ten units of cargo movement.
5. Observe the pellet enter native Goal state targeting the Red Onion before it
   disappears. Require exactly its configured birth-counter increase and the
   same increase in actual Red population. Require the Leaf Purple alive,
   released and unchanged in maturity for 90 stable ticks, without another reward.

Non-test Pikmin are kept in formation by scripted action recalls. This is needed
because native formation Pikmin can volunteer on contact with a moving pellet.
The retired Red control becomes a non-test Pikmin. An already-attached helper
fails the run before recall; the fixture must never detach a helper and then
claim an uninterrupted single-Purple delivery. Recall count is reported.

## Preserved attempts

| Run | Native fixture pin | Result |
|---|---|---|
| haul01 | `502a1ed4f4ceee2eeacf8b55aec2e479f06bf528` | FAIL: idle helpers joined before the Red control. No delivery acceptance. |
| haul02 | `f9c7d562ae1313bd78bd7fd5c38d2ddb91243d35` | FAIL after 82.687 s: Red control and Purple approach/lift/movement passed, but an extra carrier joined before Onion uptake. Captain remained healthy. |
| haul03 | `5fe10ae877df4f23a4e17380d4a3394b8a4d4b9d` | FAIL: 180.125 s wall-clock timeout. Continuous recalls preserved the single-Purple test; acquisition, Red control and native movement passed, but no Onion uptake or reward. Healthy captain; route diagnosis pending. |
| haul04 | candidate `1d2c1a3c9518bbe634a21ddca54125fdf005ba74`; actual CI merge below | FAIL: standard 60-second bound, terminated at 60.110 s. Acquisition, Red control and movement passed; Red Onion selected, but no uptake/reward. |

The second failure exposed incomplete fixture isolation: a one-time formation
gather prevents free-mode volunteering, but `Piki::collisionCallback` can assign
Transport to formation members on pellet contact. Continuous non-test recalls
are a fixture correction; they do not change production carrying behavior.

Haul02 used fixture SHA-256
`30d1e8060b0addc3cbff24970b8870dace3056e3fad100b416902d4597eb593a`.
Windows CI run `36846662492` and both matching Linux runs passed. All six
artifact hash entries matched; `BUILD_INFO.txt` matched the native commit and
the build dry run reported `ninja: no work to do.`

Its fresh guard02 run correctly rejected a forced captain-down state: raw exit
86, no PASS, no timeout, 0.234 s. Haul02 logged a 960x540 window at x373/y263,
live starting field20, and real conversion/pluck. It observed 10.07 units of
single-Purple cargo movement before the later helper failure.

Private evidence is retained under `output/purple1071-runtime-haul01`,
`output/purple1071-runtime-haul02`, and their corresponding guard directories.
Haul02 log SHA-256 is
`d107b2fc5b571e7f791bec3d824f5bfb745fe814cc853fbb272a6115acc05683`.
Each attempt has its own session, input hashes, native log and acceptance JSON;
failed attempts are never overwritten.

Haul03 merges approved native main `00cd93c5e1ff4e0ecd0c85d6bba2771bf5cc5e77`.
Windows run `36851576507` passed all 211 selected tests. The CI checkout
`4cdb0a5eda286f38206f62ec9b094795d67d3581` and candidate have the same Git tree
`c0ba16a9ea43e7f35416349fbd37a20608510d03`; all seven artifact hash entries match,
and the no-work build dry run passed. Its fixture executable SHA-256 is
`d4bb3421e28fea38ffe5945c3a14f954fc48e8a0e78b4c5125b9c5e8f2ffb687`.
Guard03 again rejected captain-down with raw exit86 and no PASS/timeout.
Haul03 log SHA-256 is
`ee43c73a861a0bfa8084174513b6ab0bbd3e269c2a01e2d9ed7ab6af23c69f58`.
Its timeout must not be relabeled as delivery acceptance or assumed to be a
production defect without route/destination evidence.

## Latest standard run and next slice

Windows run `36853188764` built actual PR merge
`44764d805ec4d05bc8a6d4ef1af21fb19b9fd7a5`, combining candidate
`1d2c1a3c9518bbe634a21ddca54125fdf005ba74` with main
`03fa75bd4bd304a13950cf5dbc285223bcb69d99`.
The tested Git tree is `4c9af77eaea2b820c6e1c2f181e6d9423170df90`.
Artifact names/BUILD_INFO identify the candidate, while the Actions checkout log
identifies this actual merged production source; these pins are not conflated.
Windows passed all 211 selected tests, all seven artifact hashes match, and the
build dry run reports no work. The private CI build directory is
`D:/a/Open-Nectar---Pikmin-Native-PC-Port/Open-Nectar---Pikmin-Native-PC-Port/build`.
No local heavy build or maintained export was performed.

Fixture SHA-256:
`8fda6824b357d6147959f4667eb0467360d2542c498373e12f4bbff8b75e3edf`.
Guard04 used the canonical 60-second limit and correctly exited86 in0.422s with
captain-down, no timeout and no delivery PASS. Haul04 used a fresh session and the
same 60-second limit. It logged the centered960x540 window at373,263, field20,
native acquisition, the Red negative control and10.33units of Purple cargo travel.
Its log SHA-256 is
`6f7e537af892ee8b8dfc09311c4ae95b1a06de0813fdfc2fc6fd4ff74a7f6164`.

Telemetry establishes the intended Red Onion destination and computed native
speed17.328. Cargo starts at(-197.66,-37.72,2235.66), with the Red Onion at
(-377.66,-37.72,2155.66), waypoint67. That is about197units apart: even an ideal
straight haul at that speed takes over11seconds, before uptake and the90-tick
reward stability check. The acquisition/settling/control sequence leaves only the
initial few seconds of actual carrying within this monolithic60-second run.

Delivery remains **unaccepted**. The concrete next fixture slice is to separate
native acquisition/setup from the timed haul, using an ordinary saved state or
another independently validated setup phase without injecting identity or carrier
slots. Then use the route telemetry to reproduce and locate the longer diagnostic
run's unresolved stall. The60-second run confirms goal selection, but does not
explain the earlier180-second timeout; do not infer that a longer timer fixes it.
Only after locating that failure should a new production repair scope and file
ownership be claimed. Native91/root1090 remain drafts; this report is diagnostic
evidence for integration review, not a completed delivery handoff.

## Reproduction and evidence boundaries

Use a fresh legal-asset campaign stage, current roster validation and the bounded
canonical `scripts/run_pikmin2_fixture.py` runner. On this host the staging and
correlation helpers are `output/purple1071-stage.py` and
`output/purple1071-run.py`. They stage from the clean private root baseline
`fe7d772fcc69dddbcb1a774649f68c67acc43451` with an explicit source-2 binding.
This is a fixture manifest and local state heartbeat, not a live AP connection.
Standard acceptance uses `PIKMIN_P2_ROOM_WINDOW=960x540` and a 60-second
wall-clock limit for both the positive run and separate forced captain-down run.
The earlier 180-second attempts are diagnostic runs, never standard acceptance;
their delivery gate remains UNTESTED/failed, as recorded above. Longer diagnostic
runs cannot be promoted to standard acceptance even if they eventually deliver.

Full delivery remains unaccepted until the current exact-head runtime produces
the Onion-uptake, actual-population and delivery PASS markers. Compilation and
the earlier lift/movement observations do not close that gate.

This bounded test does not qualify player aiming/controls, every route, corpse
weights, generic ten-strength obstacles, live AP checks, or a complete campaign.
Prior Purple adult-direct and save/restart evidence stays separate and immutable.
Natural quake/stun/crush combat and ordinary controller gameplay remain separate
acceptance work; this slice must not be cited as their completion.

## Split controls and staged companion (2026-10-01)

At native dada102701a560d5fb8d0f87e02e6055dc777ae6, the separate ordinary Red
control passed in 23.86 seconds: one Red could not move/deliver the weight-ten
pellet, no population reward appeared, and it released normally. Natural positive
haul05 timed out at 60.187 seconds after native Violet acquisition and 10.09 units
of cargo travel. Red Onion waypoint67 and computed speed17.328 were correct;
the observed route initially curved away from the Onion. Uptake remains unproved.
Immutable aggregate: output/purple1071-split05-evidence.json.

Staged06 at native c142e05650fce0069773b71e5cbaaaeec541a1e5 timed out before
carrier selection. No acquisition, cargo movement or delivery acceptance follows
from that attempt. Captain state17 is ordinary Idle. Preserve its original log
and transport-acceptance.json in output/purple1071-runtime-staged06.

The follow-up fixture candidate 062518de434cd52430701f20fdff6cb2ca366270 includes
integration-approved native a0e93cbf80a3b8b08a76e2310afbf2e02588a79a. It adds
starting-squad counters and explicitly gathers a normal Red for staged/manual
modes without resetting its position. The natural positive/control paths retain
their separate acceptance requirements. Manual mode withdraws the initial20
through native Onion exit when ordinary visible startup keeps them stored.
Its reset key is F7; F6 already requests cave entry in production controls.

The manual companion deliberately changes one starting Red to Purple and spawns
one red ten-pellet at the same route origin. Other Reds are recalled if they try
to help. It does not assign transport to the Purple: the player selects/throws
it and observes pickup, travel and Onion absorption. A reset exits this fixture
and the launcher creates a fresh private session. It never resets a player save.
The prepared Play.cmd/Reset.cmd under output/purple1071-manual-smoke remain
DISABLED pending setup/reset and staged route validation. Staged identity,
scripted gathering/withdrawal and cargo placement cannot establish native Purple
acquisition, ordinary controls, campaign progression or save continuity.

## Route obstruction diagnosis and candidate08

On the same c142 fixture executable, Red06 passed in22.656s. A fresh staged06b
run reached normal carrying, then remained near(-190.65,-29.72,2096.79), short
of waypoint48(-192.13,-37.72,2075.10). Its last five two-second position samples
span only0.23units despite requested velocity, one attached Purple and strength10.
A fresh diagnostic noviolet06b omits only the appended Violet generator before
boot, preserves original generator records/map/routes and the cargo origin, and
travels past that position to final waypoint67. Its last five samples span88.78
units. It still times out60.093s without uptake; this is obstruction diagnosis,
not delivery acceptance. The first directory named noviolet06 had a preparation
path error and actually retained the Violet; PREPARATION_FAILED.txt records that
it is another unchanged baseline. Neither report is overwritten.

Candidate062518de Windows CI36874336293 passed211tests, eight artifact hashes,
and no-work dry run. Actual CI checkoutc1da70b6664666ec1b1e147ad58fbb2f94c59b88
has the same treead630d5da81bedeaf1ad5dae78674f442a3092aa as the producer.
FixtureSHA947b57b6088110145ba4ae2cca8e4f3a02ed207e81d37db76ee2118649dc1743.
Guard07 exited86 in0.219s as expected. Natural07 acquired/moved but timed out at
60.093s; staged07 waited for zero vertical velocity despite stable cargo XYZ.
Manual-ready07 rejected the partial squad before native withdrawal completed.
These failures remain preserved and do not certify the launcher.

Candidate3c51b312760dc944fed92069a434ff2e00b4bb6f fixes the fixture's partial-squad
wait and measures settled cargo with30 grounded, stable-XYZ observations rather
than requiring gravity velocityY to vanish. It adds an explicit west197 origin
(Red Onion -180x,+80z) beside the unchanged default east197 (+180x,+80z). Both
start196.98units from the same Onion. Cargo is spawned only once; the Violet,
original actors, map and route graph stay unchanged. A west result qualifies that
route only, never the obstructed east route. The natural west test still requires
native Violet conversion/pluck and all actual uptake/population/release oracles.
Manual readiness/reset tests exercise native withdrawal through MANUAL_START;
manual play uses west197 only after its own validation. No production placement
or transport code was changed. Windows CI36876547819 and fresh08 runs are pending.

## Validated staged smoke and remaining natural gate (final08)

Windows36876547819 and Linux36876548026 pass. Windows ran211tests, verified
all eight artifact hashes and reports `ninja: no work to do`. The producer is
3c51b312760dc944fed92069a434ff2e00b4bb6f, clean. Actual CI tested merge
22f52c4e281946e8e149c00ad824894ba1edb1fb on main2e6efbb1b841c1889d1bbd3b656e44ba6ae3629b;
its tree143391dadc4e9edbf43f0911144662783d11c27b differs from the producer by
current-main background virtual-pad fixes and the generated-delivery fixture.
Do not conflate those pins. ExecutableSHA:
3a56ae7ddbbe1904482d2b578dc3ab8819bcca9f9fea7cb31dae9e72fc9cc3b4.

| Fresh canonical60-second run | Result |
|---|---|
| guard08 | PASS negative guard, exit86 in0.219s, no positive marker |
| redwest08 | PASS22.781s, one Red cannot move/deliver; no reward/population change |
| stagedwest08 | PASS38.078s, native uptake, reward10 and population+10, live leaf Purple released,90 stable ticks/no duplicates |
| manualready08 | PASS11.875s, native withdrawal20, staged Purple, no transport assignment |
| manualreset08 | PASS11.985s, ready then reset-request exit90, no transport/reward |
| haulwest08 | FAIL60.093s timeout; actual Violet acquisition and movement, no uptake; final cargo approximately46units from goal |

The staged west route retains the Violet and all original map/route data. Its
success does not establish natural acquisition, ordinary controller operation,
full campaign progression or the east route. Native Violet conversion/pluck
passes separately inside haulwest08, but the combined bounded delivery remains
open. No production transport/placement fix is included, and no runtime was
manually operated by Codex.

The user-operated companion is now enabled at
`output/purple1071-manual-smoke/Play.cmd`; `Reset.cmd` or F7 requests a fresh
private session. README.txt explains selection/throw, pickup, turns and actual
Onion uptake. Setup explicitly withdraws20, changes one Red to Purple at its
existing position and places one red ten-pellet on west197. The script recalls
non-test Reds but never assigns the Purple to transport. Audio is muted by the
bounded diagnostic runner. The reset-file path is automated-tested; physical F7
and gameplay feel remain user feedback. Existing saves are separate.

Immutable aggregate `output/purple1071-final08-evidence.json` SHA256:
28f969bc7024b68041b3e1904d93f72bc435437c2063f13b5c21da2eca26466a.
It contains all exact run/report/setup/log hashes and raw results. Prior06/07
failures and the omitted-Violet A/B are retained. Native91/root1090 stay draft.
Next production follow-up is a coordinated Violet placement/return-route audit;
next natural acceptance work must fit acquisition plus real delivery within the
bound without synthetic identity, accelerated production or cargo relocation.
