# Opt-in Beasts checkpoint persistence (#292)

Owner: Codex using shared 4laric account. `BeastsSurfaceLedger` adds host-side
persistence to the Beasts reference adapter. It uses the existing
`surface-ledger.json`, `SessionLock` and atomic replacement code. There is no
separate cave checkpoint file or concurrent second writer.

Create a fresh surface session, then call `enter_beasts`. The entry transaction
stores a schema2 Beasts trip and its profile-bound checkpoint while preserving
the entire suspended surface snapshot. Each `apply_beasts_floor` transaction
updates the checkpoint, boundary token, receipts, conversion history and replay
fingerprint together. Destination generation context and per-flower budgets
are persisted inside the floor2 checkpoint. Floor3 is durable but the reference
adapter refuses its launch; returning to the surface is also unsupported.

The schema1 tutorial implementation retains its validator and behavior. Its
only refactor is routing validation through a protected method so the opt-in
writer can validate schema2. The tutorial writer rejects schema2; the Beasts
writer rejects active or previously used tutorial sessions. There is no save
migration. A freshly created schema1 surface envelope has not begun either
cave protocol and may enter Beasts once.

Reopen using the same content, campaign and Beasts profile. A changed profile,
wrong campaign, wrong token or inconsistent history fails validation. Every
mutation checks the expected revision under the session lock. Exact request
replay returns the latest state, including after subsequent boundaries, while
changed payloads conflict. Failure remains terminal after reopening; no method
repopulates the party or restores the suspended surface as an active session.

This is an opt-in host API, not a native campaign launcher. Its caller supplies
boundary data and the global population snapshot; this layer does not make
those inputs authentic. The diagnostic bridge may supply fixture evidence,
but native token attestation, individual identity, actual exit interaction and
authoritative population collection remain open. Schema2 remains experimental
and should not be used for player saves. Focused save/engine review is required
before shared integration.

Validation: 59 tests and 61 subtests across the Beasts ledger, tutorial ledger,
surface runner/loop/reentry, campaign, checkpoint/bridge and party suites.
Coverage includes restart at boundaries, exact replay, conflicting/stale
requests, failure before atomic replacement, an exception after successful
commit, terminal death, wrong writer/profile/campaign, lock contention and
rejection of tutorial migration. Failed requests preserve existing file bytes.

Local diagnostic-backed persistence evidence:
`output/beasts292-ledger/c8f98dd7cab34c4ebc821f710f74d9aa/replay.json`.
Separate ordinary/refund directories each contain one authoritative ledger.
Both persist floor3 at ledger revision3, reopen identically, reject floor3
launch, preserve the suspended surface and replay without duplicate changes.
The floor1 handoff is a declared engineering input; the floor2 outgoing party
and conversions come from the validated #287 native logs. No new native run
was performed for this host-only batch.

Ordinary source log SHA256:
`1c7ef316998ac5f7c2804e4c8f758e99bf1f82b139e7b4cda1f2856d9d3172b9`.
Refund source log SHA256:
`649a2f3b3e0b1ebe434d1defbbc39314a4f0f56f5a670cf02cf991a31b7a3857`.
