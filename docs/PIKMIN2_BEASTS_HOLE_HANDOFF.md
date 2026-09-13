# Opt-in native Beasts floor2 hole handoff (#302)

Owner: Codex using shared 4laric account. New shared cave semantics require
focused engine/save review before integration. The earlier review through #293
does not cover this extension.

The new `P2_BEASTS_ENTRY_1` profile accepts only source floor2 and a 64-hex
boundary token. It uses cargo-free preview readiness and requires a hole anchor.
The existing hole-coordinate validator is reused without changing source
floorId. Tutorial `P2_CAVE_ENTRY_1` retains its 32-hex token, treasure readiness,
floor1 hole and floor2 geyser behavior.

The native checkpoint guards still require a safe simulation phase, living
survivors, no conversion/burial/sprout state, captain walking near the exit, and
an available Pod. For Beasts, a successful checkpoint writes:

```
P2_BEASTS_TRANSFER_1
<64-hex token>
2 3 <health> <count>
<native species> <maturity>
...
```

The explicit edge is floor2 to floor3, never a return to the surface. Existing
tutorial transfer format remains unchanged. The codec rejects wrong identity,
edge, count, species/maturity and inconsistent living/failure state.

With `--exit-handoff`, the engineering fixture performs the real ten-conversion
and plucking sequence, verifies a remote hole interaction/checkpoint is rejected,
walks the captain to the marker at (-180,0,-180), and invokes the native
interaction and checkpoint guards without a confirmation dialog. It observes
the written transfer and compares it with the final native survivor snapshot.
The marker position is engineered, not a source-generated exit placement.

`checkpoint_payload` additionally requires matching boundary markers and the
ordered hole-interaction evidence, then returns the transfer party and witnessed
conversions for the existing atomic ledger. The actual fresh transfer advanced
the persisted checkpoint to floor3; reopening and exact replay were identical.
Initial floor1 handoff remains declared engineering input.

This is scripted native interaction, not manual-play acceptance. The fixture
explicitly writes the checkpoint then exits normally; the player supervisor's
exit-code42 flow and launch of the next floor are not exercised. Token/log
correlation is not cryptographic attestation. No floor3 launch, complete native
campaign resume or player-save support is claimed.

Native candidate: `1189db3a8ae757ddc12e5feb3a6dd7551a33cbce`.
Private Release build and provenance-bound fixture link passed. Executable:
`ccfb452c948c397d9d518e6d4faf26e6bd2b42d92f698b3f6923d0c8fa31209f`.
Evidence uses the preserved `output/beasts302-probe/` directory; this executable
and its inputs were not replaced after the run.

Hole run: `runs/0138ff8c71a94fe3aff78395de9077de`.
Log SHA256 `e0049a14707ee0050b2ab613d8a44ff8ac9a7cd17993ad056aae536dda97a2f7`.
Transfer SHA256 `be9b52e9af085c60f3a63658c0e3d69f5e68725548a986120da622cd3249833b`.
Ledger replay report: `output/beasts302-probe/replay.json`.

Ordinary conversion regression: `ordinary/ead44fef0dc7470796048673ce193450`.
Log SHA256 `83d2b3b3ab3a28edc3030257501231a8a3b62b57e6b9b1cb53908e8d898c8805`.
Both native runs passed, with ten Reds/ten Purples, zero cargo/Pokos and unchanged
repairs/input/executable hashes. Focused transfer, tutorial transition/campaign,
ledger, boundary, runtime and party suites passed 71 tests and 136 subtests.

Legacy `P2_CAVE_ENTRY_1` restoration also passed with health0.625 and mixed
leaf/bud/flower maturity: `legacy-entry/fc5529e6bd6d4cb4b4b2f6bf02211f14`.
Log SHA256 `de949c3e29be17c9c4fb6f5b735ed8d54eeefb789fe2a01f14657016f69552e3`.
That verifies the old loader in a cargo-free diagnostic, not a replay of the
entire tutorial cave campaign.

```powershell
$boundary = Get-Content -Raw output/beasts302-probe/boundary-token.txt
python -m experimental.pikmin2_beasts_floor2_runtime --root ../.. --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --exe output/beasts302-probe/linked/fixture.exe --output output/beasts302-repeat --global-purple-count 19 --boundary-token $boundary --exit-handoff
```
