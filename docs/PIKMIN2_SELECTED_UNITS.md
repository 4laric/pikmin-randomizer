# Selected Hole of Beasts unit import (#129 / #154)

```powershell
py -3.12 -m experimental.pikmin2_selected_units --iso <US-disc.iso> --catalog <catalog.json> --dependencies <dependencies.json> --output <new-directory>
```

Defaults to `forest_1` (Hole of Beasts). The general catalog and dependency
fingerprint must agree. The importer selects only that cave's five unit pools
and fourteen unique unit candidates, verifies disc source hashes, and extracts
those model/text archives locally. Shared converters and the existing preview
are unchanged.

Each unit receives a status in `units.json`. Successful units contain converted
`render.mod`, collision-bearing `room.mod`, `room.ini`, `collision.json`, output
hashes, unit-local route audit, source-spawn ground probes and deferred animation
names. A unit's `assembly_ready` only identifies successful conversion; it does
not mean a selected topology has been assembled or traversability proven.

Default material conversion is strict. `--approximate-materials` explicitly
permits the existing first/diffuse-texture approximation after recording the
strict failure. Unsupported geometry, collision material codes, water volumes
and remaining conversion errors stay failures. The importer does not silently
whitelist new map codes, drop water or relabel partial output as playable.

## Local audit

All fourteen candidate archives were accounted for:

- Strict: eleven units converted. `room_boss_1_tsuchi` rejects multi-stage
  materials; `room_cent2_4_tsuchi` and `room_cent3_4_tsuchi` reject unaudited
  collision material attribute0.
- Explicit material approximation: twelve units converted, including the boss
  room. The two cent rooms remain unsupported for the same map-code reason.
- Six selection/dependency tests pass. Two approximate imports produced identical
  manifests and all twelve collision-bearing model files.

Evidence: `output/p2-beasts-units-batch/strict/units.json`,
`approximate/units.json`, and `repeat/units.json`. Assets remain local. No native
build or visual/gameplay acceptance is claimed.

## Next dependency

Audit P2 collision attribute0 semantics before proposing a shared translator
change. Then validate those two rooms and select an explicit test assembly.
Retail random room selection/rotation, seam construction, weighted spawns,
Hole of Beasts actors and complete cave gameplay remain later work.
