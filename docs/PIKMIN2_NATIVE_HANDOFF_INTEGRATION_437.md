# Native handoff integration continuation (#437)

Owner: Codex through shared account 4laric. Review branch: `codex/p2-main-review`, draft #432. This continues root `1513698` / native `1d0adc67`.

## Audit correction and integrated work

A root-remote-only sweep missed native handoffs posted in GitHub issues. In particular root `7f3c992` carried the Flora fixture but its native dependency `60ed73e8` had not been integrated. The prior statement that the entire reviewed batch was drained was too broad. Integration must inspect the native branch/commit named in each issue handoff, even when no newer root push exists.

| Lane | Accepted native handoff | Result |
|---|---|---|
| 03 | `opencode/p2-lane03-native-r2` through `2837e562` | Versioned ENEMY_P2 parser, identity queries and caller-supplied bound-ID probe. Ordinary actor spawn admission remains separate. |
| 16–18 | `opencode/p2-lanes16-18-native` through `155fe6ec` | Frog source parameters, Giant cargo release on press, beetle flip/re-entry/restart state. Preserved all other family parameter hooks. |
| 20 | `opencode/p2-kabuto-muzzle` through `2fafcd29` | Moving muzzle, sampled fire clock, generation-keyed actor binding and Egg child births. |
| 23 | `60ed73e8` | Flora durable receipt bridge and the missing fixture API. |
| 28 | `opencode/p2-lane28-fuefuki-follow` through `2044906d` | Follow locomotion, moving vehicle, converted pose/motion banks and runtime tools. Preserved Titan visual fixture controls. |
| 29 | `opencode/p2-lane29-jellyfloat` through `94df004c` | Lesser/Greater flight FSM, ordinary actor suction, captain capture, sampled event clocks and per-state pose selection. |
| 30 | `opencode/p2-lane30-rebase` through `65d6b97a` | Demon host, attachment/capture/escape, ordinary sidecar binding, guarded Walk/Idle captain admission, Sarai policies and fixtures. Routed reset/forget through the maintained central lifetime seam. |

Groink `dabe0229` only adds production TUs already registered by the previous integration; source-equivalent and not applied twice. Historical worker receipts remain pinned to their worker builds.

## Integration corrections

- Flora's real Palm death called the central forget seam immediately after spawning the pellet, discarding its release record before the next tick. Retain the value-owned drop record with a null actor pointer; no dead Teki address survives reuse.
- Receipt errors are distinct from durable duplicates. Flora aborts on persistence failure rather than counting it as duplicate success. Regression exercises failure, retry, duplicate/restart and corrupt input.
- Beetle state replacement now uses an isolated atomic filesystem bridge, preserving the previous ledger if replacement fails. Malformed receipt state is rejected rather than silently replaying drops.
- ENEMY_P2 rejects any trailing enemy layout. The product-path test supplies a separately valid P1 slot layout to catch the prior sequential-parser bypass.
- The shared ElecBug/Bulbmin fixture builder supports both the current copied tutorial object and historical legacy archive layout, and uses response files for long commands. Duplicate/ambiguous replacements are rejected.
- Added delivered Kabuto, Fuefuki, Demon and Sarai contract probes to CTest with Release assertions enabled. The pose-bank probe now generates its own test input when run by CTest.

## Validation

Current native head: `bffdb0ab445b39cf195ec71c487e0f11f155f9b7`, clean at export. Export contains 1,917 tracked text files. Final build/runtime results are recorded below when complete.

The native generated-session product probe passes: actual Python generation/bootstrap, native ENEMY_P2 parse/query, content staging/cache and five rejection cases. Its roster is explicitly monkeypatched to a fixed two-identity cohort; it proves the wiring, not live admission or actor births.

The captain admission test passed 46 cases in each of Walk-only and Walk+Idle modes. First focused Python repeat: 30 passed, 9 subtests. The first Flora run correctly failed at the death/drop boundary; it is retained privately under `output/p2-cont437-flora-runtime` and is not acceptance evidence.

## Remaining work

The admitted roster remains empty. ENEMY_P2 parsing is now integrated; ordinary generated target-to-live-actor wiring and acceptance still remain. New sidecar hosts, sampled static poses and injected receipt endpoints do not establish full source behavior, natural rewards/transport or campaign persistence. Existing worker runtime evidence is not automatically evidence for this combined head.

See [the numbered ledger](PIKMIN2_LANE_COMPLETION.md). Counts remain 21 primary implementation lanes, 11 primary acceptance lanes and lane 01 coordination: 33 full lanes open, change 0. This count must be refreshed from issue states before publication.
