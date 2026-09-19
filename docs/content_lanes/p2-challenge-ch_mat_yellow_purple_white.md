# ch_MAT_yellow_purple_white P0 source audit and import contract
(lane p2-challenge-ch_mat_yellow_purple_white, #552)

Implementation owner: Codex through shared GitHub account `4laric`.
Executing worker: muse-l60 (approved pool session retained), generation 2.
Phase P0 only. Full content issue #552 stays OPEN; no playability,
admission, or promotion claim is made here.

## Source identity

- P2 Challenge 20: `ch_MAT_yellow_purple_white`, source
  `user/Mukki/mapunits/caveinfo/ch_MAT_yellow_purple_white.txt`
  (US GPVE01 revision 0).
- Recorded source pin `f6359e35e4fc27c5ef428ad3666cf419d2b93dc5a5877ba52fc8df0dc5ea94ae`
  (plan lane entry and inventory `source_sha256` agree; the adapter
  re-checks this at runtime and fails closed on drift).
- Canonical baseline: `docs/PIKMIN_CONTENT_IMPORT_LANES.json` lane
  `p2-challenge-ch_mat_yellow_purple_white` cross-checked field by field
  against `docs/PIKMIN2_CONTENT_INVENTORY.json` challenge stage
  `ch_MAT_yellow_purple_white` (`baseline_details` fails closed on drift).
- English title unresolved; source ID, table order (16) and UI index (19)
  are authoritative. No display names are guessed.

## Stage metadata (canonical baseline, not a new audit claim)

- Floors: 1; per-floor seconds: [230.0]; legacy total: 700.0 s.
- Starting roster by native color/maturity (7 rows x 3, verbatim):
  two empty rows, [30, 0, 0], [15, 0, 0], [15, 0, 0], two empty rows.
  Derived total: 60 Pikmin. Rows are preserved exactly; totals are sums.
- Sprays: bitter 0, spicy 2. Treasure-count field: 0 (a source field
  value, not a claim that the floor is treasure-free at runtime).

## Resource closure (adapter-computed, `resource_closure`)

Roster matrix, spray counts, 230 s timer, single floor, legacy 700 s,
table order 16, UI index 19. No actors, scores, results, or placements
are emitted: stage definitions stay definitions. `validate_manifest`
refuses `placements`/`actors`/`spawn_layout`/`scores`/`results` keys
outright, and requires native int/float field types exactly
(int 700 for legacy_time or int 230 for a timer is rejected, not
coerced).

## Exact missing prerequisite

The disc source is not available locally: no `caveinfo` tree exists
under any inspected asset root and the documented
`output/pikmin2-runtime/pikmin2-source-test.iso` is absent
(`locate_source` raises `MissingPrerequisite` naming the expected
relative path, the searched root, the recorded pin, and issue #552).
A present file with a non-matching hash raises `ContractViolation`
(wrong revision refused). Byte decoding and pin validation are
therefore P1 work gated on a US GPVE01 rev 0 disc or an existing
import tree - no values are invented here.

## Native/framework blockers (exact owners, no duplicates)

- P2 Challenge runtime framework: #136 (starting populations, sprays,
  per-floor timing, keys/exits, scores, retry, ordinary vs deathless
  result semantics; the host `chal0` fixture is not Challenge mode).
- Challenge content ownership: #137 (parent issue of this lane).
- Cave generation/seams/navigation: #129 (accepted generator pin; this
  lane forks nothing); actor/species semantics: #130, #131 and family
  owners.
- Unresolved enemy admission blocks promotion, not this preparatory
  work. TheKey/hole/geyser, scoring, and retry-reset validation are P1/P2
  scope with the framework owners above.

## P1 implementation packet (for the integrator)

1. Supply the disc/import tree; `locate_source` returns
   {path, sha256, bytes} only on an exact pin match.
2. Decode the single floor with the existing cave-definition brace
   parser (read-only reuse); shape the manifest as
   {cave_id, table_order, ui_index, floors,
   pikmin_by_native_color_and_maturity, legacy_time, bitter_sprays,
   spicy_sprays, treasure_count_field, floor_seconds} with native types.
3. Gate the decode with `validate_manifest` (this lane): exact field
   equality, 7x3 non-negative int roster, one positive float seconds
   value, no runtime-shaped keys.
4. Runtime activation needs the P1 acceptance from the lane plan plus
   validated dependency publications (#136/#137/#129/#130/#131); keep
   #552 open.

## Verification

- `py -3.12 -m pytest tests/content_lanes/test_p2_challenge_ch_mat_yellow_purple_white.py -q`
  -> 12 passed, 26 subtests passed (baseline agreement, pin format,
  closure preservation, valid manifest, identity/economy/roster
  rejections, fabricated-key refusal, missing-source prerequisite,
  wrong-revision rejection, summarize packet).
- Shared plan checker untouched and still green
  (`tests/test_content_import_lanes.py`).
- No native build, no runtime, no assets staged, no shared files edited.