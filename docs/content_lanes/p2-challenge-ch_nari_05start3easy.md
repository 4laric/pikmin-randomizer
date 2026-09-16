# ch_NARI_05start3easy P0 import packet (issue #548, lane p2-challenge-ch_nari_05start3easy)

Implementation owner: Codex through shared account `4laric`; executing worker
muse-l62 (same session, generation 2). Phase P0 only: source audit and additive
import contract. No claim of imported or playable content; full issue #548 stays
open for P1/P2.

## Source identity (two live sources, both hashed at audit time)

- Cave definition: `user/Mukki/mapunits/caveinfo/ch_NARI_05start3easy.txt`
  (2193 bytes), SHA-256
  `19dac7888d8151b26b6e8e00b021058ba93344b6b2a08455ceedcd3e243ef845`
  (matches the recorded `source_sha256` in `docs/PIKMIN_CONTENT_IMPORT_LANES.json`
  and `docs/PIKMIN2_CONTENT_INVENTORY.json` byte-for-byte).
- Stage table: `user/Matoba/challenge/stages.txt`,
  SHA-256 `59890efa80fe5a77d52b9a87301b97c91cd10c94ff9a3fb85c49b78dfae03cf1`;
  exactly one of its 30 stage blocks references `ch_NARI_05start3easy.txt`.
- Decoders: shared retail parser `experimental.pikmin2_cave_catalog.parse` for
  the cave half (enemy IDs from research `enemyInfo.cpp`, treasure IDs from the
  disc pellet archive); a small strict stage-block parser owned in the lane
  adapter (no shared challenge decoder exists; nothing forked).

## Stage metadata (decoded vs lane contract ? all match)

Starting roster: 1 leaf each of col0/col1/col2 (3 Pikmin); legacy time 400.0;
bitter 1 / spicy 2 dopes; 2 floors; otakara count 0; 2d UI index 15; floor
timers 120.0 s + 80.0 s. English title unresolved; source ID and UI index
authoritative per lane entry.

## Floor coverage (2 floors, same unit pool)

Unit pool `2_MAT_cent_north_tsuchi.txt`: NOT covered by the story-cave baseline
catalog (96 pools), so decoded live from disc ? SHA-256
`a487ff16fd6bb9b75e5e478670124621ae78a412853ee888c29b705139fd0d03`, 8 units
(`item_cap_tsuchi`, `way3/4/l/2/2x2_tsuchi`, `room_cent_4_tsuchi`,
`room_north_1_tsuchi`), every unit asset (arc.szs/texts.szs) verified present
in the disc table. Provenance marked `live` in the packet (not baseline).

Floor 1 enemies (9 rows): `RandPom`, `YellowKochappy_chocowhite`,
`Kochappy_ichigo`, `BlueKochappy_donguri`, `KumaKochappy_cookie_u`, `Egg`,
`Wakame_s`, `Wakame_l`, `Ooinu_s`; item `key`; one non-empty cap (`RandPom`).
Floor 2 enemies (6 rows): `Wtank_key`, `RandPom`, `Tank_silver_medal`,
`ElecHiba`, `Ooinu_l`, `Wakame_l`; items `dia_a_green`, `chess_queen_white`.
Gates: none either floor. Cargo suffixes (`chocowhite`, `ichigo`, `donguri`,
`cookie_u`, `key`, `silver_medal`) all resolve against the disc pellet catalog.
Weights are definition inputs, not placements.

## Native/framework blockers for P1 (exact)

1. Native cave/generator import hook plus Challenge-mode stage bootstrap
   (PikiCounter roster, dopes, floor timers, 2d index) ? integration owner; this
   packet wires no native path.
2. Unit-pool asset staging for `2_MAT_cent_north_tsuchi.txt` via the existing
   unit pipeline; the packet records the pool source + hash, not staged assets.
3. Seeded topology/hole selection and generator pins unproven for these 2
   floors; weights are definition inputs, not placements.
4. Enemy admission resolved per enemy roster at P1; unresolved admission blocks
   promotion, not this packet; no host chal0 fixture treated as Challenge mode.

## Adapter and tests (reserved files)

- `experimental/content_lanes/p2-challenge-ch_nari_05start3easy.py` ? isolated
  two-source adapter with live pool-decode fallback (contract load, live
  decode+hash, stage verify, cave coverage, closure verify, packet emit).
- `tests/content_lanes/test_p2_challenge_ch_nari_05start3easy.py` ? 7 focused
  tests (stage-block parse, contract match, real lanes-doc load, malformed
  block/contract/cave rejection, unreadable-source rejection). All pass on
  synthetic inputs (no disc needed).
- Integrator result file:
  `output/deepseek-wave/inbox/autofill-548-result.md` (points at this doc +
  packet JSON at `output/workflow/autofill/p2-challenge-ch_nari_05start3easy/packet/`).

No placements emitted, no runtime run, no ADMIT. P1/P2 acceptance stays OPEN.
