# Hole of Beasts traversal and haul fixture

`python -m experimental.pikmin2_beasts_fixture --assets <P1 assets> --assembly <p2-beasts-assembly output> --pod <pod111 import> --output <private output> [--exe <preview_p2_room.exe>]`

This creates a private challenge-stage overlay from the audited nine-instance authored Hole of Beasts assembly. It verifies the assembly hashes and retains its full source-room, door, seam, and route provenance. It does not alter the merged route graph. All fixture actors and controller targets must have decoded ground.

The captain starts west of the west-room center. The Pod is farther west, the unused ship is on the north arm, and twenty Reds start alongside the captain (the existing Pod harness converts them to a mixed blue/red/yellow squad before walking). Citrus Lump is deliberately borrowed as a 15-weight, 180-Poko transport test object in the east room; it is not claimed as the Hole of Beasts retail treasure. There are no enemy actors or substitutions. Controller waypoints pass both main connector seams at x=425 and x=595.

The existing native test harness calls this arbitrary-waypoint, cargo-only mode `p2-second-floor.txt`. That file selects test behavior only; it does not identify the cave or floor. The harness walks normally, then assigns the transport action directly without moving carriers or cargo. Native attachment, locomotion, collision, pathfinding, Pod delivery, and accounting run normally. Successful completion requires the delivery receipt, 180 Pokos, and unchanged P1 repairs. The existing generic harness does not emit a per-seam cargo trace, so that exact trajectory is not independently asserted here.

Preparation uses private overrides for the stage generator, stage config and room assets; other assets are shared read-only using the existing overlay mechanism. It creates a fresh UUID directory and uses no live player save. Imported models remain local.

Runtime executables require their SDL/MinGW DLL directory on PATH, for example `C:/msys64/mingw64/bin`.

Four focused tests cover missing ground, provenance/hash rejection, and the ordered connector traversal plan. Local stage preparation succeeds using the actual imported assembly. Native runtime evidence is recorded separately in the private run log; preparation alone does not mark `native_validated` true.


Actual local run `output/p2-beasts-fixture-batch/ff412ebd841b4299bdd575762f2d7d07` passed the native fixture: 1,133.63-unit controller traversal, then native cargo delivery and 180-Poko accounting. Binary SHA256 `3e369d365f91c493f5fad82948ca54a79c078aed6a50453d60a2af6f6db986cd`. Initial actor settling moved the captain away from its authored position before measurement; the log retains the actual coordinates. This validates the connected engineering scene, not retail generation or player-controlled carrying selection.
