# Frog material and apparent-scale audit

Issue #207; Codex Frog lane, shared 4laric. Diagnostic only. No converter,
native code, model colors or scale were changed. Passing runtime identity/motion/
corpse gates in #201 are unaffected; visual fidelity remains open.

## Reproducer and measured geometry

```
py -3.12 -m experimental.pikmin2_frog_visual_audit --imported output/p2-frog-import/import04 --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --output output/p2-frog-visual-audit/audit03
```

The new audit reads actual source BMD/BCA and imported MOD bytes, validates their
manifest hashes, recomputes weighted frame0 of wait1, and compares every emitted
vertex. It does not rely on the conversion JSON's reported bounds. Two real
audits are byte-identical: audit02/audit03 `audit.json` SHA256
`94afdf29e35455abe15149b1a05985b2e209244900b04762047a6f8a7d5b4ea1`.

| Model | Vertices | Baked extent XYZ | Maximum source-to-MOD vertex error |
|---|---:|---|---:|
| Frog | 392 | 45.3630,42.7588,45.8061 | 0.0000018661 |
| MaroFrog | 414 | 45.3649,30.6340,47.0266 | 0.0000009537 |

These errors are float storage precision. No uniform scaling or extra translation
was introduced into this source pose. This does not prove every animation frame
or native attachment correct. Native `BTeki::refresh` constructs the same
`onCamMtx` from actor world SRT for either the P1 fallback or imported draw hook;
the Frog family renderer adds no scale matrix. P1 Frog/Frow strategy defaults
both use TPF_Scale1. Squash/stretch and actual actor runtime SRT are separate.

The audit also records original P1 frog/frow raw vertex bounds, but those arrays
are in joint-local spaces and cannot serve as a scale ratio against baked P2
vertices. The P1 files have an exporter-comment footer after the native end
chunk; this is accepted only in the explicit source-control reader. Generated
MOD validation still rejects arbitrary trailing bytes.

The existing #201 captures show imports and controls in the same frame/camera
and original stage lighting setup. They visibly differ in brightness. They are
at different camera depths, jump heights and poses, so their screen sizes do
**not** justify a rescale. A depth/pose-matched comparison remains required.

## Concrete material loss

Source definitions: `J3DMaterialFactory.h` (material init indices),
`J3DFileBlock.h` (MAT3 tables) and `J3DTypes.h` (channel/TEV records), in the
read-only P2 decomp. The audit decodes actual per-material entries:

| Property | Frog body and MaroFrog body | Generated material |
|---|---|---|
| Register material RGBA | 204,204,204,255 | 255,255,255,255 |
| Color0 lighting | enabled; mask1; diffuse CLAMP2; attenuation SPOT1 | disabled |
| Color1 lighting | enabled; mask128; diffuse SIGN1; specular attenuation0 | disabled |
| TEV stage0 | texture×raster0, RGB scale1 (2×), clamp0 | texture×raster0, scale0 (1×), clamp1 |
| TEV stage1 | adds raster1 to previous, clamp1 | absent |

MaroFrog has **two** materials. Its second material is intentionally unlit,
white255, one channel/one TEV stage. A blanket diffuse-lighting enable or tint
would incorrectly change this material.

`pikmin2_convert.write_model` deliberately emits a generic static approximation:
white material and lighting control0 or0x1800. `PVW.h` shows0x1800 selects vertex
material inputs; it does not include diffuse-enable mask0x1. In
`dgxGraphics.cpp`, `GXSetChanCtrl` directly consumes that enable flag, so this is
a real omitted-lighting path, not a subjective inference from screenshots.
The same writer also omits the source scale/specular stage, whose opposing
effects mean arbitrary darkening is not a principled correction.

The Tank lane independently found matching body-channel loss in Tank/Wtank.
That does not establish a common explanation for Honeywisp's silhouette or
unrelated GX warnings. Their owners retain those investigations.

## Minimal proposed integration scope

Keep generic terrain/import behavior unchanged. Add an explicit audited material
profile for this recognized diffuse-plus-specular source pattern, mapped through
the actual source shape/material hierarchy. Preserve source register colors,
channel enables/diffuse functions, TEV scale/clamp and the second unlit material.
Fail closed on unsupported lighting/TEV patterns rather than turning all models
lit. Do not apply a geometric scale correction based on current evidence.

For an initial **diagnostic**, enabling only body diffuse lighting and restoring
its204 tint can isolate the unlit contribution, but it is not source parity:
the2× stage and additive specular are still missing. Such a diagnostic must be
labelled as an approximation and must not become a global default.

Next proof should use the copied #201 inputs in two private runs, matching source
actor/control position, idle pose, yaw, actor SRT, camera view/projection and
light state. Compare unmodified and explicit-profile models with the same
camera and measure their model-space bounds. Keep all bytes except the declared
material fields unchanged. Only then review a root-owned implementation and
fresh native captures; no corrected visual fidelity is claimed by this audit.

Three focused tests cover chunk truncation/nonfinite vertices, strict generated
footer handling and distinguishing vertex material-source bits from lighting
enable. The audit is executable and source-backed; paired corrected runtime and
full material acceptance are still pending.
