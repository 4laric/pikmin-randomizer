# Opt-in ordinary Purple campaign (#929)

Implementation owner: Codex through shared GitHub account `4laric`.

An ordinary P2 enemy seed can opt in on its first launch with both
`--purple-bank <source-pose-bank>` and `--purple-motion <throw-fall-bank>`.
This does not require an AP unlock. The session pins the bank hashes and rejects
later omission or replacement. Default seeds and historical room previews retain
their previous behavior. White content is not enabled.

The launcher adds one Violet Candypop 100 units along X from the starting
stage's landing origin. Its stage and generator ID are bound explicitly; other
flowers keep their conversion rules and materials. The supply converts at most
five non-Purple inputs using the existing native Candypop/Purple implementation.
Landing-relative placement is an engineering choice pending player navigation verification.

Near the ship (within 180 units), press **F10** to withdraw one Purple, taking
Flower before Bud before Leaf. **Shift+F10** deposits nearby Purple members of the
active captain's formation. Held, attached and non-normal actors are excluded.
The game must be active, with no movie, pause, overlay or day-end sequence.
Allocation/field-cap failure leaves ship stock intact. Sunset survivors enter
ship stock before the Onion-only movie routing, including safe nearby workers.

Purple and White have separate maturity compartments, independent of all three
Onions. White's compartment is reserved; this campaign rejects White save data
and cannot withdraw White. `PIKMIN_CAMPAIGN_PURPLE_1` writes Purple compartments,
consumed-benefit counters and the existing 32 KiB native world into one hashed,
immutable generation. Restart restores only the last published generation;
unsaved stock and world changes roll back together. A failed temporary write
cannot publish new stock. Buried Purple sprouts use a tagged byte in the existing
native sprout record, preserving its length and maturity; default encodings stay
unchanged. Purple actors/sprouts do not satisfy Red population objectives.

## Verification and remaining acceptance

The source includes production-parser tests for exact stage/generator binding,
malformed config rejection, default behavior and fresh-session bank pinning.
The compiled checkpoint probe covers species/maturity, paired world restoration,
unsaved rollback, reconnect, corrupt input, failed writes and opt-out rejection.
Legacy benefits and P2 bridge protocol regressions remain covered.

`tools/preview_p2_purple_campaign.cpp` is an isolated engine fixture with a
960×540 centered window and a captain guard before observation. It injects one
Purple identity/maturity to check real deposit/withdraw accounting and buried
sprout serialization. A fresh engine run passed six deposit/withdraw cycles,
population conservation, unchanged Red Onion stock, and Purple Bud sprout
serialization. Natural mode (`P2_PURPLE_NATURAL=1`) uses a scripted captain throw
and native collision/conversion/pluck; it does not inject Purple identity.
Its negative guard mode is
`P2_FIXTURE_FORCE_CAPTAIN_DOWN=1` (exit 86). Build it with the provenance builder
against a completed private build, and run through the bounded fixture runner in
a freshly staged ordinary P2 session. Injection is not natural acquisition proof.

The ordinary-campaign fixture has passed scripted native throw/collision conversion,
captain pluck, selection class 4 and strength 10, followed by storage checks without
injecting Purple identity. It stages the captain adjacent to the existing sprout
before plucking, so this does not establish approach/pathfinding or player controls.
The launcher recovery regression also covers native journals containing `PURPLE 1`.

An ordinary day-end run advanced day 2 to day 3, deposited a Flower Purple,
confirmed the native results/save UI and emitted `CAMPAIGN_SAVED`. A fresh process
restored day 3 with exactly one Flower Purple, then withdrew and redeposited it.
This is one tested native day boundary, not a full campaign playthrough. The
fixture injects maturity and uses scripted confirmation buttons for this check.

A separate run passed actual native ten-strength transport: one ordinary Red
remained below two units of displacement, while one naturally acquired Purple
attached and moved a native weight-10 pellet 10.22 units. The fixture spawns cargo
with the supported instant-spawn option and stages each carrier at its selected
slot. Native attachment, lift and movement are observed; approach is excluded.

Violet terrain clearance and navigation,
physical storage controls, a full campaign playthrough,
and enemy receiver breadth require fresh runtime acceptance. Parser tests and a
successful compile do not establish those gates. This is a draft implementation,
not gameplay sign-off. Builds, banks, receipts and private player progress stay
under ignored `output/`; no assets, binaries or saves belong in either PR.

## Source integration

The opt-in acquisition/storage slice includes native conversion and plucking, ten-strength carry, population/maturity conservation, and one native day-save/fresh-process resume. Fixture positioning and scripted inputs are disclosed above. Player navigation, full campaign/live AP and broad enemy combat remain follow-ups; ordinary staging does not yet supply the special direct-hit receiver bindings (tracked separately in #940).

The root engine snapshot applies only the reviewed Purple source changes, preserving its existing baseline. The paired native branch merges current native main before CI, retaining newer enemy imports. Native build evidence applies to that native tree; root snapshot tests are separate and do not claim a full root-engine build.

## Purple-only species and `--p2-purple-campaign` (#958)

The mechanism is generic and currently **empty**: `randomizer.seed.P2_REQUIRES_PURPLE`
(source id to citation) lists no species. The Giant Breadbug (source 40) was listed
on the claim that only Purple presses hurt it, that the Onion suck is one-off and
that it could never die. The owner killed it with Reds only (2026-09-30), and the
source agrees. P2's damage paths for `OoPanModoki`:

- Latched attacks do nothing (`PanModokiBase::Obj::damageCallBack`,
  `panModoki.cpp:450-456`, bitter-gated).
- Non-Purple presses and hipdrops are refused (`OoPanModoki::pressCallBack`,
  `panModoki.cpp:1738-1744`; `hipdropCallBack` `521-524`).
- Bombs hurt it (`EnemyBase::bombCallBack`, `enemyBase.cpp:2908-2912`).
- An Onion suck of the pellet it grabbed, carried by any colour, does `suckDamage`
  1000 of 2000 health, every time, not once
  (`pelletState.cpp:541-549` -> `panModoki.cpp:1381-1392` ->
  `panModokiState.cpp:453-481`).

Owner evidence: `output/smoke-w3-giant-breadbug/foh-2/session-0930-1214/runs/c623ce37f36785fce852781911d73cc7ab0fb88d92d808e52b88b179e24cee0e/native.log`
(sha256 `6f30f239cc50bb94b0304c8b2c5001ff517b0e0aa5d50f1a1e92dd177e3d0b4d`). Lines 2748
and 2983 are `P2_BREADBUG_OWN_SUCK_DAMAGE` for generator 4222852521, 2000 -> 1000 and
1000 -> 0, a red-only kill by two Onion sucks (line 2822 is a second Giant,
generator 1849273021, 2000 -> 1000).

So 40 is back in the default, `playable` and `full` pools with no campaign flag.

The constraint mechanism stays in `randomizer.seed.P2_REQUIRES_PURPLE`, not in a slot
list, for any species later shown to need Purple:

- `generate(..., p2_purple_campaign=True)` / `randomizer generate --p2-enemies
  --p2-purple-campaign` binds Purple-only species; the manifest records
  `p2_purple_campaign` (no native capability string, the native hello echoes the capability list). Without the
  flag the default, `playable` and `full` selections leave them out, and a named
  `--p2-species` list that asks for one is an error.
- `validate()` rejects a layout that binds a Purple-only species without the opt-in.
- `randomizer run` refuses such a seed unless `--purple-bank` and
  `--purple-motion` are given, so the Violet supply always exists.
- Placement for 40: ordinary slots only. It is not seated in a boss arena, because
  arena runs r9/r11 killed it but never carried the corpse, so there is no arena
  receipt (#958). The y7 Forest of Hope plateau corpse jam at (-192,2052) stays an
  open risk. The Purple banks are no longer needed for it.

Violet staging works on all five start stages, including the Forest of Hope. Some
local asset sets carry a harness copy of the Forest of Hope `default.gen` whose
header counts only the `    ` records (one fewer than physically present, the
inactive `next` record is a real record the game reads). `split_records` accepts
both framings and `add_violet` writes the physical count, so the appended Violet
is inside the range the game reads
(`tests/test_purple_campaign.py::test_real_stage_generators_stage_violet`).
