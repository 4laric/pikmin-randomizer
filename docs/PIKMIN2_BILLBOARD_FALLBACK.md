# J3D billboard (SHP1 shape matrix type 1) static fallback (#429, parent #128)

This note records the bounded converter capability that unblocks HikariKinoko
(enemy id 48, Common Glowcap) conversion, and the precise native interface
request for correct camera-facing rendering. It is conversion-correctness
evidence only; the visual gate is **BLOCKED/UNTESTED**.

## Reproduction

On GPVE01 US rev 0, `experimental.pikmin2_flora_assets.extract` reported
HikariKinoko at 0/1 clips. Every pose failed in `decode` with
`ValueError: Unsupported shape matrix type` at
`experimental/pikmin2_convert.py` (the `s[rec]` guard). The failure is the
shape matrix type, not the BCA pose, the envelope/weld path or the material.

## Model structure

`enemy/data/HikariKinoko/enemy.bmd` (sha256
`da3be030cac3065945c90171af2474f100c50ec492b45d7d82192f47a6e432b7`):

| | |
|---|---|
| Joints (JNT1) | 5 |
| Envelopes (EVP1) | 0 |
| Draw entries (DRW1) | 4 (all direct, joints 1-4) |
| Shapes (SHP1) | 2 — matrix types `[1, 3]` |
| Clip | `hikarikinoko.bca`, 70 frames, sha256 `35fdfbf61f536a1a29147510a013e81419b4476c12291a4dbe5c0a1d61813cf0` |

- **shape 0 — type 1 (BBoard / billboard), material 0, DRW1 draw 0 → joint 1.**
  A tiny display list (32 bytes) with only position and UV0 attributes; the
  source shape ships **no normal attribute**. Joint 1 carries the authored
  billboard anchor scale `0.8` and translation `(-4, 46, 0)`.
- **shape 1 — type 3 (Multi / skin), material 1, DRW1 draws 1/2/3 → joints
  2/3/4.** Position, normal, vertex colour and UV0 attributes; 5312-byte display
  list. This shape already converts through the existing rigid multi-matrix
  bake.

The type-1 flag is the only blocker. It is a **view-time** attribute: the source
applies `J3DCalcBBoardMtx` to the joint's world matrix using the camera view
matrix (`native/pikmin2-research/src/JSystem/J3D/J3DTransform.cpp:19`,
`J3DShapeMtx.cpp:558 J3DShapeMtxBBoardConcatView::load`). A static MOD file has
no view matrix, so the orientation cannot be baked for all camera positions.

## Capability

One opt-in knob, defaulting to the strict behavior:

- `experimental.pikmin2_convert.decode(..., billboard='error'|'static')` and
  `convert(..., billboard=...)`. The default `'error'` is unchanged and still
  raises `Unsupported shape matrix type` for type 1. `'static'` accepts a type-1
  shape **only together with `bake_rigid=True`** and bakes the authored
  vertices/normals through that shape's rigid joint draw matrix, exactly as a
  basic shape would be. Any other mode value is rejected.

The fallback is recorded, never silent. When at least one type-1 shape is
baked, the pose report gains:

- `billboard_policy`: `'static'`
- `billboard_shapes`: J3D shape indices affected (HikariKinoko: `[0]`)
- `billboard_materials`: their material indices (`[0]`)
- `billboard_note`: states that camera-facing orientation is not reproduced.

Strict and unaffected conversions keep byte-identical reports. Type 2
(Y-billboard) and type 4 stay rejected — this is a deliberately bounded slice.

`experimental/pikmin2_flora_assets.TOLERANCES` opts **HikariKinoko only** into
`{'billboard': 'static', 'missing_normals': 'compute'}`. `missing_normals`
is the pre-existing #233 policy and is needed because the source billboard
quad has no normal attribute; `'compute'` derives its normal from the baked
quad rather than inventing a unit up-vector. All other flora identities keep
strict defaults.

## What this unlocks

At `--pose-limit 6`, HikariKinoko goes from **0/1 to 1/1 clips** (6 poses,
`frames 0,14,28,41,55,69`, 161088 bytes). Every pose report records
`billboard_policy='static'`, `billboard_shapes=[0]`,
`billboard_materials=[0]`. A strict-default control on the same model still
raises `Unsupported shape matrix type`.

No other species' output changes. Pelplant and the other flora identities are
untouched and stay byte-identical.

## Non-claims and visual gate

This is conversion correctness, not visual fidelity. The baked billboard quad
is fixed in the model's authored plane; it does not turn to face the camera.
**Visual gate: BLOCKED/UNTESTED** pending the native interface below.

## Native billboard interface request

The static MOD format has no per-mesh billboard concept:

- `native/include/Mesh.h`: `Mesh` stores `mParentJoint`, `mFeatureFlags`,
  `mMtxGroupCount`/`mMtxGroupList`, `mJointList` — no shape/matrix type.
- `native/src/sysCommon/shapeBase.cpp:124 Mesh::read` reads exactly those fields.
-   Draw paths resolve each vertex's matrix from the joint/MtxGroup list with no
  camera term: `native/src/sysCore/oglGraphics.cpp:653 drawSingleMatpoly`
  (`animMatrices[...]`, `getAnimMatrix`) and the dgx equivalent
  (`native/src/sysDolphin/dgxGraphics.cpp:1358`).

Requested additive interface (shared-semantics review required, so coordinate
through #186 rather than landing it in a family lane):

1. Add a `Billboard` bit to `Mesh::FeatureFlags` (e.g. `1 << 17`) and one MOD
   format byte for the shape matrix type in the Mesh block. The converter
   already knows each shape's type; it can emit `1` for BBoard shapes.
2. In `Mesh::read`, read the byte (default `0`, so existing MODs are unchanged)
   and set the feature flag.
3. In both draw backends, when the flag is set, build the draw matrix from the
   current view matrix with a `J3DCalcBBoardMtx`-equivalent (billboard: extract
   the inverse-view basis, normalise, and apply the joint's authored scale and
   translation; keep a Y-billboard variant for type 2), instead of the plain
   joint anim matrix. Reference implementation:
   `native/pikmin2-research/src/JSystem/J3D/J3DShapeMtx.cpp:558` and
   `.../J3DTransform.cpp:19`.
4. Add a converter emit path (for example `billboard='native'`) that writes the
   flag while still baking geometry. Until step 3 exists, keep emitting the
   recorded `'static'` fallback.

## Evidence

Private, uncommitted, under `output/`:

- `output/p2-converter-evidence/run1/HikariKinoko/` and
  `output/p2-lane-verify/flora-run2/HikariKinoko/` — extracted source assets
  (model + BCA + metadata).
- `output/p2-hikari-48-evidence/run1/HikariKinoko/` — six converted
  `flora_HikariKinoko_hikarikinoko_*.mod` poses plus `hikarikinoko.json` with
  per-pose SHA-256 and the recorded billboard fields.
- `output/p2-hikari-48-evidence/convert_hikari.py` — the reproduction script
  (pose loop copied from `pikmin2_flora_assets.extract`).

Focused tests: `tests/test_pikmin2_convert_billboard.py` (synthetic type-1
model), plus `tests/test_pikmin2_convert_normals.py` and
`tests/test_pikmin2_flora_assets.py`.
