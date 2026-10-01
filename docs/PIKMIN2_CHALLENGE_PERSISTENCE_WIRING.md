# Challenge persistence-wiring adapter (#708)

Lane `p2-challenge-persistence-wiring`, issue #708 (OPEN). Implementation owner:
Codex through shared account 4laric. Implements the exact first slice the
integrated #136 audit verdict selected (`p2-challenge-persistence-wiring-v1`):
a root-only adapter mapping the 30 retail challenge stages to their
persistence keys, fail-closed on drift. Consumes the integrated #136 scope
read-only; never duplicates it. No family/shared/native edits, no runtime, no
ADMIT. All six runtime gates UNTESTED.

## Problem it closes

`p2-challenge-ch_mat_route_rover-p1` (#561, blocked gen 11) passes its base P1
chain but its persistence probe FAILs 0/7: `challenge_save_key`,
`challenge_load_key`, `clear_flag`, `highscore`, `unlock`, `receipt_dedup`,
`reentry` (probe `persistence-probe-gen11.json`, sha256
`38d87f0015db1846458e098687d5638a4b6a34e5d280d23717bcde315dc9c56f`). The
integrated #136 audit verdict (`challenge136-persistence-audit-validation.log`,
sha256 `9a9b0ddf28475a3d3572081cc685d0960336d87fec93e3a065ba8811231ffec1`)
selected exactly this wiring slice and named the native save-layer owner plus
the #186 review for any native hookup. It was never published or landed.

## Key contract

Module `experimental/pikmin2_challenge_persistence_wiring.py` pins the 30
retail stages in table order (decoded this turn from
`user/Matoba/challenge/stages.txt` with the #136 framework decoder;
cross-checked against the content inventory with zero mismatches; ui_index
covers 0..29 exactly):

- Per stage `<cave_id>`: `p2_challenge_save_<id>`,
  `p2_challenge_load_<id>`, `p2_challenge_clear_<id>`,
  `p2_challenge_highscore_<id>`, `p2_challenge_unlock_<id>` (150 keys total,
  collision-checked).
- Probe markers per stage run (the exact lines the downstream probe counts):
  `P2_CHALLENGE_SAVE_KEY/LOAD_KEY/CLEAR/HIGHSCORE/UNLOCK/RECEIPT_DEDUP/REENTRY
  stage=<cave_id>` (7 artifacts in probe order).
- Stage-table bytes pin: offset 770387248, size 18875, sha256
  `59890efa80fe5a77d52b9a87301b97c91cd10c94ff9a3fb85c49b78dfae03cf1`.
- `verify_stage_table()` fails closed on any drift (count, order, ui_index,
  floors, unknown stage); `verify_table_bytes()` fails closed on hash/size
  drift; unsafe `cave_id` values are rejected before key derivation.
- `adapter_packet()` wraps the map for the single-writer integrator with
  source pins, hookup spec, blockers and limitations.

## Native save-layer hookup + #186 follow-on (specified, never edited)

Owner: #132 save owner contract (`saves_unlocks`) + #186 hook review. Route:
coordinator #570 review/publication; #186 hook review before any native
save-layer edit. Needs: PlayCommonData challenge clear-flag/highscore/unlock
anchors plus result-screen score computation per `compute_score` semantics.
Emits: the 7 probe artifacts per stage run per this key/marker contract.

## Verification

`tests/test_pikmin2_challenge_persistence_wiring.py`: 18 tests + 5 subtests
pass - 30-stage pin (unique ids, ui 0..29, known rows incl. route_rover ui 27
and crawler ui 29), all stages map 5 keys, exact 7 probe artifacts, 150-key
collision check, unknown/unsafe stage rejection, drift fail-closed (drop, swap,
extra, non-mapping, missing key), table-bytes gate (wrong bytes/size rejected;
real disc table bytes pinned), marker shape + unknown-artifact rejection,
packet shape + full 30-stage map coverage.

## Downstream consumer

`p2-challenge-ch_mat_route_rover-p1` (#561, blocked): its persistence probe
must observe 7/7 artifacts against this key/marker contract at runtime, then
save/reload acceptance. Enemy/actor scope stays with the #561 lane; save-tree
writes stay with the native hookup owner.

## Captain safety #632

Tooling-only, no runtime run: guard adoption is N/A here. Any runtime consumer
must adopt `scripts/p2_fixture_captain_guard.h`
(sha256 `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`)
with orimaDead/NaviDead/HP<=1 checks, CAPTAIN_DOWN + BLOCKED exit, a parked
captain and labelled protection.