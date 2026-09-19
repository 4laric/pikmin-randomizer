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

## P1 private runtime import and first playable acceptance (#549)

The module adds a P1 import path that reuses the pinned P0 constants and
`ledger()` helpers, decodes the two live sources through the shared retail
parser (`experimental.pikmin2_cave_catalog.parse`; enemy IDs from research
`enemyInfo.cpp`, treasure IDs from the disc pellet archive) plus a small
strict stage-block parser owned in the adapter (no shared challenge decoder
exists; nothing forked), and stages the decoded stage into a private run
layout booted by the integrated Challenge content-loading runtime (#701).

- `p1_contract()` / `check_lane_entry()` rebuild the stage contract from the
  P0 pins and require the lanes document to match them exactly.
- `decode_cave()` / `decode_stage()` / `verify_stage()` /
  `verify_cave_contract()` decode and cross-check the live caveinfo
  (`f64c2a43...`) and stage table (`59890efa...`): 3 floors tiling 1..3,
  roster 4 reds (native color 1, maturity 2), timers [100.0, 150.0, 180.0],
  legacy 450.0, bitter 2 / spicy 3, ui 16.
- `verify_closure()` resolves unit-pool resource closure; all three pools
  decode live from disc with full arc/texts asset closure (provenance
  `live`): `1_units_big2_kusachi.txt` (`a0ebbb43...`, room
  `room_big2_kusachi`), `1_NARI_4x4b_conc.txt` (`65191386...`, room
  `room_4x4b_4_conc`), `3_units_d_f_ujikou_tile.txt` (`3b3233f5...`).
- `floor_manifest()` / `content_sidecar` / `generate_sidecar` /
  `preview_record` / `stage_manifest_record` build the run layout:
  `p2-challenge-content.txt` (P2_CHALLENGE_CONTENT_1; stage/floor/pool/spawns/
  anchor), `p2-cave-generate.txt`, `stage-manifest.json` and `preview.json`.
- `stage_run_layout(...)` writes the four files, hashes them and fails closed
  on any missing/undecodable input; boot floor is floor 1.
- `parse_run_markers(log)` / `verify_receipt(markers)` parse and enforce the
  receipt-parseable runtime markers (content SELECTED/SPAWN_COVERED/READY/LIVE/
  PASS, room collision `P2_ROOM_GROUND`, actor `P2_PLACEMENT_PROBE`), and refuse
  a captain-down receipt.

Preserved stage facts: floors=3, floor_seconds=[100.0, 150.0, 180.0],
legacy_time=450.0, bitter_sprays=2, spicy_sprays=3, treasure_count=0,
ui_index=16, roster 7x3 with starting_pikmin=4. Boot floor 1: pool
`1_units_big2_kusachi.txt`, anchor hole, 7 spawn intents (Clover, Hana with
silver_medal cargo, Magaret, Ooinu_s, RandPom, Tanpopo, key); floor 2 pool
`1_NARI_4x4b_conc.txt` (RandPom, Chappy with be_dama_red_l cargo; key,
gold_medal; 1 gate); floor 3 pool `3_units_d_f_ujikou_tile.txt` (Tank with key
cargo, Tank with be_dama_red_l cargo, Hiba x6, ElecHiba; bell_red; 1 gate).

### Observed runtime receipt (private leased build)

Fresh private leased build of native `f91c2143` (elastic cap respected, leased
CLI) plus the content-loading fixture, run over the staged run layout with a
960x540 centred window. Observed markers (runtime.log):

```
[PC Port] SDL2 Window & OpenGL Context initialized successfully (960x540)
P2_CHALLENGE_CONTENT_SELECTED cave=ch_NARI_06start3hard floor=1 pool=1_units_big2_kusachi.txt spawns=7 anchor=hole
P2_CHALLENGE_CONTENT_SPAWN_COVERED id=<7 ids> count=1
P2_CHALLENGE_CONTENT_READY cave=ch_NARI_06start3hard floor=1 squad=20 captain_parked=1
P2_CHALLENGE_CONTENT_LIVE squad=20 actors=1 tick=2
P2_ROOM_GROUND ... (collision probes)
P2_PLACEMENT_PROBE actors=1 evidence_slots=1
PASS P2_CHALLENGE_CONTENT_RUN content=1
```

`verify_receipt` accepts this receipt. No `P2_FIXTURE_CAPTAIN_DOWN`, no
FAIL/REFUSED.

Captain safety (#632): the guard is adopted first-after-engine-idle, before
movie/pause/UI returns and every observed tick; the captain is parked outside
attack reach; guard header sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`. No blanket
invincibility; this is labelled protected observation.

Honest limits: the observed live squad is the current starting-Pikmin overlay
(20); the stage roster (starting_pikmin=4) is the decoded contract carried in
the manifest. All six arena gates stay UNTESTED; this is a boot/collision/actor
receipt, not gameplay acceptance. The engine host-mode stage table
(`pc_port/pc_bbft.cpp` kP2ChallengeStages) still lists only `ch_NARI_01kusachi`,
so the `--experimental-challenge-stage` arm is not yet generic for start3hard;
that is the remaining P2 blocker for the stage-select path (scoped shared review
to the host-mode owner), not for this content-loading boot receipt.
