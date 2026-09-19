# P0 import contract — ch_NARI_04series (lane p2-challenge-ch_nari_04series, #545)

Lane: p2-challenge-ch_nari_04series (category p2-challenge, Challenge
stage table order 12, UI index 12), issue #545, phase P0 only. Sources:
caveinfo ch_NARI_04series.txt (6469 bytes on the local GPVE01 rev 0
disc, sha256 83cda0aa4e8fc96a68060ed1dba8e1e9ff53151a29856d813e23328618b70e18,
matching the catalogued hash) and the Challenge stage table
user/Matoba/challenge/stages.txt (stage block at line 424). English
title unresolved; source ID and UI index are authoritative. No native
worktree, build, or runtime belongs to this slice.

## Decoded content (7 floors)

| Floor | Unit pool | Enemies | Treasures |
|---|---|---|---|
| 1 | 1_MAT_mid2_tsuchi.txt | Chappy, Tukushi | toy_ring_a_red, bane_red, diamond_red_l, dashboots |
| 2 | 2_units_tako_north_tile.txt | BlueChappy | be_dama_blue_l, castanets, toy_cat, channel |
| 3 | 1_units_north_metal.txt | Chappy, DaiodoRed, DaiodoGreen | gear, watch, sinkukan_c, bolt_l, tatebue |
| 4 | 1_NARI_4x4b_conc.txt | YellowChappy | dia_b_red, dia_c_red, dia_c_green, donutschoco_s, tape_blue |
| 5 | 1_NARI_north4_tsuchi.txt | Chappy, Zenmai, HikariKinoko | compact_make, locket, diamond_green_l |
| 6 | 2_units_tako_north_tile.txt | BlueChappy | creap, toy_lady, toy_dog, ahiru, sensya |
| 7 | 1_MIYA_manh2_conc.txt | MiniHoudai, Wakame_l | robot_head, j_block_red, j_block_yellow, j_block_green, j_block_blue, j_block_white, juji_key, juji_key_fc, donutswhite, donutsichigo_s, radar_a |

## Stage record (stages.txt block)

Starting roster: 50 flower White Pikmin only (native color 4,
maturity 2; all other colors zero). Legacy time 450.0 s; bitter
sprays 2, spicy sprays 3; treasure-count field 0; per-floor seconds
40, 30, 40, 40, 40, 45, 60 (sum 295 s, inside the legacy limit).
The adapter asserts every field verbatim against the catalogued
contract, plus stage-to-cave floor-count agreement.

## Adapter (experimental/content_lanes/p2-challenge-ch_nari_04series.py)

Isolated per-source layer over the EXISTING shared parsers
(experimental.pikmin2_cave_catalog.parse,
experimental.pikmin2_cave.unit_definition,
experimental.pikmin2_pod.pellet_catalog,
experimental.pikmin2_assets.disc_files) plus a small local reader for
the previously-unparsed stages.txt stage block. No shared file is
edited. Fail-closed: FileNotFoundError on absent inputs, ValueError on
malformed definitions, mismatch strings on contract drift.

## Verified P0 result (live decode, this host)

- 7 of 7 floors decoded; source hash matches the catalogued value;
  contract mismatches: none.
- All 6 referenced unit pools decoded; unit arc and texts closure:
  complete, 0 missing.
- Tests: tests/content_lanes/test_p2_challenge_ch_nari_04series.py —
  13 passed plus 7 malformed subtests (synthetic plus the live-decode
  test, which skips cleanly without a local disc image).

## Exact blockers (framework, not decode failures)

- P1 and P2 runtime import needs the existing owners: Challenge
  framework #136, Challenge content #137, caves #129, species and
  assets #130, species #131.
- Promotion needs species admission per the roster ledger; unadmitted
  floor roster members (including floor-7 MiniHoudai) block promotion,
  not this preparatory packet.
- No playability is claimed; the full content issue stays OPEN.

## Boundaries

Owns only the three reserved files. No shared parser or schema edits,
no native hooks, no asset redistribution. Evidence and runtime state
live under output/workflow/content-expansion/
p2-challenge-ch_nari_04series. The integrator packet is
output/deepseek-wave/inbox/content-545-p0.md.

---

# P1 private runtime import - ch_NARI_04series (lane p2-challenge-ch-nari-04series-p1, #545)

P1 extends the P0 adapter above (reused decode helpers, no forked parser)
with a private runtime import path: stage the decoded packet into a run
layout, boot the room-preview path in a private runtime, and validate
receipt-parseable markers. Captain safety #632 is mandatory; all six gates
stay UNTESTED unless genuinely observed. No ADMIT, no ledger writes. Owns
only the same three reserved files.

## P1 adapter surface (same module)

- `stage_select_record(packet)` / `check_stage_record(text, packet)`: render
  and fail-closed-validate the #669 `P2_CHALLENGE_STAGE_SELECT_1` record
  (cave, ui_index, table_order, floors, source path+sha, timers+legacy,
  sprays+treasure field, 7-row roster). Any drift raises ValueError.
- `stage_p1_run(packet, run_dir)`: refuses packets with contract mismatches
  or missing unit assets, then writes `p2-challenge-stage-select.txt`,
  `p2-challenge-p1-squad.txt` (50 flower Whites + sprays),
  `p2-challenge-p1-timers.txt` (40/30/40/40/40/45/60 + legacy 450) and
  `p2-challenge-p1-manifest.json` (decoded packet copy), re-validating the
  select record after writing.
- `run_p1(packet, assets, converted, output, exe, seconds)`: fresh arena via
  the shared preview prepare (current starting-Pikmin overlay), P1 sidecars
  copied in, private binary boots `--experimental-pikmin2-room` with centred
  960x540 (`PIKMIN_P2_ROOM_WINDOW`) and dummy audio; returns run/meta/
  findings. Captain-down in the log raises (BLOCKED path observed).
- `validate_p1_log(text, packet)`: window/squad/stage-selected/resolved,
  actors (`P2_LIFECYCLE_ENEMY`), collision (`P2_FINAL_POSITION` + ground),
  no-immediate-extinction. Unobserved legs stay False.
- `CAPTAIN_GUARD_HEADER` + `CAPTAIN_GUARD_SHA256` pin the canonical guard
  consumed read-only at review
  (`scripts/p2_fixture_captain_guard.h`, sha256
  d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474).

## P1 verification (this host)

- Focused tests: stage round-trip, drift/magic/hash rejections, layout
  files + squad/spray content, bad-packet refusals, observed/unobserved log
  findings, captain-down BLOCKED, guard-header pin.
- Leased private build of the unchanged native tree (configure + full
  `pikmin_pc` link + `ninja -n` no-work) with exe SHA-256 recorded.
- Fresh staged arena + room-preview boot; findings recorded per leg; gates
  reported exactly as observed.

## Known P1 boundary (exact defect, not a decode failure)

The integrated engine stage table (`pc_port/pc_bbft.cpp`) carries only the
`ch_NARI_01kusachi` row: the `--experimental-challenge-stage ch_NARI_04series`
flag path and the stage-boot fixture refuse with unknown-stage, so native
stage-select wiring for this cave is a shared-native change requiring #186
review (not owned here). The P1 import path above stages everything the
engine reader consumes and observes the room-preview boot honestly; full
stage-select boot awaits that shared edit.
