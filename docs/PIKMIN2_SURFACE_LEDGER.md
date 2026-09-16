# Surface/cave handoff ledger (#132, #112)

Codex implementation owner through shared account 4laric. Scope recorded in [#132](https://github.com/4laric/pikmin-randomizer/issues/132#issuecomment-5648140208). This batch adds host-side infrastructure, not a playable native surface or completed Emergence round trip.

`experimental.pikmin2_surface_ledger.SurfaceLedger` persists one authoritative `surface-ledger.json`. It stores an explicit surface destination and squad, the suspended surface during a cave visit, the existing schema-1 two-floor cave checkpoint, and committed handoff fingerprints. Squad, health and treasure receipts move together in atomic file replacements. The existing standalone campaign runner, its saves, native protocol and launchers are unchanged.

## States and integration contract

| Phase | Authoritative playable state | Next permitted operation |
| --- | --- | --- |
| `surface` | Caller-supplied surface snapshot | Enter a new cave trip |
| `cave` | Nested cave checkpoint | Stage native entry, then apply a validated floor transfer |
| `return_ready` | Completed cave result; surface still suspended | Commit return |
| `failed` | Failed cave result, no living cave squad | Explicit future failure policy; no automatic restoration |

The surface snapshot contains `region`, `day`, `time`, `position`, `squad`, `health`, and `receipts`. It covers only the active party/current captain and destination. **It does not contain a native world snapshot, stored Pikmin, sprouts, generators, enemies, equipment, two captains or campaign story state.** The future surface implementation must preserve those systems before using this as a playable roundtrip. Suspended surface data must never be launched when the ledger phase is `cave`, `return_ready` or `failed`.

Construct the ledger with a separate local directory, the existing cave content fingerprint and a stable caller-owned 32-hex campaign ID. Create it from an explicit validated surface snapshot. Call `enter_cave(expected_revision, trip_id)` with a new stable 32-hex trip ID. The returned `trip.checkpoint` is directly compatible with `pikmin2_campaign.entry_text`; use the returned persisted `trip.token` rather than creating a separate token.

After native exit42, call `apply_floor(expected_revision, token, transfer_text, runtime_receipts, allowed_receipts)`. It uses the existing cave `transition` validator, preserving its species, population, content and receipt restrictions. Floor1 success creates a new persisted token for floor2. Floor2 success enters `return_ready`; `return_to_surface(expected_revision, trip_id)` then replaces the suspended party/health/receipts while retaining its region, position, day and clock. Retaining the clock is this host snapshot contract, not a claim that complete source surface-time behavior has been ported.

Do not run the standalone cave writer alongside this ledger or mirror it to a second authoritative checkpoint file. Future launcher integration should prepare disposable native runs from the nested checkpoint and submit handoffs back here. The current module deliberately has no CLI that pretends to launch an absent surface scene.

## Recovery and exactly-once behavior

- An OS session lock covers each read/mutation. Mutations also compare the caller's expected revision to reject stale work.
- Reuse the exact original revision and payload when retrying an uncertain operation. An identical committed event returns the latest ledger without applying its effect again; it may now be in a later phase. Callers must inspect that returned phase.
- Reusing a trip/token ID with a changed payload is a conflict. Old completed-trip replay cannot re-enter the cave or replace a newer party.
- All changes use the existing flush/fsync plus atomic replacement helper. A crash before replacement leaves the previous whole ledger authoritative; after replacement, replay finds the committed fingerprint.
- Corrupt, duplicate-field, wrong-content/campaign and missing-ledger sessions fail rather than silently resetting. Replaying initial creation cannot erase progress.
- Failed cave receipts stay within the failed trip; they are not credited back to the suspended surface. A future explicit failure/abandonment policy must decide their fate.
- Receipts are stable identifiers with values, not increments. Return does not add the cave total onto an already credited balance. Existing schema1 limits still apply: four currently supported species, at most100 active Pikmin and1024 receipts. The ledger reserves enough of its4096 event slots to finish a started two-floor trip.

## Validation and remaining gates

Run `py -3.12 -m pytest tests/test_pikmin2_surface_ledger.py tests/test_pikmin2_campaign.py -q` from the repository root.

The focused suite passes16 tests and4 subtests. Tests cover mixed-maturity survivors and Purple conversion, preserved surface destination, exactly-once treasure return, repeated creation/entry/floor/return, fresh floor tokens, later visits, interrupted entry/floor/return replacement, OS locking, conflicting identity/revision, malformed native rewards, missing/corrupt saves and non-replenishing failure.

These are real host persistence operations with synthetic native handoff text. They do not test physical surface entry/return, a native world reload or natural gameplay. Native surface snapshotting/restoration, contextual cave entrance, equipment/storage/story persistence and a player-driven round trip remain open under #112/#132.
