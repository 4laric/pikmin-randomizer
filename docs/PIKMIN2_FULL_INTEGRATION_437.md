# Full P2 integration pass (#437)

Implementation owner: Codex through shared account 4laric. Review destination: draft [#432](https://github.com/4laric/pikmin-randomizer/pull/432), `codex/p2-main-review` into this repository's `main`. No upstream issue/PR is created, no main merge is performed, and native origin is not pushed.

## Integrated batch

This pass starts at root `bf9ce07` / native `41304fd7` and combines **90 native commits** through `1d0adc67eb95dd2c7a165c5506fff6e1ab4be5af`. The isolated native worktree was clean at export; all 1,852 tracked exportable source files were copied to `engine/`. Worker build/runtime receipts remain historical evidence for their named commits, not acceptance of this combined build.

| Lane / handoff | Integrated work |
|---|---|
| 02/03/04/05, through `bd0c710` (r3 is equivalent) | Admission-gated seed generation, accepted-placement filtering, AP option, loaded-seed validation, content identities, native asset overlay, family-installer consumer. Fixed launcher attempting a second junction over installed assets. |
| 06/07, through `dea5491` | Scripted-pad input and new-scene fixture plus central death/slot-reuse forget seam, stage-exit reset, safe new-scene generation signal, ordinary reward endpoint/restart fixture. Preserved the earlier receipt corruption fix. Extended the central list for new families. |
| 08/09, `c9480f7` / native `8c9a6cbf` | Armor sampled-event consumer and renderer billboard matrix path, source converter/staging and probes. Combined Armor receiver/stone behavior without replaying consumed sampled events. |
| 10/11/12, `c03be34` + `13b7dec` | Bulbmin identity, hazard capabilities and actual electric/gas reactions, Mother registration, captain/squad contracts and inactive follow, ElecBug actual InteractDenki emitter, schema-3 checkpoint/restart tooling. Second-captain live gate remains closed. |
| 13/15, `f25f507` | Opt-in partial KochappyBase FSM plus Dwarf Orange, Qurione and Shijimi consumers and three-identity scene tooling. Preserved existing family parameter, draw/update, AI-suppression and cleanup hooks. Separate species-lane Spectralid arena retained under its own module name. |
| Species `8c8cda8` | ElecBug pair/flip, Mitite groups, Imomushi, Hana, Mar, Hanachirashi, Tadpole, Catfish, Jigumo, UmiMushi/Blind, SnakeCrow/SnakeWhole, DangoMushi; Armor/Hana/Catfish receiver and lifecycle residuals. Existing Jellyfloat integration is preserved. |
| 21, corrected native `4b308e5c` + `22ba5941` | Groink classifier and projectile-receiver strike bridge; tracker capacity fails closed, with overflow regression. Older runtime evidence remains explicitly fixture-pinned. |
| 22, `da3ce77` | Dweevil capture/drop sidecar, BombOtakara sidecar and shared BombSarai blast consumer, tests and harnesses. |
| 23, `7f3c992` | Pelplant Onion receipt/restart fixture plus Flora/Pom/Plant native slice, Queen colour-correct sprouts and capacity conservation, plant LOD/sentinel policy and fresh-runtime tooling. |
| 24, `7327cf9` | Natural Flick/trample harness and evidence, retaining existing King/Bulblax integration. |
| 25, `1ad3669` / native `0140fb56` | Crawbster source FSM now calls the already-integrated Turn-window/Rock/Egg decision policy. |
| 26/27, `5c42741` / native `6fcfaa11` | Long Legs FSM runs from simulation update, landing/foot effects, death/damage edges; BombSarai/Fuefuki/Titan CTest registration and non-vacuous Release tests. |
| 31, `b41ed19` | Waterwraith visual/host/registered actor/encounter consumer and policy gates. Omitted the unrelated worker static-library restructuring. |
| 32, `ca7ae78` / native `7908de30` series | Titan encounter fixture, full 29-clip staging/motion and standalone save policy; save gate linked with its actual ownership/FSM dependencies. |

Frog `0159b94`, beetle `d818a5b`, prior projectile, Mamuta, Breadbug and Jellyfloat slices were already present; their maintained changes were preserved. Older worker exports and superseded duplicate modules were not copied over the combined engine.

## Integration fixes and validation

- Fixture linking now asks Ninja `compdb -x` to expand its own response contents. It preserves actual object/library order and rejects changed or unmatched graph entries. The maintained graph expanded to 157 link arguments and 569 compiled objects; no dependency-list reconstruction is used.
- Mamuta patch generation recognizes the centralized lifetime file and still rejects partial or duplicate hooks. Cave entry tests now cover schema 3 while rejecting unknown schema 4 and keeping Beasts profiles distinct.
- Private build: `C:/Users/alari/pikmin-randomizer/output/p2-upstream433-build`, Ninja/MinGW Release with JAudio. The first broad production build passed. The expanded build passed after correcting the Titan save-test link dependencies; the final late-handoff production build at `1d0adc67` also passed, with `ninja: no work to do.` afterwards.
- CTest: **59 passed, 1 skipped (asset-dependent JAudio integration)**, 60 registered tests total. New provider gates keep assertions enabled in Release.
- First full Python run: 2,399 passed, 26 skipped, 1,088 subtests passed; three integration failures were then corrected. The affected repeat passed (15 tests, 3 subtests). Final whole-suite result follows below.

Final production executable SHA-256: `DCA6F94D2C68BB44B32545FB58B09E393DA7A49A1A93412F256DEAD7D0031C1F`. Export byte comparison: 1,852 files, zero mismatches. Strict new-scene fixture graph validation, compilation and linking passed against this exact clean native head.

Fresh combined mixed-scene smoke: **passed**, 40.09 seconds, Dwarf Orange/Qurione/Shijimi bind and draw checks all passed. Startup logged 20 reds and a 960x540 windowed, centred window; no extinction occurred. The capture was intentionally timer-terminated (exit 1), not a normal gameplay exit. Current overlay was reapplied to a new private arena; no saves were copied. Stage SHA-256: `21e8ca30ac2ed7d3ff949ce21a385f7fb775f34f550a291e2123efbb4078e3bf`. This proves a bounded mixed-scene smoke, not natural combat/reward, generated admission or a performance budget. Builds, logs, fixture data and saves stay private under `output/p2-broad437-*`.

## Concrete remaining work

The merge batch is not a claim that every enemy is randomizer-ready. See the [numbered lane ledger](PIKMIN2_LANE_COMPLETION.md): **21 primary implementation lanes, 11 primary acceptance lanes, plus lane 01 coordination; 33 full lanes remain open, change 0**.

1. The admitted roster is still empty. Native `ENEMY_P2` ordinary-session parser/spawn binding and accepted placement/transport evidence must meet the same identity contract before an identity is admitted. Python generation and asset staging alone do not prove this chain.
2. Several delivered candidates are sidecar/fixture policies. Groink still lacks its real pursuing actor; Dweevil/BombOtakara still need real actor/payload ownership; Crawbster hazard outputs are decisions, not real child births. These are implementation tasks, not unresolved merge conflicts.
3. Titan's encounter fixture uses a health sink; its save module is a standalone policy, not campaign serialization. Waterwraith and remaining captors still need their natural encounter/lifetime work.
4. Fresh in-process gameplay re-entry now also passes on this combined native head: ordinary day end through results/save/MapSelect, scene generation 1 to 2, day 2 to 8 and 11 rebound family actors. The probe exited 0 with `PASS P2_NEWSCENE_RELOAD`. Broader family coverage remains; this fixture is not source-FSM/reward parity. The safe scene-generation signal avoids dereferencing the previous scene's freed TekiMgr. Process restart and manual manager reset are different gates.
5. Source FSM/receiver, conversion/material and physical reward gaps remain per family. Dwarf Orange's visuals and health do not replace its default P1 host AI; a partial KochappyBase FSM is now available behind an explicit sidecar.
6. No full-cohort mixed-scene performance budget or generated-session end-to-end acceptance is inferred from a build, policy test or worker marker. Each admission still needs natural behavior, actual reward delivery, revisit and restart evidence.

## Next agent baseline

Use the pushed review branch containing this ledger and `ENGINE_SOURCE.md`; record exact root/native commits. Do not apply the historical bundles again merely because ancestry differs after cherry-picking. Read [the mandatory fixture baseline](PIKMIN2_IMPLEMENTATION_FANOUT.md) and [verified P1/P2 asset locations](PIKMIN2_NEXT_WAVE.md#local-p1p2-assets-verified-paths-for-every-lane). Regenerate arenas with the current overlay (20 reds when no Pikmin record exists) and use an observed 960×540 centred window. Existing authored squads are preserved.

Final fetch boundary: `7f3c992` (Flora), `f25f507` (lane 13/15), `dea5491` (lanes 06/07). Their late handoffs are included. The earlier complete Python run passed 2,403 tests with 27 skips and 1,088 subtests; the late affected repeat passed 28 tests and 9 subtests. The separate hard-lane runner passed 35/35.

Combined new-scene fixture SHA-256: `AA7B2256610A3DDB2B382FD11BAEE755E5A27623BB13DD16DD5ED2AB6D1193E1`. Strict-builder provenance is private under `output/p2-broad437-newscene-built`; run/log under `output/p2-broad437-newscene-runtime`. The fixture explicitly creates and centres a 960x540 window. Existing P1 asset lookup warnings remain visible in the log; the bounded new-scene gate itself passed.
