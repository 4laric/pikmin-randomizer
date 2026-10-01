# Surface runner adapter

`experimental.pikmin2_surface_runner.SurfaceRunner` runs the existing two-floor native cave against an already-created `SurfaceLedger`. The caller owns capture of a real surface snapshot and calls `enter_cave` first. Construct `NativeContent` with the same asset arguments as the standalone cave runner, then call `SurfaceRunner(ledger, content, exe).resume()`.

The adapter checks the content identity before launch, stages an isolated entry run using existing preparation/installers, and uses the ledger's persisted native token. Exit 42 is validated with the existing cave transition rules and committed through `SurfaceLedger.apply_floor`. Exit 0 pauses at the entry checkpoint; launch failures and other exits preserve it. A resumed active floor starts again from its entry, not the last mid-floor position. Failed parties remain failed and cannot accidentally restore the suspended living surface party.

A separate `native-runner-lease/runner.lock` prevents concurrent adapter launches without nesting the ledger's short mutation lock. Do not run the old standalone campaign writer in this save directory. `surface-ledger.json` remains the only authoritative checkpoint. `pending-handoff.json` is a command containing the original revision/token and validated handoff; an uncertain commit replays that same command idempotently before another process launches. Missing/corrupt/conflicting commands fail closed. A host interruption before this command is durable resumes the previous entry checkpoint and does not promise preservation of the uncommitted floor run.

Successful floor 2 completion reaches `return_ready`; by default the adapter calls `return_to_surface` and returns the resulting surface state. Pass `return_to_surface=False` to leave it ready for an external host. This is a host state transition only: it does not launch or render a native surface, restore actors/storage, or constitute a playable surface/cave/surface roundtrip.

The `content.stage(checkpoint, token, runs)` and `process(argv, cwd=..., stdout=..., stderr=...)` interfaces allow deterministic fake-process tests without game assets. Production staging uses `NativeContent`; tests verify launch failure, abnormal exit, pause/resume, floor progression, failure, deferred return, concurrent ownership, content mismatch, and interrupted handoff commit/replay.

Validation: `py -3.12 -m pytest tests/test_pikmin2_surface_runner.py tests/test_pikmin2_surface_ledger.py -q` (19 passed). Native playtesting and a real surface lifecycle remain separate gates under #112/#132.
