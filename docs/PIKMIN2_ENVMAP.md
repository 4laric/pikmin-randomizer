# Explicit Jellyfloat environment mapping (#286)

Codex owns this engine/toolchain implementation using the shared 4laric account.
Family #243 retains actor and receiver ownership. Default converters are unchanged.

The source-bound `experimental.pikmin2_kurage_envmap` exporter accepts the two
Kurage/OniKurage BMD hashes audited by the base-opacity tool. It preserves both
source TEV stages, register values, konst selectors and texture order: UV0 diffuse
followed by NORMAL-generated I8 environment texture. Only the MOD material chunk
changes; geometry, texture chunks and pixel state remain byte-identical.

```text
py -3.12 -m experimental.pikmin2_kurage_envmap --model <enemy.bmd> --mod <original-converted-pose.mod> --output <fresh-directory>
```

Use an original restricted-converter MOD, not the output of the base-opacity
patch. Source identity is checked; matching the converted pose to that source is
still the caller's responsibility. Existing output directories are refused.
`patch.json` records source, input and output hashes and material descriptors.

## Matrix contract

P2 J3DTexMtx::calcTexMtx case 6 in J3DTevs.cpp computes Old-SRT * qMtx2 *
translation-free view/model. qMtx2 has horizontal +0.5 and vertical -0.5 scale,
with +0.5 offsets. J3DMatBlock.cpp removes translation before this calculation;
J3DTransform.cpp supplies the Old-SRT pivot formula. The existing P1 environment
path uses positive vertical scale and omits this SRT.

The explicit PVW texture-data marker `_UNUSED10=0xE6`, `_UNUSED11=2` selects the
new path. It supports one NORMAL environment generator with static zero-rotation
SRT; duplicate markers, animated SRT and unsupported source layouts are refused.
The renderer copies scale/pivot/translation into owned matrix state. Static
shapes do not run ShapeDynMaterials::animate, so its uninitialized matrix cache
must not be read. No material or actor pointer is retained.

The PC bridge reserves texgen source 0xE6 for this opt-in path, selecting raw
model normals. Its matrix already contains view/model, so using the existing
view-transformed normal would apply that transform twice. Ordinary texgen modes
and unmarked materials retain their behavior. A rebuilt engine is required;
old executables cannot reproduce this export correctly.

## Validation and limits

The native matrix probe checks 81 values including independent 4x4 source-math
comparisons across six view/scale combinations, ignored translation, and
transactional rejection of nonfinite input. Six Python test methods cover that
probe, both real-source exports, byte preservation and refusal cases, plus the
base-opacity regressions. Retail-asset checks skip when local assets are absent.

`experimental.pikmin2_envmap_runtime` builds a private material-only fixture from
frozen family display host 0894922ef53575590eae6a28b69caeaab1c0e948 against the new
engine. OniKurage is a model/material substitution in that host, not an Oni AI
test. Each run uses fresh asset overlays and captures flight, a camera turn and
owner teardown. No receiver implementation or player session is changed.

Initial process-success captures exposed solid-white bodies. Texture-only and
UV-only diagnostic captures narrowed the fault to normal-coordinate generation;
the I8 texture itself loads correctly. Shader specialization disabled reproduced
the same failure. This prompted direct static-SRT initialization and explicit
raw-normal support. Initial evidence is in local output/envmap286/validation,
validation-uber, texture-diagnostic and uv-diagnostic; those are diagnostic runs,
not visual acceptance passes.

Source lighting, BTK playback and animated texture transforms remain outside this
bounded export. Successful loading or attractive captures do not establish full
retail material fidelity. Final validation is recorded on issue #286.

The corrected four-run comparison (validation-final, native 6a90fb10) was
visually inspected: both colored translucent bodies and their spots remain
visible, with a varying environment highlight at both camera orientations.
Fixture SHA256: 4f03c4f9f595cf89e2799fe20bd805cac0935af4ff8a8b93270b18df42b08d72.
A subsequent cleanup, native 001fafba, also avoids the otherwise-unused initial
animated-cache upload before the per-mesh source matrix is loaded. The production
build passes at that revision; fixture-accepted/validation-accepted records its
separate runtime confirmation. All paths are under the private engine root's
output/envmap286 directory and are intentionally untracked.

Final native 001fafba: all four fresh runs exit 0 with camera and runtime markers;
reviewed captures retain the corrected bodies/highlights. Fixture SHA256:
4944fe1bf83ea4c0614dd6ca51038322db9e7dbffe1ebf8983e8f757b5645c10.
The teardown capture is taken at the lifecycle boundary and can contain the
previous framebuffer; it is not evidence of a cleared post-teardown frame.
