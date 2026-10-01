# Native SurfaceRunner integration driver

Run `py -3.12 -m scripts.test_pikmin2_surface_native --help` for asset arguments. Supply the lifecycle fixture built from `native/tools/preview_p2_room.cpp`, rather than a player executable. The output directory must not already exist: the driver creates private saves and staging runs and never opens a live campaign. On Windows, include `C:/msys64/mingw64/bin` in PATH for fixture dependencies.

The driver uses real `NativeContent`, `SurfaceRunner`, `SurfaceLedger`, and native processes. It checks floor 1's transfer, pauses twice through native floor 2 restoration, then accepts the final transfer and validates that party, health, maturity, and receipt values return once to the host surface snapshot. A separate native extinction run verifies the failed ledger cannot revive the suspended party. The final JSON report records process paths, actual exit codes, and both terminal ledgers. Every process has a timeout (default 120 seconds; maximum 300), and audio uses SDL's dummy driver.

The fixture deliberately injects one casualty, maturity changes, and Purple conversion and invokes real collection/transfer hooks. This validates native persistence integration, not combat, transport AI, or player controls. The surface destination is a host-only synthetic snapshot; no native surface is rendered or restored by this test. Closing or crashing before a durable boundary retains the previous entry, not a mid-floor world save.

Focused driver tests: `py -3.12 -m pytest tests/test_pikmin2_surface_native_driver.py tests/test_pikmin2_surface_runner.py -q`.
