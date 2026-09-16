# p2-challenge-ch_nari_06start3hard import contract (P0, issue #549)

Lane `p2-challenge-ch_nari_06start3hard`, phase P0 (source audit and additive
import contract). Implementation owner: Codex through shared account `4laric`;
executing contributor Muse Spark 1.3 through OpenCode. Parent content issue
#137; autonomous backlog parent #569; integration owner #437. This document
specifies the validated import contract; the machine-readable packet is
produced by `experimental/content_lanes/p2-challenge-ch_nari_06start3hard.py`
and tested by
`tests/content_lanes/test_p2_challenge_ch_nari_06start3hard.py` (11/11 pass).

## Source identity

- Source ID `ch_NARI_06start3hard`, label `P2 Challenge 17`
  (English title unresolved; source ID and UI index 16 authoritative).
- Definition: `user/Mukki/mapunits/caveinfo/ch_NARI_06start3hard.txt`,
  recorded sha256
  `f64c2a43fa7b70fc7aa500cbd1c95d46e33a14546ac5e56d049b824d53b45d1b`
  (inventory evidence pin, equal to the plan pin; the disc was unavailable
  to this turn, so no bytes were re-extracted).
- Stage table: `user/Matoba/challenge/stages.txt`, recorded sha256
  `59890efa80fe5a77d52b9a87301b97c91cd10c94ff9a3fb85c49b78dfae03cf1`.
- Baseline inputs: lane-plan entry
  (`docs/PIKMIN_CONTENT_IMPORT_LANES.json`) and the 30-stage inventory
  collection (`docs/PIKMIN2_CONTENT_INVENTORY.json`, table orders and UI
  indices each exactly 0-29 with no collision/gap). All agree; any drift
  fails the adapter closed.

## Stage contract (verbatim definitions, not gameplay)

| Field | Pinned value |
|---|---|
| Table order / UI index | 25 / 16 |
| Floors | 3, with floor_seconds [100.0, 150.0, 180.0] (timer total 430.0) |
| Starting Pikmin | 4 total: native color index 1, maturity index 2, count 4 |
| Sprays | bitter 2, spicy 3 |
| Legacy time | 450.0 |
| Treasure-count field | 0 |

Native color/maturity indices are carried as indices, never guessed into
species names. Timers/sprays/populations are definition inputs for the P1
Challenge framework (#136), not observed gameplay.

## Explicitly open (not silently included)

- Per-floor enemy rosters: need the caveinfo bytes (exact missing
  prerequisite); no roster values invented.
- TheKey/hole/geyser, scoring, ordinary vs deathless completion, retry
  reset: unvalidated. The host `chal0` fixture is not Challenge mode.
- Full content acceptance and all runtime dependencies stay OPEN.

## Native/framework blockers (exact)

1. P1 runtime waits on the Challenge framework (#136: populations, sprays,
   per-floor timing, keys/exits, scores, retry and ordinary/deathless
   result semantics) and content/generator/actor contracts
   (#137, #129, #130, #131); no native build or runtime in P0.
2. Per-floor enemy roster decode needs local legal caveinfo bytes.
3. Display-name mapping open; stable source IDs authoritative.

## Validation evidence (this turn)

- `tests/content_lanes/test_p2_challenge_ch_nari_06start3hard.py`: 11/11
  pass (real sources validate; drifted/duplicated/corrupt/missing inputs
  rejected).
- `scripts/check_content_import_lanes.py` plan suite: unaffected
  (plan untouched; verified separately).
- Packet `packet.json` in the lane output directory with content sha256.