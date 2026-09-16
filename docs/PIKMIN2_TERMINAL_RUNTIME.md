# Repeated-entry terminal and interruption regression

Scope: #114 / #132. This private fixture tests the existing bounded entrance and
Emergence two-floor host loop. It does not change production policy or provide
a full surface, mid-floor save, or native surface water support.

`scripts/pikmin2_terminal_fixture.cpp` restores the actual native checkpoint,
then injects either extinction or captain health zero. The normal
`pc_p2_cave_tick` detects the condition, writes the terminal handoff and exits42.
The fixture does not call the checkpoint writer. Healthy transfers use the
previous repeat fixture and its injected F6 event/confirmation.

`scripts/test_pikmin2_terminal_native.py` forks only the completed baseline's
identity and ledger into fresh directories. It preserves the original save.
Each terminal case relaunches the real host loop and asserts that no native
process starts: failed remains terminal, the active trip has no surviving
party/token, and committed treasure receipts are unchanged. The suspended
surface snapshot is historical metadata, not a revival source.

Two interruption cases raise a host exception after native handoff but before
host capture, or after the entry ledger commit but before pending-command
cleanup. A fresh invocation of the launcher reloads disk state, consumes the
preserved command exactly once, completes both native floors and returns to the
bounded entrance. These are injected exceptions in one test harness process,
not OS-killed host or power-loss tests.

## Reproduction

Run `py -3.12 -m scripts.test_pikmin2_terminal_native --help` for asset arguments.
Use a fresh output directory and a completed native repeat baseline. The private
build recipe and frozen source hashes are under
`output/p2-lifecycle-batch/terminal-runtime/commands.json` and
`source-hashes.json`; copied link inputs are recorded in
`output/p2-lifecycle-batch/settings-runtime/snapshot.json`.
They represent native156cbefa, not whatever production binary exists later.
The driver records both executable paths and SHA256 hashes before execution.

Focused checks:

```powershell
py -3.12 -m pytest tests/test_pikmin2_terminal_native.py -q
```

Native evidence belongs in `output/p2-lifecycle-batch/native-terminal-01`.
Its `result.json` records every case and each actual process directory; individual
native logs retain the restored party/health/Pokos and production failure result.
The baseline has19 survivors,10 Purple Pikmin, half captain health and480 Pokos.
Repeated deliveries must remain480 Pokos.

Validated result: all six cases passed across14 native processes. Surface
failures ended at revision9, cave failures at revision10; relaunch started zero
native processes for each. Both interrupted entries completed at revision12
with19 survivors, unchanged maturity/species, health0.5 and480 Pokos.
The broader lifecycle regression suite passed52 tests and15 subtests.
