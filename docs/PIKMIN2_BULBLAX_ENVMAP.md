# Bulblax Queen body environment stage (issue #416, parent #239)

Opt-in, additive converter interface for the Empress Bulblax (Queen) body's
second TEV stage — the normal-texgen specular/environment stage that samples
TEX1[1] (`RGB565` 64×64 envmap) with `TEXMTX0` animated by
`queenchappy_model.btk`.

Chosen path **(a)**: a narrow, family-scoped interface that emits the stage
without changing any existing default output or shared converter function. No
native build/run was performed.

- Module: `experimental/pikmin2_bulblax_envmap.py`
- Tests: `tests/test_pikmin2_bulblax_envmap.py` (20 tests)
- Worker branch/worktree: `opencode/p2-bulblax-envmap` @ `output/p2-bulblax-envmap`
- Base: `opencode/p2-batch5-bulblax` (`9cd091c`)

## 1. Source contract

`p234-import/Queen/enemy.bmd` (sha256 `e4904b22…`, see
`pikmin2_bulblax_material.SOURCES`), MAT3 material 0 (mapped to INF1 body shape
1), stage 1, raw 20 bytes:

```
[255, 15, 10, 8, 0, 0, 0, 0, 1, 0, 4, 7, 6, 0, 0, 0, 0, 0, 0, 255]
 texgen 0 = (type 1, source 1 = GX_TG_NRM, matrix 30 = TEXMTX0)
 TEV order = [0, 0, 5]        (texcoord 0, texmap 0, specular raster channel 5)
 rgb args  = [15, 10, 8, 0], op/bias/scale/clamp/register = [0, 0, 0, 1, 0]
 alpha arg = [4, 7, 6, 0],    op/bias/scale/clamp/register = [0, 0, 0, 0, 0]
 texture   = TEX1 index 1 (slot 0), the envmap
```

`queenchappy_model.btk` (`J3D1btk1`/TTK1, 448 bytes, sha256
`af0dde017624a5b30459b8ba55ed70a1d70de14f841ed58802b3b07565ef4eae`) animates
`TEXMTX0` for this stage.

The converter's `diffuse_slot` (`pikmin2_convert.py:57-74`) rejects the stage,
so the single-stage writer (`pikmin2_convert.py:263-280`) bakes only the diffuse
base. The material profile already rebinds the body base from the envmap
TEX1[1] to the diffuse base TEX1[2] (`pikmin2_bulblax_material.py`).

## 2. Interface

```python
experimental.pikmin2_bulblax_envmap.apply(raw: bytes, spec=None) -> bytes
    # spec=None is a byte-exact no-op (returns raw unchanged).

experimental.pikmin2_bulblax_envmap.apply_queen_body(raw: bytes) -> bytes
    # Convenience wrapper: apply(raw, QUEEN_BODY).

experimental.pikmin2_bulblax_envmap.add_stage(raw: bytes, spec: dict) -> (bytes, dict)
    # Core; returns the rewritten MOD and a hashed report.
    # Refuses non-generated material chunks, unknown/already-injected shape,
    # out-of-range texture, textureless target, malformed combiners/SRT.

experimental.pikmin2_bulblax_envmap.prepare(bank: Path, output: Path) -> dict
    # Applies apply_queen_body to every Queen/*.mod in a Bulblax material-profile
    # bank, copies the tree, updates file_sha256 and adds an envmap_profile
    # section. Requires material_profile.policy == P2_BULBLAX_MATERIAL_1.

experimental.pikmin2_bulblax_envmap.tev_infos(raw)      # read-back view
experimental.pikmin2_bulblax_envmap.material_records(raw)  # read-back view
```

`QUEEN_BODY` (the emitted stage, mapped onto the generated layout):

| field | value | source |
|---|---|---|
| `shape` | `1` | INF1 shape 1 = body |
| `texture` | `1` | TEX1[1] envmap, after the base was rebound to TEX1[2] |
| `tex_coord_id` / `tex_map_id` | `1` / `1` | generated slots, since the baked base owns 0/0 |
| `channel_id` | `5` | source order `[0,0,5]` specular raster |
| `color_combiner` | `(15,10,8,0,0,0,0,1,0,0,0,0)` | source rgb args + op/bias/scale/clamp/register |
| `alpha_combiner` | `(4,7,6,0,0,0,0,0,0,0,0,0)` | source alpha args + op/bias/scale/clamp/register |
| `texgen` | `(1,1,30)` | source texgen (type, `GX_TG_NRM`, `TEXMTX0`) |
| `srt` | `(1,1,0,0,0,0)` | static; BTK sampling not yet fed (see §5) |
| `marker` / `tev_flag` | `0xE6` / `2` | engine `dgxGraphics.cpp:1005`/`:522` markers |

### Byte changes (only MOD chunk 48)

- target `PVWTevInfo` stage count `1 → 2` (+32-byte `PVWTevStage`),
- target material `mTexGenDataCount 1 → 2` (+4-byte `PVWTexGenData`),
- target material `mTextureDataCount 1 → 2` (+64-byte `PVWTextureData`,
  `mSourceAttrIndex = 1`, `_UNUSED10 = 0xE6`, `_UNUSED11 = 2`,
  `mAnimationFactor = 0`, `mTotalFrameCount = 0`, `mRotationZ = 0`,
  `mScaleX = mScaleY = 1`).

Every other chunk and every other shape is byte-identical. Input is never
modified.

## 3. Engine consumption (already present, no new native code)

- `dgxGraphics.cpp:1005` — a `PVWTextureData` with serialized `_UNUSED10 == 0xE6`
  and `mTexGenSrc == GX_TG_NRM` sets `mP2Envmap` and feeds `mP2EnvSRT`; abort
  guards require one marked stage, `mAnimationFactor != 255`,
  `mTotalFrameCount == 0`, `mRotationZ == 0` (all satisfied).
- `dgxGraphics.cpp:927` — `useMatrixQuick` builds the texture matrix via
  `engine/pc_port/pc_p2_envmap.h`.
- `dgxGraphics.cpp:1091/1123-1131` — the second `PVWTevStage` drives
  `GXSetTevColorIn/Op` and `GXSetTevOrder`.
- `_UNUSED11 == 2` makes `PVWTextureInfo::mTevStageCount` non-zero so
  `mHasTexGen` is true and the envmap matrix is loaded.

## 4. Pipeline use

```
bank build (pikmin2_bulblax_bank)
  -> material profile (pikmin2_bulblax_material.prepare; base -> TEX1[2])
  -> python -m experimental.pikmin2_bulblax_envmap prepare --bank <profiled> --output <new>
```

Order matters: this stage must run **after** the material profile, otherwise the
envmap is referenced as both the base and the second stage.

## 5. Remaining work to actually render it

1. **Renderer coverage.** The Dolphin (`dgxGraphics.cpp`) PVW path consumes the
   marker. The OpenGL path (`oglGraphics.cpp:584-594`) does not: its `MATFLAG_PVW`
   branch only binds `mTextureData[0]` and has no normal-texgen envmap handling,
   and `Material::mEnvMapTexture` is never populated from a MOD. If the Room
   Preview uses OGL, an equivalent PVW multi-texture path must be added there.
2. **BTK playback.** `TEXMTX0` is emitted with a static identity SRT. The
   display's existing `pc_p2_bulblax_visual.cpp` BTK hook only logs samples; it
   must feed `mP2EnvSRT` (or `PVWTextureData` animation) each frame from
   `pqueenchappy_model.btk` before the animation is visible.
3. **Native build + GL run + visual evidence** were explicitly out of scope for
   this slice and remain untested.

## 6. Evidence / hashes

- Unmodified `write_model` default sample (`converter_sample()` in the tests),
  1696 bytes, sha256
  `4abad52016f21b3dc3e44bf785fd78a61fe5344441a760122e183d160f850725`.
  Frozen by `DefaultOutputTests.test_converter_default_is_byte_identical`.
- Real profiled pose `bulblax-material-profile-01/Queen/bulblax_Queen_born_00.mod`,
  sha256 `b48638e2adb379bf3864d7274a7c76a79b77cd47180e77b4b549cd6882149071`
  (59264 bytes) → injected 59360 bytes, sha256
  `9f964698fe5907e58e35245f96e30941a7a3b4d3e3996a802ddc4c149af6e816`.
  All 54 Queen poses in that bank inject to `[1, 2]` stages; input bank unchanged.

## 7. Explicitly not changed

- `experimental/pikmin2_convert.py` (no diff), `experimental/pikmin2_bulblax_material.py`
- anything under `engine/`, `native/`, `output/p2-kimi-bulblax-native`,
  `output/integration-six`
- no CMake/Ninja build, no GL launch, no extracted assets or generated models
  committed.
