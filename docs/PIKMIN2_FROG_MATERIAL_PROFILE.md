# Frog opt-in material profile and comparison

Issue #207, Codex Frog lane (shared4laric). New modules:
`pikmin2_frog_material_profile.py` and `pikmin2_frog_material_compare.py`, with
their two focused test files. No shared converter or native source was edited.

## API and bounded encoding

`profile(source_bmd, species)` accepts only the exact audited Frog/MaroFrog model
SHA256 values, reads source MAT3 channel/stage records and INF1 shape/material
mapping, and returns a per-shape profile. `describe(profile)` exposes the common
review representation: shape/material IDs, RGBA, lighting control and stages
with order plus nine-component color/alpha combiners. The Qurione worker uses
the same combiner representation independently.

`rewrite(mod_bytes, profile)` accepts the existing static exporter layout and
rewrites only MOD chunk48. Other chunks must remain byte-identical. It preserves
pixel/depth/texture state and static TEV registers, restores source color and
alpha stages/order/scale/clamp, and adjusts material offsets/chunk length. Body
RGBA is204,204,204,255; channel control is0x93 (diffuse CLAMP, specular SIGN,
register material sources). MaroFrog's second material stays unlit/white.
No texture, geometry, normal, joint or collision bytes are changed.

`prepare(imported, output)` validates the original bank, refuses existing output,
and prepares a separate opt-in bank with fresh pose hashes/sizes and a source
manifest identity. The ordinary installer accepts this bank without native
protocol changes. Root owns eventual opt-in wiring; generic conversion behavior
is unchanged.

```
py -3.12 -m experimental.pikmin2_frog_material_profile --imported output/p2-frog-import/import04 --output output/p2-frog-material/profile03
```

Final equivalent preparations profile03/profile04 are byte-identical:264 models,
8,591,616 bytes; manifest SHA256
`bd483404d88f2b13fddaf96ba2991d58713923a6a85bd65cebe60b69ed53df7d`.
The first comparison used profile01. Profile02–04 add review metadata only;
all model bytes match profile01 exactly.

## Native adapter limitations

This restores the supported source material operations, **not complete source
lighting parity**. Current DGX/PVW fixes diffuse light mask to3 while source
body mask is1, and uses global material color for specular COLOR1 instead of
the body's source204. Ambient and light environment are P1. These limitations
are in the generated manifest, with `source_parity:false`; resolving them needs
a root-owned lighting representation change. Do not present the profile as a
universal J3D material encoder or enable it globally.

## Matched-frame private comparison

The new comparison driver uses copied #201 fixture03 objects and their original
private tutorial shim. All955 header inputs still matched that snapshot; copied
objects/compiler/private sources were hashed before and after the replacement
family compile/link. No shared build occurred and this is explicitly a historical
snapshot comparison, not a latest-HEAD freshness claim.

Private executable: `output/p2-frog-material/fixture01/compare.exe`, SHA256
`4a527366c3a0d7c09763f125bf480c16623d6d8ce05df224525a7ea909a8ce70`.
Its provenance records native b602d8c plus the original captured dirty diff.

Run: `output/p2-frog-material/comparison01/stages/2096dc6f9da24ee595971b0a124acbcd`.
Exit0. Logs/compare.json/matched-evidence.json and the capture remain local.
`frog-live.ppm` was converted losslessly to PNG and inspected.

Left to right, the comparison draws baseline Frog, profiled Frog, baseline
MaroFrog, profiled MaroFrog. Both members of each pair use identical geometry,
wait1 frame0, unit scale, yaw0 and depth, in the same frame. Fixed view is
eye(0,80,500), target(0,20,0); X positions are -75,-25,25,75. All four cases log
the same ambient70,60,70, FOV23 and aspect1.5998. This replaces only diagnostic
render matrices/pose; it is not gameplay placement evidence. Ordinary P1 controls
remain visible in the background, but are not depth/pose-matched for sizing.

The profile visibly restores shaded yellow and gray body surfaces instead of
the baseline neon-yellow/near-white appearance. Geometry has not changed, and
no rescale is proposed. The material/light contribution is established, while
exact P2 light response and final gameplay visual QA remain open. The run's
inherited lifecycle PASS line is not reused as a new gameplay acceptance claim.

The log has the existing depth-texture0x11/GXCopyTex stub warning during startup,
before comparison profiles load. No claim of an entirely warning-free run is
made; the separate GX investigation remains with its owner.

Seven new tests pass: unknown source refusal, material count/layout mismatch,
reapplication refusal, nonmaterial preservation, intentionally unlit material,
and rejecting missing/mismatched comparison transforms/light/projection. The
three earlier audit tests also pass. No game assets, builds, saves or captures
are committed. Full animated-profile gameplay and the remaining native lighting
adapter work are the next review gates.
