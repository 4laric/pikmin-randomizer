# Shared texture SRT animation (#391)

Codex implementation owner, shared account 4laric. Parent #128; coordination #186.
This first animated-material slice imports ordinary BTK texture transforms,
samples them at an actor-supplied source frame, and applies supported transforms
for one draw without leaving changes on a shared material. It does not register
an enemy or enable Queen's animated specular layer automatically.

## Import and provenance

```
py -3.12 -m experimental.pikmin2_material_srt --source <local.btk> --output <fresh-directory>
```

The output is `material-srt.json` (reviewable source metadata and curves) and
`material-srt.txt` (`P2_MATERIAL_SRT_1` native bank). Both carry the input SHA256.
Export is deterministic and refuses an existing output directory. Keep retail
source files and generated banks local. Package owners must include the bank in
their existing asset manifest/hash verification; the embedded source hash is
provenance, not authentication of an edited bank.

Supported input is one J3D1btk1/TTK1 block, ordinary texture matrices, playback
attribute 0 or 2, 1–32767 source frames, rotation shift 0–15, at most 128 named
tracks, 4096 keys per curve and 65536 active keys total. Counts, offsets, finite
values, strictly increasing key times and unique material-name/slot pairs are
validated. Constant, default, shared-tangent and independent-tangent channels
are supported. All nine source axis channels are validated; the five channels
used by J3D are scale X/Y, rotation Z and translation X/Y.

Post matrices, Maya calculation, other playback modes and malformed input are
rejected explicitly. The native bank reader applies corresponding limits and
rejects trailing tokens. Texture slots are retained as metadata; remap ordinals
are not treated as host material indices.

## Native use

Load with `p2material::read(std::istream&)` once, then keep the bank immutable.
`sample(bank, trackIndex, sourceFrame, sample)` does not advance a clock. Supply
the same authoritative source frame used for that actor's pose and events;
the actor owns loop, pause, seek and terminal-frame policy. Frames outside
`[0, duration]` and nonfinite results fail without changing the output sample.
Rotation is truncated before the BTK power-of-two scale and signed-16 wrap.
The matrix sampler uses JMath's 2048-entry angle indexing; host trig rounding
is not claimed to be bit-identical to the retail lookup table.

After the shape's normal animation update, draw a supported material using:

```cpp
p2material::Sample sampled;
if (p2material::sample(bank, trackIndex, actorSourceFrame, sampled)) {
    bool applied = p2material::draw(shape, graphics, hostMaterialIndex, sampled);
    // Handle false according to the family's explicit unsupported-binding policy.
}
```

The family must first resolve the bank's material name and texture slot against
its converted model. This adapter handles only the single texture matrix at
slot zero; do not bind a nonzero source slot to it. It cannot infer whether a
converter retained the intended material/stage. A family with several animated
materials needs an explicit combined scope before drawing; do not call `draw`
once per track because that would draw the entire shape repeatedly.

`draw` requires a camera, valid host PVW material index, exactly one texture-data
entry and one texture generator of type 1 at coordinate zero, with no competing native texture
animation (`mTotalFrameCount == 0`). Accepted coordinates:

- UV0 (`mTexGenSrc == 4`): fills the PVW matrix cache and selects it for the draw.
  Translation goes in column 3 because the host UV input is `(s,t,0,1)`.
- Existing explicitly marked environment maps (`_UNUSED10 == 0xE6`, normal
  source 1, animation factor not 255): updates scalar SRT values for the existing
  normal/view composition path. Both existing and sampled rotation must be zero.

The draw wrapper clears the material-pointer cache before and after drawing.
`ScopedSrt` restores every field it changes, including raw bytes of potentially
uninitialized static matrix caches. Nested scopes restore in reverse order;
actors sharing a model cannot accumulate one another's transforms. Use on the
draw thread only, with material arrays alive and stable until scope destruction.
Unsupported layouts return false before changing material state. Family code
still owns fallback drawing or a visible diagnostic for an unsupported binding.

## Evidence and limits

Synthetic tests exercise truncated/corrupt input, tangent formats, constants,
rotation truncation/wrap and angle indexing, endpoint sampling, invalid-frame
nonmutation, nested/exception restoration, two actors sharing a matrix, normal
map restrictions and material cache invalidation around the production draw
wrapper. They compile the production sampler/scope against observable renderer
doubles with warnings treated as errors. `sample_p2_material_srt.cpp` provides a
standalone probe; `experimental.verify_material_srt` compares its output to an
independent algebraic translation of the JMA interpolation instruction order.

Local Queen oracle: `queenchappy_model.btk`, SHA256
`af0dde017624a5b30459b8ba55ed70a1d70de14f841ed58802b3b07565ef4eae`.
Its 30-frame `mat_queen_body` slot-zero animation passed all 241 samples at
eighth-frame intervals. Maximum absolute error was `2.3403046167658204e-09`
against tolerance `2e-6`. Source data and output remain under the private
worktree's `output/material391-queen/`; no retail keys are checked in.

Native candidate `ce404ee65c2e75c1cc12ef55851ee107615feec2` builds successfully
with the Windows MinGW production target (`cmake --build build-timing --target
pikmin_pc -j 6`). Executable SHA256:
`09ea63ceb1810c8553d10b37a8bc0cc2f43f1437c7e9bf6bec71b7fea5d32d24`.
The existing Dolphin declaration and LTO serialization warnings remain.
Focused tests: 5 passed, 377 subtests passed. The rebuilt executable stays in
the private native worktree; no player launcher or save was changed.
Full `pytest tests -q -rs` with MinGW on PATH: 1364 passed, 23 skipped,
1047 subtests passed. Skips require absent local extraction outputs or Windows
symlink privileges. A subsequent focused run also passed after bounding the
decoder's aggregate key count incrementally during import.

Read-only Pikmin 2 source references: `J3DAnimation.cpp` texture-SRT transform
sampling, `J3DAnmLoader.cpp` TTK1 loading, `JMath.h` Hermite/short-angle helpers,
and `J3DTransform.cpp` standard texture matrices. The numeric oracle verifies
source equations, not PowerPC instruction rounding or live rendering.

Remaining #128 work: explicit family binding and live animated-material fixtures;
Queen's converted model currently omits the animated specular TEV layer;
multiple texture generators/stages, Maya/post matrices, BRK color animation,
BTP texture swaps and backend visual acceptance remain outside this slice.
