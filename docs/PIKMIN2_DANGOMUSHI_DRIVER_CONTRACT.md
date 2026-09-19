# DangoMushi natural-death/reset driver contract (#664)

Lane `dangomushi94-driver-contract`, issue #664 (OPEN, assigned 4laric).
Implementation owner: Codex through shared account 4laric. Review-only packet
for the #376 family owner, unblocking stopped consumer
`dangomushi94-death-cleanup-observer` (gates 4 death_corpse and 6
cleanup_reentry). No family edits, no shared edits, no builds, no runtime, no
ADMIT. All six gates UNTESTED.

## 1. Finding: no family-side change is required

Read-only inspection of the family module
`native/pc_port/pc_p2_dangomushi.cpp` (ref `claude/p2-deepseek-wave-native`,
sha256 `7bfa206c518e49a46d17802778fc0c7c8b7deb9f0db0c499d186431cf28ecb36`,
1035 lines) shows every hook the driver needs already exists.
Accordingly the exact family patch is EMPTY (recorded, not omitted). If the
owner prefers an explicit hook, they may request one against these anchors;
nothing is applied here.

| Anchor | File:line | Verified text |
|---|---|---|
| reset | pc_p2_dangomushi.cpp:668 | `void pc_p2_dangomushi_reset() {` |
| forget | pc_p2_dangomushi.cpp:675 | `void pc_p2_dangomushi_forget(BTeki* actor) { actors.erase(...); }` |
| damage gate | pc_p2_dangomushi.cpp:706 | `bool pc_p2_dangomushi_invulnerable(const BTeki* actor) {` |
| damage accepted | pc_p2_dangomushi.cpp:715 | `P2_DANGOMUSHI_DAMAGE_ACCEPTED ... stickable=1 ...` |
| damage rejected | pc_p2_dangomushi.cpp:725 | `P2_DANGOMUSHI_DAMAGE_REJECTED ... invulnerable=1 ...` |
| setup | pc_p2_dangomushi.cpp:732 | `void pc_p2_dangomushi_setup() {` |
| bind | pc_p2_dangomushi.cpp:823 | `P2_DANGOMUSHI_BIND generator=%u source_id=94 visual_only=0` |
| death guard | pc_p2_dangomushi.cpp:852 | `if (actor->mHealth <= 0.0f && s.state != DANGO_DEAD) {` |
| death marker | pc_p2_dangomushi.cpp:854 | `P2_DANGOMUSHI_DEAD generator=%u source_id=94 health=0` |
| death enter | pc_p2_dangomushi.cpp:858 | `setState(actor, s, DANGO_DEAD, "dead");` |
| corpse die | pc_p2_dangomushi.cpp:1020 | `if (s.stateTime >= clipDuration("dead")) actor->die();` |

All 11 anchors re-verified against the pinned file this turn
(`verify_anchors` PASS). Absence note: no sunset/captain driver lives in this
module; captain safety is fixture-side (#632), not a family hook.

## 2. Driver specification (fixture-side; the change under review)

1. **Bind**: run `pc_p2_dangomushi_setup()` against the wanted generator;
   require TEKI vehicle + `P2_DANGOMUSHI_BIND`.
2. **Damage**: real free-squad Attack orders only; proceed on
   `P2_DANGOMUSHI_DAMAGE_ACCEPTED` windows (Turn stickable window); no
   `mHealth`/Transport writes. Rejections (`DAMAGE_REJECTED`) are expected
   outside the window, not failures.
3. **Death**: await `P2_DANGOMUSHI_DEAD health=0` after observed natural health
   decreases; require `die()` via the dead-clip path (line 1020).
4. **Corpse**: locate the engine corpse pellet via `mPelletView`; require the
   generic `P2_BATCH3_DRAW corpse=1 key=DangoMushi` leg after death.
5. **Reset/rebirth**: `pc_p2_dangomushi_forget` + `reset`, generator re-init,
   `setup`; require a second same-generator `P2_DANGOMUSHI_BIND` with
   stale/fresh proof (no stale handle survives).

Fail-closed bounds (for the implementing lane): bounded attempt budget on the
damage window; any injected marker or captain-down evidence fails the run;
gate 5 stays family-dependent (Pod receipt only if the family emits one).

## 3. Acceptance interface (consumed, not duplicated)

The validated observer contract
(`.../enemies-5/prepared/dangomushi94-observer/experimental/pikmin2_muse_dangomushi.py`,
13 green tests + standalone checker) defines the four legs this driver must
feed: bind -> death -> corpse -> re-bind, same generator, ordered, natural,
uninterrupted. This packet's `observer_legs` field carries those four legs
verbatim for machine alignment.

## 4. Validation commands (for the owner / implementing lane)

- `py -3.12 -m pytest tests/test_pikmin2_dangomushi_driver_contract.py -q`
  (12 focused tests: contract schema, synthetic anchor verify + mismatch/
  missing/short negatives, packet validation, leg-token alignment).
- Anchor re-check: `verify_anchors(<pinned pc_p2_dangomushi.cpp>)` must PASS
  (11/11) before any driver run; a mismatch fails the run, not the contract.
- Dry-apply: no family diff exists, so there is nothing to apply; the
  `FAMILY_PATCH` field is the empty string by design (asserted in tests).

## 5. Downstream consumers

`dangomushi94` gates 4/6 via `dangomushi94-death-cleanup-observer` (#376);
#376 family owner (this packet's reviewer). No ADMIT is requested or granted
here.