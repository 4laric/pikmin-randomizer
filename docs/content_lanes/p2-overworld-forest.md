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
