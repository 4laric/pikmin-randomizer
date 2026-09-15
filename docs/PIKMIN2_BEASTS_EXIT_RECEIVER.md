# Guarded exit42 and restartable receiver (#307)

Owner: Codex using shared 4laric account. Save/handoff track, paired with floor3
assembly #306. New shared native exit-helper semantics require review.

`pc_p2_cave_exit_after_checkpoint` refuses to exit until the native checkpoint
has successfully closed and renamed its transfer file. Once complete, it flushes
output and exits with code42. Both the production cave tick and the handoff
fixture use this helper. The fixture verifies premature exit is refused and
retains its scripted, dialog-free interaction path; it does not automate the
player confirmation dialog. Ordinary fixture runs still exit0.

The runtime now requires exit42 in `--exit-handoff` mode. `receive_exit` takes
the original floor2 launch-state snapshot, run directory and Beasts ledger. It
checks successful exit42 metadata, the boundary token, a complete input hash
manifest, executable/log/transfer hashes and the bound transfer/party evidence
before atomically applying the boundary. Parsers consume the same captured
bytes that were verified. The receiver never launches a process or next floor.

Retry with the same original launch state and run after an uncertain commit.
The ledger's existing revision/token/replay checks provide idempotence; changed
payloads conflict. The launch-state copy is diagnostic request input, not a
second authoritative save. There remains one authoritative surface ledger.

These are local correlated records, not cryptographic attestation of gameplay.
The acceptance report is not signed and a caller can fabricate evidence. No
player-facing supervisor, native floor3 launch or complete campaign resume is
claimed. Floor3 remains durable and unlaunchable until its runtime is ready.

Native candidate: `e23986231d81b6f275d9fd900610c1bd82105b31`.
Private Release build and provenance-bound fixture link passed. Executable
SHA256 `fc7723b48e7396d97da2da24c4256ad0f3361dd33aeb62152a94b93ed2e8ff12`.

Fresh exit42 run:
`output/beasts307-final/runs/3f221cff89da49e595cb04840a51aa44`.
Log SHA256 `dba0f817c125908d95f1484d25dc91c29ec198a5eaefbb1003098a07f92f95f3`.
Actual native transfer was received, committed to floor3 and replayed unchanged
after reopening. Report: `output/beasts307-final/receiver.json`; original input:
`output/beasts307-final/launch-state.json`. The final byte-capturing receiver also
replayed this evidence unchanged. Initial floor1 boundary is declared engineering
input, as in the earlier fixtures.

Ordinary conversion regression passed with exit0 and ten Reds/ten Purples:
`output/beasts307-final/ordinary/8b4baf5ced5842a79de611307cdbe341`.
Log SHA256 `a1a47999b041af77056575f826aefb44e7207a0ea58a23e97ae10b368972615c`.
Both runs kept zero cargo/Pokos and unchanged repairs/input/executable hashes.
Focused receiver, transfer, transition, boundary, ledger, campaign, runtime and
party suites passed 76 tests and 143 subtests. Tests cover wrong exit codes,
changed evidence, wrong launch identity, missing input manifests, replay and
a log changing after its verified bytes have been captured.
