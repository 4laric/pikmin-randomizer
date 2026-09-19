# P0 source audit: P2 Challenge 02 ch_MUKI_metal (issue #535)

Lane `p2-challenge-ch_muki_metal`. Implementation owner: Codex through
shared GitHub account 4laric; contributor Muse Spark 1.3 via OpenCode.
Private root `output/content-p0-535`, base
`b5309fb6c402c067afc7f1817ef06365bcb822d6`, branch `codex/content-p0-535`.
No native worktree/build/runtime in this P0 slice. Expansion P0 candidate:
integrator cherry-picks only the three reserved files below, never this
worktree's maintained-root history.

Reserved files (only these):

- `experimental/content_lanes/p2-challenge-ch_muki_metal.py` (new adapter)
- `tests/content_lanes/test_p2_challenge_ch_muki_metal.py` (20 tests)
- `docs/content_lanes/p2-challenge-ch_muki_metal.md` (this spec)

## 1. Source identity

| Field | Value | Authority |
|---|---|---|
| Source ID | `ch_MUKI_metal` | lane record / inventory |
| Source path | `user/Mukki/mapunits/caveinfo/ch_MUKI_metal.txt` | lane record / inventory |
| Expected sha256 | `903b43195c5f2d53683a462af4fe1383bfe0604551f2935cb78fc3f55d0de1f1` | `docs/PIKMIN2_CONTENT_INVENTORY.json` `source_sha256` |
| English title | unresolved (not guessed) | inventory limitations |
| UI index | 1; table_order 6 | lane details |
| Floors | 2; timers [130.0, 100.0] s | lane details |
| Starting Pikmin | 50 leaf of native color 0, nothing else | lane details matrix row 0 `[0, 0, 50]` |
| Sprays | bitter 1, spicy 1; legacy_time 0.0 | lane details |
| treasure_count_field | 0 | lane details |

## 2. Source availability (exact prerequisite)

No legal copy of the caveinfo bytes exists on this host. Checked
(read-only, nothing copied): supported ISO path
`output/pikmin2-runtime/pikmin2-source-test.iso` (absent),
`C:/Users/alari/bbft/dist/cohesion/pikmin/assets/dataDir/...` (P1 asset
tree, no `user/` dir), `native/pikmin2-research` (code only, no retail
data), full workspace filename search (no hit). The inventory itself
records "Metadata inventory only; no source assets copied."

Exact missing prerequisite: US GPVE01 revision 0 legal disc source
providing `user/Mukki/mapunits/caveinfo/ch_MUKI_metal.txt` with sha256
`903b4319...0de1f1`. The adapter's `locate_source()` reports this
instead of inventing values; `verify_bytes()` enforces the digest when
bytes become available.

## 3. Import contract

Decode reuses the shared parser (`experimental.pikmin2_cave.tree` /
`parameters` / `cave_definition`) unchanged: header count must equal
`c000` and node framing, floors must be individually authored
(`f000 == f001 == index`), gate/cap rows must be `['0']` (anything else
is rejected at decode, never carried forward). Weighted enemy rows keep
`(id, packed_weight, placement_type)` and treasure rows keep
`(id, packed_weight)` as definitions with counts only — never expanded
into placements. Floor coverage requires numbers exactly 1..2.
`floor_seconds`, sprays and the 7x3 roster matrix are preserved verbatim
from the lane record and shape-checked; they are metadata, not runtime
acceptance.

Per-floor unit files (`parameters['f008']`) and map/route/collision
closure belong to P1 against the real bytes; resource closure beyond the
timer/roster/spray preservation above is explicitly unevaluated.

## 4. Exact native/framework blockers (P1/P2 prerequisites)

- #136 — P2 Challenge runtime framework: starting color/maturity
  populations, sprays, per-floor timing, keys/exits, scores, retry,
  ordinary vs deathless result semantics.
- #137 — P2 Challenge content owner: 30 per-stage children, all 59
  floors on framework/generator pins.
- #129 — cave generation/seam/navigation pin (consume; do not fork).
- #130 / #131 — actor/asset/species and hazard closure incl.
  caps/helpers/held items; unresolved enemy admission blocks promotion,
  not preparatory work.

## 5. Implementation packet (for the integrator)

1. Cherry-pick the three reserved files from branch
   `codex/content-p0-535` (base `b5309fb6`); no shared-parser, schema,
   species, native, admission or other-lane edits included.
2. P1 entry criteria: legal GPVE01 rev 0 source for the exact
   prerequisite above + published pins for #136/#137/#129 + #130/#131
   species closure for the decoded enemy ids.
3. Run `py -3.12 -m pytest
   tests/content_lanes/test_p2_challenge_ch_muki_metal.py -q`
   (20/20), `py -3.12 scripts/check_content_import_lanes.py`
   (53 lanes intact), `py -3.12 -m pytest
   tests/test_content_import_lanes.py -q`.
4. Full content issue #535 stays OPEN; no playability claim; no ADMIT.

## 6. Validation evidence

- `output/workflow/content-expansion/p2-challenge-ch_muki_metal/tests-p0.log`
  (20/20), `lanes-check.log` (53 lanes intact),
  `plan-tests.log` (`tests.test_content_import_lanes`).
- Delivery packet `output/deepseek-wave/inbox/content-535-p0.md`.
