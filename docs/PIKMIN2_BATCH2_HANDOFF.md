# Batch 2 handoff — hard lanes (#244 BombSarai, #245 Fuefuki, #246 BigTreasure)

Prepared by the Batch 2 worker session (opencode) for the integration lane.
Publishable artifact: this root branch `opencode/p2-batch2-handoff`. The native
candidate stays on the local native branch (native origin is never pushed);
patches below capture it.

## Candidate

- Native branch: `opencode/p2-hardlanes-native` (worktree `output/integration-hardlanes`), HEAD `086ed858`.
- Base: `codex/p2-bigtreasure` `d51d2916`.
- Merged cleanly (no conflicts):
  - `codex/p2-bigtreasure` `d51d2916` (BigTreasure FSM + Fuefuki through `4ccb7778`)
  - `codex/p2-fuefuki` `e82fdc48` (suspend brain-fallback → Free fix)
  - `codex/p2-bombsarai-policy` `045b872b` (BombSarai arena/FSM/blast/bomb/hover/map-trace/terrain)
- Incremental commits on top (patches in `native-candidates/hardlanes-batch2/patches/`):
  - `c47c6120` add hard-lane sources to the shared `pikmin_pc` CMake list
  - `9407175a` BombSarai live host-adapter registration seam
  - `a3dc1297` Fuefuki live host-adapter registration over the real squad
  - `2501c853` BigTreasure host seam + sampled visual registration
  - `086ed858` link the BigTreasure fixture against the shared modules (drop direct `.cpp` includes)
- Full combined diff vs the base: `native-candidates/hardlanes-batch2/hardlanes-batch2-full.patch`.

## What changed

- `CMakeLists.txt`: adds BombSarai (`pc_p2_bombsarai_arena/blast/bomb/fsm/hover/map_trace/terrain`) and BigTreasure (`pc_p2_bigtreasure`, `_attacks`, `_fsm`, `_host`, `_map_trace`, `_motion`, `_visual`) to `pikmin_pc`. Fuefuki is header-only.
- `pc_port/pc_p2_hardlanes.{h,cpp}`: one shared, opt-in registration seam:
  - BombSarai carrier arena bound to live `mapMgr` via `P2BombSaraiMapBinding`/`TerrainAdapter`, advanced on `gsys->getFrameTime()` by `P2BombSaraiSourceClock` with a `carrierAlive` callback.
  - Fuefuki `P2FuefukiBinding` with all seven host callbacks over the live `pikiMgr` squad anchored on a staged `TEKI_Napkid` vehicle; `ownershipWrite` performs the single captain-ownership write (`mNavi` + `PIKISTATE_LookAt`).
  - BigTreasure `p2_bigtreasure_host_setup` fixed-placement seam + `pc_p2_bigtreasure_visual_*` sampled bank, drawn at the fixed owner transform.
- Wiring: `pc_p2_preview_setup` → `pc_p2_hardlanes_setup`; `GameCoreSection::update` → `pc_p2_hardlanes_update`; `GameCoreSection::draw` → `pc_p2_hardlanes_draw`. All opt-in (room preview + profile/vehicle present); ordinary P1 play untouched; no shared semantics changed.
- `tools/p2_bigtreasure_runtime.cpp`: links against the shared modules instead of `#include`-ing their `.cpp` (the modules are now in `pikmin_pc`, which otherwise duplicated symbols).

## Build evidence

Private build `output/integration-hardlanes/build-hardlanes`:
`[2/2] Linking CXX executable bin\nectar.exe` (full build earlier `[507/507]`), `ninja -n pikmin_pc` → no work.
`nectar.exe` SHA-256 `5968BAEB1092246D5104E7A94C5A7A7B691C87F870B264245985523BAFC0F36C`.

## Runtime fixture evidence (real GL, retail-derived room/overlay)

- **BombSarai** `output/bombsarai-arena-preview2/975d69cd4f7f412db73599ad67f20dc6`:
  `approach`/`purple`/`death` scenarios all `P2_BOMBSARAI_SCENARIO_PASS`; `PASS BOMBSARAI_RUNTIME`.
- **Fuefuki** `output/fuefuki-arena-preview2/065f477cbe594cd79aec31bade596e7e`:
  scan claimed 3 over the real `pikiMgr`, non-routes silent, panic release ×3, reclaim via real `callPikis` (1 write), formation join, kill/carcass; `PASS FUEFUKI_RUNTIME`.
- **BigTreasure** `output/bigtreasure-runtime-sessions3/8ac519d9086a4116801c301f1f9103e8` (`verification.json` `passed`):
  floor/wall probes, elec `bounces=10`, water arc `ticks=59`, host seam `ticks=361 events=5`, visual `wait1 loops=4`, `dead keyevent100=320`; `PASS BIGTREASURE_RUNTIME`.
- Re-validated against the updated runbook: `tests/test_pikmin2_fixture_squad.py` 5 passed (20-red squad injection).

## Integration instructions (integration lane)

1. Merge the three lane branches above into the maintained native line (or apply `hardlanes-batch2-full.patch`), then apply the incremental patches. The three merges were conflict-free against `codex/p2-bigtreasure`.
2. Keep the batch-2-visuals registration (`pc_p2_batch2.*`, already exported under `origin/opencode/p2-batch2-root`) alongside `pc_p2_hardlanes.*`. The two lines are currently separate: the hard-lane candidate is based on the `bigtreasure` line and does **not** contain `pc_p2_batch2`; do not export the hard-lane line over a root `engine/` that must keep the batch-2 visuals registration. Unify first.
3. Run the maintained `pikmin_pc` build and `ninja -n` dry run, then `py -3.12 scripts/export_native_source.py` and push root source.
4. Do not double-drive a lane in a fixture: the shared seam and a lane's own fixture both set up the same module when the lane profile is present. For fixture runs, either use fixtures that predate the seam (as the BombSarai prebuilt exe does) or gate the seam off for that run.

## Blocked gaps (not integration)

- BombSarai visual bank and `kamu_jnt1` capture joint (#128 converter).
- Fuefuki source `keyEvent`/animation bank — the live FSM stays in `Land` until a Fuefuki actor/animation source exists (#128).
- BigTreasure motion staging beyond 2/29 clips; lloozy model unconverted; ballistics/damage receivers.
