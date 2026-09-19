# White Pikmin specification

Status: target specification, 2026-09-13. The [species foundation](PIKMIN2_PURPLE_WHITE_INTEGRATION.md) is implemented; [swallowed-poison progress and evidence](PIKMIN2_WHITE_POISON.md) are tracked separately. Gas, digging and ship storage remain future work. Tracking: [#395](https://github.com/4laric/pikmin-randomizer/issues/395), parent [#131](https://github.com/4laric/pikmin-randomizer/issues/131). Implementation owner: Codex through shared account `4laric`.

## Player behavior and scope

White Pikmin are a distinct species obtained through Ivory Candypop Bud conversion. They move using White-specific parameters, survive poison gas, reveal fully buried treasure through local digging behavior, and poison supported predators that successfully swallow them. They retain species and maturity through cave transitions and return to ship storage. There is no White Onion and no automatic replenishment on loading a save.

This is the experimental Pikmin 2 track. Coordinate species work with #131, campaign persistence with #132, treasure ownership with #140, White Flower Garden with #155 and Snagret behavior with #174. Purple impact remains separate. P1/AP White adaptation #10 retains its own scope; this spec adds no AP unlock, randomizer location or poison-gated item placement. Bulbmin implementation, other Candypop variants and the full base-species fidelity audit remain separate #131 work.

## Source authority and tuning

The [White capability audit](PIKMIN2_WHITE_CAPABILITIES.md) records source anchors and the five-floor cave inventory. Source revision `632af93787b9c95b63f0c13be32b161375ce3a96` was verified locally. Gas interaction, successful swallow and buried visibility were also directly inspected for this spec. References below are relative to `native/pikmin2-research`.

| Concern | Source-backed contract | Still to resolve before numeric gameplay sign-off |
| --- | --- | --- |
| Species | `include/Game/Piki.h`: White = 4; Onion species stop at Yellow | Native species/storage adapters and versioned wire schema |
| Movement | `piki.cpp:715`: doped early return, otherwise maturity-based interpolation followed by White run multiplier | Retail parameter extraction; 2.0 is a header default, not a measured universal speed ratio |
| Attack/throw/carry | `piki.cpp:880,904,915` selects species-specific parameters | Retail values and complete carrying calculation; do not infer extra carrying strength from carry-speed power |
| Poison gas | `interactPiki.cpp:531`: White/Bulbmin avoid gas panic; invincibility and transition checks precede reaction | Native panic, whistle rescue, death timing and attacker accounting audit |
| Ingestion | `enemyAction.cpp:1148`: accepted mouth-attached swallow kill triggers predator callback | Per-family parameters, alternate ingestion paths and immunity exceptions |
| Buried visibility | `itemTreasure.cpp:405`: pellet present and remaining-depth ratio at most 0.85 | Retail work/depth parameters and actual floor placements |
| Conversion | `Pom.cpp:257,279`: WhitePom produces White sprouts and does not count consumed inputs as deaths | Retail capacity, timing, same-color handling, maturity and exhaustion behavior |

Extract values reproducibly from the supported US GPVE01 revision, recording disc path, parameter key and hash. Reject missing, duplicate or invalid values. Any temporary tuning must be identified as a port adaptation rather than retail fidelity. Do not publish an invented universal poison damage, conversion yield or carry bonus.

## Species, controls and physical behavior

Introduce an explicit species identity distinct from legacy P1 color indices. Centralize species queries for immunity, stats, selection, rendering, storage and serialization. If a legacy base-color adapter is required internally, it must never grant White Red's fire immunity or route Whites into the Red Onion. Preserve Blue/Red/Yellow/Purple numeric meanings on existing protocols.

Register White model, scale, leaf/bud/flower attachments and the animations required for the supported actions: idle, follow, throw/fall, attack, carrying, digging, sprout/pluck and death. A sampled animation preview is allowed in the first slice but must be labeled; full action coverage is a later acceptance gate. Assets stay local.

White must be selectable and throwable independently in mixed squads, have a distinct dismissal group, and appear accurately in field, squad, sprout and stored-population counts. Count one White as one body and one field-cap slot. Keep physical carrier slots, required weight and carry-speed power separate; use no strength bonus without a source weight audit. Apply movement through the common species-aware path so follow, autonomous work and hauling cannot silently disagree. Preserve maturity and any source-specific doped behavior.

Whites gain no Red fire, Yellow electricity, Blue water or Purple impact capability from this feature. Species/hazard regressions must establish these boundaries without assuming that every P2 hazard is already implemented.

## Obtaining Whites and population accounting

Ivory conversion follows input capture, accepted conversion, White sprout creation and plucking. A valid one-for-one conversion changes species, not total population. Record birth/death counters according to the source; consuming an input for conversion is not a combat casualty. Audit same-color input, maturity output and exhausted-bud behavior explicitly rather than copying the existing Violet shortcut.

Before destroying an accepted input, ensure its replacement can be created, or provide an atomic equivalent that restores the input on failure. Partial batches, actor-pool exhaustion, interrupted conversion and repeat callbacks must not lose or duplicate population. Bud capacity belongs to a stable source instance, with state that follows the same checkpoint/rollback boundary as its sprouts and inputs. Never grant Whites merely because the player enters a particular floor.

The supported checkpoint schema must account for every living Pikmin in exactly one compartment: active actor, captured conversion input, sprout or ship storage. A first slice may retain the current explicit requirement to pluck/release all transient occupants before transition. It must visibly refuse the transition; silently dropping those occupants is unacceptable. Full campaign support requires source-derived boundary handling for these states.

At zero White population, retain zero across save/reload. Recovery comes from available source-authored conversion supplies and stored survivors, not an unlock-time grant or invented daily refill. Audit bud regeneration/revisit rules before promising renewable recovery. A cave without sufficient recovery supplies is a content/progression limitation to report, not a reason to manufacture Pikmin.

## Gas immunity and vent work

Route GasHiba and each enabled gas emitter through a dedicated gas interaction. White avoids the gas-panic transition. Eligible other species enter their proper panic path with attacker identity; implement and validate whistle rescue and death behavior from source before exposing a gas encounter to normal play. Generic invincibility still applies.

Gas immunity and permission to damage the emitter are separate checks. Source `GasHiba.cpp:108` uses non-captain and vertical bounds, not a universal White-only attack condition. Audit AI discovery/story gates (`pikiAI.cpp:683`) as part of task selection. A non-White may meet work eligibility while still being endangered by gas. Do not encode immunity as huge health, disable the entire hazard near Whites, or make all vents White-only by assumption.

Gas emission, active work, destroyed state, effects and collision must agree. Destroying a vent ends its hazard once; loading or replaying a floor must restore all those states consistently under the chosen checkpoint policy.

## Poisoning predators

Trigger poison only after the supported predator's swallow operation successfully kills an eligible mouth-attached White. Contact, latching onto the body, failed kill stimulation, crushing, unrelated death and cleanup must not trigger it. Preserve the normal casualty and predator death/corpse paths.

Use the family-provided poison damage and its callback, including any override. Each successfully consumed White contributes independently. Source's initial poison-feedback flag gates animation/effects/sound, not subsequent damage. Do not turn this into periodic damage every frame or suppress a second White because the first started an effect.

Maintain actor lifetime and consumption-event identity to prevent replay or object-address reuse from poisoning twice. Transient deduplication is cleared with actor teardown; persistent deaths and population changes follow the authoritative checkpoint. Discovery feedback/flags occur at the successful swallow boundary and follow the same commit/rollback policy.

Start with one explicitly registered predator whose actual native swallow boundary has been audited. Unsupported families retain their behavior and are listed as unsupported. Broad campaign enabling requires a family coverage table covering alternate ingestion and death paths; Snagret support is needed for the White Flower Garden route.

## Finding and excavating buried treasure

Own buried content through a stable treasure instance linked to the catalog and delivery receipt identity. State includes source maximum depth, remaining depth/work stage, pellet ownership and release/collection status. Use validated source parameters; guard absent pellets and invalid depth rather than dividing by zero.

Before visibility, only White can select and collide for digging, within the source local AI search/work ranges. At a remaining-depth ratio of 0.85 or less, the treasure becomes visible and other species may join, subject to normal eligibility. Apply the same rule to autonomous searching, direct action and collision. This is not a map-wide treasure reveal or a Treasure Gauge implementation.

Work advances source stage life and depth, updates the model's burial transform and work bounds, then releases exactly one actual collectible at zero remaining depth. Discovery of fully buried content records its source flag/feedback once under the campaign policy. Digging does not award Pokos: the ordinary transport/delivery system owns the receipt. Repeated work callbacks, release retries and duplicate receipts cannot create another pellet or reward.

## Persistence and ship storage

Current campaign code accepts four species, and native `pc_p2_cave.cpp` accepts colors 0–3. White therefore requires a coordinated reader/writer and ledger change, not just appending a model. Define a versioned capability/schema with White identity and compartment counts; retain old schema behavior and reject unsupported/new species explicitly in old readers. Existing sessions must not be silently reinterpreted or overwritten.

Bind population changes to stable conversion events and source bud budgets, replacing the hardcoded floor-2 Purple population allowance where the new schema applies. Validate total conservation, legitimate casualties, unique receipts and compartment transfers together. White withdrawals/deposits move population between ship and field without creating or deleting bodies, obey field limits and retain the source maturity accounting established by the storage audit. No White Onion or corpse-to-White growth shortcut.

Preserve the existing atomic boundary-checkpoint contract: closing mid-floor rolls population, conversions and new collections back together to entry. A future mid-floor save would need world-state serialization and is outside this implementation. Surface return must atomically commit destination, squad/ship population and receipts. Stale handoffs, repeated return, concurrent writers, malformed species and a crash around replacement must not duplicate Whites, reset exhausted committed supplies or award treasure twice. Coordinate the exact schema with #132 before changing either endpoint.

## Implementation gates

| Gate | Deliverable |
| --- | --- |
| A: contracts | Extract retail parameters; audit five-species adapters, carry weight, Pom rules, gas panic/rescue, first predator and ship/source save semantics; settle schema with lifecycle/treasure owners |
| B: first usable White slice | Explicit actor identity, essential visuals/controls, movement, Ivory conversion and sprout/pluck accounting in a disposable arena; prove mixed-species boundary serialization; retain visible transition restrictions where needed |
| C: gas | One real GasHiba encounter with immunity, non-White panic/rescue/death, emitter work and destruction; pass other-color regressions |
| D: ingestion | One audited predator poisons at actual successful swallow; prove multiple Whites, failed kills and lethal poison/corpse handling |
| E: buried content | One source-parameterized buried treasure with local discovery, partial-depth mixed digging, release, haul and receipt/checkpoint recovery |
| F: storage and cave | Ship deposits/withdrawals, extinction/recovery and full source-derived White Flower Garden round trip, including Snagret cargo and restart |

Likely native touchpoints are a species/White module, stats and rendering accessors, Pom/sprout/pluck lifecycle, gas receivers, selected predator swallow handlers, buried-item/work AI and cave transfer/storage adapters. Root campaign code owns schema validation and durable accounting. Record exact hook locations after Gate A; do not broadly replace shared P1 logic. Full White support requires all gates; a model preview or immunity fixture alone does not close #131.

## Acceptance evidence

These tests are proposed requirements, not executed native validation.

| Test | Expected result |
| --- | --- |
| Identity | White stays distinct at spawn, select, throw, dismissal, pluck and reload; legacy species retain IDs and abilities |
| Stats | Leaf/bud/flower and multiple movement inputs match extracted source formula; doped early return covered; mixed hauling obeys separate body/weight/speed rules |
| Conversion | Partial/full/exhausted/same-color inputs and failed births conserve total counts; correct species/maturity and source counters; duplicate callback has no extra effect |
| Gas | Same hit leaves White out of gas panic and sends eligible Red into it; invincibility respected; whistle rescue/death and attacker attribution verified |
| Vent | Work eligibility independent of immunity; captain and vertical bounds tested; destroyed vent ceases gas |
| Ingestion | Mouth-attached successful White kill poisons once; failed kill, non-White, body attachment and unrelated deaths do not; two consumed Whites contribute twice |
| Lethal poison | Predator follows ordinary death/corpse/reward path exactly once; no lost casualty or duplicate poison after actor reuse |
| Dig eligibility | Ratios 1.0 and just above 0.85 exclude non-White; equality and below admit other species; out-of-range White does not remotely reveal treasure |
| Dig release | Depth/work bounds and rendering advance; zero depth releases one pellet; only delivery awards the receipt; missing/invalid depth fails safely |
| Boundary failure | Crash before/after atomic replacement, stale/repeated transfer and concurrent writer preserve a single authoritative population and reward history |
| Storage/recovery | Deposit/withdraw respects field cap and maturity; zero Whites remains zero on reload; actual source supplies permit only legitimate recovery |
| Compatibility | Old sessions preserve old behavior; unknown versions/species reject visibly; P1/AP and Purple conversion/carrying pass regressions |
| Natural play | Controller conversion, pluck, follow/carry, gas work, ingestion and buried hauling, then exit/store/restart with expected survivors and receipts |

Use policy tests for numeric boundaries and accounting; compiled integration tests must exercise real native callbacks. Require a Windows production build and isolated controller gameplay evidence with exact executable/source revisions. Injected actor states or synthetic receipts alone do not satisfy natural-play acceptance.

White Flower Garden has five inventoried floors: conversion is on floor 3, gas on floor 4 and Snagret/cargo on floor 5. Actual counts, burial placements, exits and supplies must be decoded before setting route expectations. Existing inventory is not proof of a playable cave. Keep all disc assets, builds, saves, logs and captures local and separate from player sessions.
