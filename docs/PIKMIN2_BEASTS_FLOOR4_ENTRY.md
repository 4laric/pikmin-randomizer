# Native floor 4 diagnostic entry (#334)

Owner: Codex using shared 4laric account. This candidate adds a distinct native
Beasts floor 4 profile to the frozen #330 assembly. It restores the declared
party and verifies native walking across both room/corridor seams. The token is
caller-declared diagnostic identity; no host adapter authorizes floor 4 campaign
progress. Existing ledger files are not read or changed by this entry helper.

The native candidate is `9977856e34d54891c30260ca1d748d01e04f6e31`, based on
`a9627bebf79445dfff0253992a1f72e0926d955a`, in the private native worktree
`output/native-beasts-floor4-entry`. Only the three changed native files are
exported into `engine`. Its private Release build (`build-entry`, IPO off)
completed all 493 build steps. Parent/shared builds remain untouched.

## Contract

`experimental.pikmin2_beasts_floor4_entry.stage_profile(assets, assembly, purple,
pod, output, party, token)` accepts Path arguments, a healthy 20-member Red/Purple
party and exactly 64 lowercase hexadecimal token characters. It creates a fresh
private stage. `p2-cave-entry.txt` starts with:

```text
P2_BEASTS_FLOOR4_ENTRY_1
<diagnostic token>
4 <health> 20
```

Twenty species/maturity rows follow. Native Red is 1 and Purple is 3; maturity
is 0 through 2. `p2-floor4-boundary.txt` carries the same token for the external
survey fixture. Survey metadata declares `native_profile=forest_1`,
`party_restore_protocol_floor=4`, `token_source=caller_declared_diagnostic`,
`descent_enabled=false`, `failure_checkpoint_enabled=false`, `campaign_entry=false`
and `native_ready=false`. All input bytes and the executable are checked before
and after execution.

The profile rejects exit anchors, request/interact descent and every checkpoint
attempt. Floor 4 extinction and captain knockout persistence are also disabled.
It cannot write a successful floor 5 transfer or reach the completion exit42.
The native getters must return floorId4, Beasts mode and the supplied token.
Legacy tutorial floors 1/2, Beasts floor2 and floor3 terminal behavior remain.

## Runtime evidence

Artifacts are local beneath `output/p2-beasts-floor3-track/output/floor4-334`.
`linked/fixture.exe` SHA-256:
`bff23e3cff440e120ecf37230fa34a8d7c9d4d679d649bd5ee0cb36719ff6f1a`.
The provenance builder linked an external floor4 survey against the clean
candidate build and verified native source/build inputs stayed unchanged.

Both runs restored ten Red and ten Purple, mixed leaf/bud/flower maturity,
health 0.625. Both read back native floor4/Beasts/token, rejected active descent,
checkpoint and completion, walked all 12 goals with native floor separation
under five units, retained party/health/repair state, produced no transfer or
reward, and returned zero:

| Diagnostic token | Run directory beneath `runs` | Native log SHA-256 |
|---|---|---|
| `d` repeated 64 | `ae4803c6bf324dc9a324139013b7b4ea` | `798b62716962d4755d7aa412ce8fb7e759c82ef1aedcbc9d5c02fcfd4c96a352` |
| `e` repeated 64 | `f66746a306ab4e2caf269f2420148b27` | `201683cf3f3c17f035ec06952903413489ced3dbd157c9742ab870e2cc8e2b43` |

`verification.json` collects acceptance records. The source assembly remains
the frozen #330 `output/floor4-330/first` package: engineering placement, source
door transforms and directed routes, capped unused doors, no actor proxies.

A separately linked floor3 knockout regression on this same new native build
passed and exited42 with the original floor3 failure protocol. It used a fresh
stage from the copied #317 checkpoint; no parent ledger was changed. Evidence:
`regression.json`, `regression-runs/162e319affe94c44a1bbed9851bba3bb`, executable
`ea9f1c0bcc6512bc3c7edde65af2a3f89a8cf7f33b4369281228f4f161ed566a`.

Fourteen focused Python tests and 47 subtests passed, including wrong-floor and
token evidence rejection. Compiled entry-profile tests passed tutorial1/2,
Beasts2/3/4 and malformed floor/token combinations. The compiled floor3 terminal
policy passed active/sprout, extinction, knockout precedence and profile guards.
Independent read-only native review found no blocker in profile selection,
anchor/request/interact/checkpoint guards or preserved legacy branches.

## Reproduction and integration

Generate the external fixture with `pikmin2_beasts_floor4.fixture` using the new
native `tools/preview_p2_room.cpp`. Build it through
`python -m scripts.build_pikmin2_fixture` with the native source, `build-entry`,
exact candidate SHA and fresh output. Call `stage_profile`, then
`pikmin2_beasts_floor3_runtime.run(exe, stage)` with absolute Path values.

The parallel #333/PR335 floor5 engineering runner changes overlap the shared
`run` dispatch: retain its unbound floor5 marker remapping and token rejection;
retain this candidate's bound floor4 profile guard and `native_floor` validation.
Issue dispatch is 334 for bound floor4, 330 for unbound floor4 and 333 for unbound
floor5. Floor3 defaults stay unchanged. No automatic merge of that parallel
candidate is included here.

Remaining: source-bound floor4 host authorization, ordinary actors and treasure
carry/delivery, terminal persistence, floor5 descent, and complete cave return.
This milestone establishes native entry and traversal of engineering geometry,
not a playable floor4 campaign or full cave gameplay acceptance.
