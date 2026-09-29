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
| `P1_UNLIT_CONTROL` | `0xd0` | Source-unlit materials. Retail kabekuiA uses this word. `EnableColor0` is clear, so the renderer ignores the diffuse-function bits and it draws exactly like the old `0`. |
| `MAT_SRC_COLOR0_VERTEX` / `MAT_SRC_ALPHA0_VERTEX` | `0x0800` / `0x1000` | Vertex colour or alpha as material source. |
| `TEV_BASE_SCALE` | `0` (x1) | The base stage runs at x1, like every retail P1 teki base stage. The converter already wrote 0 here before #895; the constant only names it. |

For each source MAT3 material, `source_lighting()` reads:

- the COLOR0 and ALPHA0 channel control (enable, material source);
- the channel count;
- material colour 0.

`lighting_control()` then produces the control word for each shape:

- The base is `0xd1` when the source COLOR0 channel is lit, otherwise `0xd0`.
  Source-unlit materials stay unlit, for example KingChappy material 1 and the
  Kabuto/Fkabuto material 1.
- It adds `0x0800` or `0x1000` only when the source channel uses vertex
  colour or vertex alpha **and** that shape's display list carries colours.
- The material colour defaults to the source colour. Explicit
  `material_colors`, such as the purple body colour, still take precedence.
- Models whose MAT3 block has no colour or channel tables keep the legacy
  unlit material. These are hand-assembled cave floors (`merged_model`) and
  minimal test fixtures.

P2 base stages are mostly x2, balanced by P2's own darker light rig. The
converter never carried that x2 (it wrote x1 before and after #895), so the
brightness change comes from enabling the lighting channel, not from the TEV
scale. Vertex colours on P2 actors are mostly white (median 255) with darker
ambient-occlusion vertices, so lighting them does not darken them twice; the
in-game UmiMushi captures below support this.

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
- BombOtakara: `otakara_bomb`, applied by the dweevil extractor
  (`pikmin2_dweevil_assets`) because the native tint skips BombOtakara.

The source `enemy.bmd` is still staged unchanged, and the manifest records
`change_textures`. The table is not every decomp swap: Ftank/Wtank
(`pikmin2_tank_assets`), the Kochappy trio (their profiles) and
Koganemushi/Wealthy/Fart (`pikmin2_kogane_assets`) swap in their own
extractors. The Fiery Blowhog's grey-lavender body is its swapped retail
texture (`fire_butadokkuri_main`, mean RGB 193,182,195); Wtank's is bluer
(175,188,212). It is not an unswapped placeholder or the P1 ambient colour.

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

## Native: start-hour capture knob (local only)

`PIKMIN_DEBUG_START_HOUR=<hour>` (PC port, unset by default) overrides the
day's start hour so noon and dusk captures do not need a full real-time day.
It changes simulation state (the day clock). Use it only for solo captures:
a netplay/lockstep peer that sets it would desync, and no handshake checks
it. Its log line says `local_only=1`.

## Audit

```
py -3.12 -m experimental.pikmin2_material_audit content <content-root> [--json out.json]
py -3.12 -m experimental.pikmin2_material_audit mods <file.mod>...
```

`content` checks every pose MOD beside an `enemy.bmd` against the source
MAT3:

- the control base is `0xd1` or `0xd0` according to the source;
- vertex bits appear only where the source allows them;
- the colour equals the source colour.

It exits non-zero on any mismatch. The audit reads MAT3 with its own
named-offset reader (`mat3_channels`), not the converter's `source_lighting`,
and a unit test checks that the two agree. Both follow the same description
of the J3D format, so the audit shows that the writer emitted what the reading
implies. It cannot prove the reading itself. That ground truth comes from the
retail P1 teki MODs (`mods`: `0xd1`/`0xd3`, with kabekuiA also `0xd0`) and from
the in-game captures. `mods` prints each MOD's control words,
material colours, TEV stage scales and the mean luma of its textures. The
same command works on retail P1 MODs.

## In-game evidence (#895)

The captures use the autoplay bot, the frame dump, the same seed and the same
slot. Every figure is the mean luma of a hand-picked box; a figure after `/` is
the in-frame P1 reference. The summary sheet is
`output/p2vis-colour/p2-colour-evidence-r2.png`.

- **Lighting in isolation.** The same exe was run with the old and the new
  content. At 12:00 the Tank measures 164 old and 116 new, against P1 red
  Pikmin at 122 and 127. The old Tank glows; the new one is shaded.
- **Same species in both games.** The native P1 Yellow Wollywog in the Distant
  Spring pond measures 142 at 12:00 and 139 at 17:30. The imported P2 Frog
  measures 94 at 12:00 (a corpse on its side) and 117 at 17:30. The P2 import
  is no brighter than the P1 native. Its source material colour is 204, and P1
  adds a specular stage that P2 does not have.
- **Vertex-coloured UmiMushi (`0x18d1`).** The whole shell measures 94, 173
  and 128 at 07:00, 12:00 and 17:30. P1 white flower petals in the same frames
  measure 153, 175 and 169. At noon the shell equals the P1 white reference, so
  it is not darkened twice. It darkens in the morning and turns warmer at dusk,
  like the P1 scene.
- **Time of day.** In the Distant Spring, P1 is darkest at 07:00. At 17:30 P1
  is warmer (blue suppressed) but not darker than at noon: P1 red Pikmin
  measure 109, 127 and 157 in the Tank runs. P2 actors follow the same curve.
  Tank measures 77, 116 and 126, going from neutral RGB (78,77,71) at 07:00 to
  warm (131,128,106) at 17:30.
- **Measurement limits.** Luma between objects of different albedo is not a
  pass/fail band. The earlier "Armor 139 vs 120" compared the Armor to P1
  flowers using p90. The same-species and white-to-white comparisons above
  replace it. No native P1 Bulborb could be captured: the Forest of Hope
  attempts stalled before reaching one.

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
- **Specular.** Retail P1 chappy and tank materials are mostly `0xd3` with a
  second TEV stage for specular. The P2 bake has one diffuse stage and no
  specular, so even at matched luma, P2 actors look flatter and more matte
  than native P1. Carrying a specular stage (as the Frog and Queen profiles
  do) is the next fidelity step.
- The Kabuto 75 shell samples source UV1, and the converter bakes only UV0.
