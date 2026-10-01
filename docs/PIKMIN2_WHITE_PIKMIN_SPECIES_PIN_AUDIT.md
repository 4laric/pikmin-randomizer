# White Pikmin species pin audit (#820, downstream #562)

Bounded read-only pin-discovery/ownership for the crawler #131 gap. No native
edits, no builds, no ADMIT. Verdict: FOUND_PARTIAL with exact citations.

## FOUND: species identity/fidelity layer

- `native/pc_port/pc_p2_species.cpp:6-17`: `pc_p2_species()` overloads map
  `mP2White` -> `P2SpeciesWhite` (Piki + sprout), with `-1` on dual flags.
- `native/pc_port/pc_p2_species.cpp:20-34`: `pc_p2_set_species()` writes both
  flags (identity + sprout).
- Flag carriers: `native/include/Piki.h:336-337` (`mP2Purple`/`mP2White`,
  "never an index into legacy three-color arrays"), `native/include/PikiHeadItem.h:79`.
- Birth/pluck/sprout propagation: `native/src/plugPikiKando/piki.cpp:1274`,
  `pikiheadItem.cpp:199,215,275,304`, `navi.cpp:1254,1636`,
  `naviState.cpp:2781`, `pikiState.cpp:1371,2831`,
  `native/pc_port/pc_whistle_pluck.cpp:53`.
- Enemy White callbacks: `native/pikmin2-research/include/Game/EnemyBase.h:74,258`.
- UI counters: `native/pikmin2-research/include/og/Screen/MapCounter.h:40,45`
  (`mShipWhitePikmin`, `mLeaderWhitePikmin`).
- Owner: pc_port family modules (existing owners; read-only here).

## ABSENT: ship/storage persistence for White/Purple

- `native/src/plugPikiColin/memoryCard.cpp:933-939,1429-1431` persists
  Red/Yellow/Blue counts only; no White/Purple count exists anywhere in the
  file (208-line verified absence pattern).
- `native/src/plugPikiKando/pikiMgr.cpp` (195 lines) has no species handling
  at all (birth/count only).
- Owner routing: save-progression/engine owner (memoryCard three-color
  persistence gap).

## Consumer binding (#562)

Downstream `p2-challenge-ch-mat-crawler-p1` re-run check:
`content-loading-verify/fixture.exe --experimental-pikmin2-room` in the
staged rundir; expected SELECTED/SPAWN_COVERED/READY/LIVE/PASS markers.
Recovery `c794278c53e9e4ee68de1a23953daf8856051657fa54c4d84b6fd2ad08dbd622`.

## Verification

`py -3.12 -m pytest tests/test_pikmin2_white_pikmin_species_pin_audit.py -q`
-> 6 passed, including a live canonical-source audit test. All six runtime
gates UNTESTED. No ADMIT. No gameplay claim.
