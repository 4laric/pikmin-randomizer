# p2-lanes67 native candidate (lanes 06 + 07)

Ordered additive patches on the approved native baseline
`f14c6851473ac1161be56c8b98f4f905232f3635`, head
`87740f5def6265b1b4fbb864907f97d21f6a921e`.

| Patch | Lane | Change |
|---|---|---|
| 0001 | 07 | Centralized `pc_p2_forget_teki(BTeki*)` called from `BTeki::doKill` and reused by `TekiMgr::newTeki` |
| 0002 | 06 | Engine-free `pc_p2_receipt.h` + `pc_p2_cargo_contest.h` provider surface + standalone tests |
| 0003 | 07 | `pc_p2_reset_all_teki()` called from `GameCoreSection::exitStage` (full stage-exit teardown) |
| 0004 | 07 | `pc_p2_scene_begin()`/`pc_p2_scene_generation()` from `GameCoreSection::finalSetup` (safe new-scene signal) |
| 0005 | 07 | `pc_p2_input_script.{h,cpp}` + `ControllerMgr` hook: reusable scripted-pad input for menu/section fixtures (default-off, inert in production) |

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
  P2 FSM/drop parity.
- Lane 06 ordinary endpoint is now demonstrated end to end: a real Dwarf Bulborb
  kill drives a real corpse through `GoalItem::suckMe` ->
  `pc_randomizer_corpse_delivered` -> `pc_randomizer_check` and grants
  `Bestiary: Deliver Dwarf Bulborb` exactly once, refused on a fresh process.
  Only the Pikmin carry step is injected (lane 04 transport).
- Lane 07 in-process new scene: PASS. A Snow-campaign day transition reaches
  MapSelect; the reusable scripted pad (patch 0005) drives the menu to load a
  fresh gameplay area in-process — `P2_NEWSCENE_RELOAD gen=2 day=8 bound=11`.
- Lane 06 residual: natural Pikmin carry (lane 04 transport).
