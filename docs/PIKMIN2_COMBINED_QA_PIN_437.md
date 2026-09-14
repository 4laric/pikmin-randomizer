# Integration-approved combined QA pin (#437)

Approved for candidate runtime testing by Codex through shared account 4laric on 2026-09-14. This approval means a combined, built and reproducible QA baseline; it does not admit either identity or certify natural gameplay acceptance.

- Root source: `ff838a2cccfd384d8793578d1a1b81bdab1011ae` (clean at source commit; later pin-document commit changes docs only).
- Native: `9b15d371cc63e7b0154bfc3dfc2cf5be9874c754` (clean).
- Executable: `C:\Users\alari\pikmin-randomizer\output\p2-integration-9b15d371\nectar.exe`.
- SHA-256: `6a0b31f2adafcdcf54af1766991e2bd7cf6a078ed5d0ce3c3fc5cbedc29252d5`.
- Machine-readable pin: `C:/Users/alari/pikmin-randomizer/output/p2-integration-9b15d371/pin.json`.
- Assets: `C:/Users/alari/bbft/dist/cohesion/pikmin/assets` (read-only input; normal candidate content staging still required).
- Root integration tree: `C:/Users/alari/pikmin-randomizer/output/nectar-qol`; native: `C:/Users/alari/pikmin-randomizer/output/native-nectar-qol`.

## Included and validated

Root 90c131e ->9e550db: source 44 content/candidate support. Root 43c4334 ->95f834c: schema-9 ENEMY_P2 journal restart and candidate subprocess admission propagation, consumed once. Native f33af8db ->9b15d371: generated Dwarf Orange host binding/FSM setup, on the maintained native 156e372f with Disable Tutorials default On. Engine export is source-identical across 1996 files. Native origin was not pushed.

Fresh focused regression: 147 tests and 17 subtests PASS (candidate Snow/Orange, content, staging, generated-session acceptance, enemy/roster and placement). Full production build PASS: private output/native-nectar-qol-build, Ninja/MinGW Release, JAudio/IPO ON; final dry run says ninja: no work to do. Logs: common-root output/p2-combined-pin-tests.log and output/p2-combined-pin-build.log. The historical 2775-test result is worker-reported and was not rerun here. No GL runtime run is claimed for this combined pin.

## Remaining gates and known issues

Snow final acceptance still needs natural combat, death, actual delivery, revisit and observed cleanup. Spawn markers are not natural_fight acceptance. Assignment 3's latest natural carry stalls before delivery. Assignment 5's committed source 44 path has a known initialization-order risk: generated bind checks the Orange flag before finalSetup calls campaign setup. Its dirty setup-order/debug work in output/native-sweep437 was deliberately not imported as a verified fix. Use this pin to reproduce and deliver a reviewed follow-up; do not label Orange generated acceptance PASS.

The missing combined-pin blocker is resolved; these remaining behavior/evidence gates are not. Admission stays default-deny outside the explicit candidate scope. PIKMIN_P2_ADMITTED_IDS is a private process-tree override and must not be set in normal product launches.

## QA use

Create a new isolated root worktree from the root source SHA above (or the documentation-only descendant on origin/codex/p2-main-review). Re-run candidate plan/prepare with this pin's root/native/executable/hash values and the reviewed content and placement inputs; do not edit old prepared reports in place. Pin.from_dict(json.load(...)).verify() verifies the binary hash. The existing candidate CLI uses --root-commit, --native-commit, --executable and --executable-sha256; inspect --help for the full plan/prepare arguments.

Source includes ensure_pikmin_squad and the centred 960x540 startup. Each runtime owner must regenerate a fresh arena and observe live starting Pikmin/window adoption; source inspection is not runtime evidence. Cooperative GL locks do not account for old unleased fixtures: recheck processes before launching. Use GL-A for ordinary interactive runs; GL-B only for reviewed hidden no-input fixtures.

The checkout output/p2-main-review at ef1cace is historical and dirty; it is not the current remote maintained line. Do not reset or export it. output/p2-sweep437-root and output/native-sweep437 remain worker recovery trees. This pin and the latest maintained remote supersede their stale pin instructions.
