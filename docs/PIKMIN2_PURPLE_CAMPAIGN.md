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

Actual ten-strength transport, Violet terrain clearance and navigation,
physical storage controls, full native day-end UI/relaunch,
and enemy receiver breadth require fresh runtime acceptance. Parser tests and a
successful compile do not establish those gates. This is a draft implementation,
not gameplay sign-off. Builds, banks, receipts and private player progress stay
under ignored `output/`; no assets, binaries or saves belong in either PR.
