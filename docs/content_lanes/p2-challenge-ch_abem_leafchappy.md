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