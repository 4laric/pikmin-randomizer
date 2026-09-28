# P0 import contract ? p2-overworld-forest, real source (lane p2-overworld-forest-p0-real-source, issue #149)

Generation-2 slice finishing the synthetic-only P0 against REAL legal
source bytes. P0 tooling only: no native build, no runtime run, no shared
edits, no ADMIT. All six runtime gates UNTESTED. Issue #149 stays OPEN.

## Real source decode (observed, never invented)

- Input: `user/Abe/stages.txt` read off the supported local ISO
  (`C:\Users\alari\Downloads\PIKMIN2 for GAMECUBE.iso`) via the shared
  `experimental.pikmin2_assets.disc_files` reader: 3275 bytes, sha256
  `4de9008c99e799b99b2746c0156846eeb7ad50895ad110fc7f2070db6de1fff8`.
- Decoded with the existing `stage_cave_links` framing (no fork): 5 forest
  cave links in table order ? `f_01`..`f_04` mapping to
  `user/Mukki/mapunits/caveinfo/forest_1.txt`..`forest_4.txt`, plus the
  `test` link to `caveinfo.txt`. Manifest validates clean.
- The prior synthetic-only boundary tests are preserved green alongside
  the new real-bytes tests.

## What changed vs the synthetic P0

- Adapter gains `DEFAULT_ISO`, `locate_source()` (exact prerequisite when
  the ISO is absent) and `decode_source_file()` (bytes in, hashed manifest
  out). All prior functions byte-identical in behavior.
- Tests gain a `RealSourceTests` class (hash/size pins, 5-link order,
  closure paths, helper round-trip, missing-input boundary).
- This doc records the observed hash, decoded summary and remaining
  blockers below.

## Exact remaining P1/P2 blockers

- P1 private runtime import awaits validated surface save/progression
  (#132) and receipt (#140) publications plus actor/asset closure
  (#128/#130/#131/#144/#145/#146).
- Timed/scored AP campaign behavior stays with its owner; this slice makes
  no campaign, retry, save or travel claim.

## Verification

`py -3.12 -m pytest tests/content_lanes/test_p2_overworld_forest.py -q`
-> 16 passed (10 synthetic boundary + 6 real-bytes). Real-source manifest
attached as `prepared/forest-p0-output/manifest-real-source.json` beside
the lane evidence.

## P1 runtime import + surface-session acceptance (lane p2-overworld-forest-p1-surface-session)

P1 extends the P0 adapter in place (all P0 functions behavior-identical):

- Baseline pin verified real: content line `codex/content-lanes-531`
  @ `3a6b34e38075a60c7f60de5e2add768e5efdc8b4` (P0 adapter commits
  `aad91cfd`/`5d69c760`); the three files were imported verbatim from that
  pin, then extended. Nothing invented.
- Consumes the integrated generic contract `surface-session-provider-contract`
  (#132, schema `p2-surface-session-1`) with no fork and no vendoring:
  `load_surface_contract()` resolves the checker from the live checkout when
  integrated there, else byte-exact from the canonical git object store at
  the content pin (blob sha256
  `3ba71fe92a8989180358cbb1617cf040e3ebf9a25aac1754cec25a1e192460f1`,
  SCHEMA asserted). Otherwise `P1GapError` names the exact pins.
- `stage_p1_run()` stages the validated real-source manifest (5 links,
  stages sha `4de9008c...`) into a private run layout (`manifest.json`,
  `session-seed.json` day 1 course `forest`, `boundaries.json`).
- `drive_session_boundaries()` drives the real checker over day transition
  (begin_day/sunset/save/reload/begin_day), receipt replay (grant then
  exactly-once duplicate rejection) and exit/reentry (surface-exit rejected,
  enter/exit/enter accepted); native-backed requests are recorded missing via
  `request_integration` (sunset driver, save serializer, receipt endpoint,
  generator-cache restore). Wake: record decoded + entrances known, receipt
  endpoints not admitted, ready false.
- CLI: `--p1-run DIR` stages, drives and writes `boundary-report.json`.
- Tests: 9 new (loader pins/real/gap/contract-error; stage layout; boundary
  verdicts; missing-layout/stage/tamper negatives). `25 passed`.

## Game-runtime record (explicit, no theater)

No game-engine fixture is owned or specified by this slice, and the consumed
contract declares native day/save/receipt/generator integration missing by
design, so no pause/movie return or observed tick occurred. All six runtime
gates stay UNTESTED; no playability claim; no ledger writes. Captain safety
#632: guard source `scripts/p2_fixture_captain_guard.h` (canonical-disk sha256
`d2f678c9...`, absent at lane base `7416cc7a` — recorded for the future
P1-native slice that will own a fixture) adopted by non-execution; a captain
park/reach statement is vacuous with no runtime and is not claimed as
protection. A leased full native build was not run: the tree has zero owned
native changes and no fixture consumes it; the build is deferred to the
P1-native slice.

## Remaining P2 blockers

Native sunset driver, save serializer, receipt ledger endpoint and
generator-cache restore (#132 line); species/actor closure (#128/#130/#131/
#140/#144/#145/#146); receipt endpoint admission for wake.ready.