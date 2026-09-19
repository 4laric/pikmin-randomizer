# Parallel Emergence Cave implementation

> Historical track allocation. Current execution, resources and recovery follow
> [PIKMIN2_WORKFLOW.md](PIKMIN2_WORKFLOW.md); current pushes follow
> [AGENTS.md](../AGENTS.md#git-push-policy). These assignments are not a live lane registry.

Integration owner: Codex using shared GitHub account 4laric, [#114](https://github.com/4laric/pikmin-randomizer/issues/114). All work remains experimental and outside v0.1. Starting point: root `530fd17`, native `a78ea6d6`.

| Track | Issue | Branch in both repositories | Ownership |
| --- | --- | --- | --- |
| Native enemies | [#120](https://github.com/4laric/pikmin-randomizer/issues/120) | `codex/p2-enemies` | Source enemy identity/assets, local importer, opt-in native actor support and tests |
| Cave lifecycle | [#112](https://github.com/4laric/pikmin-randomizer/issues/112) | `codex/p2-lifecycle` | Transition location/action, boundary guards, checkpoint integration and tests |
| Content fidelity | [#110](https://github.com/4laric/pikmin-randomizer/issues/110) | `codex/p2-content` | Source roster, stable placement manifest, all three treasure assets and content tests |
| Integration | [#114](https://github.com/4laric/pikmin-randomizer/issues/114) | `codex/pikmin2-room-preview` | Shared interfaces, conflict resolution, native snapshot export, combined validation and player bundle |

Each worker has a root worktree with its own native worktree. Builds, extracted assets and fixtures stay private. The maintained native build and existing player executable are not worker outputs. Native commits stay local; workers may export source to their own root branch using explicit paths. The integration owner updates the maintained branch and combined build.

## Shared interfaces

- Keep checkpoint schema 1, nonce validation and native exit 42 until a schema change receives integration review. Existing saves must either remain valid or fail explicitly with a content mismatch; never silently reset them.
- Species identity is distinct from a compatibility actor family or Pikmin color. A reused P1 behavior must be documented as such; imported visuals do not establish full P2 behavioral fidelity.
- Content instance IDs are stable and floor-scoped. Treasure catalog IDs identify the source item, not its particular placement. Do not rename existing saved receipt IDs without an explicit compatibility decision.
- Native delivery credits the Pod ledger. P1 seed production, repairs and AP rewards must not leak into the P2 experimental mode.
- Content tools own manifests and local asset preparation. Native enemy modules consume explicit configuration. Lifecycle consumes an explicit transition kind and location. Additive APIs avoid competing changes to the same setup/render function.
- Source roster and placements come from disc/decomp data. Random spawn categories are recorded as such, not presented as exact authored coordinates. Unsupported actors/materials remain explicit.

## Integration gates

Review worker commits and test evidence separately. Resolve source naming disagreements before connecting content to actors. Build a combined candidate only after interface agreement; use an isolated executable and fresh test session. Exercise existing room behavior with new features absent, then enemy/corpse receipt behavior and configured descent/exit with features enabled. Re-run native restoration when shared setup order changes.

Only package a combined player build after those checks pass. Source-only or partial increments can land with their limitations recorded, without changing the current playtest. A complete Emergence Cave still requires its full roster, physical transitions, surface round trip and a player-driven completion/reload test.
