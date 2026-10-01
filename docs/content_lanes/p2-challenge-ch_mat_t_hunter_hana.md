# P0 import contract — ch_MAT_t_hunter_hana (lane p2-challenge-ch_mat_t_hunter_hana, #547)

Lane: p2-challenge-ch_mat_t_hunter_hana (category p2-challenge,
Challenge stage table order 8, UI index 14), issue #547, phase P0 only.
Sources: caveinfo ch_MAT_t_hunter_hana.txt (1436 bytes on the local
GPVE01 rev 0 disc, sha256
3bc86de3c581eeccaa8367ba1acbeb4b824c574e7db0ddc3b392f4af6ff8be9a,
matching the catalogued hash) and the Challenge stage table
user/Matoba/challenge/stages.txt (stage block at line 282). English
title unresolved; source ID and UI index are authoritative. No native
worktree, build, or runtime belongs to this slice.

## Decoded content (1 floor)

Unit pool 1_units_manh_conc.txt (7 units: item_cap_conc, way3_conc,
way4_conc, wayl_conc, way2_conc, way2x2_conc, room_manh_2_conc).
Enemies: Miulin carrying gold_medal plus Hanachirashi carrying
diamond_red three times. Treasures (19): key, bane, tel_dial,
diamond_blue, toy_gentle, tatebue, leaf_yellow, dia_b_blue,
sinkukan_b, nut_l, bolt_l, be_dama_red_l, diamond_green_l, tape_red,
turi_uki, badminton, gold_medal, baum_kuchen, chocolate_l. No gates,
no caps.

## Stage record (stages.txt block)

Starting roster: 40 flower blues, 20 flower yellows, 20 flower whites,
nothing else. Legacy time 400.0 s; bitter sprays 0, spicy sprays 0;
treasure-count field 0; single floor timer 145.0 s (inside the legacy
limit). The adapter asserts every field verbatim against the
catalogued contract, plus stage-to-cave floor-count agreement.

## Adapter (experimental/content_lanes/p2-challenge-ch_mat_t_hunter_hana.py)

Isolated per-source layer over the EXISTING shared parsers
(experimental.pikmin2_cave_catalog.parse,
experimental.pikmin2_cave.unit_definition,
experimental.pikmin2_pod.pellet_catalog,
experimental.pikmin2_assets.disc_files) plus a small local reader for
the stages.txt stage block. No shared file is edited. Fail-closed:
FileNotFoundError on absent inputs, ValueError on malformed
definitions, mismatch strings on contract drift.

## Verified P0 result (live decode, this host)

- 1 of 1 floor decoded; source hash matches the catalogued value;
  contract mismatches: none.
- The referenced unit pool decodes; unit arc and texts closure:
  complete, 0 missing.
- Tests: tests/content_lanes/test_p2_challenge_ch_mat_t_hunter_hana.py
  — 13 passed plus 6 malformed subtests (synthetic plus the
  live-decode test, which skips cleanly without a local disc image).

## Exact blockers (framework, not decode failures)

- P1 and P2 runtime import needs the existing owners: Challenge
  framework #136, Challenge content #137, caves #129, species and
  assets #130, species #131.
- Promotion needs species admission per the roster ledger; unadmitted
  floor roster members (Miulin, Hanachirashi) block promotion, not
  this preparatory packet.
- No playability is claimed; the full content issue stays OPEN.

## Boundaries

Owns only the three reserved files. No shared parser or schema edits,
no native hooks, no asset redistribution. Evidence and runtime state
live under output/workflow/autofill/p2-challenge-ch_mat_t_hunter_hana.
The integrator packet is
output/deepseek-wave/inbox/autofill-547-result.md.