# Retail surface source bundles (#1051)

Implementation owner: Codex through shared GitHub account `4laric`. This is a
source-import foundation for #148–#151. It supplies the four retail courses to
level owners without changing native boot, cave generation, saves or installed
assets. It does not make any of these courses playable.

From the root source checkout, use a fresh ignored output directory:

```powershell
py -3.12 -m experimental.pikmin2_surface_import import `
  --iso 'C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso' `
  --course forest --output output/surface-forest-source-01
```

Course IDs are `tutorial`, `forest`, `yakushima`, `last`. Only US `GPVE01`
revision 0 is supported, using the existing disc/archive readers. The importer
prints the receipt identity and decoded counts. Preserve the identity outside
the bundle, then verify it before conversion or other consumer work:

```powershell
py -3.12 -m experimental.pikmin2_surface_import verify `
  --bundle output/surface-forest-source-01 --identity <printed-sha256>
```

Python consumers call `verify_bundle(path, pinned_identity)` before reading
`surface-geometry.json`, `surface-water.json`, `surface-generators.json`, or
`surface.route.ini`. Changed, missing or extra files and a changed receipt are
refused. The pin is necessary: recomputing an identity from an edited receipt
does not prove it is the original import. This is content provenance, not a
digital signature. Imports refuse existing output directories. A decode failure
may leave private source files but never a completed receipt; preserve that
failure and use a new output directory.

The bundle contains the complete source `arc/` and `texts/` archive members;
all generator `.txt` files under that course; the original CP932 route bytes in
`source/route.txt`; a normalized route file for decoding; and deterministic JSON
geometry, topology, water, generator and import reports. The receipt records
exact disc-member offsets, sizes and SHA-256 hashes, plus every output file's
size/hash. Paths and timestamps never enter the receipt, so repeated imports of
the same disc/course reproduce byte-for-byte.

The surface decoder preserves source vertex/triangle order, 16-float triangle
records, raw P2 mapcodes, route IDs/links/widths and bounds. Mapcodes are never
translated to P1 material flags. It also retains the incompatible acceleration
bytes as original `grid.bin` and records their remaining count. `surface.route.ini`
is a reusable P1 route syntax export; it does not establish navigation or corpse
return routes. Water JSON uses the existing source AABB parser and explicitly
marks native consumption unimplemented. Generator schedules remain separate by
source filename. Parser failures retain raw bytes and an error instead of silently
dropping them or inventing a translated actor.

Perplexing Pool contains a valid source triangle record with zero area at
zero-based face **2659**. The generic dry-room collision converter rejects it.
This importer retains that face, its plane record and mapcode; the topology audit
skips it explicitly and retains original source face IDs in every diagnostic.
`degenerate_triangles` and `audit_triangle_source_ids` identify the exact policy
boundary. Out-of-range vertex indices, truncated records and nonfinite geometry
still fail. No face is removed from the exported geometry. A native conversion
owner must decide how to represent degenerate/nonmanifold faces before admission.
All topology reports keep `native_conversion_approved: false`.

Real local-disc validation decoded all four courses twice with matching receipt
hashes and verified every bundle member:

| Course | Vertices | Faces | Route points | Water boxes | Generator files |
|---|---:|---:|---:|---:|---:|
| Valley of Repose | 3,027 | 5,332 | 102 | 3 | 13 |
| Awakening Wood | 3,849 | 6,578 | 145 | 5 | 11 |
| Perplexing Pool | 3,138 | 5,809 | 132 | 8 | 12 |
| Wistful Wild | 2,393 | 4,003 | 109 | 2 | 5 |

Valley geometry, planes, raw mapcodes, routes, bounds and acceleration count match
the existing decoder with the audited Valley translation policy. Its default
generator parse matches the existing Valley importer. Pool and Wild each retain
one unsupported generator-file parse; all source bytes stay in the bundle.

Run `py -3.12 -m unittest tests.test_pikmin2_surface_import
tests.test_pikmin2_surface_physics tests.test_pikmin2_surface_topology
tests.test_pikmin2_collision -q` for refusal and regression coverage. No ISO-derived
assets are committed. No native runtime was launched for this source-only slice;
the mandatory squad/window/captain-guard baseline remains required when level
owners perform their next runtime acceptance. Render/material conversion, native
topology/water, actor scheduling, two captains and durable level persistence
remain open.
