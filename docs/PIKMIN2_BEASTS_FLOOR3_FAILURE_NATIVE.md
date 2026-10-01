# Native floor 3 terminal handoff (#324)

Owner: Codex using shared 4laric account. Native base
`df041d0cf019b7f842f516df6d3258d101afa6c7`, candidate
`a9627bebf79445dfff0253992a1f72e0926d955a`, private worktree
`output/native-beasts-floor3-failure`. Companion host receiver/ledger work is
#323 / PR #326. The native branch publishes a terminal transfer and exits42;
the host owns the durable campaign commit and replay handling.

## Contract and guards

The failure file is exactly four LF-terminated lines:

```text
P2_BEASTS_FAILURE_1
<active floor3 boundary token, 64 lowercase hexadecimal characters>
3 0 0 0
<extinction or knockout>
```

The numeric line means source floor 3, destination 0, health 0, survivor count 0.
Knockout uses the existing native captain-health threshold `<=1` and takes
precedence if both conditions apply. Extinction requires no living Pikmin and no
living sprouts. Both normalize the terminal payload to empty crew/zero health;
captain knockout does not preserve the still-living field crew in the checkpoint.

The production tick detects the condition, calls the existing safe-time guard,
publishes through the existing temporary-file/rename path, then uses guarded
exit42. Successful floor4 descent, request and interaction remain disabled.
An active crew or a surviving sprout alone does not qualify as extinction.
Paused terminal requests are rejected. Existing tutorial/Beasts2 transfer
serialization is unchanged; the writer body is shared with the new terminal path.

The writer provides atomic publication through rename after flush/close. It does
not establish power-loss durability or commit the host ledger. Independent
focused native review found no blocker for the bounded handoff contract.

## Native evidence

Both cases used fresh stages from the validated #314/#317 floor3 checkpoint,
with restored ten Reds/ten Purples and health 1.0. The external fixture checks
actual profile/token and rejects active-party checkpoint/interact/exit first.
It snapshots the restored party, then **synthetically** kills all field Pikmin
or sets captain health to zero. The next production tick writes and exits42;
the fixture does not call the terminal writer or exit directly.

Both native cases passed. Each reported unchanged repairs/zero Pokos, exact
token/reason/payload, no remaining temporary file and unchanged inputs/executable.
The independent host receiver consumed both actual files in fresh private ledger
copies, reopened and replayed them identically, preserving source ledger,
suspended surface and existing history. Host evidence is recorded under
`output/p2-cave-lane/output/beasts323/{extinction,knockout}/receiver.json`.

| Native run under output/floor3-324/runs | Native log SHA256 | Transfer SHA256 |
|---|---|---|
| 54661a57438e4d658e319b00e545f22f (extinction) | `5bea7db8ef3a092b20d1712a386a8590ba9437e135978a1840425e2a006c2f1a` | `a96e1d46db76490632fd7ee223fa392cc652a83082fb17f8302b29fc738b7650` |
| c7902958903e4f8190083a7dad5f4d01 (knockout) | `6094275fbc424253886285c222a23fdf63ee6f15dc5cb04c090a4b696db2afd0` | `a50b75fe5368f7fc9f9c9ced3f006f54e95f2c32d572cb22894a16cc261fcd08` |

Terminal fixture executable SHA256:
`5767229bc44683ec20e294ff791e61ee99d625f40817a7c24061b928298f7a79`.
Provenance: `output/floor3-324/linked-final/provenance.json`.

The separate active-party regression completed all 12 grounded walking goals,
preserved its party and emitted no transfer:
`output/floor3-324/active/0b358184ffc84f8087c1aeffa158e56d`.
Its walking fixture SHA256 is
`20ca814908f2280c3d684af189e21f3f152b55002efeef51cfd778901443b447`.
Thus enabling terminal handoff did not enable successful floor4 descent.

## Build and reproduction

Private Release build completed 493 tasks with native JAudio ON, test hooks OFF,
IPO OFF. No parent/maintained source or build was changed. Compiled `-Werror`
policy probes passed terminal thresholds/precedence/sprouts/profile guards and
existing tutorial1/2, Beasts2/3 entry/header rejection cases.

12 Python tests and 50 subtests passed:

```powershell
python -m pytest -q tests/test_pikmin2_beasts_floor3_failure_runtime.py tests/test_pikmin2_beasts_floor3_entry.py tests/test_pikmin2_beasts_floor3_runtime.py tests/test_pikmin2_beasts_party_restore.py
```

From the private root worktree, generate the external fixture with
`experimental.pikmin2_beasts_floor3_failure_runtime.fixture(source, output)`;
`source` is `../native-beasts-floor3-failure/tools/preview_p2_room.cpp` and
`output` is a fresh `.cpp` path. Link using `scripts.build_pikmin2_fixture` with
source `../native-beasts-floor3-failure`, build `build-failure` beneath it,
the exact native candidate above, and a fresh root output directory.

Create a bound stage through #317's `stage_checkpoint`, then call
`arm(directory, "extinction")` or `arm(directory, "knockout")` and
`run(exe, directory)` from the failure runtime module. Arguments naming files
or directories are `Path` values. Arm adds its marker to the input hash set.
The acceptance record exposes policy, reason, token, returncode42, passed flag,
input hashes, executable hash, log hash and transfer hash for the independent
receiver. Fresh outputs are required; submitted evidence is never reused.

Tests reject wrong token/reason, live destination/nonzero health/count, malformed
or conflicting logs, altered pre-injection party, unexpected rewards and reused
or unbound stages. An initial build attempt used a mistyped expected commit and
was rejected before compilation; the successful provenance is `linked-final`.

Remaining: ordinary floor3 content/treasures/carrying, successful floor4 descent,
later-floor terminal coverage and complete cave return/resume. Synthetic terminal
injection demonstrates persistence plumbing, not natural combat or complete cave
gameplay acceptance.
