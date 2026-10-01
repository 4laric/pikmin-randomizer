# Honeywisp material diagnosis (#207)

Codex via assigned4laric. Source/data audit and bounded fix proposal; no native or
shared converter changes. Four focused tests pass. Run:
`py -3.12 -m experimental.pikmin2_qurione_material_audit --imported <Qurione import> --output <audit.json>`.
Actual evidence: output/p2-qurione207/material-audit.json.

## Concrete loss in conversion

The retail Qurione BMD contains **zero textures**, two materials and two shapes.
This is not a missing-texture problem. Both source materials use one TEV stage:
color inputs ZERO,C0,RASC,ZERO, ADD, zero bias, SCALE_2, clamp, PREV output.
The source expression is clamp(2*C0*lit_RASC). Register0 values are:

| Material | Source RGBA C0 | White-raster reference RGB |
|---|---|---|
| 0 | 226,226,226,255 | 255,255,255 |
| 1 | 255,50,200,255 | 255,100,255 |

The second material therefore loses a source-backed pink tint in the export.
The first material can legitimately saturate under bright raster lighting; it
would be wrong to darken both materials by eye. Material1's magenta material-color
field is not automatically the right replacement: its channel chooses vertex
color, and the TEV register supplies the actual tint. Source vertex colors are
white/grey with several alpha values for shape0 and white for shape1.

The audit parses the actual emitted MOD tag48, not just converter comments.
Both emitted C0 registers are white and both stages use ZERO,ZERO,ZERO,RASC,
scale1. Thus source register and scale are absent. Source alpha stage0 multiplies
A0 by RASA, while stage1 passes RASA. Current white A0 makes these equivalent for
these inputs, but a supported translation should still preserve the alpha formula.
Source lighting is enabled with ambient50 and channel-specific material/ambient
sources; the restricted exporter does not reproduce that complete lighting setup.

Offsets are grounded in local P2 J3DMaterialInitData/J3DMaterialBlock and
J3DColorChanInfo declarations. GXEnum.h confirms C0=2,RASC=10,SCALE_2=1.
Native sysDolphin/dgxGraphics.cpp loads mTevColRegs into GX_TEVREG0..2, so the
receiver already has the required constant-register mechanism. No guessed RGB
values or geometric scaling are needed to preserve this source expression.

## Minimal root-owned proposal

Add a narrowly validated optional untextured single-stage TEV descriptor to the
existing converter write path. Populate constant RGBA registers from MAT3 and emit
exact color/alpha op, scale, bias, clamp and output register fields for this audited
pattern. Preserve ordinary exporter behavior when absent. Refuse other expressions
rather than treating arbitrary multi-stage TEV as supported. Carry shape-to-material
mapping from INF1, not positional assumptions, into the implementation. This audit's
actual model has two shapes/materials and reports them in current traversal order;
the generalized implementation must verify/map them explicitly.

Regression should parse generated MOD bytes and prove source registers, color
inputs and scale survive, verify unchanged vertex/bounds/texture bytes, preserve
alpha/depth/blend/draw-order metadata, and retain defaults for unrelated models.
Then rebuild all21 poses privately, reinstall with regenerated source-bound hashes,
check cross-pose resource equality, and run the existing fresh copied fixture under
the same camera/light. This is a reviewable proposal; it has not been applied.

## Mesh versus host effects

Fixed capture output/p2-qurione203-runtime/observe/arena.png shows the mesh as a
white silhouette with a distinct bright effect below, plus the ordinary control's
effect to the right in the same frame. The proxy retains P1 effects; these are not
part of the source BMD texture count. Their exact intensity/attachment parity remains
unmeasured. The parsed mesh-material mismatch exists independently of those effects.
No effect was suppressed and no controlled effect-off comparison was performed.

Do not claim full visual fidelity after only fixing C0: lit-channel parity and
recognizable same-camera rendering remain acceptance gates. Source glow, translucency
and shading require fresh runtime comparison. No scale change is proposed; birth,
movement and real P1 nectar evidence from #203 remain separate passing gates.
