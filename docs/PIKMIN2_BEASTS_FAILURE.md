# Floor 3 terminal checkpoint receiver (#323)

Owner: Codex using shared 4laric account. Native counterpart: #324.
This opt-in receiver persists floor-3 extinction or captain knockout; successful
floor-4 descent, retreat and return to the surface remain unsupported.

The native protocol is exactly four lines:

```text
P2_BEASTS_FAILURE_1
<64 lowercase hex boundary token>
3 0 0 0
extinction
```

The last line is `extinction` or `knockout`. Numeric fields are source floor 3,
no destination (0), normalized health 0 and survivor count 0. Native knockout
takes precedence when both conditions hold. Extinction requires no living Pikmin
or sprouts; knockout follows the existing captain health threshold. This does
not claim natural combat testing: the native engineering fixture induces the
terminal condition and then uses the production checkpoint/exit path.

`receive_failure(ledger, launch_state, run_directory)` verifies the exit42 report,
captured stage inputs, original checkpoint, actual native entry party, boundary,
executable, transfer and ordered native failure diagnostics. It requires a
floor-3 profile and matching checkpoint identity. Evidence is hash-correlated,
not cryptographically authenticated. It does not launch a game process.

`apply_failure` is the lower-level API for already-verified transfer text. The
ledger's `fail_beasts_floor3` performs one locked atomic update: phase `failed`,
floor still 3, checkpoint revision 3, outer revision 4, token cleared, no survivors
and health 0. Suspended surface, receipts, conversion history and generation
context remain unchanged. The failure reason is bound into the event fingerprint;
the human-readable reason remains in the immutable run evidence. An identical
retry returns the same ledger; another reason for that boundary is a conflict.

The reference validator now accepts this terminal revision; old active floor-3
checkpoints are unchanged. Older code cannot read the new failed floor-3 state,
so consumers of these experimental saves need this update. No player-save
migration is performed. Terminal state cannot launch, descend, return or revive.
The suspended surface remains retained for future lifecycle implementation.

## Validation

The focused failure tests and broader receiver, transfer, boundary, reference,
party, generation, supervisor and surface suites pass: **91 tests, 172 subtests**.
Cases include exact reopen/replay, conflicting reason, wrong floor/token/party,
modified evidence, invalid process outcome, survivor/health normalization and
continued rejection of a successful floor-4 handoff. Independent host review found
no blocker and separately ran 24 tests/54 subtests.

Both actual #324 native runs returned **42** and were consumed by this receiver.
Each used a separate private copy of the actual #314 floor-3 ledger, whose source
bytes stayed unchanged. Each resulted in failed floor 3/outer revision 4, preserved
surface/receipts/conversion history, and reopened with a byte-identical replay.
The original profile uses the documented engineering reference audit and
placeholder content/campaign identities; this is not a player campaign save.

| Reason | Run under sibling `p2-beasts-floor3-track/output/floor3-324/runs` | Resulting ledger SHA256 |
|---|---|---|
| Extinction | `54661a57438e4d658e319b00e545f22f` | `0ded48b006b46175ebd873244ce99654a5e7ccb3dbcd31686a1b3c44877e1049` |
| Knockout | `c7902958903e4f8190083a7dad5f4d01` | `d6d9da2fa8df27560be439e06b853713b16b43bf738e30b5ff695abc56288ed6` |

Private receiver reports: `output/beasts323/extinction/receiver.json` and
`output/beasts323/knockout/receiver.json`. Native candidate:
`a9627bebf79445dfff0253992a1f72e0926d955a`; executable SHA256:
`5767229bc44683ec20e294ff791e61ee99d625f40817a7c24061b928298f7a79`.
The reports point to the complete native acceptance manifests and captured hashes.
Independent native review found no blocker within scope. Its writer retains
existing atomic publication; this does not add a power-loss durability guarantee.

The receiver is explicit, not yet wired into the player launcher or an automatic
floor-3 supervisor. Review #322/PR #325 integrated the preceding entry and asset
stacks; this terminal extension needs its own persistence integration review.
