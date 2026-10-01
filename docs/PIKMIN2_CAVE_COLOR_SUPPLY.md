# Ordinary Blue-bud supply and mixed persistence (#1086)

This fixture starts with a disclosed 20 Red Pikmin. It walks to the Blue bud,
aims the cursor and presses/releases the mapped throw button through an SDL virtual
gamepad explicitly assigned to P1 by instance ID in this process. No direct throw API, AI transition, actor
position, velocity, species or attachment writes are used. Existing production
bud behavior consumes airborne actors and immediately plucks its real sprouts;
this does not prove player-operated plucking or UI input.

Acceptance requires five ordinary Red inputs consumed by the Blue bud, five
Blue outputs, exactly 15 Red and 5 Blue alive, consumed bud budget five, no
pending outputs, and a recalled mixed squad moving on the west side. The
fixture disbands there and walks only the captain across the water to the hole.
The native checkpoint saves the global mixed squad. This does not claim mixed
water traversal or full-squad physical arrival at the exit.

A fresh process must restore the actual 15 Red/5 Blue transfer and consumed
budget. The captain-down negative must exit 86 without success. All modes use
a fresh current overlay, centered 960x540 startup, background-test policy,
measured capacity admission and the mandatory 60-second wall-clock supervisor.
The native exit42 contract is assessed separately from the unchanged raw
supervisor result. Inherited autoplay is disabled and producer hashes are
verified before restart.

New fixture: `native/tools/p2_cave_color_supply_fixture.cpp`.
Runner: `scripts/run_pikmin2_cave_color_supply.py`, modes `supply`, `restore`,
`negative`, with explicit workspace, fixture, production, generator, assets,
pod and new private run paths; restore also takes the accepted producer path.

Bounded runtime acceptance passed on 2026-10-01. No Blue/Yellow entry staging or terrain changes
are permitted. Initial20Red, scripted native controller input, production
auto-pluck, captain-only exit and checkpoint-confirmation bypass remain explicit.
Natural Yellow supply, mixed hazard gameplay, actual checkpoint UI integration,
hand-play F6, full campaign/AP/supervisor and maintained export remain open.


Evidence is under canonical `output/cave-color-supply/`, at native
`5c2943a9274473149de291e85d32ef3c1b4dcdd5`. The private production build and
no-work Ninja check passed. Fixture-03 SHA-256:
`d505d054a1241427f4c3fe54cd993b0625bdc85732c048dd71b78352585c4eea`.

- `run-supply-04`: five mapped SDL throws produced five Red acceptances and
  five Blue sprouts. Mixed recall/movement had all 20 in formation, with maximum
  distance 153.456 units at the west-side waypoint. Actual checkpoint recorded
  15 Red/5 Blue and Blue bud usage five, Yellow usage zero. Exit 42 in 37.984 seconds.
- `run-restore-04`: actual producer transfer and bud state restored the same
  mixed squad and budgets, with the empty receipt ledger unchanged. Exit 0 in
  3.422 seconds.
- `run-negative-04`: same fixture, captain-down exit 86 in 0.906 seconds,
  without success. All three runs used the mandatory 60-second supervisor.

SDL background gamepad events are enabled only in the child environment,
recorded with input hashes. This preserves background-test policy without
stealing focus. No native controller override is used. Eight existing
playable-cave tests passed; runtime output hashes are verified before handoff.
Raw supervisor outcomes for 42/86 remain unchanged and are assessed separately
against the expected scenario exit contract.

Failed attempts remain preserved: run-01 targeted an out-of-room waypoint;
run-02 lacked SDL background gamepad events; run-03 reached the bud but a too
strict cursor-alignment tolerance prevented throwing. The final route stays
inside the existing room, approaches the bud more closely, and starts throws
within 20 units of its center. Production still owns its unchanged 30-unit
capture test. No terrain or gameplay actor relocation was used.
