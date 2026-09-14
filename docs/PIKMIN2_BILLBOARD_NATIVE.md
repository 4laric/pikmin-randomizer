# Native camera-facing billboard for type-1 MOD meshes (#429, parent #128)

Lane 09, Codex through shared account `4laric`. Closes the renderer half of the
HikariKinoko (enemy id 48, Common Glowcap) shape-matrix type 1 (BBoard) failure
that the static fallback left as a labelled approximation.

## Previous state

`docs/PIKMIN2_BILLBOARD_FALLBACK.md` records the bounded `billboard='static'`
converter path: 1/1 clips convert, but the baked quad is fixed in the model's
authored plane and does not turn to face the camera. The requested native
interface was a `Mesh::FeatureFlags::Billboard` bit, a MOD shape matrix type, and
a view-matrix billboard matrix in the draw path.

## What changed

**Native** (branch `opencode/p2-lanes89-native-v2`):

- `include/Mesh.h`: new `Billboard = (1 << 17)` feature flag. It lives in the
  already-read `mFeatureFlags` word, so no MOD layout changes and existing MODs
  are byte- and behaviour-identical (the bit is 0).
- `pc_port/pc_p2_billboard.h`: engine-independent 3x3 helper
  `facingRotation(out, model, view)` = normalised `(view * model).rotation`
  transposed. Unit columns preserve any model/joint scale; a degenerate basis
  returns false and the caller keeps the plain joint matrix.
- `src/sysCommon/shapeBase.cpp` (`Joint::render`, PC-port only): for a mesh with
  the flag, each draw matrix becomes `joint * facingRotation`, where
  `facingRotation` cancels the combined model/model-view rotation. Because the
  billboard geometry is pivot-centred around its joint translation (below),
  concatenation re-places the quad at its joint while making it screen-facing.
  The bounding-box debug branch and the GameCube match build are untouched.

**Converter** (`experimental/pikmin2_convert.py`):

- `decode`/`convert` accept `billboard='native'` (default stays `'error'`,
  `'static'` stays the recorded fallback). Native requires `bake_rigid`, a single
  billboard shape, and an **axis-aligned, uniform positive** rigid joint; other
  cases raise explicit errors rather than silently mis-orienting.
- The billboard shape's baked geometry is re-expressed in the joint's
  pivot-relative, unit-scale local frame (`(v - p) / s`). The emitted MOD joint
  carries `scale = s` and `translation = p`, so non-billboard shapes are restored
  exactly and the flagged mesh is re-placed by the same joint at draw time.
- The billboard shape's MOD mesh flags get `1 << 17`.
- The report records `billboard_policy='native'`, `billboard_shapes`,
  `billboard_materials`, `billboard_pivot`, `billboard_scale` and a note stating
  that the renderer orients it from the view matrix.

## Evidence

Converter (offline, synthetic J3D2bmd3, no disc assets):

```powershell
py -3.12 -m pytest tests/test_pikmin2_convert_billboard.py -q   # 16 passed
```

Covers: the flag is set and the joint carries the pivot/scale; geometry is the
static bake shifted/scaled into the local frame; uniform scale is divided out;
rotated and non-uniform joints are rejected; strict and `'static'` output never
sets the flag.

Native math probe:

```powershell
g++ -std=c++17 -Wall -Wextra -Werror tools/test_p2_billboard.cpp -o p2_billboard.exe
./p2_billboard.exe   # PASS p2_billboard
```

Registered as CTest `p2_billboard_test`. Proves `view*model*facing` is
rotation-free, the facing basis is orthonormal for scaled models, and degenerate
bases are rejected.

Strict defaults: `tests/test_pikmin2_convert_billboard.py` and the wider
converter/flora/material suites stay green (98 passed, 1 skipped focused).

Real-source check (private, no disc assets committed): the extracted
`output/p2-converter-evidence/run1/HikariKinoko` model converts all six sampled
poses with `billboard='native'`:

```text
frame 0  pivot (-4.00, 46.00,  0.00) scale 0.8 shapes [0] materials [0]
frame 14 pivot (-4.30, 45.68, -1.13) scale 0.8
frame 28 pivot (-6.29, 45.69, -2.93) scale 0.8
frame 41 pivot (-2.40, 46.13,  2.12) scale 0.8
frame 55 pivot (-3.94, 46.01, -0.24) scale 0.8
frame 69 pivot (-4.00, 46.00,  0.00) scale 0.8
converted=True poses=6
```

The pivot and scale match the audited source anchor (translation `(-4, 46, 0)`,
scale `0.8`), and every sampled pose satisfies the axis-aligned/uniform
precondition, so the converter path works on the real HikariKinoko geometry.
Candidate native bank: `output/tracks/p2-lanes89-next/hikari-native-01`.

## Remaining dependency

The **real-GL visual gate is UNTESTED**. It needs this native bank rendered in a
camera-framed fixture through a reserved real-GL slot. Two items are recorded
rather than assumed:

1. HikariKinoko's flora conversion uses BCA-derived `draw_matrices`; the native
   path requires the billboard joint to be axis-aligned and uniformly scaled at
   each sampled pose. The six-pose real-source check above passes; a wider
   `pose_limit` should be re-checked when the bank is staged.
2. `gfx.mLastModelMatrix` must be the active actor model matrix at draw time for
   the flagged mesh; if a caller path renders a shape without it, the flag falls
   back to the plain joint matrix.

The default flora tolerance for HikariKinoko therefore stays `'static'`
(approximation explicitly counted). Flipping it to `'native'` is a one-line
`TOLERANCES` change in `experimental/pikmin2_flora_assets.py`; it is held until
the GL pass confirms the camera-facing output.
