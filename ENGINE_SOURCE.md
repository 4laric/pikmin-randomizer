# Native source provenance

The current P2 source-delivery snapshot is native
`9a76a11d9d65529690237e2ed55344302cb29b13`, exported from the clean private
`output/native-p2-acceptance-wave` worktree under #1131. It adds independently
reviewed native Red cave identity, White ingestion and durable enemy receipt
handling, plus a physical-input smoke companion. See
[the frozen batch and acceptance limits](docs/PIKMIN2_ACCEPTANCE_WAVE_1131.md).
The preceding #1118 snapshot remains recorded at
`2e6efbb1b841c1889d1bbd3b656e44ba6ae3629b` in
[its combined acceptance report](docs/PIKMIN2_COMBINED_ACCEPTANCE_1118.md).
The preceding frozen #1105 snapshot remains recorded at
`54743e12003888891d4dc3de249214cb18627fa6`; its evidence is preserved.
The preceding combined baselines remain recorded under #1073 and #1087.
The release descriptions below are historical provenance.

`engine/` is a source-only snapshot of the isolated Open Nectar/BBFT-derived native checkout used for this randomizer, at native commit `597d8f926833e1aa5c2a25df823a5e824d1118ce` (4laric/Open-Nectar---Pikmin-Native-PC-Port `main`, exported for v0.32.0-playtest.1; see the release note at the end). It includes the inherited native compatibility and adapter code, standalone randomizer integration, health-gauge fix, guarded day-end saves, collection-check hooks, configurable starting Flarlic, and seeded per-color stats, progressive AP stat upgrades stacked on optional wider initial rolls, weighted carrying, scalable check storage permanent-structure observers and damage-per-event structure work, expanded bestiary and exploration-free new seeds and portable boss-generator parameter decoding and per-color total-population milestones, durable consumable benefits and progressive captain upgrades. The native source history is retained locally; this directory is a snapshot, not a submodule.

Upstream: https://github.com/SSunnKing/Open-Nectar---Pikmin-Native-PC-Port (itself based on https://github.com/projectPiki/pikmin). The original local upstream boundary was `71db8405b78d5ae5765ac5d5f71d3305ca67c1ef`; upstream main through `511f22fe` is merged in draft #432; validation and limits are recorded in UPSTREAM_SYNC.md. Local BBFT-derived changes are included in the engine source; standalone play does not require the BBFT conductor or its separate repository.

Original `LICENSE.MD`, `LEGAL.md`, and per-file notices are preserved. The inherited engine README and BBFT notes describe upstream or historical workflows; the root README is authoritative for building and running this randomizer.

The export copies Git-tracked source files and permitted desktop build resources under `packaging/icon/`, excluding the upstream portable archive, formatter executable, CI workflows and editor settings. Android/touch binary assets are skipped. It never copies extracted game assets, untracked runtime files, saves, build outputs or nested Git history. `scripts/export_native_source.py` refreshes this snapshot from the maintainer's ignored `native/` checkout or an explicitly selected private worktree; it is not required to build a public checkout. Review deletions manually when refreshing a later snapshot.

Graphics integration (#48): Original/Enhanced/Custom presets preserve existing settings; Enhanced selects FXAA, 8x anisotropy and subtle bloom. Unsaved previews revert on menu close. Post-processing now sets and restores GL color-write masks. See engine/tools/GRAPHICS_VALIDATION.md for the focused renderer/menu/scene validation workflow.

Integration #437: exported from the clean isolated `output/p2-main-review/native` worktree. See [the current dependency reconciliation](docs/PIKMIN2_DEPENDENCY_RECONCILIATION_437.md) for validation and acceptance limits.

Release export (v0.32.0-playtest.1, #906): exported from a clean, detached checkout of native `main` at `597d8f92` with no local changes. Before this, `engine/` had drifted: 275 files matched older native states and 4 carried root-side merge resolutions, while native `main` had moved on (upstream Open Nectar 0.8.5–0.9, local co-op/VS, Progressive Maturity/Day Length, Better Pathfinding, the Whistle Pluck item and the Disable Tutorials filter). The exporter now skips binary assets under the Android and touch-control folders, which desktop builds do not use. Three files no longer in native `main` remain because root docs or tests reference them: `pc_port/tests/tutorial_settings_test.cpp`, `tools/preview_whistle_pluck.cpp` and `tools/test_p2_pose_bank.cpp`.
