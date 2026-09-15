# Cave navigation diagnostics proposal (#193)

Isolated patch only; no production source or fixed QA bundle changes. Generate with `python -m experimental.pikmin2_cave_nav_diagnostics --source native/pc_port/pc_p2_cave.cpp --output <new private directory>`. The output includes a unified patch, modified translation unit, portable rate-limit header and source hash. Root must review/apply after concurrent snapshots finish, build and create a separately versioned QA bundle before runtime use.

Enable only with PIKMIN_CAVE_NAV_DIAGNOSTICS=1. All other values/default disable logging. At most120 rows per stage, separated by at least2000ms of SDL monotonic ticks, including wrap-safe arithmetic. Stage setup resets count, draw counter and marker-log latch. Existing checkpoint/interaction/reward/input bodies remain unchanged. The diagnostic reads state and prints; it never moves actors, presses keys or writes a ledger.

Rows provide captain XYZ/world heading radians; anchor XYZ, signed dx/dz, horizontal/vertical separation, radius; inside-anchor, captain Walk state, safeTime, pause/UI/movie/day-end/completed/Pod flags; interaction eligibility; model/fallback/none path and cumulative draw invocations. interaction_eligible mirrors spatial interaction preconditions, not final checkpoint acceptance: survivors in combat/flowers/sprouts and confirmation can still prevent transfer. Draw count proves invocation, not screen visibility, clipping, occlusion or GPU output.

## Fixed manual-qa-02 audit

All9 floor2 runs have P2_CAVE_VISUAL_1 geyser and loaded169-vertex transition model; each log includes P2_CAVE_MARKER_DRAW. The model path in pc_p2_cave_draw_transition returns before cyan-ring code. Therefore looking specifically for cyan is the wrong expectation for this bundle. Model visibility remains unconfirmed.

Anchor is(-550,25,520), radius45. Spatial activation requires horizontal distance<=45 and vertical difference<=40 (captain Y between-15 and65 inclusive), plus safe timing and walking. Anchor height is a configuration value, not proof of rendered-model placement or terrain accessibility. Fixed ledger revision2 SHA256b0572e68b842699e3ddc64d254bdcb05121ae16d240c9cedc821ba4779c3500f. Config/log hashes and per-run evidence are in output/p2-cave-nav193/fixed-bundle-audit.json. No QA file was written.

## Next independent QA handoff

Use a NEW versioned diagnostic build with executable SHA/native commit recorded, preserving manual-qa-02 and revision2 ledger. On floor2, use nav rows to approach X=-550,Z=520 while keeping Y near25. Horizontal<=45, vertical<=40, walk=1 and safe=1 identify the spatial interaction region. Expect the imported geyser model, not a cyan ring. Record camera view and draw-count behavior there; press existing F6 only as ordinary authorized QA input, then test boundary transfer/reentry/restart gates separately. This patch does not claim those gates completed.

Verification: two focused tests pass, including compiled C++ rate-limit/reset/wrap assertions and byte-identical checkpoint function comparison. The isolated modified cave translation unit compiles successfully with frozen e704b268 headers; this is a compilation check, not a fresh production build or runtime visibility measurement. No shared build or source export performed.

## Shared integration

Root integrated the opt-in diagnostic into native after review. Full build passed (output/p2-team-batch1/cave-navigation-build.log), followed by no-work dry run. The patch generator now normalizes CRLF and writes exact bytes; its unit test uses an isolated source sample so it stays valid after production integration. A separate QA bundle and runtime navigation acceptance remain pending; manual-qa-02 is unchanged. The shared exporter accepts explicit source/destination paths so root integration does not write into a Kimi checkout.
