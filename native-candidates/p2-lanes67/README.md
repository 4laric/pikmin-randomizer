# p2-lanes67 native candidate (lanes 06 + 07)

Ordered additive patches on the approved native baseline
`f14c6851473ac1161be56c8b98f4f905232f3635`, head
`87740f5def6265b1b4fbb864907f97d21f6a921e`.

| Patch | Lane | Change |
|---|---|---|
| 0001 | 07 | Centralized `pc_p2_forget_teki(BTeki*)` called from `BTeki::doKill` and reused by `TekiMgr::newTeki` |
| 0002 | 06 | Engine-free `pc_p2_receipt.h` + `pc_p2_cargo_contest.h` provider surface + standalone tests |
| 0003 | 07 | `pc_p2_reset_all_teki()` called from `GameCoreSection::exitStage` (full stage-exit teardown) |

Apply with `git am native-candidates/p2-lanes67/00*.patch` on the maintained native
line. See `provenance.json` for build/test/runtime hashes.

## Notes for review

- The family list in `pc_p2_teki_lifetime.cpp` mirrors the pre-existing inline
  `TekiMgr::newTeki` list exactly (behaviour-neutral there) and the
  `TekiMgr::reset` list for the stage-exit reset.
- Shared-semantics items for #186: the `doKill` forget call, the `newTeki`
  de-duplication, and the `exitStage` full reset. `TekiMgr::reset()` had no
  runtime caller, so the stage-exit reset is a genuine teardown fix.
- Runtime evidence is on P1-proxy placements (flora/Chappy vehicles), not source
  P2 FSM/drop parity. Lane 06's ordinary endpoint wiring and lane 07's
  new-scene re-entry remain open.
