# Pinned MUKI houdai + redblue stage rows (#748)

Coordinator shared producer for the blocked P1 lanes
p2-challenge-ch-muki-houdai-p1 (#735) and p2-challenge-ch-muki-redblue-p1
(#744). The engine table names neither MUKI stage; this lane pins both rows
from live retail decode, implements the lookup + guarded fixture, and proves
resolution with compiled evidence. SERIALIZED: pc_bbft.cpp / CMakeLists.txt
integration is an explicit follow-on requiring #186 review; nothing here edits
shared targets. No ADMIT; all six gates UNTESTED.

## Source identity (live decode, never invented)

Retail stage table user/Matoba/challenge/stages.txt (18875 bytes, sha256
59890efa80fe5a77d52b9a87301b97c91cd10c94ff9a3fb85c49b78dfae03cf1),
decoded as shift_jis (30 stages) through the #136 framework contract parser,
cross-checked against the P0 catalogue pins (#541 houdai, #551 redblue).

| Stage | Cave file | UI | Floors | Timers (s) | Roster | Pop | Bitter/Spicy |
|---|---|---|---|---|---|---|---|
| ch_MUKI_houdai | ch_MUKI_houdai.txt | 8 | 2 | 100.0, 150.0 | 5 colours x 10 leaf | 50 | 1 / 1 |
| ch_MUKI_redblue | ch_MUKI_redblue.txt | 18 | 2 | 200.0, 200.0 | 2 colours x 25 leaf | 50 | 1 / 1 |

Roster bins use stage-table native color x happa ordering (houdai rows 0-4,
redblue rows 0-1, all happa Leaf). Treasure-count field 0 for both.

## Native mapping (owned files, additive only)

- native/pc_port/pc_p2_challenge_muki_stages.h/.cpp: kMukiStages[2] +
  selectMukiByUiIndex, reusing p2challenge::StageEntry from the accepted #651
  host-mode module (native base 93603dc2 already carries it).
- native/tools/p2_muki_stage_table_fixture.cpp: standalone argv-selectable
  boot (default both rows), #632 guard before every tick, descend + retry,
  P2_MUKI_STAGE_* markers. Module TU ridden along via include; no CMake edit.
- scripts/build_p2_muki_stage_table.py: leased configure/build/fixture/
  guardcheck/run harness using the maintained builder; guard consumed
  read-only via CPLUS_INCLUDE_PATH, never copied.
- experimental/pikmin2_muki_stage_table_rows.py + tests (10 tests incl.
  live-decode cross-check and fail-closed divergences).

## Build/run evidence (leased private build)

Recorded in the lane handoff (prepared/muki-stage-table-rows-native-output):
configured + built pikmin_pc with ninja -n no-work, fixture exe SHA-256,
guard self-test exit 0, negative guard exit 86 (CAPTAIN_DOWN, no PASS), and
the marker log for ui 8 + ui 18 (RESOLVED/BOOT/TICK/FLOOR_ADVANCE/RETRY/DONE).
Captain safety #632 adopted with canonical guard sha256
d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474.

## Serialized integration + consumers

pc_bbft.cpp stage-table wiring + CMakeLists.txt registration are NOT done
here; they are specified as follow-on requiring explicit #186 review. Hashed
packet names #735 + #744 as downstream consumers. No other edits.
## Observed evidence (generation 2, leased private build)

- Native 3c50ca44 (table + lookup + fixture; mode TU linked from pikmin_pc, not vendored). Root 98dc264f (pins + adapter + 10 tests + doc + harness with the canonical guard include flag).
- Configured + built pikmin_pc 621/621 in output/muki-stage-table-build (lease-held); ninja -n -d explain reports "ninja: no work to do." (ninja-dry.log sha256 e58361b0...).
- Fixture exe sha256 7caa3562ff59d43146a4fa783d81f2563a256d56ca5c1580a65c1948d2d00c3c; guard sha256 d2f678c9... (canonical, read-only via CPLUS_INCLUDE_PATH).
- Guardcheck: self-test exit 0 (RESOLVED..BOOT..TICK..TABLE_DONE); negative guard TU exit 86 with P2_FIXTURE_CAPTAIN_DOWN and no PASS.
- Run (both rows + single-stage ui 8 / ui 18), exit 0: houdai ui 8 pop 50 (100.0s -> 70.0s, descend 150.0s, retry) and redblue ui 18 pop 50 (200.0s -> 170.0s, descend 200.0s, retry); marker log sha256 8bfb0557.... No captain-down. Python tests 10/10 pass including live retail cross-check.
