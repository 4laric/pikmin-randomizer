# Open Nectar upstream synchronization

Tracking issue: [#25](https://github.com/4laric/pikmin-randomizer/issues/25).
User authorized periodic upstream pulls and tested integration on 2026-09-11.
The desktop heartbeat runs daily at 10:00 America/Toronto and stays quiet on unchanged state.

## Draft integration #433 (2026-09-13)

Upstream main `511f22fe` (12 commits after `f88c7810`) is integrated into
private native `9735870cea769169446c524b6ae0cbdb07ed920e` for draft PR #432.
This supersedes the historical state below for the draft only.

Includes portable/legacy card discovery and PAL matching, per-save Hard mode,
object-space normal texgen/specular fixes, DIRECT matrix handling, Wayland GPU
selection, installer recovery/progress and the opt-in F7 debug shortcut.

Conflict decisions: explicit randomizer/BBFT session card roots retain priority;
ordinary game launches use upstream card discovery. Hard-mode max life uses
P2-aware parameter lookup. Expanded randomizer allocation retains its maximum
reservation before ordinary Hard-mode limits. Preserve broader transient rename
retry handling and upstream installer UX. Remove duplicate CMake test entries.

Private Release/MinGW/Ninja build with JAudio ON, randomizer test hooks OFF:
`output/p2-upstream433-build`, targets `pikmin_pc` and `pc_randomizer_probe` PASS;
dry run: `ninja: no work to do.` Executable SHA256:
`15439A5FE924CF4BE282EA582EA06FBDB455FC4EF3ED180A04CD87192BA62277`.
First configure exposed duplicate asset-finalize targets; corrected before build.

Full suite: **1627 passed, 24 skipped, 1052 subtests passed**. Seven native tests
pass: installer UI, asset finalization, prepared image, Hard mode, GPU preference,
TEV shader and render packets. Native IPC, campaign assignments, prerelease
receipt/save/reload protocol and DeathLink pass; catalog check and UT regeneration
(12 slots/48 reachability comparisons plus fills) pass.

Two old probe assumptions were corrected: the single-write DeathLink harness
must cross MinGW's one-second timestamp resolution; the startup harness must use
the current goal marker and per-color population catalog. Failed attempts remain
in local output logs. Native startup results and packaged fill results follow.

Startup follow-up: production build PASS in a fresh private session, Forest of
Hope, 20 red Pikmin, other Onion grants exactly once, area gates, completion,
current population checks and world rendering. CARDInit confirms the session's
`campaign/card/card0` root. Source export parity: all 1593 tracked text files.

No native-origin push, live save migration or main-branch merge. PAL save UI,
ordinary-game legacy card migration, Hard-mode gameplay and P2 specular visual
fidelity are not established by these automated gates.

## Historical recorded state (2026-09-12)

- Upstream: `SSunnKing/Open-Nectar---Pikmin-Native-PC-Port`, branch `main`.
- Last fetched/reviewed: `f88c7810` (integration tracked in #107).
- Last integrated upstream: `f88c7810` (including merged PRs #15 and #22–24).
- Current maintained downstream native commit: `5421633e` (see ENGINE_SOURCE.md); includes experimental Purple support and two-floor cave checkpoints and preserves the separate release boundary.
- **Earlier integration complete:** [#26](https://github.com/4laric/pikmin-randomizer/issues/26), all 14 commits across 51 files, merged without conflicts. This historical integration does not include the newer reviewed commits above.
- [Health gauges PR #2](https://github.com/SSunnKing/Open-Nectar---Pikmin-Native-PC-Port/pull/2): MERGED at `398258e7`, 2026-09-11.
- [Save-slot PR #3](https://github.com/SSunnKing/Open-Nectar---Pikmin-Native-PC-Port/pull/3): CLOSED after maintainer manually applied the save guards on main in `4df56740`; not rejected. CI PR #7 was likewise applied manually and closed. Boss PR #4 and health-gauge PR #2 are merged.

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


## Public CI repair (#64)

Upstream PR #7 separates private matching builds (manual dispatch, existing container access required) from automatic public Linux validation. Global sqrtf/fmodf calls fix GCC math.h namespace failures; the clean-distro job downloads its package into the directory it executes. Native 30b4364b merges upstream main plus CI branch fab3f170. Save PR branch 22339471 and boss PR branch 7e46481e also include the CI changes. Final upstream PR #7 CI and fork CI pass: Linux USA/PAL builds, 21 offline tests (asset-dependent audio explicitly skipped), standalone packaging, permission-preserving tar artifact and clean Debian12 launcher/dependency smoke. The smoke environment installs the documented GBM/DRM/Mesa graphics runtime. Evidence: https://github.com/SSunnKing/Open-Nectar---Pikmin-Native-PC-Port/actions/runs/34637042965 .

During CI repair the maintainer merged boss PR #4 at b8a31a8a (2026-09-11 18:51:56 UTC). Its PR checks remain attached to that earlier head; the updated boss branch7e46481e passes fork CI run34637067020. Save PR #3 current upstream checks pass. Main b8a31a8a was observed but has not been integrated as an upstream merge commit here; its boss patch is already present downstream. PR #7 is ready and green, awaiting upstream review/merge.

## Three focused upstream PRs (#71–#73)

User authorized submission of quick-grab timing, post-process color mask and hold-to-pluck. All branches start directly at reviewed upstream `f80a7246`, independently, with one source file each. No randomizer hooks, other PRs, CI changes, settings presets or defaults are bundled.

- [PR #11](https://github.com/SSunnKing/Open-Nectar---Pikmin-Native-PC-Port/pull/11): quick-release grab, `ea190fad`, tracking #71. Rerun of the existing downstream real-engine fixture passes near and approaching targets with A released (Flying reached in 2 and 16 sampled frames). This is not physical SDL/controller input validation.
- [PR #12](https://github.com/SSunnKing/Open-Nectar---Pikmin-Native-PC-Port/pull/12): post-process color-mask save/enable/restore, `b3058ada`, tracking #72. Existing downstream GL fixture rerun passes poisoned targets, mixed/all-disabled masks, FXAA/bloom/grading and mask restoration on Intel OpenGL 3.3.
- [PR #13](https://github.com/SSunnKing/Open-Nectar---Pikmin-Native-PC-Port/pull/13): hold-to-continue initiated plucking, `086521ef`, tracking #73. Existing downstream live fixture rerun passes unbroken hold, release, whistle cancellation, re-press, animation-boundary release and bounded fast-pluck counter. Physical multi-sprout controller acceptance remains distinct.

These reruns use the existing downstream fixture binaries, not newly built upstream binaries. All patches applied cleanly and passed diff checks. Fresh upstream CI builds were still running when submitted; do not infer a green upstream build from downstream fixture results. Upstream runs: 34648747460 / 34648752134 / 34648761610 respectively. Local evidence is under output/upstream-grab-71-recheck, output/upstream-color-mask-72-recheck and output/upstream-pluck-73-recheck. No downstream game binary, save or playable checkout was changed.

## Integration and PR feedback — #83

Integrated canonical 7dc430c7 via candidate merge aed49cdf, native 85a581b0. Conflicts reconciled in CI/CMake, save guards, boss decoding and pluck handling. Randomizer runs preserve hold-to-pluck; ordinary PC play uses upstream F1 optional setting. New upstream changes include menu depth-of-field exclusion, real control names in tutorials, DualSense capture fixes and PAL startup fix.

PR #11 merged. PR #12 manually applied in 2fc6298d because post_apply gained allowDof. PR #13 manually applied in 7dc430c7 as an off-by-default F1 mod: maintainer considers this a gameplay change rather than a bug fix. Future gameplay proposals should follow that optional-mod convention.

Validation: clean Windows production build (portable optimization, JAudio ON, test hooks OFF); 92 Python tests/eight subtests; 150 AP custom fills/10 remote-Blue multiworlds; legacy/new consumed-benefit save/reconnect probes and campaign protocol; all five live area startups with seed-matched births; four render/camera tests; real GL mask fixture; real pluck hold/release/cancel/re-press fixture. PAL runtime and physical controller/menu acceptance not claimed.

Submitted bomb-warning fix as upstream PR #15 (b179e12a), tracking #84. CI pending at submission. Eight-line PC guard only; no randomizer hooks. Dynamic field-limit messaging is another candidate; Candypop timing, faster throws and other gameplay conveniences need optional-mod treatment upstream.


## Experimental P2 fixture follow-up (2026-09-12)

Native `f292a028` extends the standalone room fixture with decoded terrain expectations and a partial-recruitment fallback. The production runtime is unchanged from `5b0e3857`. This does not integrate the separate upstream candidate or alter the release boundary. Emergence entrance-room native validation passed; see docs/PIKMIN2_EMERGENCE_IMPORT.md.

Native `34f2760e` adds controller-driven cross-seam walking and distant corpse-delivery assertions to the experimental fixture. Production runtime remains unchanged. The authored Emergence first-floor assembly passed native validation; no upstream integration was performed in this increment.

Native `9630447e` adds the isolated Research Pod/economy scaffold and second-floor/mixed-color native fixtures. Automated P2 fixtures use a silent SDL device after the continuous-tone report (#116). No upstream integration is included in this increment; cave lifecycle and full Pod acceptance remain open.

Native `6a1c352be46e` adds the opt-in Purple/Violet/Atlas preview (#113), sampled source poses and separate carry strength/speed. This is another downstream experimental increment, not an upstream pull. Purple campaign storage and full behavior remain open.

## Heartbeat integration — #107 (2026-09-12)

Fetched canonical upstream `f88c7810787d4dd8cb5e14785a5b73cd790a5946`. The previously isolated #107 candidate `8c9ffb82` was pending promotion; it was not repeated or discarded. Merged it into a new candidate based on current Purple native `6a1c352b`, then merged upstream through `f88c7810`, producing `ad82784ead43a84fddf773a7cd411a21d1be822a`. Both merges completed without new conflicts. Promoted source only after validation; experimental ancestry was not merged into release/main.

New upstream work includes the opening ship exhaust rendering, mouse-look/WASD interaction correction, analog trigger/stick bindings, and our accepted bomb-warning, portable ARAM temporary-file, remapped prompt and controller settings-menu fixes. PR #15 and PRs #22–24 are merged with no additional review comments. PR #2 remains merged; PR #3 remains closed after the previously recorded manual application, with no new feedback. #108's three upstream submissions therefore no longer await merge.

Validation in the isolated candidate: clean Windows Release build with native JAudio, portable CPU settings and test hooks OFF; 24 CTests passed and one asset-dependent JAudio test skipped (ARAM test passes with TMPDIR unset); 154 Python tests plus eight subtests; matching generated native catalog; 150 custom AP fills, ten remote-Blue multiworlds and 30 Prerelease-trap fills; five compiled protocol suites covering legacy IPC, campaign mappings, color stats, benefit persistence and Prerelease modes 17–32; five silent production area startups with ten yellows, rendered worlds, handshakes and seed-matched enemy births.

The older `scripts/test_native_startup.py` reached native completion but timed out waiting for obsolete text `GOAL: Ship repaired!`; maintained native already emits `GOAL: Seed complete.` and the script also contains retired population expectations. This is a stale harness, not an observed new native regression. It was not retried unchanged; current campaign startup and protocol suites passed. Repairing or retiring that legacy harness remains a testing-maintenance item. An unscoped pytest discovery was stopped before running tests because it traversed local research/output checkouts; the reported 154-test pass explicitly targets `tests/`.

Candidate build/evidence remains under ignored `output/upstream-sync-sep12-purple*`. Source snapshot was refreshed, but existing playtest executables, game assets, Purple launcher, sessions and saves were preserved. The candidate binary is `output/upstream-sync-sep12-purple-build/bin/nectar.exe`. Physical controller/menu acceptance, PAL runtime, full campaigns and the separate #116 audio investigation are not claimed by this integration. No new upstream PRs or external review replies were sent.

Native `85074274` adds the downstream PC carry-counter expansion and P2 render/counter fixture diagnostics (#119). Upstream integration remains through `f88c7810`; no additional upstream PR is included.

## Daily check — 2026-09-13 00:35 America/Toronto

Fetched canonical upstream; main remains f88c7810787d4dd8cb5e14785a5b73cd790a5946 and HEAD..upstream/main is empty. No candidate integration or rebuild required. Open PR25 (installer UX) and PR26 (F10 fast-forward) have no review comments/reviews and both Linux build/smoke checks succeed. They remain open, not merged. Existing validated upstream integration is unchanged; no external review replies sent.
