# Open Nectar upstream synchronization

Tracking issue: [#25](https://github.com/4laric/pikmin-randomizer/issues/25).
User authorized periodic upstream pulls and tested integration on 2026-09-11.
The desktop heartbeat runs daily at 10:00 America/Toronto and stays quiet on unchanged state.

## Recorded state (2026-09-11)

- Upstream: `SSunnKing/Open-Nectar---Pikmin-Native-PC-Port`, branch `main`.
- Last fetched/reviewed: `18ce1303b488bc906721d1389143b65ace345695`.
- Last integrated upstream: `18ce1303b488bc906721d1389143b65ace345695`.
- Current maintained downstream native commit: `9be55fad` (see ENGINE_SOURCE.md).
- **Integration complete:** [#26](https://github.com/4laric/pikmin-randomizer/issues/26), all 14 commits across 51 files, merged without conflicts. No pending upstream commits as of this review.
- [Health gauges PR #2](https://github.com/SSunnKing/Open-Nectar---Pikmin-Native-PC-Port/pull/2): OPEN, commit `b487872`.
- [Save-slot PR #3](https://github.com/SSunnKing/Open-Nectar---Pikmin-Native-PC-Port/pull/3): OPEN, commit `c0b6d377`. Two files, 29 PC-only lines; no randomizer fixtures or game content.

## Integration workflow

1. Inspect current worktrees, issue state and ongoing local changes. Fetch canonical upstream in the independent `upstream-health-gauge/` checkout. Its full upstream history is available. Never pull into the original BBFT or decomp repositories.
2. Check pending integrations before treating an unchanged upstream SHA as no work. Record/assign implementation issues before editing. Compare the maintained native baseline to the target upstream revision; review changes that overlap our hooks and platform fixes.
3. Import the needed upstream history into the isolated `native/` repository and create a separate candidate worktree/branch. Merge there and resolve conflicts. Keep the playable native checkout and packaged binaries unchanged until validation passes. Preserve the PC-only health-gauge/save fixes until equivalent upstream fixes are present; avoid duplicating merged fixes.
4. Configure a fresh build with portable optimization settings and randomizer test hooks disabled. Build `pikmin_pc` and `pc_randomizer_probe`; run Python tests, catalog check, packaged AP fills, and affected native protocol/startup regressions. Changes to save handling, rendering, enemy creation or color/population behavior require focused checks. Build/test failures stay in the candidate with exact evidence; do not repeatedly retry an unchanged blocker.
5. Promote a passing native candidate, update `engine/` using the source-only export, audit incoming files and licenses, and update ENGINE_SOURCE.md plus this ledger with integrated SHA, native commit and validation. Commit/push the randomizer source as authorized. Never include extracted assets, binaries, saves or logs, and never overwrite a running game binary.
6. Report only a verified integration, meaningful PR feedback, actionable failure or required user input. New upstream messages/PRs beyond the explicitly authorized save and health fixes need separate authorization.

## Save PR evidence and limits

The downstream direct boot left current save index zero. A first valid save rotated that zero into the backup index; the next serialization targeted before the card buffer. The fix rejects invalid backup indices before writes, re-derives a valid backup after first-save rotation, and sends invalid save notices through card preparation. The downstream synthetic regression rejected indices 0/5/255 without buffer or live-pointer changes and completed two consecutive saves from current index zero with metadata readback.

The trigger has not been reproduced through upstream's normal title/file-selection flow. Both patched and unmodified upstream save translation units currently fail clean MinGW compilation on existing `HWND`/`HINSTANCE` declarations in `include/system.h`. The downstream production build passes with inherited Windows compatibility changes. Do not describe the upstream clean build or player-driven save UI as validated.

## Integration validation — issue #26

Native merge `9be55fad` retains the downstream Windows compatibility patches, health-gauge submission, save-slot guards, enemy/collection hooks and configured Flarlic. Built Windows USA Rev 1 Release with native JAudio, portable CPU settings and test hooks OFF. Passed 34 Python tests, 2,160 packaged AP fills plus remote-Blue multiworld, all six native protocol suites (including all 15 area/color combinations), three adapter/audio tests, and four camera/shader/postprocess/render-packet tests.

A hidden production gameplay startup with enemy shuffle, collection checks and starting Flarlic 1 rendered the world, withdrew 10 red Pikmin with 10 still stored, reported the two expected opening checks, applied other-color grants exactly once and passed area/goal gates. No physical full-campaign, PAL, movie playback or day-end UI acceptance is claimed. Existing save routines and our save guards are unchanged by this merge.

The validated local executable is `output/native-upstream-26/build-sync/bin/nectar.exe`, SHA-256 `A6F7D3AE733751F6345A6D984E98D7B55E65C2942DDE639190C20817AFB89754`. The previous playtest packages remain intact. Future packages should use this executable or rebuild from current source; older `native/build-randomizer` binaries predate this integration until rebuilt. Local test evidence is under `output/sync26-*` and is excluded from GitHub.
