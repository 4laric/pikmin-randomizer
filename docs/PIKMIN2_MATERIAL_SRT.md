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
materials should use the binding-set API below; do not call `draw` once per
track because that would draw the entire shape repeatedly.

## Binding sets (#396)

`pc_p2_material_binding.h` adds `p2material::Binding` and explicit `Target`
records `{sourceMaterialName, sourceTextureSlot, hostMaterialIndex}`. A bank
track may map to several converted materials, but every bank track must have
a destination. Empty or oversized mappings (over 128 targets), unknown names,
nonzero texture slots, duplicate host indices and shared writable texture-data
or texgen-array pointers are rejected. Unbound materials are also checked for
these storage aliases because drawing the whole shape visits them too.

```cpp
p2material::Binding binding;
std::vector<p2material::Target> targets = {
    {"source_body", 0, bodyMaterialIndex},
    {"source_body", 0, secondBodyMaterialIndex},
    {"source_trim", 0, trimMaterialIndex},
};
bool ready = binding.bind(bank, shape, targets, sceneGeneration);
// After shape.updateAnim(...), on the draw thread:
bool drawn = binding.draw(bank, shape, graphics, actorSourceFrame, sceneGeneration);
// Before tearing down/replacing the bank or model:
binding.reset();
```

Use a nonzero generation owned by the scene/actor lifecycle, and advance it
before addresses can be reused. The binding checks the exact bank, shape,
material array/count, target storage pointers and generation. It does not own
those objects or generate lifecycle tokens. Keep the bank/model storage alive
and immutable for the binding's lifetime. A failed `bind` clears an older
binding; `reset` is idempotent. No callback is registered automatically.

Every sample is computed before material mutation. Targets are then scoped
together, the model is drawn once, and all values are restored. A later target
refusal rolls back earlier scopes without drawing. Draw exceptions also clear
the material cache and restore the scopes. Different actors can use independent
frames against one shared model. Draw uses bounded stack storage rather than
allocating one scope per material on the heap. Unsupported future samples (for
example nonzero rotation on the limited envmap path) still return false; the
family must handle that diagnostic explicitly.

The binding is explicit runtime glue, not an inferred converter mapping or a
package authenticator. Family owners must validate that the converted model
retained each intended source material and matrix slot.

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

### Binding-set validation

Native candidate `8ea6bde3` builds with the production Windows target; executable
SHA256 `120ad9592687638dc1c55164200a34efe39d017f352e6bce8167d3f8e9c7ed65`.
Compiled production tests cover two source tracks driving three host materials,
two actor phases, transactional refusal, draw exceptions, missing/duplicate/
aliased destinations, changed storage, generation mismatch and reset.
Full suite: 1364 passed, 23 skipped, 1047 subtests passed (same local asset and
symlink-privilege skips). Focused suite: 5 passed, 377 subtests passed.

`scripts/pikmin2_material_binding_fixture.cpp` is a separate test executable
built with `scripts.build_pikmin2_fixture`; it is not shipped as the player game.
In a private room stage retaining `snow_wait1_00.mod`, it creates a synthetic
single UV0 translation track and performs three draws within one frame: source
frames 0, 10, 0. Current OpenGL rendering produced 277233 visible color channels;
146107 channels changed at frame 10; the two frame-zero images were byte-equal.
Binding reset refused a subsequent draw. Captures were inspected and visibly
show the changed texture mapping. This is a renderer transform test, not a
claim that Snow has a source BTK animation or that its displayed pose is final.

Fixture SHA256:
`6a4723b1f43688bad6d55c0dd1af640c6be4c8933a287fed41a6f4cc02c2cc7d`.
Build provenance, native log and captures remain in private
`output/material396/`. Live multi-material/marked-envmap animation and other
backends remain unverified; the multi-material transaction has compiled tests.
Queen's omitted TEV stage and source-correct family material adoption remain
follow-up work. No player package, save or retail asset was changed.

### Queen adoption (#399)

The first source-derived diffuse + animated normal/specular layer is now
available for Queen. See [Queen specular contract and evidence](PIKMIN2_QUEEN_SPECULAR.md)
for the UV1 bake, opt-in stage command, two-stage renderer, integration inventory
and fidelity limits. This supersedes the older statements above that Queen
specular adoption is entirely pending; its third source stage and source lighting
remain future work.
