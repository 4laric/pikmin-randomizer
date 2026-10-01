# Complete tutorial terrain topology adapter

Issue #1089, parent #148; implementation owner Codex through shared `4laric`.
The primary delegated the listed core hooks and must review their semantics under
#186 before integration. This is an opt-in terrain prerequisite, not complete
surface gameplay admission.

P2 source revision `632af93787b9c95b63f0c13be32b161375ce3a96` uses
`src/plugProjectKandoU/mapMgrTraceMove.cpp:69` to sweep every nearby triangle and
`src/sysCommonU/geometry.cpp:2653` to project every containing ground triangle.
Its serialized triangles have no P1-style single-neighbor field. Retail tutorial
contains 5,332 faces, 18 multi-incident edges and two coincident overlays with
different slip codes (673/4914 and 727/4915, source codes 103/65).

The new full-terrain assembler retains every face, vertex and mapcode in source
order, emits the conservative spatial grid, and puts -1 in ambiguous legacy
adjacency slots. Existing small-room collision conversion still refuses those
edges. Use only the matching optional native tutorial index:

```powershell
py -3.12 -m scripts.stage_pikmin2_full_surface --assets <P1-assets> --bundle <verified-tutorial-bundle> --identity <receipt> --output <new-private-arena>
```

Native `MapMgr::initShape` rebuilds the complete incident index on every map load;
the constructor clears it before the previous scene can leave stale pointers.
The owner verifies that queried triangles belong to that exact static map.
Default P1 and campaign paths retain their previous adjacency behavior.

For optional tutorial jump classification and `getNextTri`, a continuation must
have reversed shared-edge winding, a positive floor normal, and contain the
query's projected X/Z point. More than one qualifying source face returns
explicit ambiguity, never nearest/angle/face-ID selection. This is a conservative
engineering limitation: ambiguous or long forward queries can return null and
retain jump/boundary handling. It does not establish P2 sweep parity or source
faithful traversal of every route. `getNextTri` currently has no external call
site; its existing `checkForward` caller consumes the output as an edge index, so
the optional path returns that index separately from the chosen face.

Shadow recursion enumerates all incident faces with its existing visited list,
angle test and 50-face cap. It preserves duplicate overlays rather than deleting
their distinct physics. Detailed shadow opacity/fidelity remains unaccepted.
P1's existing physical sphere sweeps still test all spatial-grid candidates;
the adapter does not replace them with a fabricated neighbor or invisible wall.

Native policy tests cover unique/boundary/ambiguous continuations, duplicate slip
overlays, finite queries and reset. The grid synthetic floor test also now uses
positive winding and asserts actual heights; the prior accepted whole-source
42-floor-probe/exhaustive-cell evidence was already non-vacuous and unchanged.

The custom runtime fixture stages all 5,332 collision faces, uses the real SDL
controller/native input path, checks 20 live Pikmin and canonical captain safety,
and attempts travel beyond the earlier 60-unit entrance pocket. Retail policy
queries are read-only observations, separate from ordinary controller travel.
Source water is retained but has no native consumer; materials remain approximate,
original generator schedules/actors are absent, and carry/campaign/full traversal
remain open. Runtime outcomes and exact source/build/input hashes stay under
ignored `output/p2-surface-topology/`.
