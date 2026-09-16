# P1 Challenge Trial P0 source audit and import contract
(lane p1-challenge-trial, #567)

Implementation owner: Codex through shared GitHub account `4laric`.
Executing worker: muse-l60 (approved pool session retained), generation 2.
Phase P0 only. Full content issue #567 stays OPEN; no playability,
admission, or promotion claim is made here.

## Source identity

- P1 Challenge Trial; source `stages/chal4.ini` under a P1 dataDir asset
  root (observed at `C:/Users/alari/bbft/dist/cohesion/pikmin/assets`,
  read-only).
- Observed file: 2484 bytes, sha256
  `424771962bb01f908f0f8e4370bb85ec201299c059d28f94d102289752cbf0f4`
  (recorded observation of the local copy, not a canonical plan pin:
  the plan keeps P1 source hashes null by design).
- Canonical baseline: `docs/PIKMIN_CONTENT_IMPORT_LANES.json` lane
  `p1-challenge-trial` cross-checked against the shared native
  destination row `challenge:trial` in `experimental/levels.py`
  (key, area ID 4, stage file, 16+area index rule) by
  `experimental/content_lanes/p1-challenge-trial.py`
  (`baseline_details` fails closed on any drift).
- Level key `challenge:trial` stays qualified despite the shared native
  area ID 4; story-destination (#100) and timed-campaign (#52) tracks
  stay separate. No display names are guessed.

## Decoded definitions (structural decode of the observed file)

- Directives: `navi_start 0.0 0.0`, `map_file
  courses/laststage/garden.mod` (model resolves under the asset root:
  `dataDir/courses/laststage/garden.mod` present), `day_multiply 1`.
- `dayMgr`: `numsettings 5` with contiguous `timesetting 0..4` blocks.
- `new_room` starting record: `index 0`, `radius 4.0`,
  `centre 0.0 0.0`.
- No unsupported top-level names; braces balanced. Lighting/fog rigs
  are counted, never interpreted.

## Resource closure (adapter-computed, `resource_closure`)

Spawn position, resolved map model, day multiplier, 5 timesettings, and
the starting-room record. No actors, scores, results, or placements are
emitted: stage definitions stay definitions. `validate_manifest`
requires native int/float field types exactly and refuses
`placements`/`actors`/`spawn_layout`/`scores`/`results`/`checks`/
`receipts` keys outright.

## Native/framework blockers (exact owners, no duplicates)

- P2 Challenge runtime framework: #136 (starting populations, sprays,
  per-floor timing, keys/exits, scores, retry, ordinary vs deathless
  result semantics; the host `chal0` fixture is not Challenge mode).
- Challenge content ownership: #137 (parent issue of this lane).
- Cave generation/seams/navigation: #129 (accepted generator pin; this
  lane forks nothing); actor/species semantics: #130, #131 and family
  owners.
- Story destinations/saves: #100; timed AP campaign: #52; shared
  randomizer core: #6.
- Unresolved enemy admission blocks promotion, not this preparatory
  work. Retry/reconnect/check deduplication and remote-upgrade playtest
  are P1/P2 scope with the framework owners above.

## P1 implementation packet (for the integrator)

1. Supply the P1 asset root; `locate_source` returns
   {path, sha256, bytes} and `summarize` runs the full
   locate -> decode -> closure -> manifest chain (verified green
   against the local copy in tests).
2. Shape any re-decode as {level_key, native_area_id,
   stage_info_index, tracks, source_sha256, navi_start, map_model,
   day_multiply, timesettings, new_room} with native types.
3. Gate the decode with `validate_manifest` (this lane): exact
   identity, exact observed hash, exact decoded fields, no
   runtime-shaped keys.
4. Runtime activation needs the P1 acceptance from the lane plan plus
   validated dependency publications (#136/#137/#129/#130/#131,
   #100/#52/#6); keep #567 open. Do not repeat preview-only import:
   all five layouts already carry native preview startup evidence.

## Verification

- `py -3.12 -m pytest tests/content_lanes/test_p1_challenge_trial.py -q`
  -> 13 passed, 19 subtests passed (baseline agreement, synthetic
  decode, imbalance/duplicate rejection, unknown-name listing, valid
  manifest, identity/economy/roster rejections, fabricated-key refusal,
  missing-source prerequisite, local-copy characterization incl. model
  resolution and full manifest validation, summarize packet).
- Shared plan checker untouched and still green
  (`tests/test_content_import_lanes.py`).
- No native build, no runtime, no assets staged, no shared files edited.