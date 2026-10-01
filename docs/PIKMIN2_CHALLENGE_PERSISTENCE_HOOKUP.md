# Challenge persistence native hookup (#713)

Lane `challenge-persistence-native-hookup`, issue #713. Implementation owner:
Codex through shared account 4laric. Consumer-repair for stopped consumer
`p2-challenge-ch_mat_route_rover-p1` (#561, gen 12): its base P1 passes but the
persistence probe fails 0/7 because the integrated #708 contract specified a
native save-layer hookup that was never landed. This lane implements the
anchors/score/markers module the #708 contract names, proves it with a guarded
fixture, and specifies the engine call-site follow-on without touching it.

## What was built (owned files only)

- `native/pc_port/pc_p2_challenge_persistence.{h,cpp}`: per-stage save
  anchors, result-screen score, and the exact 7 probe markers per stage run.
  Engine-free (plain data + printf markers); no save-tree writes.
- `native/tools/p2_challenge_persistence_fixture.cpp`: replacement-main
  guarded fixture driving one full probe-order session for
  `ch_MAT_route_rover` (ui 27, the #561 stage).
- `scripts/build_p2_challenge_persistence.py`: leased build/run helper
  (Ninja response-file expansion, marker assertions, run-log persistence).
- `experimental/pikmin2_challenge_persistence_hookup.py`: run-log observer
  (marker grammar, 7/7 checks, key/score twins cross-checked against #708).
- `tests/test_pikmin2_challenge_persistence_hookup.py`: 16 focused tests.
- This document.

No other files touched. No `#710` (engine call site) edits, no consumer
(#561) edits, no CMakeLists/preview edits, no ADMIT.

## Key/marker contract (mirrors #708 verbatim, read-only input)

Per stage `<cave_id>`: `p2_challenge_{save,load,clear,highscore,unlock}_<id>`
(150 keys across the 30 pinned stages). Probe markers, exact lines in probe
order: `P2_CHALLENGE_SAVE_KEY/LOAD_KEY/CLEAR/HIGHSCORE/UNLOCK/RECEIPT_DEDUP/
REENTRY stage=<cave_id>` — nothing else on the line. The 30-row stage table is
transcribed read-only from the #708 adapter (ui 0..29, zero mismatches);
`selectStage` fails closed on null/empty/oversize/unsafe/unknown keys.

## Score semantics (mirrors the #651 host-mode precedent, read-only)

`score = pokos*10 + floor(timeLeftSeconds) + population*10`. Negative or
non-finite inputs are refused (`-1`); the fixture asserts the deterministic
sample (42 pokos, 120.5 s, 15 population = 690).

## Anchors (fixture-scoped PlayCommonData shape)

Per selected stage: `cleared`, `highscore`, `unlocked`, `saveSeen`,
`loadSeen`, `receiptCount`/`lastReceiptId`/`dedupHits` (repeat ids dedup, never
double-count), `reentered`. The module never persists to disk; the future
engine call site owns save-tree writes.

## Captain safety (#632)

The canonical guard (`scripts/p2_fixture_captain_guard.h`, recorded hash
alongside the lane) is vendored verbatim into the fixture and proven by the
engine-independent self-test (7-row truth table, exit 0) and negative test
(`P2_FIXTURE_CAPTAIN_DOWN`, exit 86 BLOCKED, no PASS). The fixture boots no
game world, so there is no Navi to observe per tick; no blanket invincibility
exists anywhere.

## Engine call-site follow-on (SPECIFIED, blocked on #710 + #186, no edit)

Owner: engine runtime hook lane #710 with #186 hook review. When that lane
lands, it wires these calls (exact names) into the P1 challenge result path
and admits the module to `pikmin_pc` CMake membership:

1. Stage end: `selectStage(caveId, &anchors)`; on refusal, abort the save
   write for that stage (fail closed, no fabricated keys).
2. Result screen: `recordSave`, `recordLoad`, then `recordClear` on clear,
   `recordHighscore(&anchors, pokos, timeLeft, population)`,
   `recordUnlock` on unlock.
3. Receipt pipeline: `recordReceipt(&anchors, receiptId)` per receipt
   (duplicates dedup automatically).
4. Stage transition: `recordReentry` on re-entry.
5. Emit order must stay probe order (save, load, clear, highscore, unlock,
   receipt, reentry) so the #561 probe counts 7/7.

Until #710 lands, the ONLY caller is the guarded fixture in a private build.

## Verification

Focused tests (16, engine-free) green; leased private build with fixture
provenance `built`; guarded run exit 0 with `PASS
P2_CHALLENGE_PERSISTENCE_RUN markers=7`, the exact 7 marker lines, 960x540
centred window, no abort, no captain-down, no injection markers. All six
runtime gates UNTESTED (no gameplay); gate closure belongs to #561 after the
call site lands.

## Downstream consumer

`p2-challenge-ch_mat_route_rover-p1` (#561): its persistence probe must
observe 7/7 artifacts against this contract at runtime, then save/reload
acceptance. Enemy/actor scope stays with #561; save-tree writes stay with the
call-site owner (#710).
