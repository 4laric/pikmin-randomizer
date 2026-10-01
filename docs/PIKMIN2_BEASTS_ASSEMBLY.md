# Hole of Beasts first connected assembly (#129 / #154)

```powershell
py -3.12 -m experimental.pikmin2_beasts_assembly --imported <selected-unit-import> --output <new-directory>
```

The importer must be the converted Hole of Beasts set, including the now-audited
attribute0 cent rooms. This new assembly module uses existing shared model,
collision and route merging APIs unchanged.

Floor1's source pool permits the selected two `room_cent3_4_tsuchi` rooms,
`way2_tsuchi` connector and `item_cap_tsuchi` caps. Main room centers are
(0,0,0) and(1020,0,0); a quarter-turned connector sits at(510,0,0).
Six caps are positioned and rotated from their source door waypoints. There are
nine unit instances in total, two of which are main rooms. The choice is an
explicit engineering layout, not the original weighted generation algorithm.

Every source door is paired exactly once with an opposite-facing coincident
door. Source cell rectangles do not overlap. Merging preserves source directed
route links and collapses matching seam nodes through the shared assembly API.
All24resulting route nodes can reach every audited destination. Eight seams
pass312ground samples over a50-unit-wide strip,30units into each side, with
maximum permitted height deviation0.1units. Source vertices and instance
transforms are retained; no artificial floor offsets are used.

Output includes `render.mod`, collision-bearing `room.mod`, `room.ini`,
`collision.json`, and `assembly.json`. Metadata records explicit layout/seams,
source and converted hashes, footprint rectangles, route and ground audits.
Existing output directories and changed converted-unit hashes are rejected.

Seven focused assembly tests pass. Two independent real imported-unit builds
produced byte-identical models, routes, collision metadata and assembly manifest.
Local output: `output/p2-beasts-assembly-batch/assembly01`.

No captain, Pod, enemy, treasure, hole or geyser placement is chosen here.
Scenery footprint clearance, native camera/movement, physical carrying across
the joins and complete source gameplay remain integration work. This assembly
does not modify the current playable campaign or represent retail generation.
