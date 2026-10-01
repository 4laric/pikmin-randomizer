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

## Reproduction and evidence boundaries

Use a fresh legal-asset campaign stage, current roster validation and the bounded
canonical `scripts/run_pikmin2_fixture.py` runner. On this host the staging and
correlation helpers are `output/purple1071-stage.py` and
`output/purple1071-run.py`. They stage from the clean private root baseline
`fe7d772fcc69dddbcb1a774649f68c67acc43451` with an explicit source-2 binding.
This is a fixture manifest and local state heartbeat, not a live AP connection.
Standard launch uses `PIKMIN_P2_ROOM_WINDOW=960x540` and a 180-second wall-clock
limit. Every executable revision also gets a separate forced captain-down run.

Full delivery remains unaccepted until the current exact-head runtime produces
the Onion-uptake, actual-population and delivery PASS markers. Compilation and
the earlier lift/movement observations do not close that gate.

This bounded test does not qualify player aiming/controls, every route, corpse
weights, generic ten-strength obstacles, live AP checks, or a complete campaign.
Prior Purple adult-direct and save/restart evidence stays separate and immutable.
Natural quake/stun/crush combat and ordinary controller gameplay remain separate
acceptance work; this slice must not be cited as their completion.
