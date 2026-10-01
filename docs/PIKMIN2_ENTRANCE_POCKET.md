# Emergence entrance collision subset (#114)

`experimental.pikmin2_entrance_pocket` produces actual native-compatible collision around the source Emergence entrance at **(-190,80,1160)**. It intentionally represents a small entrance pocket, not the entire Valley and not a repair of the full surface's nonmanifold topology.

The declared travel radius is **60 units**. Complete source triangles whose XZ bounding boxes overlap the surrounding100-unit half-width selection box are retained, with source vertex/triangle IDs. Nothing is cut, flattened, translated, rewound, or capped. The resulting32 triangles and35 collision vertices contain none of the full surface's ambiguous edges. Mapcode material uses the audited surface palette; original slip/bald bits remain intact. Source routes are omitted because this artifact is for local walking/entry bootstrap, not hauling.

The whole source render remains unaltered and aligned. Consequently terrain beyond the collision subset is visible but unsupported. The crop perimeter is **not physically sealed**. A native travel-radius boundary and water consumer are required before any player launch; the declared radius is metadata, not enforcement. All three water volumes remain byte-for-byte in the mandatory sidecar even though the validated travel samples are dry.

Local output `output/p2-lifecycle-batch/entrance-pocket-01` contains `entrance-pocket.mod`, source-indexed `entrance-collision.json`, all-water `surface-water.json`, and `entrance-pocket.json`. There are184 source-versus-subset grid/perimeter probes: every selected ground height is exactly80, with no water overlap using a10-unit sphere radius. These offline samples do not substitute for native movement testing. A larger100-unit travel radius had missing-floor samples during selection and is deliberately not claimed walkable.

Validation: six focused tests cover exact source remapping, unchanged slips/source arrays, probes, wetness refusal, missing floor, nonmanifold source rejection, and empty/bad selections. Actual generated MOD mapcodes were checked against every source triangle; all32 match the expected bit translation. Water sidecar is byte-identical. MOD SHA256: `f26afdbeb9c03fcf911495c4c075ecfce0d45fa783f02f0dd5bbcd7b805e3b6f`.

Command: `py -3.12 -m experimental.pikmin2_entrance_pocket --source-import <surface-pocket import> --physics <surface-physics output> --output <new directory>`.
