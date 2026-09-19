# P0 source audit: P2 Challenge 22 ch_MIYA_oopan (issue #554)

Lane `p2-challenge-ch_miya_oopan` (parent #569; content owner #137).
Implementation owner: Codex through shared GitHub account 4laric;
contributor Muse Spark 1.3 via OpenCode. Private root
`output/autofill-root-554`, base
`533e7f4a1edbae5cbc59f44f8f543d84142fe158`, branch `codex/autofill-554`.
No native worktree/build/runtime in this P0 slice. Expansion P0 candidate:
integrator cherry-picks only the three reserved files below, never this
worktree's maintained-root history.

Reserved files (only these):

- `experimental/content_lanes/p2-challenge-ch_miya_oopan.py` (new adapter)
- `tests/content_lanes/test_p2_challenge_ch_miya_oopan.py` (21 tests)
- `docs/content_lanes/p2-challenge-ch_miya_oopan.md` (this spec)

## 1. Source identity

| Field | Value | Authority |
|---|---|---|
| Source ID | `ch_MIYA_oopan` | lane record / inventory |
| Source path | `user/Mukki/mapunits/caveinfo/ch_MIYA_oopan.txt` | lane record / inventory |
| Expected sha256 | `76fad15ebc041af12f05e887ad64c324354d49fc89acad57d043d9881951b4b9` | `docs/PIKMIN2_CONTENT_INVENTORY.json` `source_sha256` |
| English title | unresolved (not guessed) | inventory limitations |
| UI index | 21; table_order 15 | lane details |
| Floors | 1; timer [150.0] s | lane details |
| Starting Pikmin | 5 young of each native color 0..4 (rows `[5,0,0]`); colors 5-6 empty | lane details 7x3 matrix |
| Sprays | bitter 0, spicy 0; legacy_time 0.0 | lane details |
| treasure_count_field | 0 | lane details |

The staged starting roster (five colors x five young) is preserved
verbatim; `starting_roster()` exposes it as `{native_color, maturity,
count}` for non-zero cells only. This is metadata staging, not a runtime
observation.

## 2. Source availability (exact prerequisite)

No legal copy of the caveinfo bytes exists on this host. Checked
(read-only, nothing copied): supported ISO path
`output/pikmin2-runtime/pikmin2-source-test.iso` (absent),
`C:/Users/alari/bbft/dist/cohesion/pikmin/assets/dataDir/...` (P1 asset
tree, no `user/` dir), `native/pikmin2-research` (absent in this
worktree / code-only), full workspace filename search (no hit). The
inventory itself records "Metadata inventory only; no source assets
copied."

Exact missing prerequisite: US GPVE01 revision 0 legal disc source
providing `user/Mukki/mapunits/caveinfo/ch_MIYA_oopan.txt` with sha256
`76fad15e...951b4b9`. The adapter's `locate_source()` reports this
instead of inventing values; `verify_bytes()` enforces the digest when
bytes become available.

## 3. Import contract

Decode reuses the shared parser (`experimental.pikmin2_cave.tree` /
`parameters` / `cave_definition`) unchanged: header count must equal
`c000` and node framing, floors must be individually authored
(`f000 == f001 == index`), gate/cap rows must be `['0']` (anything else
is rejected at decode, never carried forward). Weighted enemy rows keep
`(id, packed_weight, placement_type)` and treasure rows keep
`(id, packed_weight)` as definitions with counts only - never expanded
into placements. Floor coverage requires number exactly 1 (single-floor
stage). `floor_seconds`, sprays and the 7x3 roster matrix are preserved
verbatim from the lane record and shape-checked; they are metadata, not
runtime acceptance.

Per-floor unit files (`parameters['f008']`) and map/route/collision
closure belong to P1 against the real bytes; resource closure beyond the
timer/roster/spray preservation above is explicitly unevaluated.

## 4. Exact native/framework blockers (P1/P2 prerequisites)

- #136 - P2 Challenge runtime framework: starting color/maturity
  populations, sprays, per-floor timing, keys/exits, scores, retry,
  ordinary vs deathless result semantics.
- #137 - P2 Challenge content owner: 30 per-stage children, all 59
  floors on framework/generator pins.
- #129 - cave generation/seam/navigation pin (consume; do not fork).
- #130 / #131 - actor/asset/species and hazard closure incl.
  caps/helpers/held items; unresolved enemy admission blocks promotion,
  not preparatory work.

## 5. Implementation packet (for the integrator)

1. Cherry-pick the three reserved files from branch `codex/autofill-554`
   (base `533e7f4a`); no shared-parser, schema, species, native,
   admission or other-lane edits included.
2. P1 entry criteria: legal GPVE01 rev 0 source for the exact
   prerequisite above + published pins for #136/#137/#129 + #130/#131
   species closure for the decoded enemy ids.
3. Run `py -3.12 -m pytest
   tests/content_lanes/test_p2_challenge_ch_miya_oopan.py -q` (21/21),
   `py -3.12 scripts/check_content_import_lanes.py` (53 lanes intact),
   `py -3.12 -m pytest tests/test_content_import_lanes.py -q`.
4. Full content issue #554 stays OPEN; no playability claim; no ADMIT.

## 6. Validation evidence

- `output/workflow/autofill/p2-challenge-ch_miya_oopan/tests-p0.log`
  (21/21), `lanes-check.log` (53 lanes intact), `plan-tests.log`
  (`tests.test_content_import_lanes`).
- Delivery packet `output/deepseek-wave/inbox/autofill-554-result.md`.
