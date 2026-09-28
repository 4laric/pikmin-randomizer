# Native camera-facing billboard for type-1 MOD meshes (#429, parent #128)

Lane 09, Codex through shared account `4laric`. Closes the HikariKinoko
(enemy id 48, Common Glowcap) shape-matrix type 1 (BBoard) failure end to end:
conversion, renderer and a real-GL acceptance.

## What changed

**Native** (branch `opencode/p2-lanes89-native-v2`):

- `include/Mesh.h`: new `Billboard = (1 << 17)` feature flag in the existing
  `mFeatureFlags` word — no MOD layout change, so strict MODs and every
  non-billboard identity stay byte- and behaviour-identical.
- `pc_port/pc_p2_billboard.h`: engine-independent `screenRotation(out, active,
  scale)` = `scale * normalised(active.rotation)^T`, rejecting a degenerate
  basis.
- `pc_port/pc_p2_billboard_draw.h`: `billboardFromJoint(out, joint, active)`
  keeps the joint's pivot translation and uniform scale but replaces its 3x3
  with `screenRotation`. `offDiagonal` and a small `Stats` counter feed the GL
  fixture.
- `src/sysCore/oglGraphics.cpp` and `src/sysDolphin/dgxGraphics.cpp`
  (`drawSingleMatpoly`): for a flagged mesh, each per-dependency draw matrix is
  replaced by `billboardFromJoint(joint, active)`.

The important correction found during GL bring-up: **`Joint::render` is dead on
the PC port**. The real draw is the OGL/DGX `drawSingleMatpoly`, and callers use
two composition conventions (some bake `lookAt*model` into the joint matrices and
use an identity active matrix; others keep model-space joints and apply
`lookAt*model` on the GPU). The renderer therefore keys off the **active GPU
matrix** alone: it forces `active * mesh` to be screen-aligned while preserving
the joint pivot, which is correct under both conventions.

**Converter** (`experimental/pikmin2_convert.py`):

- `decode`/`convert` accept `billboard='native'` (default stays `'error'`,
  `'static'` stays the recorded fallback). Native requires `bake_rigid`, a single
  billboard shape, and an axis-aligned, uniformly scaled rigid joint; otherwise
  it raises an explicit error.
- The billboard shape's baked geometry is re-expressed in the joint's
  pivot-relative, unit-scale local frame `(v - p) / s`; the MOD joint carries
  `scale = s` and `translation = p`, so non-billboard shapes are restored
  exactly and the flagged mesh is re-placed by that joint at draw time.
- `experimental/pikmin2_flora_assets.TOLERANCES['HikariKinoko']` is now
  `{'billboard': 'native', 'missing_normals': 'compute'}`: the default flora
  extraction emits the camera-facing bank.

## Evidence

Converter (offline, synthetic J3D2bmd3): `tests/test_pikmin2_convert_billboard.py`
— 16 passed (flag/pivot round-trip, pivot-relative geometry, uniform-scale
division, rotated/non-uniform rejection, `'static'` never flags).

Real source (private, no disc assets committed): all six sampled HikariKinoko
poses convert with `billboard='native'`; pivot/scale match the audited
`(-4,46,0)` / `0.8`, and every pose satisfies the axis-aligned/uniform
precondition. Candidate bank `output/tracks/p2-lanes89-next/hikari-native-01`.

Native math probe: `tools/test_p2_billboard.cpp` (CTest `p2_billboard_test`) —
`PASS p2_billboard`, proving `active * billboard` is screen-aligned with the
joint scale, the pivot is placed by the active matrix, and degenerate bases are
rejected.

**Real-GL acceptance** (`experimental/pikmin2_hikari_billboard_fixture.py`): a
replacement-main fixture loads the native Hikari MOD, renders it at two world
yaws with the preview camera, and reads the backend `Stats`:

```text
HIKARI_MODEL meshes=2 materials=2
PASS HIKARI_BILLBOARD draws=2 max_offdiagonal=0.000000 visible=2364
```

`draws=2` (one per yaw) proves the OGL backend took the billboard path;
`max_offdiagonal=0.000000` proves the composed draw matrix is screen-aligned
under the active matrix. Run `output/tracks/p2-lanes89-next/hikari-gl-run-02`,
native.log SHA-256 `95EE2D4487DED8DE6070EAA6A6961E2CB0EC115EDB3402AA7F7BB14B89EA401E`.

## Remaining / notes

- The converter requires an axis-aligned, uniformly scaled billboard joint. The
  six sampled Hikari poses satisfy it; a wider `pose_limit` re-check is cheap
  (the converter fails loudly otherwise). Handling a rotated billboard joint
  (baking `R^-1` out of the local frame) is future work if a source needs it.
- The GL fixture uses a manually staged native bank; the flora extract now emits
  that bank by default, so a full flora-install arena run is the natural next
  integration gate.
