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

Runtime acceptance pending. No Blue/Yellow entry staging or terrain changes
are permitted. Initial20Red, scripted native controller input, production
auto-pluck, captain-only exit and checkpoint-confirmation bypass remain explicit.
Natural Yellow supply, mixed hazard gameplay, actual checkpoint UI integration,
hand-play F6, full campaign/AP/supervisor and maintained export remain open.
