# Explicit baked normal policies (#233)

`decode(..., bake_rigid=True, missing_normals="compute", singular_normal="transpose-adjugate")`
is available now. `convert` also forwards both keyword options. Defaults remain
`missing_normals="error"`, `singular_normal="error"`. Nondefault policies require
baked geometry. A missing display-list normal now raises a clear ValueError rather
than an incidental KeyError; the existing reproducer catches both.

Missing policy compute derives area-weighted normals AFTER all position transforms,
including explicit weighted draw matrices. Original shape, position/joint and UV/
color attributes identify smoothing groups; separate shapes/seams are not welded.
Only missing corners receive generated normals; authored normals retain the old
transform path. Zero-area/cancelling geometry is rejected, not given an invented
normal. Explicit default mode supplies unit+Y for missing corners instead. Repeated
vertex-dict aliases are detached before mutation, while distinct original vertex
objects retain the existing in-place mutation contract.

The singular policy uses transpose-adjugate (cofactor matrix) when abs(det)<1e-12,
normalizes its result and preserves determinant sign for nonzero near-singular
matrices. For exact singular matrices this is an oriented-area normal convention,
not a unique inverse-transpose. A zero transformed normal remains an error because
rank collapse has destroyed its direction. No zero-vector/NaN acceptance or silent
+Y fallback is introduced for authored singular normals.

Opt-in reports include normal_policy with both selected policies, generated-normal
scope and degenerate behavior. Default reports keep their previous fields. This
provenance travels through decode/write_model, including explicit draw matrices.
Policies apply geometry approximations; native boss behavior, shading sign-off and
BTK animation remain separate.

Real local evidence output/normal233/final-evidence.json: all42 sampled frames
across14 KingChappy clips and9 Queen problematic samples convert twice with identical
MOD hashes. Queen dead83/111/139 and6 carry samples pass with nonzero cofactors.
Strict path failed those missing/singular samples as expected before opt-in. An
existing normal-bearing Qurione pose produces identical default bytes versus the
pre-change bake, SHA8cb5e730b64e66297cf21bcb49822cc27b3e3715c75e4e660d9a4a66e8091055.
No source assets or generated binaries are committed.

Focused tests cover area weighting, shape/UV seam separation, shared-corner aliases,
strict/default policies, degenerate triangles, rank2/annihilated normals and invalid
policy arguments. Existing Pod external-vertex mutation regression passes. Full
selected converter/enemy/skinning/Pod/Bulblax test result recorded in handoff.
