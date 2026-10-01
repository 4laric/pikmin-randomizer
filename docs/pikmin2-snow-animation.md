# Snow Bulborb sampled animation increment (#128, #120)

The opt-in Snow import now samples at most 24 poses from each retail BCA clip
instead of 12. `P2_SNOW_2` records each source frame explicitly. Native drawing
chooses the closest source frame to normalized P1 motion progress; dead corpses
hold the final source pose. `P2_SNOW_1` retains its old floor-index selection.
P1 dwarf combat, collision, animation events and timing remain authoritative.
This is still baked-pose playback, without source skeletal interpolation or P2 AI.

The source is local-disc `enemy/data/Kochappy/anim.szs` (`wait1`, `move1`,
`attack`, `dead`, `flick`), with the Kochappy model and YellowKochappy body
texture. The source clips have 75, 55, 90, 90 and 80 frames respectively.
No disc assets are committed.

## Cost controls

Both installer and native setup validate the complete bank before copying or
loading Shapes: maximum 24 poses per clip, 512 KiB of MOD payload per clip and
2 MiB total. Static texture, texture-attribute and material chunks must be
byte-identical across poses. Native drawing shares the first Shape's material,
TEV and texture-attribute arrays, including rebinding every MatPoly material
pointer. Only that canonical texture set is explicitly attached. Per-pose
vertices, meshes and joints remain separate.

The existing Shape loader still parses and allocates CPU copies of the static
resources before those references are replaced. They belong to the scene heap
and are not individually freed. The 2 MiB limit is the input payload, **not a
claim about total heap or GPU memory**. A transform-based animation runtime is
needed to eliminate that duplication. Full 390-frame banks were rejected because
they would multiply the old 60-Shape load by 6.5.

Local extraction comparison on September 12, 2026:

| Bank | Poses | MOD bytes | Extraction wall time |
| --- | ---: | ---: | ---: |
| Original density | 60 | 960,000 | 0.320 s |
| Capped new density | 120 | 1,920,000 | 0.521 s |

The dense import has 120 distinct posed meshes. Static resource chunks occupy
1,472 bytes per MOD. Across 10,001 normalized phase samples, maximum source-frame
error falls from 5.360–8.541 frames with the old floor selection to 1.500–2.000
frames with the new nearest selection. This measures pose selection, not FPS.

Extraction reports a 30-second advisory budget in `snow.json`. Native setup logs
`P2_SNOW_BANK` with total poses, input bytes, texture attach calls, load seconds
and whether its 5-second advisory load budget was exceeded. Time limits are
advisory because machines vary. In-game frame rate and scene heap consumption
remain unmeasured pending integration; this change does not claim to fix the
reported low FPS. `--pose-limit 12` provides the previous density with v2 lookup
if the denser bank is too expensive.

## Validation and integration

`py -3.12 -m pytest tests/test_pikmin2_animation.py tests/test_pikmin2_enemy.py tests/test_pikmin2_purple.py -q`
passes 28 tests, including a compiled native policy probe. The modified native
enemy object also compiles in isolation with production flags. Source-backed
local imports are in `output/p2-animation128/dense24` and `baseline12`; comparison
metrics are in `output/p2-animation128/comparison.json`.

The parent integration owns the native build and export. Use the dense import
with the existing Snow installer, then verify living/attack/dead rendering,
canonical textures, load log, corpse delivery and frame rate in the integrated
playtest. Native validation reads the private experimental room under
`assets/dataDir/courses/pikmin2room` in the run directory, matching the installer.
Existing v1 imports remain supported; existing run assets are not changed.
