# Static tutorial source water bridge

Issue #1124; implementation owner Codex through shared account 4laric.

The optional `full.water` reader retains all three source volumes in source order,
with inclusive X/Z sphere overlap and center Y <= surface - 3, without a bottom
cutoff. This follows read-only P2 source 632af93787b9c95b63f0c13be32b161375ce3a96,
`src/plugProjectKandoU/gameSeaMgr.cpp:269`. Dynamic lowering is rejected.

Only the opt-in tutorial accepts this sidecar. Missing sidecars preserve the
previous P1 attribute behavior; present malformed files refuse loading. Map load
resets the owner and volume list. All 5,332 source triangles/mapcodes remain
unchanged; water is independent of face centroids and correctly distinguishes
upper bridges from lower pool floors.

Creature effects, captain water/ripple/footstep classification, and Pikmin
bounce/update water timers consume the query using P1 feet position and native
collision radius. This is a bounded P1 engine behavior bridge, not retail P2
body, swimming, animation, effect-height or visual-water parity. Existing attached
object and Pikmin burial water checks remain legacy. PikiState.cpp is reserved
by #883 and is untouched; its existing drowning recovery consumes the timer.
The existing Blues Only In Water mod retains its normal behavior.

The new stager wraps the accepted complete-terrain conversion without changing
geometry. It stages the captain at X/Z (220,1000) on the dry source shoreline,
retains the 20 Reds on the dry entrance bank, and adds the source-only static
water sidecar. No retail generators, water rendering, lowering/drain actors,
carry routes or full campaign/gameplay admission are claimed.

The owned fixture uses actual SDL controller input for a round trip to (340,1000)
and observes actual captain water entry and dry return. Read-only upper/lower
pool probes are separate from controller travel. Canonical-equivalent captain
safety runs immediately after engine idle before movie/readiness returns;
960x540 centered startup and 20 live actors are required. Runtime acceptance,
fixture provenance and a direct user launcher remain pending until fresh builds
and observed runs pass; source/policy checks alone are not gameplay acceptance.
