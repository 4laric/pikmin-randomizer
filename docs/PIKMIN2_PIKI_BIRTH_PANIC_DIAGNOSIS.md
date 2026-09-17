# PIKI BIRTH FAILED panic diagnosis (lane piki-birth-panic-diagnosis, #721)

Bounded engine diagnosis pinpointing why `pikiMgr->birth()` returns null in
the #567 trial boot. Root-only tooling: engine sources and #567 logs consumed
read-only (no duplication, no family/shared/native edits); no runtime, no
ADMIT. All six gates UNTESTED.

## Observed (native c549997e, exe ea209738)

- Guarded chal4 run: 960x540 centred window, `CHALLENGE_LAYOUT_READY
  id=challenge-4` (runlog line 236), generators spawn (63+162 default,
  49+49 plant; lines 375-376, 635-636), movie heap reset (766-767), then
  `[PANIC] .../system.cpp:1229: *** PIKI BIRTH FAILED !!!` (line 769).
- No `P2_CHALLENGE_SQUAD`, no `CAPTAIN_DOWN`. No `2d err`, `CONTAINER`,
  `numObjects`, or `no empty slot` lines anywhere in the 827-line log.

## Pinpoint: POOL_EMPTY (field cap and Onion counts exonerated)

- Null site: `GoalItem::exitPiki()` calls `pikiMgr->birth()` (goalItem.cpp:433)
  and hits `ERROR("*** PIKI BIRTH FAILED !!!")` (goalItem.cpp:438); the halt
  at the first error means this was the FIRST failed birth, so pool
  exhaustion-by-use is impossible and counts were legitimately queued.
- Onion counts exonerated: the challenge boot writes 20 Leaf x 3 colors
  (gameSetup.cpp:309, 316-324, same block that printed the observed
  layout-ready line), and the Onion reads them into `mHeldPikis`
  (goalItem.cpp:675-678).
- Field cap exonerated quantitatively: the cap defaults to 100 in every path
  (pc_settings.cpp:95, 133, 2724-2728) and is written once per setup
  (gameCoreSection.cpp:1470); a first-dispense total near 19 can never reach
  it (pikiMgr.cpp:44-50).
- Pool path is the only remaining null source (objectMgr.cpp:331-353). Its
  PRINT diagnostics never appear because PRINT output is gated by
  `gsys->mTogglePrint` (default FALSE, system.cpp:787; documented at
  moviePlayer.cpp:716-727) — absence of pool diagnostics proves nothing.
- memStat cannot adjudicate pool state either way: plain `new` bypasses
  memStat (sysNew.cpp:104-155), so the `piki : 0.00 kbytes` rows are
  allocation-path artifacts, not pool measurements. The pool is identified by
  elimination over pinned facts, not by a log line.
- Sole pool creation site: `pikiMgr->create(limit+2)` (gameCoreSection.cpp:1021),
  reached via `gamecore->initStage()` (newPikiGame.cpp:2021) with
  `finalSetup()` on first update (newPikiGame.cpp:2271-2276).

## Fix / follow-on owner (files + lines)

Shared piki-birth owner via #186 hook review (piki birth path,
newPikiGame.cpp) + #52 campaign contract (matches the #567 blocked
dependencies):

- `src/plugPikiKando/gameCoreSection.cpp:1009-1027` — ensure
  `pikiMgr->create` executes on the challenge stage-setup path.
- `src/plugPikiColin/newPikiGame.cpp:2021,2271-2276` — initStage/finalSetup
  order on challenge setup.
- `src/plugPikiKando/objectMgr.cpp:331-353` +
  `src/plugPikiKando/pikiMgr.cpp:33-53` — toggle-independent (printf, not
  PRINT) birth-failure diagnostics dumping pool/cap state.
- `src/plugPikiKando/goalItem.cpp:424-441` — halt-site pool/cap context.

## Module, tests, packet

- `experimental/pikmin2_piki_birth_panic_diagnosis.py`: machine-readable
  registry builder + fail-closed adjudicator (`adjudicate`: trial facts ->
  POOL_EMPTY; cap facts -> FIELD_CAP; unwired counts -> ONION_COUNTS;
  unpinned -> UNDETERMINED) + registry validator (`--check`,
  `--registry-out`, `--packet-out`).
- `tests/test_pikmin2_piki_birth_panic_diagnosis.py`: 33 focused tests
  (adjudication matrix incl. boundary and refusal cases, pins, evidence
  hashes, fix owner, packet contents, refusal battery).
- The emitted packet names exact pins (native c549997e, exe ea209738) and
  downstream consumer `p1-challenge-trial-runtime-acceptance` (#567).

## Handoff

`output/workflow/autofill/prerequisites/piki-birth-panic-diagnosis/out/handoff.json`
(kind=tooling) names the exact pins and the emitted packet. Downstream: #567
squad spawns once the birth cause is fixed, then gate evidence.

## Captain safety #632

N/A (no runtime run). Any future runtime work must adopt
`scripts/p2_fixture_captain_guard.h` (sha256 `d2f678c9...`) with
orimaDead/NaviDead/HP<=1 checks, CAPTAIN_DOWN + BLOCKED exit, and a parked
captain; guard/source hashes recorded at adoption.
