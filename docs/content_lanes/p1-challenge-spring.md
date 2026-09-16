# P0 import contract — p1-challenge-spring (lane p1-challenge-spring, #566)

Lane: p1-challenge-spring, issue #566, phase P0 only. Parent #531; existing content owner #52; integration owner #437. Source: `stages/chal3.ini` inside the local legal P1 asset tree (`dataDir/stages/chal3.ini`, 132 lines, sha256 `d1b0537e22c614a7101f56bf2da1f8ee44e2973ba6f7b30dc23b65e1a862de40`) plus the stage-info table `dataDir/stages/stages.ini` (sha256 `38536201e20e4019e32b549af93e7509c3f46fc0201bd7903fb91df38a58198f`). No native worktree, build, or runtime belongs to this slice.

## Catalogued contract (verified live)

| Field | Value |
|---|---|
| level_key | challenge:spring |
| native_area_id | 3 |
| stage_info_index | 19 |
| stage record | visible, name "Challenge 3", id 3, chid 3, file stages/chal3.ini, no generator block |
| navi_start | 0.0 0.0 |
| map_file | courses/stage3/yakusima.mod |
| day_multiply | 1.4 |
| dayMgr | numsettings 5: night, morning, day, evening, movie |
| new_room | index 0, radius 4.0, centre 0.0 0.0 |

`stage_info_index` counting follows the engine parser
(`engine/src/plugPikiColin/game.cpp`): `mStageIndex` increments once per
`new_map` token, so the 20th block (0-based 19) is Challenge 3. The
engine's `createMapObjects` (`newPikiGame.cpp`) consumes `map_file`,
`day_multiply` and `dayMgr`; `Engine/include/GlobalGameOptions.h:41`
documents `chid` as `mChalStageID`. The level-key to area/stage-file map
is reused from `experimental/levels.py` (never forked).

## Adapter (`experimental/content_lanes/p1-challenge-spring.py`)

Isolated per-source layer with a small local tokenizer (comments `//`,
brace blocks, quoted strings) that follows the engine field names. It
reuses `experimental.levels.BY_KEY` for the level-key mapping and reads
the asset tree read-only. Fail-closed: `FileNotFoundError` on absent
inputs, `ValueError` on malformed definitions or unknown top-level keys,
mismatch strings on contract drift. It emits a metadata packet and an
explicit blocker list; it starts no preview and emits no placements.

## Verified P0 result (live decode, this host)

- `stages.ini` block 19 decodes exactly to the catalogued record; the
  Spring stage ini decodes to navi_start, map_file, day_multiply,
  numsettings 5, all five timesetting label blocks (lights, ambient,
  fog) and the single starting new_room. Contract mismatches: none.
- Resource closure complete: geometry `courses/stage3/yakusima.mod`
  present, `default.gen` and `plants.gen` present with recorded sha256
  (`default.gen` `6950b44065844ccd0f83655b27aa9b51b0e6727eb63c26787846b130de44de55`,
  `plants.gen` `0b02213aa3c3cd80c3dbd293a1611973fdb1ca7207927fe89b8eea3413898b5a`).
- Tests: `tests/content_lanes/test_p1_challenge_spring.py` — 15 passed
  plus 17 malformed subtests (synthetic plus the live-decode test, which
  skips cleanly without a local asset tree).

## Exact blockers (framework, not decode failures)

- P1 runtime import needs existing owners #52 (timed/scored AP campaign),
  #100 (story destinations) and #6.
- Preview-only startup evidence already exists for all five layouts and
  is deliberately not repeated; travel/save/check logic and the timed AP
  campaign remain open.
- Story-destination and timed-campaign tracks must stay separate even
  though area id 3 is shared; level keys must stay qualified.
- No playability is claimed; full content issue #566 stays OPEN.

## Boundaries

Owns only the three reserved files. No shared parser/schema edits, no
native hooks, no asset redistribution, no ADMIT. Evidence and packets
live under `output/workflow/autofill/p1-challenge-spring`. The integrator
report is `output/deepseek-wave/inbox/autofill-566-result.md`.