# Weighted skeletal palettes (#370)

Codex implementation owner through shared account 4laric. This extends the
shared CPU deformation API from #367; it does not modify Groink AI or activate
a new renderer in player packages.

## Format and math

`P2_SKIN_WEIGHTED_1 <joints> <positions> <normals> <draws>` is followed by each
draw palette entry: influence count, then one `joint weight` plus row-major
3x4 inverse-bind matrix per influence. Finally, position and normal bindings
use the existing `index x y z` layout; their index now selects a draw entry.
A direct DRW1 joint is encoded as weight 1 with an identity inverse matrix.
`P2_SKIN_RIGID_1` is still accepted without changes.

For each draw, the runtime computes
`sum(weight * animatedJointWorld * authoredInverseBindJoint)`.
It transforms positions with that blended affine matrix and normals with its
normalized inverse transpose. Inverse binds belong inside the influence sum.
Normals are not blended after individually transforming/normalizing them.
This matches the existing source converter's normal policy; exact J3D
scale-flag shortcuts remain outside the contract.

Bounds: 128 joints, 512 draw entries, eight influences per entry, 65,536 vectors
per position/normal array, 8 MiB input. Duplicate joint influences, out-of-range
indices, nonfinite/negative weights, weight sums outside 1 +/- 0.0001, invalid
inverse matrices and trailing data are rejected. Weights are not silently
renormalized, clipped or truncated. A blended matrix can become singular even
with valid inverse matrices; deformation then returns false and the caller
must not publish its partial output. Use immutable parser-validated meshes.

Palette and joint scratch storage is stack allocated; callers preallocate pose
outputs. No new animation clock is introduced. Owner generation, pause and
reset behavior comes from the shared attachment instance. The current palette
is evaluated in model space; the actor transform remains the renderer's job.

## Importer and source comparison

`python -m experimental.pikmin2_weighted_skin --iso PATH --output FRESH` exports
Groink's source BMD, BCA clips, shared joint bank, skin bindings and a hash report.
All generated content is local. It reuses bounded EVP1/DRW1 validation and the
converter's stable binding order. Source envelope weights/inverse binds are
preserved directly rather than reconstructed from an assumed rest pose.

The Groink reference has 18 joints, 30 draw entries (16 multi-influence), maximum
three influences, 335 position bindings and 363 normal bindings. All eight
clips and their 351 integer source frames are supported: attack, death, flick,
rebirth, search, turn, carried pose and walk. Every frame's CPU output is compared
with the independent existing `draw_matrices` plus baked-converter path.
Maximum position-component error: 0.000037933; normal error: 0.000000667.
The rigid Snow reference still matches all 390 frames within 0.000010541.

Run `tests/test_pikmin2_weighted_skin.py` with `P2_WEIGHTED_BANK` pointing to the
export. Without that variable the synthetic native contract still runs, but
retail comparisons do not. Tests cover distinct inverse binds, the normal of
a blended nonuniform matrix, invalid sums/indices/duplicates/nonfinite values,
singular inverse and singular blend. The shared kernel also retains midpoint,
pause/death/stale-generation/independent-instance checks.

## Adoption boundary

The family renderer must bind a private mutable Shape with identical exported
vertex/normal ordering, sample the shared joint player at its authoritative
frame, deform into preallocated scratch, and publish only on success. Bind the
source joint bank and mesh report as a pair; count checks alone are not asset
identity. Source aim callbacks must modify the relevant joints before palette
construction. Runtime material animation and Groink aim callbacks are not added
by this patch. No live weighted Groink drawing, attack or visual-fidelity claim
is made by the command-line CPU probe.

Compact Snow model loading is covered by [#373](PIKMIN2_COMPACT_SKELETAL.md).
Enabling weighted playback for individual actors remains a separate follow-up.
Existing player defaults are kept.

## Evidence

Native `73c257579fc2e1ce7938c8edf3394baf2dc365d5`; production build passed.
Focused regression set: 13 tests, 8 subtests; 3 local-asset tests skipped. Both
retail Groink and Snow comparisons ran explicitly in this set. Standalone C++
probe compiled with `-O2 -Wall -Wextra -Werror` and passed; its SHA-256 is
`a73d574bf554635b4f485596aefd47b428273a06802f348edd95c05ba5fa0e69`.
The Groink bank contains 351 source frames.
Local evidence: `output/weighted370/regressions.log`, `probe-final.log`,
`dump-final.txt` and `bank/weighted.json`.

An assert-checked CPU microprobe evaluated 10,000 sample/deformation calls in
49.0972 ms on this Core Ultra 9 275HX system. This optimized standalone loop has
no rendering, actor AI, GPU work or full-squad load; it does not establish native
frame-time improvement or replace an in-game performance gate.
