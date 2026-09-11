# Enemy randomizer roadmap

Tracking issue: [#41](https://github.com/4laric/pikmin-randomizer/issues/41). Implementation owner: Codex using the shared 4laric account. This is a staged backlog, not a claim that the features below have shipped.

The next playable milestone is **different members of the same family at individual spawn points**, instead of swapping every member of a species everywhere. Broader pools follow once spawn compatibility and bestiary coverage are explicit. Bosses come last because they require encounter-specific adapters.

## Current baseline

Campaign-wide tranche (#44): `campaign_enemies` now covers 72 compatible Teki generator records across Impact, Hope, Navel and Spring, with one seeded miniboss in each large area. Final Trial hazards/Emperor remain pinned. Native mapping, source-aware AP fills, five-stage disk/cache and startup tests pass; physical combat/carry-route acceptance remains open. See DEVELOPMENT.md for the cohort matrix and exact coverage.


Grouped tranche (#53): opt-in fixed-count circular generators now receive group-wide dwarf or Sheargrub choices, in addition to the 15 adult choices. Twelve groups retain original counts/distributions/schedules and protected sources; Spring's dwarf groups remain day-16 sources. Per-member mixed groups need additional persistent member identities and are deferred. Physical compatibility/route acceptance still gates broader habitat pools.

Progress update: the first experimental per-spawn tranche supports 15 named adult generators in Hope/Spring. The 690-record five-area registry matches native disk/cache reads; actual stage-cache APIs restore all 15 choices, with mixed species observed at startup. All-check solo/AP reachability tests pass. Physical clearance/corpse-route acceptance and distributed dwarf/grub adapters remain open, so #42/#43 remain tracking issues. The global-mask baseline below still applies to legacy/default family mode.

- `enemy_shuffle` currently selects a deterministic nonzero three-bit mask: dwarf Bulborb/Bulbear, adult Bulborb/Bulbear, and female/male Sheargrub pairs. There are seven nonempty masks, plus vanilla/off. Every eligible instance of a species follows the same global swap.
- Named-drop and special-parameter generators remain pinned. Replacement assets are preloaded and original generator identity is retained.
- The seed stores a versioned layout of 28 aggregated campaign source/protection/earliest-day facts. This is not yet an individual spawn-slot catalog, terrain audit or full schedule model.
- The 19 bestiary checks use resulting species sources, conservative color requirements, native corpse weights and carrying strength. Most are deliveries; Puffy Blowhog is a defeat and Clamclamp uses its pearl.
- The player has validated visible Bulborb swaps. Combat, corpse return and revisit coverage remains incomplete in [#19](https://github.com/4laric/pikmin-randomizer/issues/19).
- Repeated Beady Long Legs were caused by the separately fixed boss-generator bitfield decoding bug. Boss randomization is not currently enabled.
- Full native campaign resume remains unfinished in [#6](https://github.com/4laric/pikmin-randomizer/issues/6). Stable randomization on a revisit and restoring the entire saved campaign are distinct requirements.

## Implementation sequence

| Batch | Deliverable | Completion gate | Issue |
| --- | --- | --- | --- |
| 1 | Stable spawn IDs, exact schedules, habitat/drop/return-route facts and compatibility allowlist | Five-area catalog matches native births; unknown replacements stay unsupported | [#42](https://github.com/4laric/pikmin-randomizer/issues/42) |
| 2 | Saved per-spawn choices within the three existing families | Mixed family members in one area, no rerolls on revisit, every bestiary check has a reachable source | [#43](https://github.com/4laric/pikmin-randomizer/issues/43) |
| 3 | Broader pools, released one tested cohort at a time | Ground, aquatic and flying compatibility tested separately; required drops, corpse returns and farming preserved | [#44](https://github.com/4laric/pikmin-randomizer/issues/44) |
| 4 | Variety/density settings, encounter budgets and constrained Chaos preset | Predictable engine load and difficulty bounds, with all required checks still supported | [#45](https://github.com/4laric/pikmin-randomizer/issues/45) |
| 5 | Opt-in special-enemy and boss encounter adapters | Each encounter passes combat, cleanup, drops, day/revisit and save-identity tests | [#46](https://github.com/4laric/pikmin-randomizer/issues/46) |

Dependencies are sequential: #42 -> #43 -> #44 -> #45 -> #46. Existing #19 playtest acceptance can inform the first two batches. Every batch should produce a named test seed and preserve older seeds.

## Seed and logic contract

Resolve the enemy layout **before item placement**. The generator chooses compatible assignments, establishes required species coverage, and derives reachability from those assignments. Native code consumes that exact saved mapping; runtime spawn order, memory addresses and visits never determine a new roll.

A slot must identify its area, generator file/schedule and stable record identity, with versioned source data. Audit activation, expiry, repetition and group counts instead of treating an earliest-day record as a full lifetime. A mismatch between seed and supported source catalog must fail clearly rather than silently substitute vanilla enemies.

For each enabled bestiary check, retain at least one supported source with both combat access and, where required, a return route. Include water/hazards, carrying strength, minimum bodies, maximum carrier slots, schedule and prerequisite colors/areas. Use bounded constrained assignment or coverage repair; if no layout satisfies the constraints, generation fails with the unsatisfied source/slot identified. Do not silently drop checks.

Check **all enabled locations**, not just whether the player can collect 25 repairs. Extra optional combat can exceed the conservative route assumptions, but required species and rewards cannot depend on unsupported terrain or carry behavior.

Population farming is also a dependency. Replacing enemies changes corpse supply, so the layout must preserve the renewable pellet/corpse sources assumed by population rules, or change those rules before the replacement cohort ships. Useful +10 Pikmin deliveries remain optional assistance and must not become an undocumented substitute for guaranteed farming access.

Intentional multiworld waits, such as a water-heavy start needing a remote Blue Onion, remain supported when represented in logic. Chaos does not mean losing required species or accepting invalid native placements.

## Pool expansion policy

Start with the existing verified pairs. Then audit small ground enemies before larger ground enemies; investigate aquatic and flying cohorts separately. Enemy size, movement, home behavior, asset dependencies and corpse routes matter more than appearance or taxonomy. An interesting candidate is not automatically compatible.

Protected ship-part carriers, unique/scripted drops, spawners and special personality configurations remain pinned until individually adapted. Keep terrain and actor counts unchanged for the first per-spawn release. Density changes belong to a later, separately bounded mode.

Boss work operates on complete encounters. Separate Teki-based special enemies from boss-manager objects; the latter also includes non-enemies such as geysers and Candypops. Beady Long Legs, Snagret groups and the final boss remain excluded until individually tested adapters exist. Do not add boss bestiary checks implicitly as part of spawn replacement.

## Validation and rollout

Each release needs deterministic generation/legacy tests, source coverage and all-check reachability sweeps, AP fills with remote progression, compiled protocol validation, and native combat/death/corpse tests. Exercise different starting areas/colors, cap 10, weak/strong stat rolls, scheduled spawns, camera culling and revisits. Record save/resume limitations explicitly.

Difficulty scores and actor budgets are tuning tools, not mathematical proofs that combat is possible. Choose defaults from playtest evidence. Proposed presets are Vanilla, Families, Habitat Shuffle and Chaos; names and exact YAML semantics are finalized with their implementation, preserving existing option/seed meanings.

Recommended first implementation: #42's slot audit followed immediately by #43's per-spawn family shuffle. That provides visible variety while keeping the replacement behavior within families already exercised by the prototype.
