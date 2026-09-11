# Open Nectar upstream synchronization

Tracking issue: [#25](https://github.com/4laric/pikmin-randomizer/issues/25).
User authorized periodic upstream pulls and tested integration on 2026-09-11.
The desktop heartbeat runs daily at 10:00 America/Toronto and stays quiet on unchanged state.

## Recorded state (2026-09-11)

- Upstream: `SSunnKing/Open-Nectar---Pikmin-Native-PC-Port`, branch `main`.
- Last fetched/reviewed: `18ce1303b488bc906721d1389143b65ace345695`.
- Last integrated upstream: `18ce1303b488bc906721d1389143b65ace345695`.
- Current maintained downstream native commit: `88557248` (see ENGINE_SOURCE.md); per-color stats and progressive upgrades added after integration in #28/#29/#30, with permanent checks in #31 and damage-based structure work in #32, expanded bestiary/landing-only checks in #33.
- **Integration complete:** [#26](https://github.com/4laric/pikmin-randomizer/issues/26), all 14 commits across 51 files, merged without conflicts. No pending upstream commits as of this review.
- [Health gauges PR #2](https://github.com/SSunnKing/Open-Nectar---Pikmin-Native-PC-Port/pull/2): OPEN, commit `b487872`.
- [Save-slot PR #3](https://github.com/SSunnKing/Open-Nectar---Pikmin-Native-PC-Port/pull/3): OPEN, commit `c0b6d377`. Two files, 29 PC-only lines; no randomizer fixtures or game content.

## Integration workflow

1. Inspect current worktrees, issue state and ongoing local changes. Fetch canonical upstream in the independent `upstream-health-gauge/` checkout. Its full upstream history is available. Never pull into the original BBFT or decomp repositories.
2. Check pending integrations before treating an unchanged upstream SHA as no work. Record/assign implementation issues before editing. Compare the maintained native baseline to the target upstream revision; review changes that overlap our hooks and platform fixes.
3. Import the needed upstream history into the isolated `native/` repository and create a separate candidate worktree/branch. Merge there and resolve conflicts. Keep the playable native checkout and packaged binaries unchanged until validation passes. Preserve the PC-only health-gauge/save fixes until equivalent upstream fixes are present; avoid duplicating merged fixes.
4. Configure a fresh build with portable optimization settings and randomizer test hooks disabled. Build `pikmin_pc` and `pc_randomizer_probe`; run Python tests, catalog check, packaged AP fills, and affected native protocol/startup regressions. Changes to save handling, rendering, enemy creation or color/population behavior require focused checks. Build/test failures stay in the candidate with exact evidence; do not repeatedly retry an unchanged blocker.
5. Promote a passing native candidate, update `engine/` using the source-only export, audit incoming files and licenses, and update ENGINE_SOURCE.md plus this ledger with integrated SHA, native commit and validation. Commit/push the randomizer source as authorized. Never include extracted assets, binaries, saves or logs, and never overwrite a running game binary.
6. Report only a verified integration, meaningful PR feedback, actionable failure or required user input. The user also authorized upstreaming the boss-generator fix (#35). Other new upstream messages/PRs need separate authorization.

## Save PR evidence and limits

The downstream direct boot left current save index zero. A first valid save rotated that zero into the backup index; the next serialization targeted before the card buffer. The fix rejects invalid backup indices before writes, re-derives a valid backup after first-save rotation, and sends invalid save notices through card preparation. The downstream synthetic regression rejected indices 0/5/255 without buffer or live-pointer changes and completed two consecutive saves from current index zero with metadata readback.

The trigger has not been reproduced through upstream's normal title/file-selection flow. Both patched and unmodified upstream save translation units currently fail clean MinGW compilation on existing `HWND`/`HINSTANCE` declarations in `include/system.h`. The downstream production build passes with inherited Windows compatibility changes. Do not describe the upstream clean build or player-driven save UI as validated.

## Integration validation — issue #26

Native merge `9be55fad` retains the downstream Windows compatibility patches, health-gauge submission, save-slot guards, enemy/collection hooks and configured Flarlic. Built Windows USA Rev 1 Release with native JAudio, portable CPU settings and test hooks OFF. Passed 34 Python tests, 2,160 packaged AP fills plus remote-Blue multiworld, all six native protocol suites (including all 15 area/color combinations), three adapter/audio tests, and four camera/shader/postprocess/render-packet tests.

A hidden production gameplay startup with enemy shuffle, collection checks and starting Flarlic 1 rendered the world, withdrew 10 red Pikmin with 10 still stored, reported the two expected opening checks, applied other-color grants exactly once and passed area/goal gates. No physical full-campaign, PAL, movie playback or day-end UI acceptance is claimed. Existing save routines and our save guards are unchanged by this merge.

The integration executable is `output/native-upstream-26/build-sync/bin/nectar.exe`, SHA-256 `A6F7D3AE733751F6345A6D984E98D7B55E65C2942DDE639190C20817AFB89754`. The previous #31 production executable is `native/build-stats/bin/nectar.exe`, also packaged in `output/turkey-build-01/bin/nectar.exe`, SHA-256 `92AB358D1CCA9C8435510B5F76CEB401743155023CD4F1132220BD7BB7976012`; it retains this upstream integration and adds progressive per-color AP upgrades. See DEVELOPMENT.md for its validation. Future packages should use the current executable or rebuild current source; older `native/build-randomizer` binaries predate this integration until rebuilt. Local test evidence is under `output/sync26-*` and `output/stats28-*` / `output/stats29-*` / `output/stats30-*` / `output/checks31-*` and is excluded from GitHub.

## Damage-based work validation — issue #32

Current native source `9c1bac13` adds per-hit structure work and alternate wall-animation attack-rate scaling. The production TEST_HOOKS OFF executable is `native/build-stats/bin/nectar.exe`, packaged in `output/turkey-work-01/bin/nectar.exe`, SHA-256 `0257E30399D6C25084A3EB5D8926B229109ECAD6DB2F58E17BB9260F03B0E9A6`. Validation includes 48 Python tests, real-object work/damage/clock fixtures, Navel completion/serialization/deduplication, and a separate production startup session. Evidence is under ignored `output/work32-*`; see DEVELOPMENT.md for exact scope and remaining gameplay balance checks.

## Bestiary validation — issue #33

Current native `c048b606`, production TEST_HOOKS OFF, packaged in `output/turkey-bestiary-01/bin/nectar.exe`; SHA-256 `CE158D7535EB557EDF4FEF8FE2DFFFF106465A64FA62A4665AC6DB8582E1256D`. Schema 9 adds eleven bestiary checks and retires scout checks; legacy schemas remain supported. Passed 50 Python tests, 2,460 AP fills and two multiworld cases, new/legacy compiled protocols and synthetic native Onion/death callbacks with real loaded corpse weights. Local evidence: `output/bestiary33-*`. See DEVELOPMENT.md for physical carry/combat validation limits.

## Remove landing rewards — issue #34

Native `db04c6c9`; new seeds exclude all exploration checks while preserving old manifests. Passed 51 Python tests, 2,460 AP fills/two multiworld cases and modern/legacy compiled protocols. Production TEST_HOOKS OFF executable: `output/turkey-no-land-01/bin/nectar.exe`, SHA-256 `4BB0928E5B4DFC66AF4BD826AB6704FBF5564395CAA57C6D257B7F3C6CBBD12D`. Evidence: `output/no-land-*`. AP v0.14.0; 59/120 checks.

## Boss generator decoding — issue #35

Native `6a3ef245` replaces implementation-defined GenObjectBoss bitfields with explicit retail bit positions in read/write paths. The same bitfield code exists at integrated upstream 18ce1303; submitted as upstream PR #4 at user request. Passed 7,686 native parameter/serialization cases and all five area spawn/startup audits: exactly one Spider in Navel, none in the other four areas; Hope Snagrets and Trial Emperor restored. Evidence: `output/boss35-*`. See DEVELOPMENT.md for test scope.

Corrected production executable (TEST_HOOKS OFF): `output/turkey-bossfix-01/bin/nectar.exe`, SHA-256 `F925414EC4A8DCA6E3C8E47BF6FC4BDA47135CEB55B9D05FBFB4E6675778AF23`. New packages should use this build or rebuild current source.

Boss fix upstream submission: [PR #4](https://github.com/SSunnKing/Open-Nectar---Pikmin-Native-PC-Port/pull/4), OPEN, commit `68d3c567`, based on freshly fetched upstream `18ce1303`. One source file, 13 insertions / 39 deletions. The two methods match the downstream native-tested implementation; randomizer logging/fixtures are excluded. PR explicitly distinguishes downstream gameplay evidence from an unvalidated clean upstream build.

Issue #36 updates Python/AP source-aware bestiary logic and versioned seed enemy layouts; native remains `6a3ef245` with the existing family mask. Validated all masks against the native probe and audited retail source/protection facts. `output/turkey-layout-01` reuses the current boss-fixed production executable. No native/upstream source integration was performed for this change.
