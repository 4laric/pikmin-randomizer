# Red manager replacement acceptance

Issue #120/#186. This private fixture tests actual TekiMgr replacement and native generator rebirth, not a direct family reset. GameCoreSection::cleanupDayEnd calls tekiMgr->killAll and nulls it; later gameplay setup constructs a new TekiMgr. The fixture executes that enemy-manager subset at observation120, allocates a new manager/actors, uses startStage and the original generators' native init, then applies the same profile through normal family setup. Source map, collision, routes and live captain remain in the same scene.

Checks: old pointer loses registry membership after new-manager construction; new actors initially have P1 default health; Red becomes200 and ordinary control stays130 after profile setup; full stored birth equals original generator XYZ; another120 normal updates per actor advance animation. Explicit profile/bank hashes and executable provenance accompany results. Old manager allocations remain in the scene heap until process exit, matching a scoped lifecycle test rather than full heap reclamation.

Whole scene exit clears Navi, factories, effects and heap-owned systems, so invoking it in the active observer and retaining pointers would be invalid. Full scene/heap teardown, campaign save/load reentry and allocator same-address reuse remain separate unmeasured gates. No production source edits or timing overrides are made.

## Measured result

Private frozen e704b268 fixture exits0 after25.44s, SHA25694cd6f382764df3645db1761a78defce8c997686f1464c26d8545f2de265c09e. Evidence output/p2-red-arena-reentry/observe/evidence.json. Actual manager and actor addresses differ; old registry cleared; both newly born actors initially130; source-profile setup yields Red200/control130; native generator/personality fullXYZ preserved. Each new actor completes120 normal updates with advancing animation. No direct family reset was called. Two focused tests pass. The profile and bank hashes are recorded in evidence. This closes the manager replacement subset, not full scene/heap teardown or campaign save/load.
