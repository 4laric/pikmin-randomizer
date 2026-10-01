# Two-captain scene reentry acceptance (#1074)

Implementation owner: Codex through shared account 4laric.

This follow-up tests the scene lifecycle after the merged #1052 captain repair. Its independent fixture calls the real `GameCoreSection::exitStage`, queues `ONEPLAYER_NewPikiGame`, then lets `PlugPikiApp` reconstruct the section via `softReset`. It repeats the transition twice. The existing captain handoff stays immutable.

Each scene must contain two healthy captains and exactly 20 live generated Pikmin. Scripted controller input switches both ways, verifies the camera target/controller, and moves the selected captain. A transient actor capture survives until exit; teardown must unbind the adapter, clear captures and null the manager. Fresh-scene captures must reject the previous epoch. Fixture actor pointers are discarded before reconstruction.

The transition trigger and captures are injected. This does not verify native day-end save/relaunch, persisted captain health, natural cave transport or full campaign playability. Production code is unchanged. The new CMake registration was specifically delegated by the integration owner; the old lane retains its shared-file claim until maintained export.

## Reproduce

Build the `pikmin_ci_fixture_captain_reentry` CI artifact from the exact native PR92 commit. Verify `sha256.txt`, `BUILD_INFO.txt`, `build-dry-run.txt` and actual checkout tree against the producer commit before running locally.

Stage a fresh arena with `scripts/run_pikmin2_captain_reentry.py --root <root-worktree> --run-dir <canonical-root>/output/<new-run> --assets <legal-P1-assets> --treasure-model <local-room-model>`. The stager preserves the existing practice terrain, explicitly positions the landing and ship, and uses the current `overlay()` and its 20-Pikmin generator baseline. It never launches a runtime.

Run with the canonical guarded fixture runner, `--experimental-pikmin2-room`, explicit PASS marker `PASS P2_CAPTAIN_REENTRY`, and a 120-second wall-clock limit. Separate fresh `--force-captain-down` and `--force-inactive-down` runs inject zero HP and pause, then must exit86 through the next ordinary guard with the strict captain-down marker and no PASS. The fixture sets and records a centered960x540 window after settings load; the runner records exact input/executable hashes.

## Current evidence

Native candidate `c1dcec364390c65e6a5c92293d10d705d52d3e30` received independent source review, including both initialized captains guarded before movie/readiness/pause returns. Native fixture syntax check passed with the maintained MinGW PC include/define setup. Fresh positive and negative arenas are staged. CI artifact and runtime acceptance are pending; no reentry gameplay PASS is claimed.
