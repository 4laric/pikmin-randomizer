# P2 Challenge 08 ch_MUKI_bigfoot — P0 import contract (issue #539)

Owner: Codex through shared account 4laric. Lane `p2-challenge-ch_muki_bigfoot`, P0 only.
Metadata and import contract only; no claim of playability, no runtime import, no ADMIT.

## Source identity

- Source ID `ch_MUKI_bigfoot` (authoritative; English title unresolved), UI index 7.
- Disc path `user/Mukki/mapunits/caveinfo/ch_MUKI_bigfoot.txt`, pinned SHA-256
  `9d3efaf030587a94366bf2db7ed26aecfd93f37b806708061bd218440a2a782f`
  (docs/PIKMIN2_CONTENT_INVENTORY.json, docs/PIKMIN_CONTENT_IMPORT_LANES.json).
- Actual disc bytes are unavailable locally ("metadata inventory only; no source
  assets copied"). The adapter fails closed with the exact missing prerequisite
  (disc path plus expected hash) instead of inventing values.

## Floor coverage and preserved data

- Floors: 1; floor timer: 200.0 s; table order 14.
- Starting roster by native color/maturity (pinned baseline, counts only):
  rows `[0, 25, 0, 0, 25, 0, 0]`, total 50. Never rendered as placements.
- Spicy sprays 2, bitter sprays 0, treasure-count field 0, legacy time 0.0.
- Weighted enemy/treasure rows decode as definitions (id plus packed weight);
  the adapter never emits positions, actor counts or runtime placements.

## Adapter (`experimental/content_lanes/p2-challenge-ch_muki_bigfoot.py`)

Reuses the shared caveinfo brace grammar (`tree`, `parameters`, `weighted`
from experimental.pikmin2_cave) without modifying it. Entry points:
`missing_prerequisite`, `validate_source_bytes`, `load_source`, `decode_stage`,
`roster_totals`, `resource_closure`, `stage_contract`. Malformed input raises
`MalformedStage`; absent source raises `MissingSource` carrying the prerequisite.

## Tests (`tests/content_lanes/test_p2_challenge_ch_muki_bigfoot.py`)

Eight focused tests: pinned identity, missing-source prerequisite wording, empty
and mismatched source bytes, minimal-stage decode with placement-key ban,
six malformed variants, roster preservation and rejection of bad rows,
blocker closure contents, contract packet shape and limitations.

## Exact blockers (runtime dependencies stay OPEN)

- #136 P2 Challenge runtime framework: starting populations, per-floor timing,
  keys/exits, scores, retry, ordinary/deathless semantics.
- #137 P2 Challenge content: per-stage completion across all 59 floors.
- #129 generator/seams/navigation (with lanes 34–51, #468); #128, #130, #131
  actor/assets/species and hazards.
- Missing prerequisite above gates any actual stage-byte decoding.

## Delivery

Reserved files only; no shared edits. Test evidence is captured in the lane
output directory. Full content issue #539 stays open for P1/P2.
