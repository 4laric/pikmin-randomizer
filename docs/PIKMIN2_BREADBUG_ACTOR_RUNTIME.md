# Original P1 Breadbug proxy arena runtime

Scope #168/#186. New `pikmin2_breadbug_arena` stages the original Impact Site
practice map, collision/routes and base generator into a private chal0 slot.
It adds one nativeCollec8 proxy186081 at(-150,30,1850) and one ordinaryCollec8
control186082 at(150,30,1550). These are engineering arena placements, not P2
source placements. Generator offset is zero, birth count/radius is made
explicit with the existing deterministic-birth helper, and every original
course file is byte-verified unchanged. No shared seed/assets are overwritten.

`pikmin2_breadbug_actor_fixture.cpp` uses ordinary native AI updates. It does
not reposition the enemy or write enemy velocity/state/health. It positions
only the fixture captain near the initial actor for camera framing, disables
further tutorial demo flags and provides a zero-input controller. Movement
acceptance requires over15 units horizontal displacement and at least15 frames
of native horizontal velocity. Mere gravity settling is not enough.

The driver verifies exact production readiness identity/type/full birthXYZ,
live visual delegation and movement evidence. The fixture keeps the control
alive, resets the family mapping and verifies that drawing now declines both
the proxy and ordinary control. This tests registration reset, not a full
stage unload/reload or natural death/corpse route. SourceP2FSM, cargo stealing,
receiver damage and rewards remain outside this proxy test.

Captures cover initial actor, later movement and post-reset visuals. A capture
must be inspected before reporting framing/appearance success. Native process
success alone does not establish source model fidelity. The binary and frozen
build inputs must be identified in the result/provenance; do not use current
production filenames as historical evidence.

Two driver tests cover fullXYZ, real movement threshold, missing draw and
multiple-ready rejection. Local staging passed at
`output/p2-lifecycle-batch/breadbug-arena-prepare-01`. Runtime is pending the
fresh root build in this initial document version.
