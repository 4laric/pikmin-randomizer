# AFK implementation handoff

The task heartbeat now runs every15 minutes, retaining the previous daily upstream-sync duty. It advances issue-scoped source batches, coordinates private snapshots, tests and integrates root source only. Kimi remains independent QA. Do not publish releases or game assets.

Current integration: native e704b268 adds separate Dwarf Red actor profile/health200 plus visual-only Breadbug displays, with common setup/draw/reset hooks. Python focused integration:19tests passed. The initial combined native build passed, but final freshness found the late-added Breadbug reset in tekimgr still pending; the final incremental build is recorded in `output/p2-team-batch1/families-final-build.log`. Verify that completion and a no-work dry run before authorizing private fixture snapshots.

Ready lanes awaiting fresh build confirmation:

- Enemy worker: Red identity, health, rendering and lifecycle fixture. Existing imported room is a bounded receiver test; the general P1-stage arena launcher remains to be implemented.
- Content worker: corrected grounded ten-Uji XYZ/emergence/combat/haul fixture. Earlier rejected executable must not run; its source changed during freshness validation.
- Lifecycle worker: Breadbug visual rendering/pose/nest/reset fixture. It has no actor, collision, AI or reward behavior.

Keep native source and build inputs stable while workers snapshot. The integration lead owns shared CMake, setup/draw/reset hooks and export. Native origin is never a push target. Preserve all unrelated archives and worktrees in root status.
