# Kimi native bindings handoff

Ownership update, 2026-09-13: [the current workflow](PIKMIN2_WORKFLOW.md) lets
family owners continue native mechanics in private worktrees. The remaining
capability gaps below describe what these fixed binaries support; they are not
a requirement to wait for root to implement the next family step.

Integration commit f9f0839, native 7faa64475176658af85e2f558858c6d660cd4d20. Shared full build passed and no-work dry run confirmed freshness. Ten focused tests and nine parser subtests pass. Native runtime checks are being recorded separately below; a build alone is not visual acceptance.

Fixed private executable and resolved DLL closure:
`C:/Users/alari/pikmin-randomizer/output/p2-root-integration/output/kimi-native-bindings-01/nectar.exe`.
The sibling runtime-provenance.json hashes the executable and all bundled DLLs. This package contains no game assets; use a fresh private arena with verified local assets. Existing manual-qa-02 and player saves are untouched.

From the fresh arena directory, run the fixed executable with `--experimental-pikmin2-room`. Do not replace shared nectar.exe or switch the common root branch. Source work should use each session's own worktree; integration source is output/p2-root-integration.

| Lane | Available binding | Preparation |
|---|---|---|
| Beetles219 / native228 | Typed source-ID registry, visual bank, ordinary control fallback/reset | Keep Kimi v1 files; call experimental.pikmin2_kogane_native.emit(bank, run, arena, expected_manifest_sha256) to add explicit species/frame sidecar. See KOGANE_NATIVE_BINDING doc. |
| Giant220 / native229 | Separate Giant wait/move/nest displays, reset and missing-profile fallback | Use experimental.pikmin2_giant_breadbug_visual.prepare then install(profile,run); explicit display placement profile. See GIANT_BREADBUG_NATIVE_BINDING doc. |
| Mamuta221 / native230 | Exact P1 Miurin24 binding, source wait/swing/corpse anchors, fallback/reset | Existing Kimi P2_MAMUTA_ACTORS_1 and installed models are accepted unchanged. See MAMUTA_NATIVE_BINDING doc. |

This unblocks binding/visual/arena tests only. Beetles still run P1 placement-vehicle AI; source FSM, drops, gas and escape are not implemented. Giant is a noninteractive display, not a boss actor. Mamuta retains P1 behavior, not P2 sprout conversion/cap semantics. Shijimi followers are not created; safe owner lifecycle remains required before enabling them. Report those as blocked, not failed or passed.

Family owners may implement remaining native mechanics and validate them in new private builds. The fixed packages here support installed bytes, profile refusal, identity/control, visual/counter behavior and the recorded reset paths. No complete-family closure is implied.

## Validated local launchers

- Beetles: `C:/Users/alari/pikmin-randomizer/output/p2-root-integration/output/kogane228/runtime/stages/f0bb11777d6040f5a68e7be3768dbc95/Check.cmd`. Automatic 300-frame developer check, not open-ended gameplay. Typed IDs, full XYZ, imported draws and ordinary control passed. Source species textures remain approximate.
- Giant/nest: `C:/Users/alari/pikmin-randomizer/output/p2-root-integration/output/p2-giant-breadbug-runtime/kimi/Play-wait.cmd`, `Play-move.cmd`, `Play-nest.cmd`. Each creates a fresh private stage and holds a noninteractive display open. Wait/move/nest/disabled checks passed, visible captures inspected, reset/reload passed with unchanged actor/cargo/repair counts.
- Mamuta: `C:/Users/alari/pikmin-randomizer/output/p2-lifecycle-batch/mamuta-kimi-01/Play.cmd`. Native binding/control/reset checks passed; supplementary imported-wait capture is recorded by the Mamuta runtime report. Swing/dead and P2 planting acceptance remain open.

These are machine-local developer launchers and depend on existing local assets/Python. They are not portable release bundles. Kimi should use them in these private sessions, record each executable/config hash, and report unsupported behavior as a remaining dependency. Do not substitute a moving shared executable.
