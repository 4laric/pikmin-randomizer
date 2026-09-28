# Dwarf Orange route, delivery and lifecycle acceptance (#440 / #461)

Integration owner: Codex through shared account4laric. Current candidate runtime PASS on root `bcbfa604de7280d2b3d0a9a236f6759ca40dc373`, native `ae00c510f7f1dca6c26f49c00a6f6f96e9e52fe2`. No production changes were required for wall damage. This supersedes the zero-damage gate blocker; the previous fixture placed workers inside the gate's work-detection spheres. Starting outside those spheres allows normal approach, contact, attack animations and damage.

## Evidence and pin

- Private fixture `output/p2-generated-route-fixture-v7/fixture.exe`, SHA256 `9f58f8caa4adc455a8eaa58679db2abda02cd0857c31dc9791fc010ead8cdde0`; builder provenance alongside it, native clean, Ninja freshness checks passed.
- Fresh session report: `output/qa-dwarf-orange/scene-reentry-08-route-v7/evidence.json`.
- Fresh run `d06601b925361548cf4c67059dc724f8041bdce1bc1ecc8f3b9dd8e7a571849f`; native exit0, GL-A result `output/gl-lanes/run-1789426116267787800/result.json`.
- Restart report: `output/qa-dwarf-orange/scene-reentry-08-route-v7/restart-evidence.json`; run `732eb50a0248f6557e4404504140589df03761580240aed4c110ea9257e03934`, exit0. Both log hashes are recorded in their reports.
- [Production combined pin](PIKMIN2_CACHE_IDENTITY_FIX_437.md) remains unchanged. These runtime tests use a replacement-main fixture linked from that build.

## Observed results

Initial live20-red squad, 960x540 window centered after settings, no immediate extinction. Native wall attack motion48 replaced the stalled walking motion2. Gate health fell from18, and waypoint92 opened at frame1417 without health/damage/route-flag writes. Source44 target1849273021 died naturally at frame1582. Thirteen live Pikmin were staged near the corpse; six carriers were observed on the actual route. The corpse moved970.138 units to the Onion at (-377.662,-37.722,2155.664). GoalItem delivery emitted check30 once.

The fixture then executed cleanupDayEnd, exitDayEnd, exitStage and normal section reconstruction. Scene generation1->2; the delivered actor correctly remained absent (registered0/bound0), the reward persisted, and six surviving Pikmin were stored. Process restart of the same session/executable preserved the reward and emitted zero new checks; the journal contains exactly one delivery credit. The restarted baseline's live actor also survived a second same-process reconstruction with registered1/bound1 and20 stored Pikmin. This is session reward restart evidence, not native campaign memory-card save/resume acceptance.

## Scope and remaining work

Staged interventions: starting squad; free-squad positions outside the gate work spheres; safe captain position; free squad around the generated Orange; free carriers beside the corpse; calls into the normal scene-transition lifecycle. Enemy health/state, wall damage, forced transport, reward calls and waypoint flags were not injected. This is natural engine behavior after staged setup, not full player-input sign-off.

The route is conditional on opening the stage1 soft gate at waypoint92 through ordinary Pikmin work. Do not turn this into an unconditional placement.route approval or silently omit the gate prerequisite. No roster admission or whole-lane completion count changes. Snow's natural chain, independent final review and full native campaign save/resume remain separate open work.
