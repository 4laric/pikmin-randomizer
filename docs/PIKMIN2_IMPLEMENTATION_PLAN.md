# Pikmin 2 in Open Nectar: implementation plan

Date: 2026-09-12. Owner: Codex using shared GitHub account 4laric. Parent: [#109](https://github.com/4laric/pikmin-randomizer/issues/109). This is experimental work after Pikipelago v0.1, not a release dependency. Issue assignment denotes ownership, not that every batch is underway.

## Recommendation

Build **Emergence Cave** as the first complete slice, with a small Valley of Repose landing/entrance pocket. Follow it with **Hole of Beasts**. Do not require an entire surface region before proving the cave loop.

| Candidate | What it exercises | Decision |
| --- | --- | --- |
| Emergence Cave | Two fixed floors, three treasures, Purple introduction, heavy treasure and cave exit; no environmental hazards or boss | First complete slice: bounded content with important sequel mechanics |
| Hole of Beasts | Five floors, fire hazards, generated layouts and Empress Bulblax | Second slice: generation, combat variety and a boss |
| Full surface region | Broad navigation, time, obstacles, multiple destinations and persistent objects | Expand after cave entry/return is reliable |

Cave content references: [Emergence Cave](https://www.pikminwiki.com/Emergence_Cave), [Hole of Beasts](https://www.pikminwiki.com/Hole_of_Beasts). These describe gameplay; local disc data and the decomp are authoritative for implementation. The imported concrete room is not either cave, and their materials and actors still need an asset audit.

## What the prototype proves

The player has confirmed movement and carrying in an imported P2 room after floor and route corrections. We have rigid model/texture conversion, separate collision conversion, native P1 actors, an imported treasure visual, and a distinct collection receipt. Fifteen focused Python tests and a native far-corpse delivery fixture support that result. See [prototype evidence](PIKMIN2_ROOM_PREVIEW.md).

That initial room did **not** prove animated P2 characters, arbitrary materials, procedural caves, cave persistence, a Research Pod, two captains, Purple/White behavior, or a complete campaign. Its receiver was an Onion and the treasure used pellet physics. Subsequent Pod and Purple increments are recorded below. A successful room is evidence that engine reuse is practical, not a meaningful percentage of a finished port.

## First slice: playable contract

Player loop: enter from a small surface pocket with Reds; explore the first floor and deliver treasure to the Research Pod; descend with surviving Pikmin; convert Pikmin through Violet Candypops; carry the heavy Spherical Atlas using Purples; leave through the geyser; return with the correct squad, treasure accounting and next-area unlock; restart and retain that outcome.

Internal checkpoints:

1. **Red-only first floor:** imported authored layout, suitable enemy behavior, working Pod and treasure accounting. No campaign-completion claim.
2. **Complete cave:** both floors, actual Purple identity and abilities, conversion, heavy treasure, descent/exit and checkpoint recovery.
3. **Surface round trip:** entrance pocket, entry snapshot, return and unlock persistence. This is the first complete vertical slice.

The first engineering checkpoints may use one captain. A faithful P2 campaign requires the later two-captain gate. Temporary actor or material approximations must appear in the manifest and playtest notes. They cannot silently become the definition of completion.

Manual acceptance includes controller throwing, natural recruitment, carrying from distant corners, camera usability, conversion, descent, exit and restart. The current fixture's explicit Transport assignment does not replace that playthrough.

## Assigned implementation batches

| Order | Issue | Deliverable and gate |
| --- | --- | --- |
| 1 | [#110](https://github.com/4laric/pikmin-randomizer/issues/110) | Inventory and import both Emergence floors; validate geometry, collision, directed goal routes and unsupported assets |
| 2 | [#111](https://github.com/4laric/pikmin-randomizer/issues/111) | Research Pod, stable treasure ledger, corpse currency and independent economy |
| 3 | [#112](https://github.com/4laric/pikmin-randomizer/issues/112) | Cave entry/descent/exit, squad transfer and atomic checkpoints |
| 4 | [#113](https://github.com/4laric/pikmin-randomizer/issues/113) | Real Purple identity, storage, models/animations, carrying and Candypop conversion |
| 5 | [#114](https://github.com/4laric/pikmin-randomizer/issues/114) | Integrate surface pocket and complete cave; manual and restart acceptance |

The floor audit comes first. Pod and lifecycle work must agree on collection/save events. Purple and lifecycle work can proceed separately once color/storage and checkpoint schemas are settled; integration follows both. Existing [#9](https://github.com/4laric/pikmin-randomizer/issues/9) covers a P1 AP Purple proposal, and [#12](https://github.com/4laric/pikmin-randomizer/issues/12) a handcrafted P1 cave. Reuse applicable work without silently replacing those scopes or importing their campaign rules.

## Remaining sequel tracks

| Track | Scope | Completion gate |
| --- | --- | --- |
| Content pipeline | Animated/skinned models, animation events, material coverage, textures, lighting, water and audio; local extraction manifests | Every required asset either faithfully supported or explicitly blocked; no invisible fallback success |
| Room assembly | Unit transforms, doors/seams, shared collision/water/routes, spawn rules, deterministic layout generation | Connected walk/carry graphs and viable starts/exits across generated samples; exact layout retained on resume |
| Two captains | Switch input/camera, separate squads, following, throwing, inactive captain behavior, health/knockout and save state | Split-task, reunion, cave transition and reload scenarios work without squad ownership loss |
| Purple and White | Purple impact/stun and weight; White poison interactions, detection/digging, movement; ship storage and population accounting | Source-based behavior and mixed-squad tests; abilities are more than stat changes or palette swaps |
| Combat and hazards | Enemy families, bosses, attack events, elemental/poison/electric/water interactions and corpse behavior | Per-species behavioral checklist; randomized P1 stand-ins do not count as implemented P2 enemies |
| World interactions | Plants, conversion, obstacles, treasures, sprays, upgrades and equipment | Interaction, persistence, carrying requirements and UI match the intended campaign rules |
| Surface campaign | Valley of Repose, Awakening Wood, Perplexing Pool and Wistful Wild; time, entrances and progression | Every region has traversable routes, correct unlocks, persistent changes and round-trip cave tests |
| Story and collection | Debt accounting, later campaign objectives, rescue, treasure completion and results | Goals have distinct tested triggers; complete treasure inventory with no duplicate credit |
| Presentation | HUD, menus, Piklopedia/treasure records, effects, audio, tutorials and required cinematics | Player can understand and complete the game without debug tools; intentional omissions documented |
| Pikipelago integration | Stable location IDs, items/options, ability/carry reachability, enemy placement dependencies and reconnect journal | Multiworld logic matches physical capabilities; saving/reconnecting cannot duplicate or lose rewards |
| Additional modes | Challenge Mode and two-player battle, including their distinct rules and interfaces | Separate acceptance/release gates after the story campaign; not implied by campaign completion |

Progress through representative systems before bulk content: Emergence -> Hole of Beasts -> a complete surface region and two-captain play -> White/poison/buried-treasure content -> broader hazards, bosses and remaining campaign. Audit a suitable White-focused cave from disc before selecting that third cave. Generate the eventual region/floor/enemy/treasure coverage checklist from the local asset inventory rather than claiming completion from a handful of demos.

## Architecture boundaries

- Keep a separate P2 campaign mode and save namespace. Reuse Open Nectar rendering, collision, input and actor infrastructure, but translate selected P2 behavior rather than transplanting its whole manager stack.
- Use explicit region/cave/floor, treasure and actor identifiers. P2 treasures must not masquerade as P1 ship parts; corpses underground yield currency rather than Onion seeds.
- Treat color identity, physical attachment slots and carrying power as different concepts. Audit hardcoded three-color arrays, UI, model loading, storage and serialization before adding Purples/Whites.
- Store campaign state, floor state and external AP receipt state separately, with an atomic commit relationship for rewards. Define abandon/death/restart behavior from source before implementation. Save layout identity and RNG state; restarting must not accidentally reroll a cave.
- Apply one agreed unit transform to geometry, collision, routes, water and placements. Validate seams and incoming approaches to destinations. Preserve directed source graphs: the prototype needed two specific goal approaches, not indiscriminate reverse edges.
- Audit render/collision alignment per asset. The concrete prototype's render-only -1 offset is not a universal P2 conversion rule.
- Support authored floors first. Add procedural assembly only once a fixed floor can be entered, completed, saved and exited reliably.
- Extract from the user's local disc. Keep assets, ISOs, generated bundles and saves out of GitHub. Check in source, manifests/schema and synthetic fixtures; a future playtest needs its own local extraction flow.

## Verification and risk gates

For each batch, require focused converter/state tests plus a native fixture where it adds meaningful coverage. Inspect actual rendered scenes and player controls; hashes alone cannot establish correct visuals. Carry tests must include every destination and disconnected/seam cases, not only an object beside the Pod.

For persistence, exercise process restart at floor entry, after collection, descent and exit; repeat loading must neither credit treasure twice nor restore lost Pikmin for free. Explicitly test full squad loss and interrupted writes. Keep P1/AP regression coverage around shared engine changes.

The highest uncertainties are animation/material compatibility, generated-room connectivity, two-captain ownership and durable campaign state. Resolve these as gates before estimating the entire project. Static room conversion is lower risk now; arbitrary P2 content remains unproven. Full enemy/boss fidelity and presentation are a substantial content effort even if the engine primitives are reusable.

Continue #111's Pod/economy acceptance, then #112's cave entry/descent/exit and squad checkpoints. This document authorizes no automatic merge of experimental code into v0.1. General engine fixes can be proposed upstream separately from campaign-specific additions.

## Source basis

Behavior reference: local `native/pikmin2-research`, commit `632af93787b9c95b63f0c13be32b161375ce3a96`. Relevant primary sources include `src/plugProjectKandoU/gameMapParts.cpp` (room assets), `gameCaveInfo.cpp` (layout information), `include/Game/Piki.h` and Pikmin state implementations (colors/carrying/abilities), `include/Game/gamePlayData.h` and `singleGS_CaveGame.cpp` (campaign/cave state). Resolve full file paths in the checkout before implementation; translate behavior at our engine boundaries.

Current Open Nectar prototype native commit: `5b0e3857f3f367b6c4003498110b86c551a514c5`; root carry/floor fix: `7f72f92`. Historical research reports predate the working room; the linked preview evidence supersedes their unvalidated-render status.

## Implementation progress

Batch #110: [Emergence import and floor previews](PIKMIN2_EMERGENCE_IMPORT.md). Both floor definitions and all referenced unit assets convert. An authored first-floor assembly passes native walking and cross-seam carrying; the second floor now passes native slope traversal and return carrying on the original directed graph. Actual cave gameplay and visual fidelity remain outstanding.

Batch #111: [Research Pod and economy preview](PIKMIN2_RESEARCH_POD.md). Static imported Pod, source-configured treasure weight/value, corpse currency and a separate duplicate-resistant receipt ledger are implemented in the isolated preview. The first native run reached 182 Pokos from treasure and corpse deliveries without P1 repair or seed credit. This is not cave/world persistence or a complete Pod actor; full acceptance remains tracked on the issue.

Batch #113: [Purple preview](PIKMIN2_PURPLE_PREVIEW.md). Opt-in Purple species metadata, actual source model with sampled idle/walk/attack poses, separate ten-unit carrying strength, source numeric stats and Violet conversion are implemented. The isolated Atlas scenario exercises a 101-strength load. Landing/stun, full animation coverage and ship inventory remain open; this is not the full Purple acceptance gate.

Batch #112: [Cave checkpoints](PIKMIN2_CAVE_CHECKPOINTS.md). Two standalone floors are linked with F6 at the Pod, survivor/Purple/maturity/health transfer and atomic receipt checkpoints. Mid-floor closes roll the whole floor back; extinction persists failure. Surface entry/return, physical transition actors and complete authored content remain open.

Combined follow-up: [Snow and transition playtest](PIKMIN2_COMBINED_PLAYTEST.md) integrates opt-in source enemy visuals and marker-based descent/exit. [Content manifest](PIKMIN2_CONTENT_MANIFEST.md) prepares all three treasures independently; native multi-treasure support remains next.

Roster follow-up: [three-treasure/full enemy-count playtest](PIKMIN2_ROSTER_PLAYTEST.md) connects optional per-instance cargo and deterministic4+7 Snow placements to the checkpoint runner. Source behavior/animation fidelity and surface roundtrip remain outstanding.
