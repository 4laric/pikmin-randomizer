# P1 impact post-PARK freeze-frame diagnosis (#797)

Lane `p1-impact-freeze-frame-diagnosis`, issue #797 (OPEN, assigned 4laric;
downstream `p1-challenge-impact-runtime-acceptance` #565 gen 4, owner
heartbeat stale). Owner: Codex through shared account 4laric. Diagnosis
only; never an engine unblock. Consumes the blocked #565 gen-4 evidence
read-only; no native changes, no rebuild, no runtime claim beyond this
packet. No ADMIT. Captain safety #632 labelling applies to any observation
handling (this lane only reads logs; guard/source hashes recorded below).

## Consumed evidence (read-only, verified)

- Gen-4 run log `output/workflow/autofill/planning-shards/p1-challenge/prepared/p1-challenge-impact-runtime-output/acceptance-gen4/runs/ddb4bfd607d4473eb560bff34fd18142/native.log`
  sha256 `48b1efe38d01f680ece6ade6e586d4b99833cb46c97e6367285209db21ba5d3c`
  (50446 bytes, 800 lines, exit 1/timeout): boot with 20 reds,
  `P2_CHALLENGE_PARK nx=309.663 ny=0.000 nz=1505.612`,
  `P2_CHALLENGE_PARK_ALIVE pikis=1`, then render-only silence; zero
  SQUAD/BOOT/PASS/GATE_DIAG/CAPTAIN_DOWN/FAIL lines. Verification
  `160cfb6f` failed as recorded.
- Fixture source (read-only pins, never edited):
  `native/tools/p2_challenge_guarded_boot_fixture.cpp` (#649 prerequisite
  lane): gateDiag throttle :62-65 (`frames%300`, 48-mark cap), pre-increment
  gates :68-72 (managers/navi/movie/pause, all emitting GATE_DIAG),
  PARK/PARK_ALIVE :82-85, SQUAD :86, BOOT :87-89, PASS :90-92.
- Captain guard `scripts/p2_fixture_captain_guard.h` sha256
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`
  (vendored in the fixture; this lane runs no observed ticks).

## Verdict: ENGINE-OWNER idle-loop freeze/crawl (not a throttle artifact)

`observed` reached 1 (PARK baseline pikis=1) but SQUAD (observed==60) never
fired and zero GATE_DIAG appeared. Every persistent pre-increment stall must
emit within ~300 frames at rate under the :62-65 budget, so the silence
proves the idle loop itself stopped advancing (hang or crawl). Squad loss
alone cannot explain it: a dead squad still advances `observed` (the fixture
gates squad count only at PASS), and SQUAD would still print. The
`frames%300`/48-mark throttle bounds gate signals but cannot produce zero
markers over a 300 s window at rate.

## Owner routing

- Primary: #649/engine owner - deadlock/loop-freeze investigation of the
  post-PARK idle path (a gate that blocks `idle()` entirely, or a loop that
  stops ticking, bypasses all GATE_DIAG paths).
- Prescription first: one longer bounded run with unthrottled gate
  diagnostics to exclude extreme slowness (frames crawling too slowly to hit
  a %300 multiple) before engine surgery.
- Follow-on: #52 scope 1 per the brief.
- PARK baseline pikis=1 (19 of 20 reds lost pre-PARK) is recorded as a
  secondary engine-side squad-loss fact for the #565 owner, not the freeze
  cause.

## Owned deliverables (3 new root files, disjoint)

- `experimental/pikmin2_p1_impact_freeze_frame_diagnosis.py` (analyzer +
  packet CLI; fail-closed).
- `tests/test_pikmin2_p1_impact_freeze_frame_diagnosis.py` (10 focused
  tests green: engine-owner, throttle, passing, blocked, refused,
  malformed, unattributable, missing).
- This doc (hashed packet).

## Gates

All six gates UNTESTED (tooling diagnosis; no runtime run by this lane).
No gameplay acceptance. No engine/file duplication; no ADMIT.