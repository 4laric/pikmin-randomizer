# P2 actors under Pikmin 1 lighting (#895)

Imported Pikmin 2 actors are converted by `experimental/pikmin2_convert.py`
`write_model`. Before #895 every material got PVW lighting control `0x1800`
(vertex colour present) or `0`. `EnableColor0` was never set, so actors were
drawn unlit at full brightness and ignored the P1 sun, point lights and
DayMgr time-of-day ambient. Material colours were also forced to white.

## Policy

All tunables live at the top of `experimental/pikmin2_convert.py`.

| Constant | Value | Meaning |
| --- | --- | --- |
| `P1_LIT_CONTROL` | `0xd1` | COLOR0 lit, clamp diffuse. Retail P1 teki diffuse materials use this word. |
| `P1_LIT_SPECULAR_CONTROL` | `0xd3` | Adds the COLOR1 specular channel. Used only with a TEV stage that reads it (Frog profile). |
| `MAT_SRC_COLOR0_VERTEX` / `MAT_SRC_ALPHA0_VERTEX` | `0x0800` / `0x1000` | Vertex colour or alpha as material source. |
| `TEV_BASE_SCALE` | `0` (x1) | The base stage runs at x1, like every retail P1 teki base stage. |

For each source MAT3 material, `source_lighting()` reads:

- the COLOR0 and ALPHA0 channel control (enable, material source);
- the channel count;
- material colour 0.

`lighting_control()` then produces the control word for each shape:

- The base is `0xd1` when the source COLOR0 channel is lit, otherwise `0`.
  Source-unlit materials stay unlit, for example KingChappy material 1 and the
  Kabuto/Fkabuto material 1.
- It adds `0x0800` or `0x1000` only when the source channel uses vertex
  colour or vertex alpha **and** that shape's display list carries colours.
- The material colour defaults to the source colour. Explicit
  `material_colors`, such as the purple body colour, still take precedence.
- Models whose MAT3 block has no colour or channel tables keep the legacy
  unlit material. These are hand-assembled cave floors (`merged_model`) and
  minimal test fixtures.

P2 base stages are mostly x2, balanced by P2's own darker light rig. Once the
material is lit by P1's rig, x1 matches native P1. Vertex colours on P2 actors
are mostly white (median 255) with darker ambient-occlusion vertices, so
lighting them does not darken them twice.

The Bulblax and Frog profiles use the same canonical words. The old `0x93`
differed from `0xd3` only in the unused alpha diffuse-function bits.
`experimental/pikmin2_specular_slice2.py` still matches the native specular
layer's runtime log marker `control=0x93`.

## Retail texture swaps

Several species share an `enemy.bmd` whose texture slots hold 8x8 `*_dummy_i4`
placeholders. The species manager swaps the real textures in with
`Obj::changeMaterial`. `experimental/pikmin2_change_texture.py` carries the
decomp table and applies it before baking, in the proxy and cannon
extractors:

- Chappy, YellowChappy and BlueChappy: `moyou_565` and `swallow_565`.
- Kabuto and Fkabuto: `babykabuto_green`.
- Rkabuto: `babykabuto_red`.

The source `enemy.bmd` is still staged unchanged, and the manifest records
`change_textures`.

The native batch-2 draw tints the dweevils (Fire/Water/Gas/ElecOtakara) over
the placeholder instead (`pc_p2_batch2.h` `p2batch2tint`). Their swap stays a
follow-up until that tint is retired, because baking the real texture now
would apply the tint twice.

## Native: late-loaded textures

P2 family setup hooks load their pose MODs after the stage's
`StdSystem::attachObjs`. Their textures stayed unattached, which gives a zero
`GXTexObj` and therefore a black actor, until the next `attachObjs` (for
example after a cutscene). This is why live Bulborbs were drawn as black
silhouettes, with the old content as well as the new.

In the native repo, `GameFlow::loadShape` now attaches the textures of every
`courses/pikmin2room/` shape as it loads, as `pc_p2_tank`, `pc_p2_sheargrub`
and `pc_p2_preview` already did for their own shapes. `Texture::attach` is
idempotent.

## Audit

```
py -3.12 -m experimental.pikmin2_material_audit content <content-root> [--json out.json]
py -3.12 -m experimental.pikmin2_material_audit mods <file.mod>...
```

`content` checks every pose MOD beside an `enemy.bmd` against the source
MAT3:

- the control base is `0xd1` or `0` according to the source;
- vertex bits appear only where the source allows them;
- the colour equals the source colour.

It exits non-zero on any mismatch. `mods` prints each MOD's control words,
material colours, TEV stage scales and the mean luma of its textures. The
same command works on retail P1 MODs.

## Follow-ups (not changed here)

- P2 cave geometry is still drawn with `setLighting(false)` in
  `pc_p2_cave.cpp`, `pc_p2_cave_geometry.cpp` and `pc_p2_cave_rooms.cpp`, and
  cave floors keep the legacy unlit material.
- The converter writes only the base texture level, with an image count of 1.
  Whether missing mipmaps make distant P2 actors shimmer is unverified.
- Swapping the real dweevil textures needs the native `p2batch2tint` to be
  retired first.
- KumaKochappy's model carries only `kochappy_dummy_i4`, and the decomp shows
  no swap for it. Its real colouring source is unresolved.
