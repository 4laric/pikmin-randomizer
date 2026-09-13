# Token-bound native Beasts floor 3 entry (#317)

Owner: Codex using shared 4laric account. Root base: frozen #315,
`8ce3fe9e1bd6dc5e15723ab0625cf62858927587`. Native base:
`e23986231d81b6f275d9fd900610c1bd82105b31`; native candidate:
`df041d0cf019b7f842f516df6d3258d101afa6c7`, private worktree
`output/native-beasts-floor3-entry` and its own `build-floor3`.

The new native profile restores a validated checkpoint into actual Beasts floor 3
state. It no longer uses the engineering tutorial floor 2 tag. The distinct wire
header is:

```text
P2_BEASTS_FLOOR3_ENTRY_1
<64 lowercase hexadecimal boundary token>
3 <health fraction> <survivor count>
<native species index> <maturity>
...
```

Tutorial `P2_CAVE_ENTRY_1` remains limited to floors 1/2 and 32-character tokens.
Existing `P2_BEASTS_ENTRY_1` remains floor 2 only with a 64-character token and
required hole anchor. Native parsing rejects wrong profile/floor/token mixtures.
The floor 3 profile sets `beasts=true`, `floorId=3`, restores the exact party and
retains the boundary token. The fixture checks in-process profile/floor/token
readback and native ready diagnostics against its expected checkpoint token.

Floor 3 rejects transition-anchor files. Request, interaction and checkpoint APIs
cannot generate a floor 4 handoff; premature process exit42 remains rejected.
The title says floor 4 descent is unavailable. **Extinction/knockout checkpoint
persistence is also disabled on floor 3**: automatic attempts hit the same guard.
This is an engineering entry milestone, not a playable or save-safe campaign.
Independent focused native review found no blocker for that bounded contract;
full campaign integration remains separate.

## Host contract

`experimental.pikmin2_beasts_floor3_entry.stage_checkpoint(adapter, checkpoint,
assets, assembly, purple, pod, output)` validates the checkpoint with the supplied
`BeastsReferenceAdapter`, requires active floor 3 and a 20-member Red/Purple party,
and derives the token through `adapter.token(checkpoint)`. It returns a fresh
stage directory. The existing survey `run(exe, directory)` then launches and
validates native evidence. All arguments naming directories are `Path` values.

`checkpoint.json`, native entry text, expected boundary and all stage overrides
are hashed in `survey.json`. This includes actual `native_profile=forest_1` and
`party_restore_protocol_floor=3`, plus profile/checkpoint identities and
`descent_enabled=false`. `campaign_entry=false` and `native_ready=false` remain:
the helper validates a caller-supplied checkpoint but does not authenticate
ledger ownership, acquire supervisor launch authority or change campaign state.
The token is identity correlation, not a cryptographic attestation.

## Actual durable checkpoint evidence

The first run used a byte-for-byte, read-only snapshot of #314's successful
exit42 receiver ledger:
`output/p2-cave-lane/output/beasts314-final/ledger/surface-ledger.json`.
The adapter configuration is explicitly an engineering test profile:
`audit()` from `tests.test_pikmin2_beasts_checkpoint_reference`, content identity
`'a'*64`, receipts `{1:{},2:{},3:{}}`, campaign `'b'*32`. This is actual native
floor 2 checkpoint/receiver evidence under placeholder test identities, not a
production campaign save. The validated floor 3 party is ten Reds/ten Purples,
all leaf maturity, health 1.0.

The snapshot SHA256 is
`f34d5273d2331773bdc5a425ad22e41dea642d436979d7f1d4296bb424b39d29`.
The original was unchanged after the run. Native readback matched token
`57c79f18a03824ddc032606e13c0f276bca794176f9d5699e99f4f72db6dd7c7`.

A second run used an explicitly synthetic, validated reference checkpoint with
ten Reds/ten Purples, mixed maturity and health 0.625, token
`e9235bc0a1d8a4481d0de483879d96526e758dd9802ec3efe8941d0c096ac4f8`.
Both native floor 3 runs completed all 12 controller goals across both room seams
and back, preserving the party and health. Native ground checks held throughout;
rewards remained zero and repairs unchanged. No temporary/final transfer file
appeared. A third process passed the old tutorial-floor2-tagged party survey,
asserting that native profile/floor remained tutorial/2.

## Build, tests and reproduction

Private Release production build: all 493 tasks completed. Native JAudio enabled,
test hooks disabled; project default `PIKMIN_ENABLE_IPO` remained ON. The external
fixture links the private completed build and records source/dependency/object
hashes and before/after Ninja no-work observations. It does not certify historical
compilation. No shared native checkout/build or player save was changed.

Native policy probe compiled with `g++ -std=c++17 -Wall -Wextra -Werror` and passed
tutorial1/2, Beasts2/3 and malformed-token/wrong-floor cases. Python:

```powershell
python -m pytest -q tests/test_pikmin2_beasts_floor3_entry.py tests/test_pikmin2_beasts_floor3_runtime.py tests/test_pikmin2_beasts_party_restore.py tests/test_pikmin2_beasts_checkpoint_reference.py
python -m experimental.pikmin2_beasts_floor3_runtime fixture `
  --source ../native-beasts-floor3-entry/tools/preview_p2_room.cpp `
  --output output/floor3-317/new-fixture/survey.cpp
$env:PATH='C:/msys64/mingw64/bin;'+$env:PATH
python -m scripts.build_pikmin2_fixture `
  --source ../native-beasts-floor3-entry --build ../native-beasts-floor3-entry/build-floor3 `
  --fixture output/floor3-317/new-fixture/survey.cpp `
  --output output/floor3-317/new-linked `
  --expected-native-head df041d0cf019b7f842f516df6d3258d101afa6c7
```

**18 tests and 57 subtests passed**, covering strict checkpoint/profile/token
binding, Red native index 1, wrong-floor staging, readback mismatch, malformed/
duplicate diagnostics and forbidden floor 4 transfer evidence, plus prior party
and checkpoint regressions. All three native runs passed with unchanged stage
inputs/executable. Fixture SHA256:
`67e78921e631c8f0b56cf101166c127c6c7fd0f859dec4a073e338c2be15a386`.
Provenance: `output/floor3-317/linked/provenance.json`.

| Run under output/floor3-317 | Native log SHA256 |
|---|---|
| runs/dab6f02497ae407cbd851c3bcbb93b46 | `28c0b4a3ca6e5e6ed17ff0e4877946677c6b9d8842730dede0fb0b8f83f625d0` |
| runs/99c5988cec6b488a8e12d8c172f493b1 | `7b5c0678237dcb5c84370577c44c33d9fac975c39e4b98c2780d73f2a5fa673b` |
| legacy/c41486ef261d407b8fb1b57c5339d2ee | `95cf7253cfe116a5820d6220320b7414f0466a998382538d196b0df555296b0a` |

Full hashes and final revalidation are in `output/floor3-317/verification.json`.
The exported four native files include inherited Beasts2/guarded-exit42 changes
from native base e2398623 because this root PR stack previously contained an older
engine snapshot. Integration must combine the parent handoff lane, not discard
those dependencies. The independent native commit isolates the #317 delta.

Remaining: supervisor-authorized floor3 launch, floor progress/receipts, actual
treasures and Hiba/plant content, terminal persistence, floor4 descent and full
cave resume. No part of this survey certifies native carrying or natural gameplay.
