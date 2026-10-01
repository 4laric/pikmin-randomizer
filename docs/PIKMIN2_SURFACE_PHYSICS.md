# Valley surface collision and water audit (#114/#132)

`experimental.pikmin2_surface_physics` converts source Valley terrain through the existing geometry writer with an explicit surface-only material policy, and emits a mandatory independent water sidecar. It never changes the dry-room material whitelist. The native surface is **not playable** until it consumes that water representation: the terrain MOD by itself does not reproduce water.

Source evidence:

- `native/pikmin2-research/src/sysCommonU/mapCode.cpp`: low four bits are the material attribute; bits 4–5 are slip, bit 6 is bald.
- `native/pikmin2-research/src/plugProjectKandoU/navi.cpp`, `Navi::onKeyEvent`: material selects walking sound, replaced by sound 4 when `inWater()` is true.
- `native/pikmin2-research/src/plugProjectNishimuraU/HoudaiShotGun.cpp`: actual `findWater` is checked first; material 6 selects an alternate dry impact.
- `native/pikmin2-research/src/plugProjectKandoU/gameSeaMgr.cpp`, `SeaMgr::read`: reads AABB min/max, extends runtime minimum Y downward by 1000, and sets sea level to maximum Y.
- Same file, `AABBWaterBox::inWater`: sphere XZ bounds overlap the box and centre Y is at most sea level minus 3. There is no lower-Y test. `update` adjusts water height for lowering; this first conversion preserves initial boxes only and explicitly excludes drain-state simulation.
- `native/src/plugPikiKando/mapcode.cpp` and `creature.cpp`: P1 water is a ground-triangle attribute. Therefore equating P2 material 3 (or 9) to P1 water would misrepresent the source and is not done.

Valley source materials observed are 0,1,3,5,6,7,9. Their rendering/footstep palette falls back to solid physics while slip/bald bits remain intact; actual water stays in the three source AABBs. The importer rejects other material attributes, reserved high-bit flags, malformed water counts/bounds, and unrecognized water structure versions. No flat floor, water removal, or material coercion enters the general cave path.

Artifacts: `surface-terrain.mod`, full `surface-collision.json`, `surface-water.json`, and `surface-physics.json` with source hashes and ground/wetness probes at Emergence, source landing actors, water centers, and both sides of shores. The water sidecar includes the source bounds and exact query semantics. It currently has no native consumer and does not add water visuals, drowning, drain progression, storage, actors, or surface return placement.

Command: `py -3.12 -m experimental.pikmin2_surface_physics --imported <surface-pocket import> --output <fresh directory>`.

Actual Valley audit (`output/p2-lifecycle-batch/surface-physics-01`): 5,332 triangles and 3,027 source vertices decode successfully with the explicit surface policy. The source has **18 nonmanifold shared edges** (17 with three incident triangles and one with four), including two coincident triangle groups. The general native writer refuses this topology. Consequently this run writes physical collision JSON, water JSON, and probes but **does not write a native terrain MOD**. No source triangles were deleted, duplicated vertices introduced, or ambiguous neighbors chosen. The manifest lists exact source vertex/triangle indices for the next topology audit.

Emergence's source origin probes at ground Y80 and dry. The ship and three regular Onions probe at ground Y0 and dry; initial Red Onion probes at Y60 and dry. Shore probes preserve the exact water-box wet/dry boundary. Some water-center/shore ground probes have no acceptable upward floor at the selected ceiling; those remain `null`, never a substituted flat height. Actual water rendering/query integration and source topology policy remain blockers.

The optional keyword-only `mapcode_translator` is forwarded through decode, geometry validation, and attachment. Regression preserves a pre-change native-MOD SHA256 and checks default versus explicit-default bytes; the general material3/9 rejection still holds.
