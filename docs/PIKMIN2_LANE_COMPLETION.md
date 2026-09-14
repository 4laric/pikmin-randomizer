# Numbered lane completion ledger (#437)

Full lanes and delivered slices are different units. All 33 representative tracking issues remain OPEN (verified 2026-09-14); no full lane is declared complete merely because its candidate merged.

This integration pass drains the reviewed published handoff batch. The remaining work is **21 lanes needing implementation, 11 lanes primarily needing combined acceptance, and lane 01 integration/coordination**. These are primary next actions, not claims that every secondary task is finished. No reliable count of live worker sessions is available. Full-lane count: **33 open, change 0; 0 complete**.

Use [cohort preparation integration](PIKMIN2_SWEEP_COHORT_437.md) for accepted commits, tests and concrete limitations. “Acceptance” means the delivered slice is integrated and still needs the listed real gameplay evidence. It does not admit an identity into the randomizer.

| Lane | Tracking issue | Primary next action | Remaining work |
|---|---|---|---|
| 01 | [#437](https://github.com/4laric/pikmin-randomizer/issues/437) | Integration | Groink and omitted root helpers reconciled; Purple/White, late Jellyfloat/Sarai and lanes 16–18 dependencies integrated. See the dependency reconciliation ledger for pinned validation. |
| 02 | [#438](https://github.com/4laric/pikmin-randomizer/issues/438) | Implementation | Admission list remains empty until one identity passes the generated-session chain. |
| 03 | [#439](https://github.com/4laric/pikmin-randomizer/issues/439) | Implementation | Native ENEMY_P2 parsing/query and Python seed/bootstrap pass together; ordinary target-to-live-actor spawn binding remains. |
| 04 | [#440](https://github.com/4laric/pikmin-randomizer/issues/440) | Implementation | Accepted native terrain and carry-route evidence for generated placements. |
| 05 | [#442](https://github.com/4laric/pikmin-randomizer/issues/442) | Implementation | Complete family adapters and identity-to-runtime binding for ordinary generated sessions; staging/launcher consumer is integrated. |
| 06 | [#441](https://github.com/4laric/pikmin-randomizer/issues/441) | Acceptance | Validate P2 rewards at actual endpoints across restart; ordinary P1 endpoint evidence is retained. |
| 07 | [#397](https://github.com/4laric/pikmin-randomizer/issues/397) | Acceptance | Combined new-scene gate passed (generation 1 to 2, 11 rebound actors); broader family lifetime/re-entry coverage remains. |
| 08 | [#431](https://github.com/4laric/pikmin-randomizer/issues/431) | Implementation | Adopt sampled animation events across remaining family consumers; Armor migration is integrated. |
| 09 | [#429](https://github.com/4laric/pikmin-randomizer/issues/429) | Implementation | Remaining conversion/material gaps and per-family visual fidelity; native billboard path is integrated. |
| 10 | [#408](https://github.com/4laric/pikmin-randomizer/issues/408) | Implementation | Remaining family emitters and physical elemental receivers; ElecBug electric path is integrated. |
| 11 | [#131](https://github.com/4laric/pikmin-randomizer/issues/131) | Acceptance | Combined Bulbmin/schema-3 checkpoint restart passed; natural Mother Bulbmin and production cave placement acceptance remain. |
| 12 | [#130](https://github.com/4laric/pikmin-randomizer/issues/130) | Implementation | Real second captain controls, camera, HUD and survival semantics; live opt-in stays disabled. |
| 13 | [#120](https://github.com/4laric/pikmin-randomizer/issues/120) | Implementation | Opt-in KochappyBase turn/home/dead and real queued-damage/corpse path integrated; press ingress, eating/swallow and generated-session acceptance remain. |
| 14 | [#165](https://github.com/4laric/pikmin-randomizer/issues/165) | Acceptance | Natural combat, rewards and re-entry across the newly integrated ground species. |
| 15 | [#166](https://github.com/4laric/pikmin-randomizer/issues/166) | Implementation | Real carried-Egg/reward ownership and remaining lifecycle parity; flight/Spectralid consumers are integrated. |
| 16 | [#167](https://github.com/4laric/pikmin-randomizer/issues/167) | Acceptance | Aquatic source FSMs plus Frog combined combat, delivery and re-entry acceptance. |
| 17 | [#219](https://github.com/4laric/pikmin-randomizer/issues/219) | Acceptance | Beetle ordinary generated placement and reward/lifecycle acceptance. |
| 18 | [#220](https://github.com/4laric/pikmin-randomizer/issues/220) | Acceptance | Breadbug ordinary cargo/reward endpoints and restart acceptance. |
| 19 | [#221](https://github.com/4laric/pikmin-randomizer/issues/221) | Acceptance | Mamuta Pod receipt/cargo handoff integrated; combined natural run did not observe death in 2,400 ticks, so kill/carry/receipt remain unproven. Generated/mixed-scene acceptance remains. |
| 20 | [#169](https://github.com/4laric/pikmin-randomizer/issues/169) | Implementation | Moving muzzle, sampled Kabuto fire clock, actor binding and Egg child births integrated; complete natural encounter/receiver and generated-session acceptance. |
| 21 | [#198](https://github.com/4laric/pikmin-randomizer/issues/198) | Implementation | Real Groink actor/pursuit, muzzle alignment, natural moving hits and corpse/revival; corrected strike bridge is integrated. |
| 22 | [#447](https://github.com/4laric/pikmin-randomizer/issues/447) | Implementation | Dweevil/BombOtakara sidecars still need real actor/payload ownership; the shared blast consumer is integrated. |
| 23 | [#448](https://github.com/4laric/pikmin-randomizer/issues/448) | Implementation | Remaining Flora conversion gaps and complete natural plant/Pom interactions. |
| 24 | [#445](https://github.com/4laric/pikmin-randomizer/issues/445) | Implementation | Bulblax material/BTK fidelity and full natural encounter/campaign behavior. |
| 25 | [#174](https://github.com/4laric/pikmin-randomizer/issues/174) | Implementation | Crawbster Turn vulnerability application and actual Rock/Egg births; source hazard decisions are integrated. |
| 26 | [#312](https://github.com/4laric/pikmin-randomizer/issues/312) | Acceptance | Long Legs source FSM/landing effects need combined natural encounter and lifecycle acceptance. |
| 27 | [#244](https://github.com/4laric/pikmin-randomizer/issues/244) | Implementation | Complete natural BombSarai child/receiver/lifecycle chain. |
| 28 | [#245](https://github.com/4laric/pikmin-randomizer/issues/245) | Implementation | Vehicle follow/motion/visual and owner-death release handoff integrated; remaining actual actor parity, natural campaign ownership and reward integration. |
| 29 | [#243](https://github.com/4laric/pikmin-randomizer/issues/243) | Acceptance | Greater-specific poses and GroundFlick captain release integrated; combined suction/ownership acceptance, rewards and re-entry remain. |
| 30 | [#242](https://github.com/4laric/pikmin-randomizer/issues/242) | Implementation | Demon host/escape, ordinary sidecar binding and Walk/Idle admission integrated; Sarai isolated captain capture/carry/drop and dedicated Demon native type35 integrated; ordinary Sarai/Pikmin capture parity, lifecycle and generated placement remain. |
| 31 | [#443](https://github.com/4laric/pikmin-randomizer/issues/443) | Implementation | Waterwraith natural navigation/encounter and complete lifetime behavior beyond registered actor/roller gates. |
| 32 | [#246](https://github.com/4laric/pikmin-randomizer/issues/246) | Implementation | Titan ordinary FSM, authored clock and live element detection integrated; actual elemental damage receiver and campaign save/reward ownership remain. |
| 33 | [#444](https://github.com/4laric/pikmin-randomizer/issues/444) | Acceptance | Whole-cohort mixed-scene performance, re-entry and restart on the final integrated pair. |

Every sweep must report newly integrated handoffs, unresolved merge blockers separately from implementation/acceptance, and the full-lane count with its change. Never decrement the count from a worker-finished message or an isolated PASS marker.
