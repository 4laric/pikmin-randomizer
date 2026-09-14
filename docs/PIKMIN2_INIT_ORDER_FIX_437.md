# Generated bank initialization fix (#437 / QA-45-437-01)

Owner Codex through shared account 4laric. Root 3bacebc29da8fc19955a416e112f5f8f7a0d9550; clean native 08bae2517b77ed809a 75d085afb83ee532f7b92a. Includes worker a2f4b9dc (Orange post-reset setup) plus 08bae251 (Snow at the same point). Native origin not pushed.

Cause: TekiMgr stage reset clears generated bank state; initStage births bound actors before GameCoreSection::finalSetup initializes the bank. Generated bind aborts when its mode flag is still false. Bank setup now runs after startStage reset and before generator births. The existing finalSetup scan remains, so Snow emits its ready marker once at birth and again after the late scan; this is not evidence of two actors.

Build PASS: output/native-nectar-qol-build, Ninja/MinGW Release, JAudio/IPO ON; final ninja dry run no work to do. Exact export parity 1996 files. Immutable executable C:\Users\alari\pikmin-randomizer\output\p2-integration-08bae251\nectar.exe; SHA256 4a199b540465a084799f0e63603ff74fea39b3e0ae6d9bdfff100fcbcc84d1bc. Pin: C:/Users/alari/pikmin-randomizer/output/p2-integration-08bae251/pin.json.

Fresh startup replay uses the failed QA manifest in a NEW session, verified 121-entry Snow content, the normal candidate launcher, GL-A lease, and a 75-second job timeout. No combat input or forced damage. Prepared report: output/p2-init-order-snow-smoke/prepared.json. Native log: output/p2-init-order-snow-smoke/session/runs/e0c66436ec4473357fd50e3d26192bec98cfb3722dc3c2b1342300adfba391b8/native.log.

Observed: centred 960x540 startup log; P2_ENEMY_READY species=YellowKochappy generator=1849273021; P2_SNOW_GENERATED_READY dwarfs=1; P2_SNOW_DRAW corpse=0; PIKMIN_GAMEPLAY_READY; PIKMIN_FOH_READY day=2 field_red=20; START_COLOR_READY and START_READY; sustained approximately 30FPS. Startup regression PASS for this Snow repro. Timeout is deliberate bounded smoke cleanup, not a normal game completion or natural-acceptance PASS.

Remaining: natural combat/death/physical delivery/revisit/restart, input-driving fixture, and independent QA on this replacement pin. Orange source44 startup was not tested by this Snow run. The original five-finding QA report remains unchanged as historical failed-pin evidence. No identity is admitted.

Completed bounded cleanup: GL runner exit124/timeout at75seconds, process tree terminated and GL-A lease released. Machine-readable startup evidence: output/p2-init-order-snow-smoke/startup-evidence.json.
