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