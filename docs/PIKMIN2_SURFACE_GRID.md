# Conservative whole-course collision grid prerequisite

Issue #1081, parent #148. This source-only converter emits a P1 CollisionGrid
chunk (`0x110`) with unchanged retail triangle indices. It replaces the small-room
strategy of putting every course face in every grid cell. It does not emit or
approve full-course triangle adjacency, water, generators, or a playable map.

Run from the repository root with a verified local import bundle:

```powershell
py -3.12 -m scripts.build_pikmin2_surface_grid --bundle <tutorial-import> --identity <receipt-identity> --output <fresh-private-output>
```

`collision-grid.chunk` is the concrete consumer output. A MOD assembler can use it
after its matching CollisionPrism chunk, retaining the exact same face order.
The current collision attachment path still refuses nonmanifold triangle edges;
this module deliberately does not bypass that refusal. `grid-report.json` records
source identity, source/grid hashes, group sizes, and remaining topology gates.

The native consumer contract is `BaseShape::read` in
`native/src/sysCommon/shapeBase.cpp` (CollisionGrid case), `BaseShape::getCollTris`
in `native/include/Shape.h`, and static-group selection in
`native/src/plugPikiColin/mapMgr.cpp`. Cells are 64 units. Each group includes every
triangle whose X/Z AABB intersects that cell plus the native loader's 64-unit
border. This conservatively retains walls, long/sliver triangles, duplicate
overlays, and faces crossing a cell without a vertex inside it. Groups contain
sorted source-face IDs; identical groups share a record; empty cells use -1.
Far-culling count stays zero. Source geometry and physics codes are unchanged.

Independent binary decoding and ground probes check the output contract. Passing
them establishes conversion evidence only; native full-course loading, traversal,
performance, multi-incident transitions, water, and campaign content still require
owned implementation and runtime acceptance. No render or native adjacency policy
is inferred from this broad-phase artifact.
