# ch_MUKI_redblue P0 source-audit packet (p2-challenge-ch_muki_redblue, #551)

Lane `p2-challenge-ch_muki_redblue`, issue #551, parent #137 (P2 Challenge
content) / #569 (autonomous backlog). Implementation owner: Codex through
shared account 4laric; executing worker muse-l61 (session
`opencode:ses_f589767f6ffevqCbXXLg35sDpL`, generation 2). P0 only:
source audit and additive import contract. No native build, runtime, ADMIT,
or asset redistribution. Full content issue stays OPEN for P1/P2.

## Source

- Stage `ch_MUKI_redblue` (P2 Challenge 19), definitions in
  `user/Mukki/mapunits/caveinfo/ch_MUKI_redblue.txt` (shift_jis, parsed with
  the existing `cave_definition` framing).
- Catalogue pin: 2 floors, table order 17, UI index 18, floor timers
  200.0 s + 200.0 s, bitter 1 / spicy 1, 25 leaf + 25 leaf in the first
  two native-color rows (Red/Blue pair per stage name; native color order
  is resolved by the #136 framework, not guessed here), treasure-count
  field 0, legacy time 0.0. Expected source hash
  `f81653301ec2f1b4f5cd1e51d2e15c81608bfbea0beaaadeb623de58db791434`.
  English title unresolved; source ID and UI index authoritative.
- Actual source bytes were NOT available in this turn, so no hash is
  validated here and no roster is claimed. The adapter reports the exact
  missing prerequisite instead of inventing values: legal US GPVE01 rev 0
  disc or an extracted `ch_MUKI_redblue.txt`.

## Adapter (`experimental/content_lanes/p2-challenge-ch_muki_redblue.py`)

- `decode_cave(text)` reuses `cave_definition` as-is and requires exactly
  the catalogued 2 floors numbered 1-2. Fails closed on empty input,
  malformed framing or floor-count mismatch.
- `summarize_roster(floors)` preserves source enemy/treasure IDs, packed
  weights and placement types as data; nothing is resolved to placements.
- `check_challenge(row)` validates an optional challenge row against the
  catalogued pin (order, UI index, timers, sprays, roster, treasure
  field, legacy time); without a row the manifest records
  `baseline_catalogued`.
- `build_manifest(text, sha256=None, challenge=None)` returns the isolated
  packet: cave/source IDs, `hash_status` (`hash_validated` only for the
  pinned hash), floor coverage, roster, challenge, single-file resource
  closure, the five runtime `blockers` and `playable: false` with an
  explicit no-placement policy.
- CLI: `--cave <path> [--output <path>]`; without `--cave` it prints the
  missing prerequisite and exits non-zero.

## Tests (`tests/content_lanes/test_p2_challenge_ch_muki_redblue.py`)

10 focused tests on synthetic caveinfo text (deliberately non-retail token
names): 2-floor decode with source rows preserved, floor-count/missing/
malformed failures, manifest closure + non-playability + no-placement
boundary, unvalidated/validated hash states, bad-hash/challenge/
playability rejection, exact prerequisite text, sha256 helper boundary.
No retail assets read.

## Verification

- `py -3.12 -m pytest tests/content_lanes/test_p2_challenge_ch_muki_redblue.py tests/test_content_import_lanes.py -q`
  -> 25 passed (log in lane output dir).
- `py -3.12 scripts/check_content_import_lanes.py` -> PASS 53 lanes
  (plan untouched; this slice only adds reserved files).

## Blockers for P1/P2 (unchanged, reported not resolved)

#136 Challenge runtime framework, #137 Challenge content, #129 cave
generation, #130/#131 actor/asset closure. Starting native color/maturity
roster, sprays, per-floor timers, keys/exits, scoring, ordinary vs
deathless completion, retry reset, and actual collision/routes all require
validated dependency publications plus the actual source bytes. The host
chal0 fixture is not Challenge mode and is never treated as such. No
playability claimed; issue #551 stays OPEN.
