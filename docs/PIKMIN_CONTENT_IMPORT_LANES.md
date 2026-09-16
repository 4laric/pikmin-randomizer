# Remaining content import lanes

Owner: Codex through shared GitHub account `4laric`. Coordination #531; source coverage #109. This is an executable lane specification, not a claim that catalogued content is playable.

## Dispatch policy

**Existing work > new content work > idle.** Keep available capacity used. Existing actionable implementation, repair, integration, review and QA get first dispatch priority; their priority precedes role ordering. Running or genuinely blocked existing lanes do not prevent independent new source/import work. Do not preempt live workers. New jobs use `work_class: "expansion"`; absent fields and legacy/dependency/recovery intents remain `existing`. At most one new runner starts per controller tick; measured RAM stops new dispatch at90% and resumes at87%. Two heavy build jobs total, exclusive private directories. More source-audit workers may run while build slots are occupied.

Workers pull explicit issue-backed scopes through the existing paid pool, retaining their sessions. Planned lanes are not fake live registry claims: a registry execution lane is provisioned only with a real available worker, prepared private worktree and brief. Source audits have no artificial dependency on an unfinished gameplay gate. Runtime phases wait for concrete validated dependency publications. Registering ownership or creating an issue does not indicate active execution.

## Coverage and status

- P2: **14 campaign caves /105 floors**, **four overworld courses**, **30 Challenge stages /59 floors**.
- P1: **five Challenge layouts**, with story-destination integration (#100) kept separate from the timed/scored AP campaign (#52).
- **53 content lanes** total. Existing issues are reused for14 caves and4 surfaces;35 stage/layout child issues provide disjoint ownership under the existing mode parents.
- Source catalog and dependency manifests already cover all retail caves. Emergence and Hole of Beasts have partial engineering/runtime progress. Existing cave generator/physical-loop lanes34–51 and #129/#468 retain ownership; their work is consumed, not duplicated.
- P1 Challenge preview startup is already implemented. P2 Challenge metadata is catalogued, but stage completion is not established. The host fixture's `chal0` is not evidence of either timed mode working.
- Source IDs are authoritative. Unresolved localized Challenge/cave display names must be extracted and reconciled later, not guessed.

The machine-readable [lane plan](PIKMIN_CONTENT_IMPORT_LANES.json) records every source ID, source path/hash when available, floor roster/timer/starting-population metadata, issue, reserved files, dependencies and phased acceptance. [Original inventory](PIKMIN2_CONTENT_INVENTORY.json) remains the factual baseline. Local disc assets are not redistributed.

## Three phases per lane

**P0 — source audit and additive import contract.** Reuse existing importers and outputs. Decode actual definitions, resource closure, coordinates/schedules, unsupported actors, and complete floor coverage; produce isolated import metadata/adapters with malformed-input tests. Cite pinned source hashes and exact existing owners. Full native builds are not needed for this phase. Completing P0 does not close the full-content issue.

**P1 — private runtime import.** Consume accepted generation/actor/mode contracts. Use a private root/native pair and exclusive leased build, current starting-Pikmin overlay and fresh centred960x540 fixture. Validate actual collisions, water, routes, doors/entrances/exits, selected placements and source interactions. Weighted rows remain definitions, not actor counts. Unknown or unadmitted species remain explicit blockers to promotion; preparatory metadata can still be completed.

**P2 — persistence and natural acceptance.** Verify deterministic seeded layout replay, source-position collection/carrying, all floors/areas and required exits, death/extinction, reentry, reset/retry, save/reload, duplicate-resistant receipts and no cross-content save/check leakage. Label injected/proxy/startup-only evidence. Require independent QA and integrator disposition before declaring complete. No new ADMIT authority is created.

## Shared systems and existing owners

| Contract | Existing owner | Lane requirement |
|---|---|---|
| Cave generation, seams and navigation | #129; active #468 and lanes34–51 | Consume the accepted generator pin. Do not fork a replacement or repeat item5 QA #489. |
| Actor/assets/species and hazards | #128, #130, #131, #140–146 and family owners | Resolve full source closure, including caps/helpers/held items; don't fabricate fallback behavior. |
| Surface days, saves and progression | #132 | Preserve stable course/floor/instance identity and source schedules; bounded Valley pocket is not a full-area pass. |
| P2 Challenge runtime framework | #136 | Starting native color/maturity populations, sprays, per-floor timing, keys/exits, scores, retry and ordinary/deathless result semantics; P0 stage audits can proceed now. |
| P2 Challenge content | #137 | Thirty per-stage children below; all59 floors audited and tested on framework/generator pins. |
| P1 story destinations | #100 | Carry distinct level keys through navigation, five reused native area IDs, cache/card/check routing and save/reload. |
| P1 timed AP Challenge campaign | #52 | Separate mode/check contract; guaranteed resources and practical routes determine supported targets; remote-upgrade multiworld/retry/reconnect acceptance. |
| Integration | Existing cave and species leads | Applied review dispositions, immutable evidence, compatible batches, per-lane receipts; no shared checkout writes from content workers. |

## Content lanes

| Lane/source | Floors | Issue | Initial phase |
|---|---:|---|---|
| `p2-cave-tutorial_1` | 2 | [#114](https://github.com/4laric/pikmin-randomizer/issues/114) | Existing continuation; preserve prior evidence |
| `p2-cave-tutorial_2` | 9 | [#152](https://github.com/4laric/pikmin-randomizer/issues/152) | P0 eligible; runtime dependencies remain |
| `p2-cave-tutorial_3` | 8 | [#153](https://github.com/4laric/pikmin-randomizer/issues/153) | P0 eligible; runtime dependencies remain |
| `p2-cave-forest_1` | 5 | [#154](https://github.com/4laric/pikmin-randomizer/issues/154) | Existing continuation; preserve prior evidence |
| `p2-cave-forest_2` | 5 | [#155](https://github.com/4laric/pikmin-randomizer/issues/155) | P0 eligible; runtime dependencies remain |
| `p2-cave-forest_3` | 7 | [#156](https://github.com/4laric/pikmin-randomizer/issues/156) | P0 eligible; runtime dependencies remain |
| `p2-cave-forest_4` | 7 | [#157](https://github.com/4laric/pikmin-randomizer/issues/157) | P0 eligible; runtime dependencies remain |
| `p2-cave-yakushima_1` | 5 | [#158](https://github.com/4laric/pikmin-randomizer/issues/158) | P0 eligible; runtime dependencies remain |
| `p2-cave-yakushima_2` | 6 | [#159](https://github.com/4laric/pikmin-randomizer/issues/159) | P0 eligible; runtime dependencies remain |
| `p2-cave-yakushima_3` | 7 | [#160](https://github.com/4laric/pikmin-randomizer/issues/160) | P0 eligible; runtime dependencies remain |
| `p2-cave-yakushima_4` | 5 | [#161](https://github.com/4laric/pikmin-randomizer/issues/161) | P0 eligible; runtime dependencies remain |
| `p2-cave-last_1` | 10 | [#162](https://github.com/4laric/pikmin-randomizer/issues/162) | P0 eligible; runtime dependencies remain |
| `p2-cave-last_2` | 15 | [#163](https://github.com/4laric/pikmin-randomizer/issues/163) | P0 eligible; runtime dependencies remain |
| `p2-cave-last_3` | 14 | [#164](https://github.com/4laric/pikmin-randomizer/issues/164) | P0 eligible; runtime dependencies remain |
| `p2-overworld-tutorial` | — | [#148](https://github.com/4laric/pikmin-randomizer/issues/148) | P0 eligible; runtime dependencies remain |
| `p2-overworld-forest` | — | [#149](https://github.com/4laric/pikmin-randomizer/issues/149) | P0 eligible; runtime dependencies remain |
| `p2-overworld-yakushima` | — | [#150](https://github.com/4laric/pikmin-randomizer/issues/150) | P0 eligible; runtime dependencies remain |
| `p2-overworld-last` | — | [#151](https://github.com/4laric/pikmin-randomizer/issues/151) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_abem_tutorial` | 2 | [#534](https://github.com/4laric/pikmin-randomizer/issues/534) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_muki_metal` | 2 | [#535](https://github.com/4laric/pikmin-randomizer/issues/535) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_mat_conc_cave` | 3 | [#536](https://github.com/4laric/pikmin-randomizer/issues/536) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_nari_01kusachi` | 1 | [#533](https://github.com/4laric/pikmin-randomizer/issues/533) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_nari_02tile` | 2 | [#537](https://github.com/4laric/pikmin-randomizer/issues/537) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_nari_03toy` | 2 | [#540](https://github.com/4laric/pikmin-randomizer/issues/540) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_muki_damagumo` | 1 | [#538](https://github.com/4laric/pikmin-randomizer/issues/538) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_muki_bigfoot` | 1 | [#539](https://github.com/4laric/pikmin-randomizer/issues/539) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_muki_houdai` | 2 | [#541](https://github.com/4laric/pikmin-randomizer/issues/541) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_muki_king` | 5 | [#542](https://github.com/4laric/pikmin-randomizer/issues/542) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_mat_t_hunter_enemy` | 5 | [#543](https://github.com/4laric/pikmin-randomizer/issues/543) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_mat_limited_time` | 1 | [#544](https://github.com/4laric/pikmin-randomizer/issues/544) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_nari_04series` | 7 | [#545](https://github.com/4laric/pikmin-randomizer/issues/545) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_muki_enemyzero` | 1 | [#546](https://github.com/4laric/pikmin-randomizer/issues/546) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_mat_t_hunter_hana` | 1 | [#547](https://github.com/4laric/pikmin-randomizer/issues/547) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_nari_05start3easy` | 2 | [#548](https://github.com/4laric/pikmin-randomizer/issues/548) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_nari_06start3hard` | 3 | [#549](https://github.com/4laric/pikmin-randomizer/issues/549) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_abem_leafchappy` | 2 | [#550](https://github.com/4laric/pikmin-randomizer/issues/550) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_muki_redblue` | 2 | [#551](https://github.com/4laric/pikmin-randomizer/issues/551) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_mat_yellow_purple_white` | 1 | [#552](https://github.com/4laric/pikmin-randomizer/issues/552) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_nari_07whitepurple` | 2 | [#553](https://github.com/4laric/pikmin-randomizer/issues/553) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_miya_oopan` | 1 | [#554](https://github.com/4laric/pikmin-randomizer/issues/554) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_muki_bombing` | 1 | [#556](https://github.com/4laric/pikmin-randomizer/issues/556) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_mat_t_hunter_otakara` | 1 | [#555](https://github.com/4laric/pikmin-randomizer/issues/555) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_nari_08tobasare` | 2 | [#557](https://github.com/4laric/pikmin-randomizer/issues/557) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_nari_09suikomi` | 1 | [#558](https://github.com/4laric/pikmin-randomizer/issues/558) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_miya_trap` | 1 | [#560](https://github.com/4laric/pikmin-randomizer/issues/560) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_mat_route_rover` | 1 | [#561](https://github.com/4laric/pikmin-randomizer/issues/561) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_mat_flier` | 1 | [#559](https://github.com/4laric/pikmin-randomizer/issues/559) | P0 eligible; runtime dependencies remain |
| `p2-challenge-ch_mat_crawler` | 2 | [#562](https://github.com/4laric/pikmin-randomizer/issues/562) | P0 eligible; runtime dependencies remain |
| `p1-challenge-impact` | — | [#565](https://github.com/4laric/pikmin-randomizer/issues/565) | P0 eligible; runtime dependencies remain |
| `p1-challenge-forest` | — | [#564](https://github.com/4laric/pikmin-randomizer/issues/564) | P0 eligible; runtime dependencies remain |
| `p1-challenge-navel` | — | [#563](https://github.com/4laric/pikmin-randomizer/issues/563) | P0 eligible; runtime dependencies remain |
| `p1-challenge-spring` | — | [#566](https://github.com/4laric/pikmin-randomizer/issues/566) | P0 eligible; runtime dependencies remain |
| `p1-challenge-trial` | — | [#567](https://github.com/4laric/pikmin-randomizer/issues/567) | P0 eligible; runtime dependencies remain |

## Verification and boundaries

Run `py -3.12 scripts/check_content_import_lanes.py` to check exact source coverage,105/59 floor totals, unique issues/owned paths and phase contracts. Tests reject omitted/duplicated content and corrupted source details. No test/demo/KFes maps are silently included. P2 Battle remains separate #138/#139 because this request named dungeons, overworld and Challenge. Existing P1 story areas are not new imports.

Per-lane outputs, extracted assets, compiled executables, sessions and logs stay under ignored `output/`. The tracked reserved paths contain only code, tests and metadata/specification. Shared files are reviewed by their existing owners; never broaden a per-level claim to seize shared runtime modules. Initial pool dispatch is explicitly P0. Completing and accepting one P0 slice frees that worker for its next issue-backed slice; later phases require updated scope and real dependency evidence.
