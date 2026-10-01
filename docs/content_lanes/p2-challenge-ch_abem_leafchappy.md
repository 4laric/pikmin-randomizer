# P2 Challenge 18 ch_ABEM_LeafChappy -- P0 source audit and import contract (#550)

Lane p2-challenge-ch_abem_leafchappy; work class expansion; phase P0 only.
Implementation owner: Codex through shared account 4laric; executing
contributor Muse Spark 1.3 (worker muse-l58). Full content issue #550 stays
OPEN; no playability is claimed anywhere in this packet.

## Source identity

- Stage: ch_ABEM_LeafChappy (P2 Challenge 18, UI index 17, two floors),
  definition file user/Mukki/mapunits/caveinfo/ch_ABEM_LeafChappy.txt.
- Recorded pin: source_sha256
  49cc9076cede949786025b3bcd08ce60362096d8fe8f8b5330c725de4acd2baf,
  consistent across the lane entry
  (docs/PIKMIN_CONTENT_IMPORT_LANES.json lane
  p2-challenge-ch_abem_leafchappy), the inventory
  (docs/PIKMIN2_CONTENT_INVENTORY.json challenge.stages entry and its
  source_sha256 map), and the adapter's embedded pin (triple-consistency
  guard in tests).
- Local bytes: unavailable. No retail ISO is present in this workspace
  (output/pikmin2-runtime/ is empty; the supported source-test image is
  not a retail disc), and no caveinfo/ tree exists in the repo, native
  research checkout, or local asset staging. Exact prerequisite: a US
  GPVE01 revision 0 disc image exposing the member above (see adapter
  read_iso_entry), after which verify_source_hash pins observed bytes and
  the unit-pool arc/texts closure audit can run.

## Catalogued stage manifest (baseline, not decoded bytes)

From the lane entry details, agreeing field-for-field with the inventory
challenge stage entry:

- Floors: 2; per-floor seconds: [85.0, 100.0]; legacy_time: 400.0.
- Starting roster (native color/maturity indices, preserved as indices):
  7x3 matrix, colors 0-2 at maturity 0 nonzero: 10 each (30 leaf Pikmin).
- Sprays: bitter 1, spicy 1. Treasure count field: 11.
- Enemy roster, unit pools: unresolved until definition bytes decode
  (no roster invented here).

## Adapter contract (experimental/content_lanes/p2_challenge_ch_abem_leafchappy.py)

Schema p2-challenge-import-p0-1. Reuses shared pikmin2_cave_catalog.parse
unedited. Test-only synthetic fixtures exercise the real parser; the
adapter emits no placements (playable False, retail_generation False).

- verify_source_hash(data) -- observed-bytes pin check, fail-closed.
- hash_pin_consistency(lanes, inventory) -- triple-record drift guard.
- validate_stage_metadata(details) -- 7x3 roster matrix, timing, sprays,
  UI index 0..29, per-floor seconds coverage; range-checked.
- metadata_agreement(details) -- field-by-field baseline comparison;
  mismatches reported, never corrected.
- decode_source / occupied_floors / validate_floor_coverage -- fail-closed
  definition decode and 2-floor coverage.
- read_source_file / read_iso_entry -- exact missing-prerequisite errors.
- native_framework_blockers() -- exact owners below.
- summarize(...) -- reviewed P0 packet dict for integrator review.

Tests (tests/content_lanes/test_p2_challenge_ch_abem_leafchappy.py):
18 passed, 25 subtests passed -- pin format/triple consistency, drift and
tamper negatives, metadata validation and drift detection, decode
boundaries, malformed battery, coverage gaps, source/ISO boundaries
(including non-retail ISO rejection), metadata-only packet shape.

## Exact native/framework blockers (P1/P2 activation)

- #136 P2 Challenge runtime framework: starting color/maturity
  populations, sprays, per-floor timing, keys/exits, scores, retry and
  ordinary/deathless result semantics; nothing staged here.
- #137 P2 Challenge content: thirty per-stage children, all 59 floors
  audited and tested on framework/generator pins.
- #129 cave generation/seams/navigation (active #468): accepted generator
  pin required; nothing forked here.
- #130/#131 actor/assets/species: stage roster admission blocks
  promotion, not P0 preparation.

## Existing evidence preserved

Challenge framework/content lanes, cave generator lanes 34-51, and all
existing issue evidence are untouched; this lane consumes the shared
parsers, lane plan, and inventory as read-only references and duplicates
no existing stage work. English title remains unresolved per the lane
record; source ID and UI index are authoritative.

---

# ch_ABEM_LeafChappy P1 runtime import (lane p2-challenge-ch-abem-leafchappy-p1, #550)

Owner: Codex through shared account `4laric`. Extends the P0 adapter
(`experimental/content_lanes/p2_challenge_ch_abem_leafchappy.py`,
underscores; real-source decode helpers reused verbatim, no forked parser)
with a P1 import path that stages the decoded stage manifest into a private
run layout. No playability claim beyond observed evidence; no ADMIT.

## Source identity

- Stage `ch_ABEM_LeafChappy` (2 floors); source
  `user/Mukki/mapunits/caveinfo/ch_ABEM_LeafChappy.txt`, sha256
  `49cc9076cede949786025b3bcd08ce60362096d8fe8f8b5330c725de4acd2baf`
  (matches the P0 pin; verified against the local retail ISO on every run).
- Floor 1: LeafChappy_diamond_blue_l, Egg; treasures key, kouseki_suisyou,
  bell_yellow. Floor 2: FireChappy_key, Kochappy_be_dama_red; treasures
  apple, leaf_kare; Blue/YellowKochappy + Egg cap entries.
- Roster: 10/10/10 leaf (30 Pikmin); sprays 1 bitter + 1 spicy; timers
  85 s + 100 s; treasure field 11; ui_index 17.
- Reference score (zero receipts): 485 = 0 + 185 + 300 via the framework
  `compute_score` formula.

## Host-mode contract mapping

`host_stage_entry()` mirrors `native/pc_port/pc_p2_challenge_mode.h`
`p2challenge::StageEntry`: caveId, uiIndex 17, floorCount 2,
floorSeconds[8] = (85, 100, 0, ...), roster 7x3, bitterSprays/spicySprays
1/1. Values only; the native runtime binding of this entry is the missing
framework piece below, not claimed here.

## Run layout (private, per run)

`stage_run_layout()` writes `stage.json` (entry), `squad.json` (roster +
window), `expected.json` (BOOT/TICK/DONE markers, reference score,
captain-down token) and `manifest.json` into a fresh directory. It refuses
an existing directory and never touches engine inputs or saves.

## Runtime baseline (guarded room boot)

Fresh leased private build of the pinned native, fresh arena via the
current starting-Pikmin overlay, `PIKMIN_P2_ROOM_WINDOW=960x540`, captain
safety #632 adopted with the canonical guard hash recorded. Observed and
reported exactly: centered window line, live starting squad, active
gameplay entry, no immediate extinction. Challenge host markers
(`P2_CHALLENGE_MODE_*`) are validated by `validate_host_markers()` when a
wired runner emits them; their absence is reported as unobserved, never
synthesized.

## Exact blockers

- Host-mode runtime wiring (`challenge_host_mode` in the framework
  provider map): the native state machine exists but no runtime path feeds
  it stage entries; needs a #186-reviewed hook, not claimed here.
- Full stage P1 acceptance (collision/routes/actors/receipts) awaits that
  wiring plus family admission; gates stay UNTESTED.
- Captain safety #632: adopted for every observed tick; guard/source hashes
  recorded per run.