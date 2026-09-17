# Gap-stages stage-select extension (#743)

Bounded root-only slice extending P2 challenge stage-select resolution to the
six gap keys, unblocking #735/#740 P1 boot. Implementation owner: Codex
through shared account 4laric. No family/shared/native edits, no runtime,
no ADMIT. All six arena gates UNTESTED.

## Problem

The #705 table resolves only `ch_NARI_01kusachi` and `ch_NARI_02tile` and
refuses everything else, so the P1 lanes for `ch_MUKI_houdai` (#735, running)
and `ch_MUKI_damagumo` (#740, blocked) cannot boot, and stages 540/549/551/553
have no P1 path at all.

## Solution (read-only wrap, no re-derivation)

`experimental/pikmin2_challenge_gap_stages_select.py` loads both committed
selectors byte-pinned and read-only, re-verifies kusachi/02tile resolve
unchanged, and resolves the six gap keys from the canonical plan+inventory
cross-check (same record shape and boot-request text as #669):

| Selector | Commit | Blob SHA-256 |
|---|---|---|
| #669 base | 01a35f3a5a74ed2a3fe1e07ddcde23184804010e | d8c2413cb60616571e3df02be1f9ef0b40ced36f9580a513fb760fa4203410f0 |
| #705 landing | 2cf2141868e98c561d633c1bcfd41560da64c223 | ff376f49917c2a3c9178cc03d3f30223bc79a470ad07f4f55cea79ca2faf7722 |

Any selector byte drift fails closed ("refusing substitute"). Provenance
labels: `base` (kusachi via #669), `landing-extended` (02tile via #705),
`gap` (six keys here). Unknown keys - including P1 `chal<N>` slots, wrong
case, and whitespace variants - are refused. Rendered records additionally
check path/identity consistency, so a record with a swapped valid key is
rejected.

## Gap keys resolved

`ch_MUKI_damagumo` (1 floor), `ch_MUKI_houdai` (2), `ch_NARI_03toy` (2),
`ch_NARI_06start3hard` (3), `ch_MUKI_redblue` (2), `ch_NARI_07whitepurple` (2).
Each record carries cave_id, cave_path, source_sha256, ui_index, table_order,
floors, floor_seconds, the 7x3 roster matrix, sprays, legacy_time and
treasure_count_field, all cross-checked plan-vs-inventory with roster/timer
shape validation.

## Integration-ready packet (for the single-writer integrator)

- Module: `experimental/pikmin2_challenge_gap_stages_select.py`
  (schema `p2-challenge-gap-stages-select-v1`).
- #735/#740 adopt `select_stage_extended(key)` for boot selection and
  `render_boot_request_extended(record)` for the request text; the still-missing
  native consumer hook is documented in the #669 module (`missing_hook()`).
- #705/#669 sources verified byte-identical before and after (hashes above);
  no shared file was touched - verify with `git status --short` (clean apart
  from the three new files) and `git diff --stat` (empty).
- Tests: `py -3.12 -m pytest tests/test_pikmin2_challenge_gap_stages_select.py -q`
  (5 passed, 21 subtests).

## Tests

Focused fail-closed coverage: all six gap keys resolve with identity fields;
kusachi/02tile unchanged with provenance labels; unknown/P1/malformed keys
refused; foreign and tampered records rejected at render.
