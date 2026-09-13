# Jellyfloat base-opacity repair (#282)

Codex engine/toolchain implementation, shared account 4laric. Family #243 keeps
ownership of actor and receiver behavior.

Both verified Kurage/OniKurage source models use two TEV stages. Stage zero
computes alpha as clamped `A0 + RASA * TEXA`, with A0=100/255. The restricted
exporter emits `RASA * TEXA`, which removes the body wherever texture alpha is
zero. This explains the observed spots-only display independently of the second
stage's missing NORMAL/envmap coordinates.

The explicit `experimental.pikmin2_kurage_material_patch` tool restores the
source's first color/alpha operation and three color registers. It accepts only
the two source hashes recorded in the module and the expected two-shape,
single-stage diffuse MOD layout. It changes only register and operation bytes;
geometry, texture data, material pixel state and file size remain unchanged.
Already patched files and existing output directories are refused. This is an
opt-in approximation; shared converter defaults are unchanged.

```text
py -3.12 -m experimental.pikmin2_kurage_material_patch --model <enemy.bmd> --mod <converted-pose.mod> --output <fresh-directory>
```

Output contains patched.mod and patch.json with source/before/after hashes and
descriptors. Source-model identity is verified; pairing the converted pose to
that source remains the caller's responsibility. This is not an installer or a
general material converter.

Validation: three tests cover byte-scope preservation, emitted-alpha evaluation,
malformed/repeated patch refusal, source identity and no-overwrite behavior.
Both source models' descriptors are checked from local assets. Kurage runtime
before/after uses the same frozen fixture from kurage-fixture-build-09, native
0894922e, in fresh private overlays of the sessions-11 assets. Both runs exit 0
with runtime/owner teardown markers. Inspected captures change from floating
spots to a visible translucent body. The patch changes 36 bytes in the tested
pose. Evidence: private engine root output/kurage282/comparison.json and patch/
patch.json, plus before/after captures and logs. Original session bytes were
verified unchanged after the comparison. No new executable build was needed
for this material-data-only change.

Remaining limits: the second TEV stage (normal-generated environment texture),
its texture matrices, source lighting and complete retail material appearance
are not implemented here. OniKurage's descriptor is tested but it has no runtime
capture in this batch. The earlier green/purple whole-frame capture did not
reproduce in the fresh baseline, so this patch does not claim to fix it.
