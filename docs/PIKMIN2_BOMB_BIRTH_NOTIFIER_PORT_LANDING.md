# Bomb birth hook-notifier port landing (lane bomb-birth-notifier-port-landing, #719)

Bounded landing submitting the missing handoff for the done-but-unlanded #715
notifier port. Root-only tooling: the #715 port is consumed read-only (no
re-derivation, no duplication of its nine files); no family/shared/native
edits, no runtime, no ADMIT. All six gates UNTESTED.

## Re-verified #715 pins (hash-identical to the #715 review)

- Root commit `f807392feef43a145559350406e467136d49de06` (base `ecf5f53a`),
  4 files: doc, verifier, build helper, tests.
- Native commit `a6ca7bc6842a24bb8c2321f446fcfb8ec94f1b65` (base `5d03a790`,
  the #677 head), 4 changed files: strong notifier header/source,
  `CMakeLists.txt`, guarded fixture; `generalEnemyMgr.cpp` verified intact
  and unchanged (same blob at base and head), not duplicated.
- All seven `out/` evidence files re-hashed byte-identical to the #715 handoff
  record (pytest, verify, provider CTest, default-config build log, both build
  records, doc `974f3feacc...`); guard header `d2f678c9...` recorded.

## Validation against the #186 packet + integrated #691/#700/#703

- #186 packet `provider-bomb-birth-186-review-packet` (issue #186): item 1
  (hook extern + notify calls intact in `generalEnemyMgr.cpp`, strong notifier
  TU defined with LTO retention) and item 2 (`pc_p2_bomb_mgr_birth.cpp` +
  notifier in the build with provider test `p2_bomb_birth_notifier_test`)
  verified present in `a6ca7bc6`; item 3 (dynamic bridge source 93) stays
  integrator work, out of scope here as in #715.
- #691 integrated: root `1fcaf074`, native `95172ea4` (real engine birth,
  handoff slice passed).
- #700 integrated: root `34752630`, native `58df488e` (joint capture,
  handoff slice passed).
- #703 integrated: root `f985d17c` (#616 provider landing, handoff slice
  passed).
- #186 decision still pending before shared-line landing; no decision claimed.

## Module, tests, packet

- `experimental/pikmin2_bomb_birth_notifier_port_landing.py`: machine-readable
  registry builder + fail-closed validator (`--check`, `--registry-out`,
  `--packet-out`) with every pin, blob hash, evidence hash, integration pin,
  #186 packet item, and the downstream consumer recorded.
- `tests/test_pikmin2_bomb_birth_notifier_port_landing.py`: 24 focused tests
  (pins, nine-file integrity with the hook-verified-intact case, #186 packet,
  evidence completeness, downstream #573, UNTESTED gates, packet contents,
  refusal battery).
- The emitted packet is integration-ready for the single-writer integrator +
  #186 reviewer and names downstream consumer
  `enemy-bombotakara93-payload` (#573), whose gate-1/3 block evidence is cited
  read-only.

## Handoff

`output/workflow/autofill/prerequisites/bomb-birth-notifier-port-landing/out/handoff.json`
(kind=tooling) names the exact #715 commits/hashes and the emitted packet; the
packet hash is recorded in the handoff evidence. Downstream: #573 gates 1/3
once integrated alongside the bridge landing.

## Captain safety #632

N/A (no runtime run). Any future runtime work must adopt
`scripts/p2_fixture_captain_guard.h` (sha256 `d2f678c9...`) with
orimaDead/NaviDead/HP<=1 checks, CAPTAIN_DOWN + BLOCKED exit, and a parked
captain; guard/source hashes recorded at adoption.
