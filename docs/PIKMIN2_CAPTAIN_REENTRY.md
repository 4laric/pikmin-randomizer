# Two-captain scene reentry acceptance (#1074)

Implementation owner: Codex through shared account 4laric.

This follow-up tests the scene lifecycle after the merged #1052 captain repair. Its independent fixture calls the real `GameCoreSection::exitStage`, queues `ONEPLAYER_NewPikiGame`, then lets `PlugPikiApp` reconstruct the section via `softReset`. It repeats the transition twice. The existing captain handoff stays immutable.

Each scene must contain two healthy captains and exactly 20 live generated Pikmin. Scripted controller input switches both ways, verifies the camera target/controller, and moves the selected captain. A transient actor capture survives until exit; teardown must unbind the adapter, clear captures and null the manager. Fresh-scene captures must reject the previous epoch. Fixture actor pointers are discarded before reconstruction.

The transition trigger and captures are injected. This does not verify native day-end save/relaunch, persisted captain health, natural cave transport or full campaign playability. Production code is unchanged. The new CMake registration was specifically delegated by the integration owner; the old lane retains its shared-file claim until maintained export.

## Reproduce

Build the `pikmin_ci_fixture_captain_reentry` CI artifact from the exact native PR92 commit. Verify `sha256.txt`, `BUILD_INFO.txt`, `build-dry-run.txt` and actual checkout tree against the producer commit before running locally.

Stage a fresh arena with `scripts/run_pikmin2_captain_reentry.py --root <root-worktree> --run-dir <canonical-root>/output/<new-run> --assets <legal-P1-assets> --treasure-model <local-room-model>`. The stager preserves the existing practice terrain, explicitly positions the landing and ship, and uses the current `overlay()` and its 20-Pikmin generator baseline. It never launches a runtime.

Run with the canonical guarded fixture runner, `--experimental-pikmin2-room`, explicit PASS marker `PASS P2_CAPTAIN_REENTRY`, and a 60-second wall-clock limit. Separate fresh `--force-captain-down` and `--force-inactive-down` runs inject zero HP and pause, then must exit86 through the next ordinary guard with the strict captain-down marker and no PASS. The fixture sets and records a centered960x540 window after settings load; the runner records exact input/executable hashes.

## Verified bounded result

Native `c1dcec364390c65e6a5c92293d10d705d52d3e30`, Windows CI run36846464710: source reviewed, build/tests passed, packaged no-work dry run and seven binary hashes verified. Actual CI merge checkout `aa64a0ca5817b3cdddd88dc27317f487e2bca38f` and candidate share tree `c01ee1e488ba876c7073ad5ddb111d2714a4de65`. Fixture SHA256: `8391a10b75756f21083f8c43eefd85a020c8f1bd203506a39bdb898faf48396c`. This is a remote CI build; the download directory is not represented as a local build.

Fresh pair02 passed in30.109 seconds: scenes0/1/2 each had20 live Pikmin, healthy captains, active slot0 initially, camera/controller selection in both directions, movement71.109/70.667/69.210 units, and stale-epoch rejection. Two actual exitStage/softReset reconstructions cleared the adapter and manager, then rebound fresh actors. Three non-black rendered captures were recorded; the final image visibly shows both captains and field count20. Startup recorded centered960x540 after settings. No captain-down or timeout occurred.

Fresh active and inactive negative02 runs each injected zero health and paused, then the next ordinary guard exited86 before the pause return, with no PASS (9.953/7.344 seconds). Each run used fresh RAM/process admission and60-second supervision; unrelated processes were untouched.

The reproducible local evidence index is `output/captain-reentry/evidence-final.json`; individual logs/inputs/results stay in `pair-02`, `negative-02`, and `inactive-negative-02`. The original unused01 staging and earlier superseded CI evidence remain separate. Registry acceptance and maintained integration/export belong to the integration lead. Native save persistence and natural cave travel remain unverified.
