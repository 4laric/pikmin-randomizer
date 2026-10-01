# ch_NARI_02tile P1 private runtime import (#537)

First P1 slice for the challenge-3 partition (P2 challenge stage keys whose
lowercased UTF-8 sha256 mod 4 == 3). This extends the P0 import contract for
P2 Challenge 05 `ch_NARI_02tile` (2 floors, `ui_index` 4, timers 200/150 s,
5 spicy sprays) with a private runtime-import path. Implementation owner:
Codex through shared account `4laric`. No ADMIT, no shared edits, no ledger
writes.

## What the P1 module does

`experimental/content_lanes/ch_nari_02tile.py` loads the P0 adapter
(`experimental/content_lanes/p2-challenge-ch_nari_02tile.py`) **by path** and
reuses its real-source decode/baseline helpers (`source_bytes`,
`verify_source`, `decode_text`, `decode_full`, `asset_closure`,
`import_contract`); the adapter is never edited or forked. It validates the
decoded manifest against the canonical baseline (cave id, 2 floors, ui_index
4, floor timers, spray counts), hash-pins the integrated host-mode module
(`native/pc_port/pc_p2_challenge_mode.{h,cpp}` at native commit `ada6bda4`),
and stages a private run layout:

- `stage-manifest.json` (validated cave identity, floors, timers, source sha)
- `p1-input-package.json` (source + host-mode pins + #632 guard + window/squad)
- `run-plan.json` (960x540 centred startup, live squad, host-mode select by
  ui_index, per-floor timer, retry, expected receipt-parseable markers, and
  the exact no-boot-path blocker statement)

All three files carry sha256 hashes. Any drift fails closed (`P1Error`).

## Run plan and boot path

The run plan boots through the existing #675 stage-boot fixture
(`--experimental-pikmin2-room --experimental-challenge-stage ch_NARI_02tile`
with a `p2-challenge-stage-select.txt` sidecar), supervised with a bounded
timeout. Expected receipt-parseable markers: `P2CHALLENGE_STAGE_ENTRY`,
`P2_ROOM_READY`, and the #632 `P2_FIXTURE_CAPTAIN_DOWN` interruption path.
The plan records the honest fallback: if the fixture boots the room-preview
stage instead of this stage content, all six gates stay UNTESTED and that
exact blocker is recorded rather than overclaimed.

## Captain safety (#632)

Any runtime run from this plan adopts `scripts/p2_fixture_captain_guard.h`
(sha256 `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`)
or a tested equivalent: orimaDead/NaviDead/HP<=1 before every pause/movie
return or observed tick, CAPTAIN_DOWN + BLOCKED exit, parked captain, no
blanket invincibility, recorded hashes. Protected observation is labelled and
cannot prove captain damage.

## Gates and acceptance

All six gates (`identity_spawn`, `movement_animation`, `attacks_receivers`,
`death_corpse`, `transport_reward`, `cleanup_reentry`) stay UNTESTED unless
genuinely observed in a real boot; no playability claim beyond observed
evidence. Downstream: #537 challenge-3 P1 acceptance.