# White swallowed poison — batch 2

Implementation owner: Codex through shared account `4laric`, issue [#395](https://github.com/4laric/pikmin-randomizer/issues/395). This increment adds poison after successful mouth consumption by explicitly configured native adult Bulborbs (`TEKI_Swallow`). Gas actors, poison panic and gas immunity remain unimplemented.

## Source contract

The retail GPVE01 revision 0 `enemy/parm/enemyParms.szs` contains `chappy/enemyparm.txt`. Its **proper** block is `fp01=30`, `fp02=750`. The poison amount is **750**, not the 300 header default. General parameters and proper parameters repeat identifiers; flattening them is incorrect.

- Archive SHA256: `3618455a8561f1e1b0aad0253a75a69fae1fe3a47160d1c1efa294b0ddeb2a84`.
- Member SHA256: `12abc387cf05d4bf2c53f453694a268bec4d00e4fee33b03626d0d071b0f80c4`.
- Read-only source revision: `632af93787b9c95b63f0c13be32b161375ce3a96`.

The source `eatWhitePikminCallBack` follows a successful mouth kill. Its `addDamage(damage, 0)` queues damage without adding a flick/melee-hit count. The native adapter captures living White identity before the existing kill, consumes a pending event once, and queues HP damage only after successful consumption. It never dereferences the consumed victim. Invulnerability blocks damage; actor allocation clears registry bindings and pending events before slot reuse so reused addresses do not inherit authorization.

## Preparing a private run

First prepare a White preview with its existing generator-bound Ivory profile. Then extract a separate poison profile from the user's disc:

```powershell
python -m experimental.pikmin2_white_poison --iso output/pikmin2-runtime/pikmin2-source-test.iso --output output/my-white-poison --predator-generators 436207616
```

The IDs are the actual native `Generator::_70` values, not assumed record ordinals. Choose IDs from the intended arena's runtime binding diagnostics. The example is illustrative; a configured ID must resolve to an actual `TEKI_Swallow`. Copy the resulting `p2-white-poison.txt` into that private run directory beside `p2-white.txt`, retaining `white-poison.json` as provenance. The native loader rejects missing, duplicate or wrong-family bindings. With no poison profile, this behavior stays disabled.

The extractor validates the retail proper block and writes the archive, member and config hashes. It rejects invalid, signed, duplicate or excessive generator IDs and never exports disc content into the repository. Source tests are in `tests/test_pikmin2_white_poison.py`; native event-policy tests are in `native/tools/test_p2_white_poison_policy.cpp`.

## Acceptance boundary

This uses the existing native adult model, swallowing animation and damage/death strategy. It does not claim a port of the P2 adult model, gas system, poison visual effects, campaign integration or controller sign-off.

## Native validation

Private native branch HEAD `f2274235d0568c84f0cb455cf16c7ca82e7ab4aa` is clean and includes the reproducible fixture `tools/preview_p2_white_poison.inc`. Release/JAudio build `output/native-white-poison-build2` passed, with a no-work Ninja dry run. Its production executable SHA256 is `f9e90d7f26dd167ca3d8020a6d8c83b1899989d53dde3d971bc0582f1fbf2742`.

`output/white-poison-fixture-04/provenance.json` records a built standalone fixture against that full HEAD. Fixture SHA256: `82bc1a1e6b969e2c46ed9f33435ec5f77d422a3a43045db396939f4009fa9352`. The native run exited successfully and printed `PASS p2 White poison` in `output/white-poison-run-01/white-poison-native-04.log`, SHA256 `f0d2bb4e3d35c3427933c6c9cc7bd0519d853cb54da360596455450e4e2d929f`.

The fixture injects mouth attachment and the ACTION_1 event, then exercises the actual native swallowing action and successful kill callbacks. Two Whites queue 1,500 damage; a Red queues none. It checks a dead victim, an unbound enemy, duplicate finish, unchanged flick count, invulnerability, lethal 750 damage and normal corpse creation. Nonlethal HP application calls the native `makeDamaged()` explicitly; the subsequent death/corpse strategy advances normally. This is scripted callback/lifecycle evidence, not natural predator capture or controller play. Portable policy tests additionally cover failed-consumption cancellation and address reuse.

Earlier attempts were not passes: incorrect byte order prevented the first arena binding, one process lacked runtime DLLs, and one fixture snapshot was rejected for an abbreviated expected commit. The successful run uses the full pinned commit and runtime generator ID `436207616` (stage record 26).
