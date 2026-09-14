# Wave-three handoff review (#437)

Owner: Codex through shared account 4laric. Review baseline root a25c0da, native f14c6851473ac1161be56c8b98f4f905232f3635 (clean). Native unchanged; no build/export/runtime acceptance in this pass.

## Groink: integration held

New root handoff 9e0a76b points to native 1ae14480. P2GroinkStrikeTracker::firstHit stores at most 64 (shellSlot,targetToken) pairs. Once full it returns true without storing a new pair. Repeating that 65th pair therefore returns true again, violating the documented once-per-shell/target damage guarantee. This is explicit in the code's overflow comment, not an inferred runtime result. Current standalone tests do not establish safe capacity exhaustion.

Lane 21 next action: define the supported concurrent shell/target bound and preserve dedup at capacity (or explicitly reject/defer untrackable hits), add a regression filling 64 unique pairs then repeating the 65th, and verify slot recycling still permits a new flight. Submit against the latest approved native baseline with the required Groink classifier/host dependencies isolated. Do not claim natural moving-hit acceptance: the worker GL log records 90 moving steps but hits=0 and wind=0. Terminal pinned damage and engine-free tests are separate evidence.

## Refreshed queue

- Shared providers: c03be34 supersedes f4f5d6c's series with 17 patches, adding electric/gas reaction states, Mother Bulbmin registration and squad follow. Requires current-line shared semantics review before family consumers.
- Species: lane 01 root 2c306cc exports 32 changed files / roughly 7,000 lines from its native merge. Reconcile native provenance and existing Jellyfloat/receiver/material hooks; do not overwrite engine wholesale.
- Long Legs: 4a6bc1d / bee6752 add foot-crush InteractFlick; review target lifetime/receiver behavior on the approved native line.
- Flora: daabb7e and fixed hazards/BombOtakara 0993db5 are additional candidate handoffs. Earlier Candypop Queen colour and capacity-conservation review remains unresolved until a correcting native delta is supplied.

All lanes retain their owners and numbers. The next-wave guide still applies: latest draft root, approved native f14c6851, fresh private arena, observed live Pikmin, centred 960x540 and per-lane adoption evidence. No direct terminal-agent control was performed. No new enemy admission, upstream write or main merge.
