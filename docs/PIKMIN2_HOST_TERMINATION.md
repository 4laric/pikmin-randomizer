# Native host-process termination recovery

Scope #114/#132. `scripts/test_pikmin2_host_kill_native.py` complements the
exception-based terminal regression with actual termination of its own Python
host process. All sessions are fresh copies of a completed native boundary;
player saves and the baseline remain untouched.

The child runs the real repeat launcher and native fixture. It writes a marker
containing its PID and the requested boundary, then blocks on its parent-owned
stdin. The parent validates the marker against the exact `Popen` object before
calling `kill()` and waiting. At either marker the native process has already
exited42, so this test leaves no running native child to clean up.

The two boundaries are native handoff before host commit, and committed entry
before pending-command unlink. A new Python process reloads the session,
finishes both native cave floors and returns to the bounded entrance. Assertions
require the original token to be consumed once, unchanged squad/maturity,
health and receipts, and exactly four native runs rather than replaying the
original entrance process.

This verifies host termination at controlled durable boundaries, not power loss,
interruption during an atomic file replacement, mid-floor saving, or physical
F6 input. Native transitions and treasure deliveries use the existing injected
repeat fixture. The immutable executable hash is recorded before testing.

Run `py -3.12 -m scripts.test_pikmin2_host_kill_native --help` for asset parameters.
Use the same imports and native-repeat-02 baseline as the terminal regression,
with a new output path. Evidence is under
`output/p2-lifecycle-batch/native-host-kill-01`: result.json, preserved-command.json,
host-before.log, host-resume.log and individual native run logs.

Both cases passed: the parent terminated its owned Python host with exit1;
interrupted revisions8 and9 both recovered to revision12. Each recovery used
four native processes with exits42,42,42,0 and retained19 survivors, their
species/maturity, captain health0.5 and480 Pokos. The focused lifecycle suite
passed40 tests and6 subtests. No production files or shared build outputs changed.

Focused safety checks:

```powershell
py -3.12 -m pytest tests/test_pikmin2_host_kill_native.py -q
```
