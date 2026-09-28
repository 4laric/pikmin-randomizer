# Pre-receipt floor 3 cargo terminal lifecycle (#356)

Owner: Codex using shared 4laric account. An explicit diagnostic opt-in now
allows the existing floor3 extinction/knockout checkpoint while one source cargo
actor is installed and no Pokos have been credited. Successful descent remains
disabled. This does not authorize a campaign failure, reward or save mutation.

Root base is frozen #355, `d10d34818cd6ce289f3639e137bd63c17a9fd147`.
Private native candidate `d69580fa7f5441286e82b065b3e36d2bc5066cf4` is based on
frozen #334 `9977856e34d54891c30260ca1d748d01e04f6e31`, in
`output/native-beasts-floor3-cargo-terminal`. Its private `build-terminal`
completed all 493 steps with native JAudio on, test hooks off and IPO off.
An initial configure used stale option names and failed to link; the corrected
configuration and full build passed. No shared native checkout/build was changed.
Only the changed cave source, new readiness header and policy test are exported.

## Narrow readiness contract

The new optional file is `p2-beasts-cargo-terminal.txt`:

```text
P2_BEASTS_CARGO_TERMINAL_1
<same 64-character token as the explicit floor3 entry>
```

Setup rejects mismatched tokens/profiles, missing Pod/preview, cargo count other
than one, or nonzero Pokos. Readiness requires Beasts floor3, this opt-in,
configured single cargo, ready Pod/preview and zero Pokos. After delivery raises
Pokos above zero, cargo terminal readiness becomes inactive. A fresh opt-in
launch with a credited ledger is rejected. Existing tutorial readiness and
Beasts cargo-free readiness are unchanged; floor4 remains checkpoint-disabled.
Existing safe-time checks, failure reason precedence and all descent guards
remain unchanged after the readiness gate.

The native transfer remains four LF-ended lines: `P2_BEASTS_FAILURE_1`, token,
`3 0 0 0`, and `extinction` or `knockout`. It represents an empty terminal party
and production exit42. No cargo receipt or campaign reward is encoded.

`experimental.pikmin2_beasts_cargo_terminal.enable(stage, reason,
empty_ledger=False)` augments a fresh #343 diagnostic haul stage. The new
acceptance policy is **P2_BEASTS_CARGO_FAILURE_DIAGNOSTIC_1**. Its full input,
executable, log and transfer hashes remain separate from host campaign evidence.
The previous cargo-free failure receiver is intentionally unchanged and does
not support this policy. A read-only invocation with actual diagnostic evidence
confirmed it rejects the policy before accessing any ledger. Tests also confirm
the old cargo-free runtime validator rejects these cargo logs. Do not feed the
raw transfer alone to a campaign mutation API.

## Actual native evidence

All local paths below are beneath
`output/p2-beasts-floor3-track/output/cargo-terminal356`.
The terminal fixture executable `linked/fixture.exe` has SHA-256
`904ad4fcfa6b6edd501a095a1142042c1f89bb10e6e7227f364fea14447f36d8`.
It uses the real #343 source model, placement, one cargo generator 63000 and
value/weight/slots 150/12/20. The fixture verifies healthy descent rejection,
captures the restored 20-Red party, then synthetically kills the party or sets
captain health to zero. A paused checkpoint is rejected; the next production
tick publishes the exact terminal transfer and exits42.

| Case | Run beneath `runs` | Native log SHA-256 |
|---|---|---|
| Extinction, absent economy | `6fe375c2f5154a868072fa2541af4df6` | `0b357789e2dc21e17e73cbcfa7d9197ecc65d9ea138cd3e5286f2d049c607261` |
| Knockout, empty economy | `8ff6d3c960a341d9a9a83db4bd327ed3` | `5b1f6762f040c7d8bb40e0664c26fa7d7706694e13b376a7c45f9c3cffeaf732` |

Both passed. Extinction left the economy absent; knockout preserved the exact
empty P2_ECONOMY_1 ledger. Neither created a treasure receipt, changed repairs,
or left temporary transfer/economy state. Transfer SHA-256 values respectively:
`1fc099d0846c785803b485f355c3b5d13042cef02b943811f5bc1f058cfe301d` and
`fb2f0770563c9b49a44c11704b38955c784015f420374a41f4c63dc61afc4dae`.
`verification.json` collects both complete acceptance records.

The separate hauling fixture `haul-linked/fixture.exe` is
`73c4c81fce9081f434ebb9dd39eb343a0d925d20d3cf8abf707d526303f2a194`.
Opt-in healthy run `haul-runs/84e4ffc893db4f849fdff2f3d28d6730` passed ordinary
transport across both actual seams, 150-Poko receipt, duplicate rejection and
native P2Economy reopen. Log SHA-256:
`f243519a5b72c8525b13b559a224a609fc8a8b36f4a36ee5da8ef12adb02d2de`.
After receipt, with normal checkpoint timing verified, the fixture briefly set
captain health to zero and confirmed checkpoint/exit rejection, then restored
health. This proves postreceipt lifecycle is inactive, not merely that a healthy
party cannot descend. `haul-verification.json` records this additional check.

The fresh-process no-marker replay is recorded separately in
`replay-verification.json` and `replay-runs/d394bb8a72e445d1ab948ab53bf984a7`.
It uses the actual first hauling ledger and unchanged ordinary cargo semantics;
it does not relax the opt-in gate to accept a previously credited ledger.
It passed with both receipt attempts `new=0`, total 150 and unchanged ledger
SHA-256 `530496e73e288c54695be73e05568441b8707acf345d020d8dc0e5a22b11b344`.
Replay log SHA-256 is
`a22feef791cbfd04819b1e177be2d9faf52d53d6bb37aafe16250b4bb95022fc`.

Thirteen focused Python tests and 65 subtests passed. Compiled tests passed the
new readiness matrix, marker/token/profile rejection, existing entry profiles
and floor3 failure policy. Independent read-only lifecycle review found no
blocker: legacy branches and safe-time/failure/descent behavior remain intact.

Reproduce with #343 `stage`, then `enable`, generate `fixture` and link through
`scripts.build_pikmin2_fixture` against this exact native candidate/private build.
Call `run(exe, stage)` for either terminal reason. For healthy hauling, use
`enable(stage)` without a reason, generate `haul_fixture`, and use the existing
haul runner. All stages and outputs must be fresh.

Remaining: postreceipt terminal semantics, campaign-authorized receipts/failure
handling, actual combat extinction/knockout, other floor3 actors/treasures and
successful descent. The probe's terminal conditions and carrier assignments are
scripted; no full cave gameplay or campaign resume acceptance is claimed.
