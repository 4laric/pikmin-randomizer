# Opt-in Snow skeletal deformation (#367)

Implementation owner: Codex through shared account 4laric. Native rendering can
now deform Snow vertices from the shared local-TRS joint player. This uses all
390 integer BCA frames across five clips, with shortest-path quaternion, linear
translation and scale interpolation between adjacent source frames. It is CPU
skeletal playback, not interpolation of two complete baked meshes.

## Data and runtime

`experimental.pikmin2_skin` exports `P2_SKIN_RIGID_1` vertex/normal bindings in
exactly the converter's existing geometry order. Snow has 13 joints, 226 position
bindings and 164 normal bindings. Each binding stores a joint index and the
original joint-local vector. Materials, topology, UVs and textures still use the
converted model. The full joint bank is 441,054 bytes and bindings are 13,765 bytes.

`pc_p2_skin.h` transforms positions and inverse-transpose-normalizes normals,
including nonuniform scale and hierarchical shear. Invalid counts, nonfinite
coordinates, out-of-range joints, singular normal transforms and stale instance
tokens fail closed. Data is limited to 128 joints, 65,536 vectors per array and
8 MiB input. The caller publishes geometry only after successful deformation.

Each Snow owns its mutable geometry, preallocated deformation buffers and joint
instance. The source clock remains the P1 animator mapping; death and squash
map to dead, and carried corpses hold the final frame. Deformation samples model
space, then the ordinary renderer applies the actor/corpse world transform.
The monotonically increasing sampling serial is an ordering token, not a second
animation clock. Reset and slot reuse destroy the instance and its token.

## Enabling and reproduction

Leave the default sampled renderer unchanged. For a private room fixture,
`p2-snow-skeletal.txt` contains `P2_SNOW_SKELETAL_1`, alongside the existing
interpolation opt-in. Stage `p2-snow-skin.txt` and `p2-snow-joints.txt` from the
exported skin and attachment bank. Normal campaign mode reads these names under
`assets/`. The fixture helper verifies source/model/timing and output hashes
before installing. Counts and clip durations are checked again natively.

Generate with `python -m experimental.pikmin2_skin --iso ... --snow ... --output
FRESH`. Build/run with `experimental.pikmin2_skin_fixture`; its `--profile` scene
contains 100 Pikmin, four Snow and four ordinary enemies. `--reference` selects
the sampled renderer in the same fixture binary. All ISO-derived assets and
runtime outputs remain local.

## Scope limits

Snow uses rigid draw bindings. Weighted envelopes, inverse bind matrices for
multi-joint vertices, source joint callbacks/IK and material animation are not
implemented by this format. The importer rejects envelopes. Quaternion
interpolation is an explicit interpolation contract; it does not claim exact
J3D Euler-channel interpolation at fractional frames.

The initial milestone retained the old pose bank for A/B comparison. The
[compact loader follow-up](PIKMIN2_COMPACT_SKELETAL.md) now requires only one
base mesh in skeletal mode. Sampled mode still uses its full bank. Existing
player executables and seed/session state are not modified by either batch.

## Validation (2026-09-13)

Native commit `da77f209de640c7217c29802e8033398c866e315`; production build passed.
The C++ kernel compiled with warnings as errors. All 390 source-frame position
and normal arrays matched the source converter with maximum component error
0.000010541. Synthetic tests cover a known 45-degree midpoint, nonuniform normal
scale, singular/malformed data, pause, death, stale tokens and independent owners.
Focused tests: 21 passed and 24 subtests; converter regressions: 7 passed with
3 local-asset tests skipped. The added midpoint test was rerun after the main set.

Native fixture SHA-256:
`488112d2d92db72af1341cdda806507661a811c59899a956d9779660482b3092`.
Local `output/skin367/lifecycle` passed native attack, death, carried final pose,
Pod delivery, exact ledger and duplicate-credit refusal, with 52 rendered
geometry comparisons. Fixture assigns Pikmin actions and positions the captain;
health and animations remain native. Captured death/carry images are partially
obscured by Pikmin/effects; profile image confirms four visible Snow actors.

Sequential A/B populated-scene runs used the same fixture executable, 100 Pikmin,
four Snow and four native enemies, 600 measured ticks after warmup. Hardware:
Core Ultra 9 275HX, RTX 5070 Ti Laptop present (also Intel integrated graphics).
GPU selection was not independently instrumented. Placements are held fixed for
comparability; this is not an unrestricted combat benchmark.

| Renderer | Tick median | Tick p95 | Tick p99 | Worst | Ticks >33.3 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sampled mesh | 13.194 ms | 15.371 ms | 16.373 ms | 17.415 ms | 0/600 |
| Skeletal | 12.323 ms | 15.989 ms | 23.872 ms | 29.587 ms | 0/600 |

Peak process-private bytes were 1,874,399,232 and 1,858,822,144 respectively;
these whole-process observations do not establish an animation memory saving.
The timings likewise do not establish a speedup. Evidence is under
`output/skin367/profile-reference` and `output/skin367/profile-skeletal`.
The renderer stays opt-in; neither public defaults nor the player's package changed.

Weighted palette support is now documented in
[PIKMIN2_WEIGHTED_SKINNING.md](PIKMIN2_WEIGHTED_SKINNING.md). The Snow-specific
export remains rigid; Groink provides the separate weighted source reference.
