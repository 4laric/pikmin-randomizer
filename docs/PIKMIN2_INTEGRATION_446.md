# Numbered-lane integration pass #446

Implementation owner: Codex through shared `4laric`. Started from draft #432
root `e514e6d`, native `9735870c`. Pushed refs were pinned before integration;
newer pushes after these pins are the next queue, not silently folded in.

## Integrated source and contract handoffs

| Lane | Pinned handoff | Result |
|---|---|---|
| 02 | `207143d` | Canonical roster, generated snapshot and read-only audit |
| 03 | `112652a` | Deterministic experimental layout/bootstrap builder; native parser and AP/CLI wiring still proposed |
| 04 | `e5f02fd` | Encounter/placement constraint schema and tests, not a catalog of accepted real placements |
| 05 | `049c165` | Hash-verified idempotent content staging/receipts; launcher/extractor wiring remains |
| 06 | `2d82fb9` | Reward/receipt reconciliation contract; no native save/reward integration claim |
| 33 | `299eb67` | Independent QA matrix/evidence tooling; seeded-run acceptance remains untested |
| 11/12 | `08f939d`, `7b1be0b` | Documentation and native captain/Bulbmin/species policy headers + standalone tests; no live species/captain migration |
| 13/15 | `508565d`, `9b9524d`, `5582fd8` | Source-backed Bulborb family and Honeywisp lifecycle contracts/tests |
| 16/17/19 | `0159b94`, `d818a5b`, `c8f45f7`, `8d53e8d` | Frog/beetle re-entry harnesses and Mamuta natural-observation harness; worker evidence retains its pinned builds |
| 24 | `52c3340`, `a61ca1c` | King flick/trample runtime gate and lane evidence; duplicate squad commit `2636961` already present |
| 08 | `cb253f5`, native `0ae8f324` / `d086b78e` | Sampled clock plus batch2 consumer adoption; preserved forced Sokkuri/Armor phases and lifecycle registration queries |
| 09 | `33c5cac` | Opt-in static billboard conversion; retained current skeletal binding and Pelplant transpose-adjugate-zero policy |
| 25/26 | `aa1181c`, `b69019d` | Native Snagret/Long Legs FSM policy modules compiled in production and tested standalone; actor host execution still absent |
| 07–09 / 32 | `b3aca83`, `edabee2` | Handoff docs and Titan patch bundle recorded; only the code explicitly described above is integrated |

## Integration corrections

- Seed bridge rejects coerced/bool/fractional IDs and empty/whitespace-bearing
  target tokens; too few targets cannot silently omit members of its cohort.
- Staging checks resolved paths before mutations and rejects junction/symlink
  escapes, Windows alternate-stream syntax and ambiguous trailing path characters.
  A real Windows directory-junction regression verifies no write outside the run.
- Billboard tests use an extracted synthetic-model helper from the worker's older
  normal tests, without restoring obsolete normal-policy expectations. Converter
  defaults, current skeletal bindings and Pelplant's newer normal policy survive.
- Batch2 event observation uses the maintained forced visual phase where present.
  Events are currently observed from drawing; they must not drive gameplay damage
  until simulation-owned dispatch is integrated. Draw/culling is not an AI clock.
- Native policy patch CMake additions reconciled additively against the current
  upstream-aware engine. No older whole-engine export was substituted.

## Still queued and why

- **Hard-lane export `87204df` and species root `3f4a0aa`:** larger runtime
  reconciliation remains. These are not covered by the new pure contracts.
  Their shared setup/update/receiver/lifetime changes must preserve current
  upstream, King, renderer and actor hooks; do not transplant their old engine.
- **Titan native `2826d61c`:** its FSM-host bundle depends on the absent hard-lane
  host/attack/FSM modules. Patch is preserved, not applied or runtime-accepted.
- **Lane07 lifetime `b9fcf751`:** references absent Purple-direct/White-poison
  providers and predates current family hooks. Reconcile after provider ownership
  and corpse-display/reward lifetime agreement; do not add unresolved references
  or erase needed corpse registration to make a fixture compile.
- **Newer cannon and reward/reuse candidates:** remain separate runtime queue;
  this pass supplies contracts but does not invent normal projectile hits,
  reward delivery or seed eligibility.
- Source eligibility is still denied without accepted family evidence. An
  explicitly supplied cohort to the experimental layout helper is a caller
  contract, not automatic proof of roster admission. No production P2 option
  or ENEMY_P2 native parser is enabled by this pass.

## Validation

Strict roster audit against the local decompilation: 102 source IDs (51 enemy,
13 boss, 2 boss helpers, 3 hazards, 2 manager bases, 3 nests, 24 plants, 4
projectiles); zero source parity problems. 64 enemy/boss identities are taxonomy
candidates, not 64 admitted enemies. Source inventory variants/carriers are not
additional independent species.

First combined Python run: 1756 passed, 24 skipped, 1064 subtests.
Focused integration corrections: 58 passed, including the junction escape case.
Seven warning-clean native standalone probes PASS: Bulbmin, captain, species,
sampled clock, batch2 clock, Long Legs FSM and Snagret FSM.

Private production native `c80d7e22f93415206fff84ec4f7a799af389ecc1`, clean, built
in `output/p2-upstream433-build` (Release/MinGW/Ninja, JAudio ON). Build PASS;
dry run: `ninja: no work to do.` Executable SHA256:
`478E2DD313CAECBB5C62A280D9C297D56EF6E23D21A0506CEDB3F4CD8BAE8F5F`.
Final combined suite: **1798 passed, 25 skipped, 1064 subtests passed** (209.44 s).
Source-only export: all 1609 files byte-equivalent after newline normalization.
Exact-build Flora lifecycle fixture provenance status `built`, SHA256
`A9758BED4CC02AB3A10513CB5EC846206004ADABE6E0A035CE8E4DFA3A195200`.
Run `p2-integration446-lifecycle-runtime/3a8482e61bd1496993e614120da97ce9`
PASS all required gates: identity/draw, mortal actors, damage/death, forget,
respawn/rebind and re-entry; control alive, live squad20 and centred960x540.
Batch2 clock events observed across initial birth and rebind. This is an injected
proxy lifecycle smoke, not natural Pelplant gameplay or reward acceptance.
All generated evidence remains private under `output/p2-integration446-*`.

This is a reviewed integration tranche, not all pushed branches or full-family
completion. Draft #432 remains draft; main and native origin are untouched.
