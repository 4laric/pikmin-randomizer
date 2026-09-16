# Waterwraith packaging provider: BlackMan99 + owned Tyre98 helper (#576)

Provider scope for consumer #572 (family runner stays with #572).
Implementation owner: Codex through shared account 4laric; executing
contributor Muse Spark 1.3 (worker muse-l58). No ADMIT, no allowlist or
admission-flag writes anywhere in this slice.

## Gap closed

At integration pin 5486ae84, experimental/pikmin2_muse_packaging.py
CANDIDATES held only 41/57/58/78 and agreement rejected outside
identities, so no family observer alone could make packaging accept
BlackMan99 (planner memo
output/workflow/autofill/planner/provider-priorities.md). This slice
extends the same module: 99 BlackMan stages through the hash-verified
candidate sidecar path (no shared-signature family installer exists --
the batch-2 waterwraith installer is bespoke and its runner stays with
#572), and 98 Tyre stages as owned-helper owner linkage, never as an
independent seeded identity.

## Contract (experimental/pikmin2_muse_packaging.py)

- Source/name agreement: 99 BlackMan and 98 Tyre resolve through the
  same fail-closed agreement shape as the four existing candidates; any
  other id/name pair is still rejected (100/Whatever, 99/Kurage,
  98/BlackMan all raise).
- Owned-helper rule: a 98 binding stages only alongside a 99 binding on
  the same target sharing the same generator (one actor per generator;
  Tyre rollers ride the BlackMan actor, they are not a second spawn).
  A lone 98 binding, a 98 binding on a target without 99, a duplicate
  98 binding on one target, or a missing actor mapping all fail closed
  with no receipt written.
- Sidecars per run dir: p2-candidate-blackman-actors.txt
  (P2_MUSE_BLACKMAN_ACTORS_1 header, generator species rows),
  p2-candidate-blackman-identity.json (hash-verified copy),
  p2-candidate-tyre-actors.txt (owner generator rows),
  p2-candidate-tyre-identity.json (hash-verified copy).
- Receipt (mode muse-candidate-packaging, candidate_only true,
  admission none): sidecars entry for BlackMan with generators, file
  names and sha256; helpers entry for Tyre with owner_source_id 99,
  owner_targets, generators and file hashes; plan_digest over
  bindings+actor_bindings; immutable files manifest. Receipts carrying
  99/98 additionally record slot_acceptance pending-placement99-provider
  (see below); four-candidate receipts are byte-identical to before.
- Cache: cache_dir/p2muse-<digest> materializes all sidecars without
  re-reading sources; matching run receipts replay cached=True; corrupt
  manifests/entries fail closed with clear-and-restage errors.
- Verify: verify_staging proves every sidecar against the receipt
  manifest and, when given layout+bindings, re-checks agreement,
  helper ownership, sidecar framing and the plan digest.

## Explicitly not prescribed: the generated slot UID

No accepted generated-slot UID for 99 exists: the placement99 provider
is a separate scope (planner memo) and this provider must not invent
one from the l63 fixed encounter. Staging validates the
target-to-generator mapping shape (int ids, duplicates refused across
independent actors) without asserting slot acceptance. Final
runtime-compatible receipt depends on the placement provider contract;
that dependency is recorded here and on every 99/98 receipt, and does
not block this independent closure work.

## Interface consumed by #572

#572's generated-acceptance runner stages a 99 (+98) layout through
stage_candidates(run, layout, content_root, actor_bindings, cache_dir)
with content_root holding BlackMan/identity.json
({schema 1, source_id 99, enum_name BlackMan}) and
Tyre/identity.json ({schema 1, source_id 98, enum_name Tyre}), then
reads receipt sidecars.BlackMan (generators, actors_file,
actors_sha256, identity_file, identity_sha256) and
receipt.helpers.Tyre (same keys plus owner_source_id and
owner_targets) for the exact generator-file actor bind correlation.
Live two-way validation awaits #572's runner; recorded as a follow-on
dependency, not a blocker for this closure.

## Tests and evidence

- tests/test_pikmin2_waterwraith_packaging_provider.py: 16 passed --
  agreement, 99-only staging, 99+98 owned staging, #572 contract shape,
  lone/misplaced/duplicate helper negatives, identity negatives,
  duplicate-generator negatives, cache replay with helpers, tamper and
  digest negatives.
- Preserved: tests/test_pikmin2_muse_packaging.py (12),
  family_install/install_binding/bombsarai_install suites -- 87 passed
  total, no behavior change on the four-candidate path.
- check_p2_handoff_gates.py is family-handoff scoped; packaging ships
  no gate table. No resolve markers are ever emitted by staging.

## Remaining work for the integrator

- Placement99 provider publication (slot/generator contract); then a
  generated session correlating seed source99, bind marker and the
  sidecars published here.
- #572 live runner validation against this interface.
