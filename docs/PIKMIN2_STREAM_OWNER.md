# Development-stream owner activation (#864)

`workflow.development_streams` can bind exactly one live lane as a stream owner,
and `bind_owner` refuses stale generations, dead processes and double ownership.
What was missing is a supported way to *create* that owner lane without stealing
a blocked lane from another issue or hand-registering fabricated liveness.
`workflow.stream_owner` is that minimal fenced contract.

## Contract

```powershell
py -3.12 -m workflow.stream_owner --root <canonical> --request prepare.json
py -3.12 -m workflow.stream_owner --root <canonical> --request activate.json
```

`prepare.json`:

```json
{"operation": "prepare", "stream": "actors-assets", "worker_id": "muse-l71", "issue": 861}
```

`activate.json` (after the controller/coordinator has a live owner session):

```json
{"operation": "activate", "packet": {...}, "pid": 12345,
 "task_id": "manual:stream-owner-actors-assets"}
```

## Fences

- The worker must be a registered pool worker with the `implementation` role.
- The worker must have no open assignment; the controller parks/releases first.
- Any non-done lane of that worker must be `blocked` with a confirmed-dead
  process, no live/uninspectable lease and no live queued request. A live or
  unknown lane is never reused.
- The stream must exist with no owner and no ready batch.
- Maintained sources and both paired stream worktrees are observed with real
  Git; a moved maintained HEAD fails closed until an explicit `configure`
  refresh.
- `activate` registers an issue-backed owner lane with the real long-lived PID
  and binds it to the stream at that live generation. Replaying the same packet
  is idempotent; a different owner or a done lane is rejected.

## Non-goals

No source delivery, no canonical `Registry.integrate`, no maintained merge or
export, no maintained-consumer wakeup and no gameplay admission. A stream owner
runs one bounded stream-local candidate through `workflow.development_streams`;
`retire-ready` is abandon-only and frees the one-ready slot. Final merges,
exports and acceptance remain with the sole integrator.
