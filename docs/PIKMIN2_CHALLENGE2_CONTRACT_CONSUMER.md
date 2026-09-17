# Challenge-2 contract consumer map (#137)

Lane `shard-challenge-2-contract-consumer`, issue #137 (OPEN, parent #586).
Review-only slice: consume the published P2 challenge framework contract
(issue #136, commit `b9bb55f0`) for the seven challenge-2 stages instead of
inventing prerequisites. No build, no runtime, no shared edits, no ADMIT.
All six runtime gates stay UNTESTED; no playable claim is made. All values
below come from decoding the real retail stage table through the contract
parser plus the pinned inventory cross-check.

## 1. Inputs (hash-pinned)

- Retail stage table `user/Matoba/challenge/stages.txt`, 18875 bytes,
  sha256 `59890efa80fe5a77d52b9a87301b97c91cd10c94ff9a3fb85c49b78dfae03cf1`
  (matches the inventory pin; decoded as shift_jis, 30 stages).
- Contract: `experimental/pikmin2_challenge_framework_contract.py` at
  commit `b9bb55f0` (schema module + validator + doc, 7/7 contract tests).
- Inventory: `docs/PIKMIN2_CONTENT_INVENTORY.json` (30 challenge rows).
- Partition: the seven keys whose lowercase sha256 mod 4 == 2.

## 2. Consumer map (decoded + cross-checked, zero mismatches)

| Stage | Floors | Pop | Timer total | Ready | Blockers |
|---|---|---|---|---|---|
| ch_ABEM_LeafChappy | 2 | 30 | 185.0 | True | none |
| ch_MAT_conc_cave | 3 | 2 | 220.0 | True | none |
| ch_MAT_flier | 1 | 50 | 160.0 | True | none |
| ch_MAT_limited_time | 1 | 40 | 130.0 | True | none |
| ch_MAT_t_hunter_hana | 1 | 80 | 145.0 | True | none |
| ch_MUKI_bigfoot | 1 | 50 | 200.0 | True | none |
| ch_MUKI_metal | 2 | 50 | 230.0 | True | none |

Ready here means definition-complete (non-empty squad, timer-per-floor,
valid sprays) under the contract unsupported list below - it is NOT runtime
acceptance. Full packet with sha256:
`output/workflow/autofill/planning-shards/challenge-2/prepared/shard-challenge-2-contract-consumer/out/packet.json`
(packet sha256 `d44148f9f6023a7fcf57646423342f456988b38dfb11f69e2c5f5965d765ddb4`).

## 3. First executable P1 slice (partition-correct)

`ch_MAT_limited_time` (1 floor, 130 s, pop 40): fewest floors, smallest
timer total, lowest ui_index among single-floor stages. Owners: host mode =
new framework lane (to dispatch, routed to #570, never duplicated here);
generation holes #129; actors #130/#131; saves+unlocks #132; treasure #140;
stage content = the seven done P0 lanes. Unsupported semantics per the
contract: challenge_host_mode, coop_2p, key_completion, result_screen.

## 4. Provider routing (no duplicates)

- Missing challenge host-mode lane -> #570 (stage select, squad/spray
  application, mTimeLimit countdown).
- Generation/actors/saves/treasure -> #129/#130/#131/#132/#140 as named by
  the contract framework_providers map.
- Stage content P0: all seven lanes done; manifest holds tooling items for
  547/550/559.

## 5. Module and tests

`experimental/pikmin2_challenge2_contract_consumer.py` (imports the
contract artifact, never forks the parser; partition filter, cross-check
delegation, readiness rules, deterministic first slice, packet builder).
`py -3.12 -m pytest tests/test_pikmin2_challenge2_contract_consumer.py -q`
-> 12 passed (synthetic fixtures only; real-decode evidence above was run
manually for this review).

## 6. Honesty notes

- Real decode executed against the local ISO for evidence only; the
  committed tests stay hermetic (synthetic) so they run anywhere.
- No gate flipped; no admission claim; captain-safety #632 not applicable
  (no runtime run; recorded here as N/A with the guard reference
  scripts/p2_fixture_captain_guard.h for any future runtime spec).