# Static tutorial source water bridge

Issue #1124; implementation owner Codex through shared account 4laric.

The optional `full.water` reader retains all three source volumes in source order,
with inclusive X/Z sphere overlap and center Y <= surface - 3, without a bottom
cutoff. This follows read-only P2 source 632af93787b9c95b63f0c13be32b161375ce3a96,
`src/plugProjectKandoU/gameSeaMgr.cpp:269`. Dynamic lowering is rejected.

Only the opt-in tutorial accepts this sidecar, and a present tutorial sidecar
must contain exactly three boxes. Missing sidecars preserve the previous P1
attribute behavior; present malformed files refuse loading. Map load
resets the owner and volume list. All 5,332 source triangles/mapcodes remain
unchanged; water is independent of face centroids. Above/below pool queries
distinguish a dry upper height from the wet lower floor; actual controller
travel across an upper bridge remains unproved.

Creature effects, captain water/ripple/footstep classification, and Pikmin
bounce/update water timers consume the query using P1 feet position and native
collision radius. This is a bounded P1 engine behavior bridge, not retail P2
body, swimming, animation, effect-height or visual-water parity. Existing attached
object and Pikmin burial water checks remain legacy. PikiState.cpp is reserved
by #883 and is untouched; its existing drowning recovery consumes the timer.
The existing Blues Only In Water mod retains its normal behavior.

The stager wraps the accepted complete-terrain conversion without changing
geometry. Both the stage and all generator headers place the captain at X/Z
(220,1000), with 40 units of clearance above the source shoreline for natural
settling. The baseline retains 20 Reds on the dry entrance bank. A disclosed
species variant stages 19 Reds and one Blue: 18 free Reds remain on the bank,
and one free Red and Blue start near the captain for ordinary whistle gathering.
Generator bytes and source terrain/water inputs are hashed after modifications.

The PC-only, explicit tutorial StartingState holds the captain's current
generator position when there is no UFO. It preserves the normal startup delay,
animation and Walk transition, and leaves ordinary P1/UFO behavior unchanged.

The owned fixture uses actual SDL controller input for a round trip to (340,1000)
and observes actual captain water entry and dry return. Read-only upper/lower
pool probes are separate from controller travel. Canonical-equivalent captain
safety runs immediately after engine idle before movie/readiness returns;
960x540 centered startup and 20 live actors are required. Automated windows are
explicitly hidden. The manual mode shows the window and allows Pikmin losses
after READY while keeping the captain guard active.

Fresh fixture source `2f10c60946c04c189509b0e31839f64eabd9a93b` passed the
ordinary captain roundtrip in 12.453 seconds and species observation in 14.187
seconds, preserving 20 live bodies and all 5,332 faces. The species run observed
native Red Drown state with a water timer, Blue wet without Drown, and Red timer
reset after ordinary whistle recovery. Forced-down and paused/movie negatives
both exited 86 without PASS. A present zero-box tutorial sidecar was refused
with exit 3. Initialized-captain disappearance is covered by the fail-closed
source guard; no synthetic disappearance run is claimed.

The human input path reached hidden automated READY in 6.656 seconds. This is
startup proof, not a visible manual verdict. The source helper
`scripts/play_pikmin2_surface_water_smoke.py` verifies the supplied executable
hash and creates a fresh private scene for each launch. Use WASD/controller
stick to walk and Shift/controller B to whistle. The prepared local companion
is `output/p2-surface-water/play_tutorial_water.cmd`; it remains unlaunched by
a human and stops only its owned game process after 60 seconds.

Private production build/no-work, fixture provenance and bounded runtime
evidence live under `output/p2-surface-water/`. Hosted CI and final workflow
handoff are tracked in issue #1124. No retail generators, water rendering,
dynamic lowering, carry routes, natural species acquisition, full campaign or
full-level gameplay admission are claimed.
