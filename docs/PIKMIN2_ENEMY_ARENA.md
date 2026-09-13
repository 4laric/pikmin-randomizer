# Parallel enemy families and P1 arena contract

Integration ownership and acceptance: [#186](https://github.com/4laric/pikmin-randomizer/issues/186). Codex uses the shared 4laric account; the issue comments identify the actual worker. This contract is the next implementation boundary, not a claim that a general arena launcher already exists.

The current workflow, handoff template and active lane assignments are in
[Enemy family import pipeline](PIKMIN2_ENEMY_IMPORT_PIPELINE.md). The first three
playable proxy batches are complete; their parent family issues retain fidelity
and remaining validation work. The table below records the original batch.

## Initial lanes (completed batch)

| Owner | Current bounded work |
|---|---|
| Enemy worker | Bulborb family: source Kochappy variant extraction and profile, reusing the Snow integration pattern |
| Content worker | Correct generator position-offset packing, then Sheargrub family placement and lifecycle |
| Lifecycle worker | Breadbug asset, animation and collision extraction using completed family audits |
| Integration lead | Common arena staging, native registration/hooks, combined builds and source export |
| Kimi | Independent fixed-build acceptance and evidence review |

Family workers own separate new modules and profiles. They request central hook changes before editing shared native setup, renderer, registry, save or reward code. Private fixtures use frozen copied build inputs. A shared rebuild starts only after any dependent worker has captured its inputs.

## First P1 arena boundary

Use a private copy of a known P1 stage with one family and a small, explicit actor roster. Keep the original map/collision/routes. Start with one actor and one ordinary control; expand only after their lifecycle is measured. Do not replace a live seed or randomize the entire level for the first acceptance run.

Separate the family profile (source species, assets, parameters, supported behavior and proxy behavior) from arena placements (generator ID, expected native type, position, and any intentionally applied transform). Generator position and generator offset are both translations: validate their sum against expected native XYZ. Source yaw must remain explicitly unapplied metadata until an orientation path is implemented; never encode it as translation.

Every stage manifest records unique generator IDs, input content hashes, selected stage and exact actor count. Existing stage IDs must be checked for collisions before new IDs are allocated. Native logs must confirm identity and effective XYZ, not merely a successful spawn. Source-position acceptance for older profiles that wrote yaw into offsets requires rerunning after correction.

Record executable hash, native commit and dirty state, asset/profile hashes, exact command and private session directory. Report model import, AI behavior and gameplay acceptance separately. P2 appearance with P1 behavior is an explicit proxy, not a completed P2 enemy port.

## Common acceptance gates

1. Spawn exact identities at expected full XYZ; load visuals and collision without disturbing the control actor.
2. Observe animation and autonomous targeting/movement under normal updates. Direct receiver tests are additional evidence, not this gate.
3. Test actual attacks, damage reception and immunity conditions. State or health injection must be labeled and cannot establish natural combat.
4. Observe death and corpse creation; validate offscreen/buried behavior only in scenarios actually exercised.
5. For carryable corpses, observe native attachment, route traversal and delivery. Assert the expected value once and no unintended seeds, repairs or duplicate receipts.
6. Test actor cleanup and subsequent stage load/respawn without stale registration or reused identity leakage.

Mark each gate passed, failed, blocked or untested with its artifact. A noncarryable enemy needs a source-backed explicit not-applicable entry, not a silently omitted test.

Kimi should use immutable bundles and fresh sessions. The current independent Emergence handoff is in [PIKMIN2_KIMI_NEXT_QA.md](PIKMIN2_KIMI_NEXT_QA.md); new family arena bundles need their own fixed manifests before QA begins. Manual input gates remain blocked if the QA environment cannot provide input.
