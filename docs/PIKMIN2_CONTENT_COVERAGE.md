# Pikmin 2 full-content roadmap and ownership

Planning baseline: 2026-09-12. Parent [#109](https://github.com/4laric/pikmin-randomizer/issues/109). This is the complete-content backlog for the US GPVE01 revision 0 port into Open Nectar, outside Pikipelago v0.1. **Coverage means an owner and acceptance gate, not completed implementation.**

The factual [inventory](PIKMIN2_CONTENT_INVENTORY.json) records source IDs and issue ownership. It contains metadata only; the disc, extracted assets, saves and runtime artifacts stay local. Source anchors come from the local disc and `native/pikmin2-research`. English cave names and regional differences must be reconciled during the catalog audit; cave source IDs are authoritative here.

## Delivery order

1. **Finish Emergence:** [#110](https://github.com/4laric/pikmin-randomizer/issues/110), [#111](https://github.com/4laric/pikmin-randomizer/issues/111), [#112](https://github.com/4laric/pikmin-randomizer/issues/112), [#113](https://github.com/4laric/pikmin-randomizer/issues/113), [#114](https://github.com/4laric/pikmin-randomizer/issues/114), [#120](https://github.com/4laric/pikmin-randomizer/issues/120), [#123](https://github.com/4laric/pikmin-randomizer/issues/123). Close the natural source-position haul gap, finish Purple behavior and native Snow animation, and prove a surface → cave → surface → restart loop. Static actors and scripted haul fixtures do not pass this gate.
2. **Reusable engine foundations:** [#128](https://github.com/4laric/pikmin-randomizer/issues/128), [#129](https://github.com/4laric/pikmin-randomizer/issues/129), [#130](https://github.com/4laric/pikmin-randomizer/issues/130), [#131](https://github.com/4laric/pikmin-randomizer/issues/131), [#132](https://github.com/4laric/pikmin-randomizer/issues/132). Native animated enemies and general room generation are the main scaling gates. Land shared interfaces before parallel content integrations.
3. **Second slice: Hole of Beasts (`forest_1`):** [#154](https://github.com/4laric/pikmin-randomizer/issues/154). Prove generated connected floors, the bulborb family and Empress encounter, treasure accounting and the full exit loop. Pair White Flower Garden (`forest_2`, [#155](https://github.com/4laric/pikmin-randomizer/issues/155)) with White/poison/buried-content work once those dependencies land.
4. **Expand in parallel:** surface courses, cave packages and enemy families below. Each cave must resolve its source roster to the enemy coverage table; importing a room or substituting P1 AI is a prototype milestone only.
5. **Late mechanics and campaign completion:** timed Waterwraith, complex arenas, Titan weapons, post-debt progression and complete save/presentation support. These depend on species, hazard, captain and actor-lifecycle contracts.
6. **Modes and integration:** Challenge and Battle can reuse the stable cave/actor contracts; AP follows stable native receipts and progression. Full-content QA is the release gate, not the number of models imported.

## Parallel work contracts

- Runtime/animation owns actor IDs, animation events, joints, damage and corpse interfaces.
- Content owns manifests, unit pools, placements and per-floor source audits; it does not invent enemy behavior.
- Campaign/lifecycle owns save schemas, populations, receipts, progression and transition boundaries.
- Each implementation batch claims one assigned issue, identifies shared-file ownership, and supplies tests plus natural gameplay evidence. Integrate one build at a time. All newly opened issues are backlog, not simultaneous active assignments.

## Surface courses

| Source course | Region | Owner |
|---|---|---|
| `tutorial` | Valley of Repose | [#148](https://github.com/4laric/pikmin-randomizer/issues/148) |
| `forest` | Awakening Wood | [#149](https://github.com/4laric/pikmin-randomizer/issues/149) |
| `yakushima` | Perplexing Pool | [#150](https://github.com/4laric/pikmin-randomizer/issues/150) |
| `last` | Wistful Wild | [#151](https://github.com/4laric/pikmin-randomizer/issues/151) |

All active generator schedules, buried/held treasure instances, environmental fixtures and cave entrances are included in these scopes. `test_map` is excluded from the four retail courses.

## Story caves: 14 caves, 105 floors

| Source cave | Floors | Owner |
|---|---:|---|
| `tutorial_1` | 2 | [#114](https://github.com/4laric/pikmin-randomizer/issues/114) |
| `tutorial_2` | 9 | [#152](https://github.com/4laric/pikmin-randomizer/issues/152) |
| `tutorial_3` | 8 | [#153](https://github.com/4laric/pikmin-randomizer/issues/153) |
| `forest_1` | 5 | [#154](https://github.com/4laric/pikmin-randomizer/issues/154) |
| `forest_2` | 5 | [#155](https://github.com/4laric/pikmin-randomizer/issues/155) |
| `forest_3` | 7 | [#156](https://github.com/4laric/pikmin-randomizer/issues/156) |
| `forest_4` | 7 | [#157](https://github.com/4laric/pikmin-randomizer/issues/157) |
| `yakushima_1` | 5 | [#158](https://github.com/4laric/pikmin-randomizer/issues/158) |
| `yakushima_2` | 6 | [#159](https://github.com/4laric/pikmin-randomizer/issues/159) |
| `yakushima_3` | 7 | [#160](https://github.com/4laric/pikmin-randomizer/issues/160) |
| `yakushima_4` | 5 | [#161](https://github.com/4laric/pikmin-randomizer/issues/161) |
| `last_1` | 10 | [#162](https://github.com/4laric/pikmin-randomizer/issues/162) |
| `last_2` | 15 | [#163](https://github.com/4laric/pikmin-randomizer/issues/163) |
| `last_3` | 14 | [#164](https://github.com/4laric/pikmin-randomizer/issues/164) |

Each cave issue carries a floor checklist. The inventory records unit pools and raw roster IDs for dependency discovery; weighted roster entries are not a claim that every listed enemy appears in every generated seed. `last_4`, alternate equipment/test/demo cave files and `test` course entries are not silently added to the retail cave count.

## Enemy coverage: every engine identity

102 enum IDs are assigned exactly once. They represent 100 registered identities and 81 Piklopedia entries, not 102 distinct combat species. Aliases, projectiles, plants, boss helpers and nonspawnable bases remain explicit.

| Family | IDs | Owner |
|---|---:|---|
| Bulborb family, Snow fidelity and Bulbmin | 10 | [#120](https://github.com/4laric/pikmin-randomizer/issues/120) |
| Ground invertebrates and disguises | 9 | [#165](https://github.com/4laric/pikmin-randomizer/issues/165) |
| Flying enemies, captors and ambient fliers | 10 | [#166](https://github.com/4laric/pikmin-randomizer/issues/166) |
| Aquatic/hopping enemies, Crawmad and Bloysters | 9 | [#167](https://github.com/4laric/pikmin-randomizer/issues/167) |
| Reward beetles, Breadbugs, nests and Mamuta | 8 | [#168](https://github.com/4laric/pikmin-randomizer/issues/168) |
| Cannon larvae, Groinks and projectiles | 9 | [#169](https://github.com/4laric/pikmin-randomizer/issues/169) |
| Blowhogs, Dweevils and fixed hazards | 10 | [#170](https://github.com/4laric/pikmin-randomizer/issues/170) |
| Flora, Candypops and enemy-manager scenery | 25 | [#171](https://github.com/4laric/pikmin-randomizer/issues/171) |
| Empress/Emperor Bulblax and Larvae | 3 | [#172](https://github.com/4laric/pikmin-randomizer/issues/172) |
| Long Legs and Man-at-Legs | 3 | [#173](https://github.com/4laric/pikmin-randomizer/issues/173) |
| Snagrets and Segmented Crawbster | 3 | [#174](https://github.com/4laric/pikmin-randomizer/issues/174) |
| Waterwraith/rollers and Titan Dweevil | 3 | [#175](https://github.com/4laric/pikmin-randomizer/issues/175) |

`PanModokiNest`/`JigumoNest` alias `PanHouse`; `Pom` and `UmiMushiBase` are shared bases, not independent spawns. `Chiyogami` retail usage remains unconfirmed. The JSON lists every ID, classification and Piklopedia number. Shared hazards and plants have both actor-family and world-interaction acceptance; the enemy ID has one primary owner.

## Modes

| Mode | Source-selected coverage | Framework | Content |
|---|---|---|---|
| Challenge | 30 stages / 59 floors, 1P and cooperative 2P | [#136](https://github.com/4laric/pikmin-randomizer/issues/136) | [#137](https://github.com/4laric/pikmin-randomizer/issues/137) |
| Battle | 10 layouts, 9 fixed edit files plus source random policy, 12 roulette effects | [#138](https://github.com/4laric/pikmin-randomizer/issues/138) | [#139](https://github.com/4laric/pikmin-randomizer/issues/139) |

Full stage-ID checklists are in the linked issues and inventory. Battle means local two-controller play; online multiplayer is not implied.

## Catalogs and systems

The runtime US catalogs contain 188 `otakara` and 13 `item` entries, plus 51 carcass, 4 number-pellet and 1 fruit entries. These include mode-only/test entries: **201 is not asserted to be the campaign collectible total.** Placement and dictionary reconciliation is a required gate. All entries have a checklist in [#140](https://github.com/4laric/pikmin-randomizer/issues/140).

| Track | Owner |
|---|---|
| complete animated asset, material and performance pipeline | [#128](https://github.com/4laric/pikmin-randomizer/issues/128) |
| retail cave generation and connected room navigation | [#129](https://github.com/4laric/pikmin-randomizer/issues/129) |
| two captains, squad ownership and controller behavior | [#130](https://github.com/4laric/pikmin-randomizer/issues/130) |
| White Pikmin, species fidelity and ship storage | [#131](https://github.com/4laric/pikmin-randomizer/issues/131) |
| surface days, campaign saves and story progression | [#132](https://github.com/4laric/pikmin-randomizer/issues/132) |
| HUD, menus, map, journals, story and audio | [#133](https://github.com/4laric/pikmin-randomizer/issues/133) |
| P2 Archipelago world, options and reachability | [#134](https://github.com/4laric/pikmin-randomizer/issues/134) |
| full-content compatibility and release acceptance | [#135](https://github.com/4laric/pikmin-randomizer/issues/135) |
| Challenge framework | [#136](https://github.com/4laric/pikmin-randomizer/issues/136) |
| Challenge content validation | [#137](https://github.com/4laric/pikmin-randomizer/issues/137) |
| Battle framework | [#138](https://github.com/4laric/pikmin-randomizer/issues/138) |
| Battle layouts and roulette | [#139](https://github.com/4laric/pikmin-randomizer/issues/139) |
| Treasure catalog and presentation | [#140](https://github.com/4laric/pikmin-randomizer/issues/140) |
| Equipment and map unlocks | [#141](https://github.com/4laric/pikmin-randomizer/issues/141) |
| Sprays nectar berries | [#142](https://github.com/4laric/pikmin-randomizer/issues/142) |
| Plants and ambient interactables | [#143](https://github.com/4laric/pikmin-randomizer/issues/143) |
| Obstacles construction and platforms | [#144](https://github.com/4laric/pikmin-randomizer/issues/144) |
| Environmental hazards | [#145](https://github.com/4laric/pikmin-randomizer/issues/145) |
| World fixtures and mode lifecycle | [#146](https://github.com/4laric/pikmin-randomizer/issues/146) |
| Regional fidelity and catalog audit | [#147](https://github.com/4laric/pikmin-randomizer/issues/147) |
| title, save-slot management and options | [#176](https://github.com/4laric/pikmin-randomizer/issues/176) |

Additional explicit inventories: 17 plant-family IDs, 16 item managers, 12 exploration-kit equipment indices plus TheKey, two sprays and three honey kinds. The equipment, plant and item-manager issues carry the source-ID inventories. Campaign scope includes both captains, ship storage, days, debt, mail, endings and post-debt continuation.

## Evidence and limits

- The current engineering build proves two-room transitions, sampled P2 visuals, some Purple/carry behavior and receipts. It does not prove full P2 AI, arbitrary cave generation or the campaign.
- A content entry passes only after import, runtime behavior, interactions, natural playthrough and persistence checks appropriate to that entry. Record approximations separately.
- US-first catalog metadata includes onboard Japanese/PAL tables for comparison; that does not establish regional executable or gameplay support.
- Retain a classified unused/demo/test list during import. Unreferenced data is a research question until source usage is established.
- Coverage audit: 4 courses; 14 story caves / 105 floors; 102 unique enemy IDs / 81 Piklopedia entries; 30 Challenge stages / 59 floors; 10 Battle layouts; every runtime catalog entry and listed system inventory has an issue owner.

See the [existing implementation plan](PIKMIN2_IMPLEMENTATION_PLAN.md) for the chronological evidence and outstanding Emergence contracts.
