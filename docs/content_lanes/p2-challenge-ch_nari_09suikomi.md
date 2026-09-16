# P0 source audit: P2 Challenge 26 ch_NARI_09suikomi (#558)

Lane `p2-challenge-ch_nari_09suikomi`. P0 only: source audit plus an
isolated import-contract adapter. No native build, no runtime, no ADMIT,
no playability claim. Full content acceptance (P1/P2) stays OPEN.

## Source identity

- Source ID `ch_NARI_09suikomi` (authoritative; English title unresolved and
  never guessed), UI index 25, table order 23.
- Retail definition `user/Mukki/mapunits/caveinfo/ch_NARI_09suikomi.txt`,
  pinned SHA-256
  `9d547811bc30a8970659c501b596afbbd903e11ed3229ce3e97e60104aaa5dc5`.
- Stage table `user/Matoba/challenge/stages.txt`, pinned SHA-256
  `59890efa80fe5a77d52b9a87301b97c91cd10c94ff9a3fb85c49b78dfae03cf1`.
- Catalogued baseline: `docs/PIKMIN2_CONTENT_INVENTORY.json` challenge entry
  (table_order 23); lane entry in `docs/PIKMIN_CONTENT_IMPORT_LANES.json`
  (`p2-challenge-ch_nari_09suikomi`, issue 558, content parent 137).

## Catalogued roster and timers (baseline, not a fresh decode)

- Floors: 1, complete coverage `[1]`; floor timer `[180.0]` seconds;
  legacy_time 450.0.
- Starting roster matrix (7 opaque native-color rows x 3 maturity columns):
  all zeros except row 1 / column 2 = 30 and row 2 / column 2 = 30.
  Total 60. Row/column positions are reported positionally because the
  inventory labels neither the native color nor the maturity each position
  names.
- Sprays: 1 bitter, 2 spicy. Treasure-count field: 0.
- These are definition inputs. They are not spawn instances, placements,
  or actor counts; weighted rows stay definitions until the accepted
  generator (#129) resolves them.

## Reserved implementation (this lane only)

- `experimental/content_lanes/p2-challenge-ch_nari_09suikomi.py`:
  `validate_stage_record()` (strict contract, fail-closed),
  `floor_coverage()` (complete 1-based floors),
  `resource_closure()` (definition totals, never `actors`/`placements`/
  `slots`), `verify_source_bytes()` (pinned-hash gate),
  `missing_prerequisites()` (read-only local probe with exact supply
  instructions), `blockers()`, `audit_packet()`, and an `audit` CLI that
  prints the packet as JSON. Standard library only.
- `tests/content_lanes/test_p2_challenge_ch_nari_09suikomi.py`: focused
  boundary tests -- baseline acceptance, missing/extra keys, identity
  mismatch, roster shape/sign, timer/floor disagreement, negative sprays,
  empty/foreign source bytes, absent vs hash-mismatched prerequisites,
  blocker identity. Synthetic inputs only.
- This file: lane specification and audit record.

## Source availability (exact prerequisite)

The retail caveinfo bytes were absent from this machine at P0 time (no
redistribution; local disc/ISO supply required). The adapter therefore
validates the catalogued baseline and hash-gates any future bytes; it
decodes no floor/generator content. P1 floor decode waits on a local
legal US GPVE01 rev0 disc/ISO containing the pinned file.

## Blockers to promotion (preparation is not blocked)

- #136 Challenge runtime framework: per-floor timing, keys/exits,
  scoring, retry, ordinary/deathless semantics unvalidated for this stage.
- #137 content parent: 59-floor audit consumes this packet.
- #129 generator: topology, seams, holes, weighted-row resolution.
- #130/#131 actors/assets: full resource closure and any unadmitted
  suikomi-encounter species.
- Local source bytes (see above); unresolved English display name.

## What P1/P2 still require

P1: private root/native pair, leased build, current starting-Pikmin
overlay, fresh centred 960x540 fixture, observed collisions/routes/actors
on pinned inputs. P2: deterministic replay, collection/exit semantics,
save/reload, death/extinction, reentry, receipt deduplication, no leakage.
None of that is claimed here; all six arena gates are UNTESTED and fixture
adoption is N/A (tooling-only P0).
