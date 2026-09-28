# Placement and native handoff sweep (#437)

Owner Codex through shared 4laric. Root base 5c53f5a; native ab7a900b unchanged and clean. Integrated a22bfd8 as ff55584: Jigumo requires a home/nest anchor, candidate corpse carriers require return routes, and water slots are represented as potentially carryable with Blue Pikmin. Native route/terrain evidence remains false and accepted gates remain empty. This is a compatibility model, not proof that every submerged slot has a viable route.

Combined placement, roster, enemy-slot, seed-bridge and staging suite: 98 passed, 17 subtests passed. Generated compatibility summary is local at output/p2-placement-sweep-summary.json. No native build/export or real-GL acceptance in this pass.

## Next native review priority

1. Hiba: root 37add4b reports exact native f139d2645ce10243feb8084a2df3c53c29dcb255 on f14c6851, additive hooks and teardown paths, rebuilt fixture and observed fire vulnerable/immune cases. Review this current-line delta next. Gas/electric application, visuals and natural gameplay remain open; the worker statement that its blocker is cleared is not combined acceptance.
2. Lifecycle: 18d81d2 reports native 4c3b32e6 on f14c6851, engine doKill forget and late-birth re-registration. Address reuse and full scene/day teardown remain open. Review shared receiver/forget ownership before adopting.
3. Waterwraith: 4ebf98b adds encounter receivers and cleanup, but depends on host/visual/registration not yet integrated. Current native has only the isolated actor/roller-policy dependency.
4. Lane 03: c49a30d/816631d document and probe a native parser; earlier product admission-validation and accepted-placement requirements still need resolving before the generator patch is accepted. Lane 05 staging-to-native asset connection is still queued.

Use the verified absolute P1/P2 inputs in PIKMIN2_NEXT_WAVE.md; no new asset upload is needed for those paths. Preserve current fixture requirements and existing lane ownership. No main/upstream changes.
