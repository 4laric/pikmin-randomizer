# Dwarf Red sampled-pose interpolation

Codex implementation owner using shared account 4laric.
[#418](https://github.com/4laric/pikmin-randomizer/issues/418), shared engine #128.

The opt-in Dwarf Red Bulborb (Kochappy) renderer interpolates between the actual
sample-frame timestamps in its bank. Add `p2-kochappy-interpolation.txt` containing
exactly `P2_KOCHAPPY_INTERPOLATION_1` alongside the existing profile, bank and actor
sidecars. The existing nearest-pose renderer remains the default.

The loader validates all baked vectors and identical topology/material/resource
bytes before native Shape allocation. Each bound actor receives a private Shape
and preallocated scratch arrays; immutable bank materials and textures are shared.
Geometry interpolation rebuilds course and root-joint bounds. Forget/reset releases
registry handles before App-heap teardown. Repeated setup allocates another private
Shape until the scene heap is reclaimed, as with existing imported renderers.

The shared `p2pose::blendInto` function writes only into correctly sized caller
storage, after validating both source poses and the weight. It does not allocate.
Positions lerp, normals normalize their interpolated direction, and cancelling
normals choose the nearer endpoint. Exact endpoints preserve original vectors.
`pc_p2_pose_shape.h` supplies private Shape construction and geometry/bounds
publication for other compatible sampled banks. Call allocation on the App heap.
Callers must establish same-source, same-topology sample correspondence; the
helper alone cannot determine whether unrelated vertex arrays correspond.

Kochappy uses its P1 animator's motion and normalized frame counter. Wait/move
selection on the enabled path follows animator motion rather than residual
velocity. Death and lethal squash use the death clip; corpses hold its last pose.
There is no independent clock, so paused/repeated draws cannot advance animation.
This is interpolation within a clip, not cross-clip blending. P1 attack events,
AI, collision and hurtboxes remain authoritative. Linear vertex interpolation
can shrink rotating limbs between sparse samples; skeletal adoption is separate.

## Acceptance

`tests/test_pikmin2_pose_into.py` compiles production headers with warnings as
errors and checks exact endpoints, normalized/cancelling normals, stable buffer
addresses, invalid-input refusal without partial publication and unchanged sources.

`experimental.pikmin2_kochappy_interpolation_fixture` builds an isolated native
fixture against an exact production head. Its fresh stage copies sidecars, adds
a second generated Kochappy and links read-only assets, without copying saves,
economy or old logs. The hidden renderer checks all five clips at start, midpoint
and end, real position/normal arrays, visible pixel changes, pause/replay equality,
independent actor geometry, final corpse pose and forget/reset behavior.

Build with the module's `build(native, build_dir, fresh_output, exact_head)`;
stage with `stage(existing_private_kochappy_stage, fresh_run)`, then execute with
`run(isolated_fixture_exe, fresh_run)`. Its build records source/dependency hashes;
the runner requires completed provenance and an unchanged binary. It uses the
same hidden rendering harness as the skeletal crossfade fixture.

Local evidence resides under the engine lane's `output/interpolation418/`.
Native source: `e2247215cff90326cc3bd89105fa694a2434fe61`.
Windows production SHA-256:
`bbb83bf197408ba09caaeaf6ef6dba98ebd56e8a558065828af0a6b630a9d422`.
Isolated fixture SHA-256:
`3063d48eb199721f653a6de8bd82acf1027449239e71146d507bf89d5200e244`.
The renderer passed all five clips and both actors, with 328,550 visible channels
and 400,230 changed channels. Endpoint geometry, midpoint normals, pause/replay,
held corpse pose, actor isolation and forget/reset checks passed. Captures were
visually inspected. Focused regressions: 71 passed, 45 subtests passed.
Final combined-suite results are recorded in #418.
No player package, launcher, seed or save is changed by this opt-in engine work.
