# P2 parallel worker handoff

Coordination baseline: 2026-09-12. Parent [#109](https://github.com/4laric/pikmin-randomizer/issues/109). Read [the roadmap](PIKMIN2_CONTENT_COVERAGE.md), [AGENTS.md](../AGENTS.md) and [DEVELOPMENT.md](../DEVELOPMENT.md) before starting.

## Active local batches

| Owner | Issues | Reserved work |
|---|---|---|
| Codex animation/enemy subagent | #128, #120 | Snow animation importer, native enemy rendering, animation-specific modules/tests |
| Codex cave content subagent | #129, #154 | New retail cave catalog decoder, metadata audit, catalog tests |
| Codex lifecycle subagent | #112, #132 | Campaign Python, durable surface/cave handoff state, lifecycle tests |
| Codex integration lead | #109, #114 | Shared interfaces, combined builds/tests, native snapshot export, integration |

These reservations describe the current batches, not permanent ownership of entire epics. Check the latest issue comments before claiming work. Ask the integration lead before editing another lane's files, shared converters, preview launchers, native build configuration, save protocols or actor interfaces.

## Starting on another laptop or agent

1. Use a separate checkout and branch from an integration commit agreed with the lead. The current track is `codex/pikmin2-room-preview`; do not assume `main` contains the P2 prototype.
2. Select an unoccupied bounded issue or child batch. Post the scope, acceptance criteria, owner, base commit and proposed files before implementation. GitHub assignment through `4laric` represents the shared account; identify the actual worker in the comment.
3. Read the repository's native-source restoration/build instructions. Native is a separate repository locally; it is not an ordinary directory to push indiscriminately. The integration lead owns source snapshot export. Never push the native repository to a guessed remote.
4. Extract any required assets locally from the supported user-supplied disc. The baseline is US GPVE01 revision 0. Do not commit disc data, extracted models/textures/audio, generated builds or saves. Do not depend on another worker's absolute paths.
5. Keep builds and runtime fixtures in a worker-specific output directory. Never reuse another worker's live playtest save.
6. Deliver a reviewable branch or patch with exact base and resulting commits, changed files, commands/results, source references, manual evidence and known gaps. Explain any required shared-interface change before implementing it.

Other models can follow the same contract. A worker does not need access to the original chat: the issue, roadmap, source and handoff must be sufficient.

## Good independent next assignments

- **Treasure catalog validation, #140:** reconcile runtime catalog entries with active placements and dictionary IDs; produce classifications and checks without changing cargo runtime interfaces.
- **Equipment audit, #141:** source-backed effect/trigger/persistence specifications and tests around an agreed data contract before editing captain state.
- **Enemy behavior audit, #165–#175:** one family at a time; document states, animation events, hitboxes, drops and dependencies. Coordinate runtime implementation with the animation lane.
- **Independent QA, #135:** reproduce current fixture failures and test release builds using separate output/saves. File actionable issues with build identity and logs.

These suggestions are unclaimed until the issue records a worker. Start additional runtime implementation only after its file and interface boundaries are agreed.

## Integration contract

One integration lead merges code, rebuilds shared binaries and exports the native snapshot. Workers must not independently revise save schemas or actor IDs. Preserve P1 behavior behind explicit P2 mode boundaries. An imported model, source inventory or scripted fixture is not a completed native enemy, generated cave or natural playthrough. Record those milestones separately.

P2 remains outside Pikipelago v0.1. The immediate milestone remains the complete Emergence surface round trip; parallel work should support that or the next Hole of Beasts slice.
