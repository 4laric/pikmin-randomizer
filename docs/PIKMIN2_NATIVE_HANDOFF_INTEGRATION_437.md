# Native handoff integration continuation (#437)

Superseded baseline: see [the dependency reconciliation](PIKMIN2_DEPENDENCY_RECONCILIATION_437.md) for the next integrated pair and validation.

Owner: Codex through shared account 4laric. Review branch: `codex/p2-main-review`, draft #432. This continues root `1513698` / native `1d0adc67`.

## Audit correction and integrated work

A root-remote-only sweep missed native handoffs posted in GitHub issues. In particular root `7f3c992` carried the Flora fixture but its native dependency `60ed73e8` had not been integrated. The prior statement that the entire reviewed batch was drained was too broad. Integration must inspect the native branch/commit named in each issue handoff, even when no newer root push exists.

| Lane | Accepted native handoff | Result |
|---|---|---|
| 03 | `opencode/p2-lane03-native-r2` through `2837e562` | Versioned ENEMY_P2 parser, identity queries and caller-supplied bound-ID probe. Ordinary actor spawn admission remains separate. |
| 16–18 | `opencode/p2-lanes16-18-native` through `155fe6ec` | Frog source parameters, Giant cargo release on press, beetle flip/re-entry/restart state. Preserved all other family parameter hooks. |
| 19 | `opencode/p2-mamuta-pod` through `a54f4af2`; root `e361ff8` | Mamuta carcass Pod receipt, cargo staging and natural transport fixture. |
| 20 | `opencode/p2-kabuto-muzzle` through `2fafcd29` | Moving muzzle, sampled fire clock, generation-keyed actor binding and Egg child births. |
| 23 | `60ed73e8` | Flora durable receipt bridge and the missing fixture API. |
| 28 | `opencode/p2-lane28-fuefuki-follow` through `2044906d` | Follow locomotion, moving vehicle, converted pose/motion banks and runtime tools. Preserved Titan visual fixture controls. |
| 29 | `opencode/p2-lane29-jellyfloat` through `94df004c` | Lesser/Greater flight FSM, ordinary actor suction, captain capture, sampled event clocks and per-state pose selection. |
| 30 | `opencode/p2-lane30-rebase` through `65d6b97a` | Demon host, attachment/capture/escape, ordinary sidecar binding, guarded Walk/Idle captain admission, Sarai policies and fixtures. Routed reset/forget through the maintained central lifetime seam. |
| 32 | `opencode/p2-lane32-ordinary` through `639499bd`; root `1433d88` | Ordinary FSM update, authored event clock, persistent elemental emissions and live-target detection (damage remains separate). |

Groink `dabe0229` only adds production TUs already registered by the previous integration; source-equivalent and not applied twice. Historical worker receipts remain pinned to their worker builds.

## Integration corrections

- Flora's real Palm death called the central forget seam immediately after spawning the pellet, discarding its release record before the next tick. Retain the value-owned drop record with a null actor pointer; no dead Teki address survives reuse.
- Receipt errors are distinct from durable duplicates. Flora aborts on persistence failure rather than counting it as duplicate success. Regression exercises failure, retry, duplicate/restart and corrupt input.
- Beetle state replacement now uses an isolated atomic filesystem bridge, preserving the previous ledger if replacement fails. Malformed receipt state is rejected rather than silently replaying drops.
- ENEMY_P2 rejects any trailing enemy layout. The product-path test supplies a separately valid P1 slot layout to catch the prior sequential-parser bypass.
- The shared ElecBug/Bulbmin fixture builder supports both the current copied tutorial object and historical legacy archive layout, and uses response files for long commands. Duplicate/ambiguous replacements are rejected.
- Added delivered Kabuto, Fuefuki, Demon and Sarai contract probes to CTest with Release assertions enabled. The pose-bank probe now generates its own test input when run by CTest.

## Validation

Current native head: `5f33a9e6e8f618394c5d78cfb1cc1201a754c1b6`, clean at export. Final build/runtime results are recorded below.

The native generated-session product probe passes: actual Python generation/bootstrap, native ENEMY_P2 parse/query, content staging/cache and five rejection cases. Its roster is explicitly monkeypatched to a fixed two-identity cohort; it proves the wiring, not live admission or actor births.

The captain admission test passed 46 cases in each of Walk-only and Walk+Idle modes. First focused Python repeat: 30 passed, 9 subtests. The first Flora run correctly failed at the death/drop boundary; it is retained privately under `output/p2-cont437-flora-runtime` and is not acceptance evidence.

## Remaining work

The admitted roster remains empty. ENEMY_P2 parsing is now integrated; ordinary generated target-to-live-actor wiring and acceptance still remain. New sidecar hosts, sampled static poses and injected receipt endpoints do not establish full source behavior, natural rewards/transport or campaign persistence. Existing worker runtime evidence is not automatically evidence for this combined head.

See [the numbered ledger](PIKMIN2_LANE_COMPLETION.md). Counts remain 21 primary implementation lanes, 11 primary acceptance lanes and lane 01 coordination: 33 full lanes open, change 0. All representative issue states were refreshed during this pass.

The initial full suite ran without the MinGW runtime on PATH and was not a valid native-test environment. Corrected full repeat: **2,405 passed, 27 skipped, 1,088 subtests** at native `bffdb0ab`. Late Mamuta/cave affected repeat: **40 passed**. CTest at that head: **71 passed, one asset-dependent JAudio skip**. Final late-pair evidence follows below.

At native `bffdb0ab`, freshly built Flora fixture **passed** release/capture/durable receipt and exactly-once process restart. Ordinary Onion/AP fixture **passed** with one target check in process 1, zero in process 2, both exit 0. Both use an explicitly injected delivery endpoint and do not prove natural transport; Flora's local receipt also does not prove actual Onion seed birth or AP grant. Runtime files remain private under `output/p2-cont437-{flora-fixed-runtime,ordinary-runtime}`.

Hiba candidate `f139d264` is superseded: its early handled-set insertion and repeated emission logging would regress the already-integrated scan fix; maintained source and lifecycle hooks were preserved.

Final native `5f33a9e6`: production build passed and Ninja reports no work to do. Executable SHA-256 `1E48039CD4C9F6FB6DA39D5D2D012655D857938C78490E4E8596929573534C8D`. CTest: **75 passed, one asset-dependent JAudio skip**, 76 registered tests. Export: **1,927 files, zero byte mismatches**. Fresh mixed-scene smoke at this final head passed all three identity bind/draw gates, required startup window and no extinction, with the current starting-Pikmin overlay. Timer-terminated after 40 seconds; no full performance/reward/admission claim.

This continuation adds 138 native history commits (including worker documentation and merge commits) since `1d0adc67`; the nine handoff rows above describe the meaningful delivered scope. All 33 tracking issues were rechecked OPEN; full-lane count remains unchanged.

Final-head Bulbmin two-process cave restart **passed all ten checks**. Process 1 exited 42 after writing schema-3 transfer (19 survivors, health 0.625); process 2 exited 0 with a restored live Bulbmin. Fixture SHA-256 `3C327614B82E5B16CD9F95A8DB60AF2670E846695743AFF0959DA853DD360413`. Private evidence: `output/p2-cont437-bulbmin-runtime2`. Current overlay authored 19 survivors, reported centred 960x540 startup, no extinction. The confirmation dialog is deliberately skipped and the floor is engineered.

Final-head Mamuta natural Pod observation completed, exit 0, with a live control and successful reset. **Natural kill/corpse/carry/receipt remain UNPROVEN** on this combined build: no death within 2,400 observation ticks, remaining health about 605, zero Pokos. A completion marker is not a natural-acceptance PASS. Fixture SHA-256 `22E2F97237C0BAF7C38B36A8B6D689D1343022ED3110C7D7EE452A6700C39D8B`; private result `output/p2-cont437-mamuta-runtime/result.json`. This is separate from the worker's historical two passing runs. Lane 19 retains the combined natural gameplay gate.

The late Mamuta receipt also exposed a stale hook-auditor assumption. The auditor now permits exactly one independent receipt consumer while still rejecting duplicate visual/setup and receipt hooks; its affected repeat passed 9 tests.

Final full Python suite after the Mamuta auditor correction: **2,423 passed, 27 skipped, 1,088 subtests passed** (107.82 seconds). Final root/native source is clean at publication; private runtime/build artifacts are not committed.
