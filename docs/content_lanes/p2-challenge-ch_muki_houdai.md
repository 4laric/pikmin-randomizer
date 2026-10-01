# ch_MUKI_houdai P0 source-audit packet (p2-challenge-ch_muki_houdai, #541)

Lane `p2-challenge-ch_muki_houdai`, issue #541, parent #137. Implementation
owner: Codex through shared account 4laric; executing worker muse-l53
(session `opencode:ses_f58980693ffeuOoioNcyCB1vYz`, generation 2). P0 only:
source audit and additive import contract. No native build, runtime, ADMIT,
or asset redistribution. Full content issue stays OPEN for P1/P2.

## Source

- Stage `ch_MUKI_houdai` (P2 Challenge 09), definitions in
  `user/Mukki/mapunits/caveinfo/ch_MUKI_houdai.txt` (shift_jis, parsed with
  the existing `cave_definition` framing).
- Catalogue pin: 2 floors, table order 24, UI index 8, floor timers
  100.0 s + 150.0 s, bitter 1 / spicy 1, five colours of 10 leaf Pikmin,
  treasure-count field 0. Expected source hash
  `07cdf2cd492024548b9982a6ed63c40ba6c781bd114814339aefc9b8b35232f3`.
- Actual source bytes were NOT available in this turn, so no hash is
  validated here and no roster is claimed. The adapter reports the exact
  missing prerequisite instead of inventing values: legal US GPVE01 rev 0
  disc or an extracted `ch_MUKI_houdai.txt`.

## Adapter (`experimental/content_lanes/p2-challenge-ch_muki_houdai.py`)

- `decode_cave(text)` reuses `cave_definition` as-is and requires exactly
  the catalogued 2 floors numbered 1-2. Fails closed on empty input,
  malformed framing or floor-count mismatch.
- `summarize_roster(floors)` preserves source enemy/treasure IDs, packed
  weights and placement types as data; nothing is resolved to placements.
- `check_challenge(row)` validates an optional challenge row against the
  catalogued pin (order, UI index, timers, sprays, roster, treasure
  field); without a row the manifest records `baseline_catalogued`.
- `build_manifest(text, sha256=None, challenge=None)` returns the isolated
  packet: cave/source IDs, `hash_status` (`hash_validated` only for the
  pinned hash), floor coverage, roster, challenge, single-file resource
  closure, the five runtime `blockers` and `playable: false` with an
  explicit no-placement policy.
- CLI: `--cave <path> [--output <path>]`; without `--cave` it prints the
  missing prerequisite and exits non-zero.

## Tests (`tests/content_lanes/test_p2_challenge_ch_muki_houdai.py`)

10 focused tests on synthetic caveinfo text: 2-floor decode with source
rows preserved, floor-count/missing/malformed failures, manifest closure
+ non-playability + no-placement boundary, unvalidated/validated hash
states, bad-hash/challenge/playability rejection, exact prerequisite
text, sha256 helper boundary. No retail assets read.

## Verification

- `py -3.12 -m pytest tests/content_lanes/test_p2_challenge_ch_muki_houdai.py tests/test_content_import_lanes.py -q`
  -> 25 passed (log in lane output dir).
- `py -3.12 scripts/check_content_import_lanes.py` -> PASS 53 lanes
  (plan untouched; this slice only adds reserved files).

## Blockers for P1/P2 (unchanged, reported not resolved)

#136 Challenge runtime framework, #137 Challenge content, #129 cave
generation, #130/#131 actor/asset closure. Timers, sprays, roster,
keys/exits, scoring, retry/reset and actual collision/routes all require
validated dependency publications plus the actual source bytes. No
playability claimed; issue #541 stays OPEN.