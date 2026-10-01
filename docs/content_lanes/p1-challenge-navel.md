# P0 import contract ? P1 Challenge Navel (lane p1-challenge-navel, issue #563)

Generation-3 P0 slice. Concrete source-import preparation only: no native
build, no runtime, no ADMIT, no playability claim. The full issue #563 stays
open for P1/P2. Reserved implementation:
`experimental/content_lanes/p1-challenge-navel.py` (adapter, stdlib only,
dependency-free pure functions) plus
`tests/content_lanes/test_p1_challenge_navel.py` (17 focused tests).

## Source identity

- Level `challenge:navel` (source id `navel`), native area 2,
  stage_info_index 18. Definition `stages/chal2.ini` in the retail P1
  asset tree (read-only input; no redistribution).
- Two consumer tracks share this identity and are kept separate by
  construction: optional story destination (#100) and the separate
  timed/scored AP campaign (#52). The adapter reports only the shared
  level identity plus the track labels as metadata.

## Decoded definitions (observed, never invented)

`stages/chal2.ini` (2465 bytes, sha256
`1a16d0e6...c51837ed`): `navi_start 0.0 0.0`, map
`courses/stage2/cave.mod`, `day_multiply 1.2`, one `dayMgr` block with
`numsettings 5` and five `timesetting` blocks ? the five challenge
layouts. Timesettings are day-phase layouts, not spawn instances.

`stages/chal2/default.gen` (sha256 `de45c8af...5914ba`): 98 records ?
50 `tlep` (treasure pellets), 19 `iket` enemies (Mizigen 9, Palm 7,
Shell 10, Collec 8, Hollec 12 per the P1 host TEKI roster), 14 `meti`,
7 `ssob`, 5 `krow`, 3 `ikip` (Pikmin). Generator ids are NOT unique in
retail: id 0 is shared by 36 records (unassigned) and id 6029413 by 12
(a pellet group); 48 distinct ids total. Reported as-is for P1 import.

`stages/chal2/plants.gen` (sha256 `0ce5e842...8f7f9f`): 38 `tnlp`
(plant) records.

Resource closure: map `courses/stage2/cave.mod` present (sha256
`da96b0a4...f9fcb8e`, 3939543 bytes). No missing references.

## Hash record

All four input hashes are pinned in the tests; any retail-tree drift
fails loudly and forces a re-audit. The lane-plan `source_sha256` stays
null until a P1 decode records the definition hash through the owning
process ? this slice does not write it.

## Exact native/framework blockers

1. Travel/save/check logic and the timed AP campaign (#52) remain open;
   this slice decodes static definitions only.
2. Story destination (#100) vs timed campaign (#52) contracts must stay
   separate through P1/P2; shared area id 2 must keep qualified level
   keys (`challenge:navel` vs story keys).
3. Full-content dependencies stay OPEN on issue #563 (#100, #52, #6).
4. No shared-file changes in this slice: global parsers/schema, species
   or other levels untouched. Any future shared need goes through scoped
   review with the owning lanes.

## Implementation packet for P1

Consume `audit_level()` output (schema `p1-challenge-navel-p0/1`,
`generated: False` with stated limitations). P1 needs a private
root/native pair, leased build, starting squad, centred 960x540 startup
and natural acceptance per the lane phases ? none of which is claimed
here. All runtime gates UNTESTED; fixture adoption N/A (kind=tooling
handoff). Do not repeat the preview-only import: the five layouts
already have preview startup evidence (historical).

## Verification

`py -3.12 -m pytest tests/content_lanes/test_p1_challenge_navel.py -q`
? 17 passed (positive pins on the real retail source; malformed,
missing-entry, count-mismatch and missing-source-boundary negatives).
