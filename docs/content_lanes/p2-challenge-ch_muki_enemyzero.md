# ch_MUKI_enemyzero P0 import packet (issue #546, lane p2-challenge-ch_muki_enemyzero)

Implementation owner: Codex through shared account `4laric`; executing worker
muse-l62 (same session, generation 2). Phase P0 only: source audit and additive
import contract. No claim of imported or playable content; full issue #546 stays
open for P1/P2.

## Source identity (two live sources, both hashed at audit time)

- Cave definition: `user/Mukki/mapunits/caveinfo/ch_MUKI_enemyzero.txt`,
  SHA-256 `301dec6cad8a366b06dd54c3bf7fa8af464c4f963ebcc40855ccb10102f17465`
  (matches the recorded `source_sha256` in `docs/PIKMIN_CONTENT_IMPORT_LANES.json`
  and `docs/PIKMIN2_CONTENT_INVENTORY.json` byte-for-byte).
- Stage table: `user/Matoba/challenge/stages.txt`,
  SHA-256 `59890efa80fe5a77d52b9a87301b97c91cd10c94ff9a3fb85c49b78dfae03cf1`;
  exactly one of its 30 stage blocks references `ch_MUKI_enemyzero.txt`.
- Decoders: shared retail parser `experimental.pikmin2_cave_catalog.parse` for
  the cave half (enemy IDs from research `enemyInfo.cpp`, treasure IDs from the
  disc pellet archive); a small strict stage-block parser owned in the lane
  adapter (no shared challenge decoder exists; nothing forked).

## Stage metadata (decoded vs lane contract ? all match)

Starting roster: 2 flower White Pikmin (col5 happa2); legacy time 0.0; bitter 0
/ spicy 0 dopes; 1 floor; otakara count 0; 2d UI index 13; floor timer 200.0 s.
English title unresolved; source ID and UI index authoritative per lane entry.

## Floor coverage (1 floor)

Unit pool `1_unit_16x17r_conc.txt` (single unit `room_16x17r_conc`, closure
verified against the existing catalog baseline). Enemy roster (18 definition
rows, raw tokens preserved): `Sokkuri_key`, `$2RandPom` x2, `Ooinu_s` x2,
`Ooinu_l` x2, `Tanpopo` x2, `Wakame_s`, `Clover`, `Wakame_l`,
`Sokkuri_flower_blue`, `Sokkuri_momiji_normal`, `Sokkuri_be_dama_red`,
`Sokkuri_be_dama_blue`, `Sokkuri_be_dama_yellow`, `ShijimiChou`.
Item roster: `be_dama_blue_l`, `be_dama_yellow_l` (weight 10 each). Gates: none.
Caps: none. Weights are definition inputs, not placements.

## Native/framework blockers for P1 (exact)

1. Native cave/generator import hook plus Challenge-mode stage bootstrap
   (PikiCounter roster, dopes, floor timer, 2d index) ? integration owner; this
   packet wires no native path.
2. Unit-pool asset staging for `1_unit_16x17r_conc.txt` via the existing unit
   pipeline; the packet records the pool source, not staged assets.
3. Seeded topology/hole selection and generator pins unproven; weights are
   definition inputs, not placements.
4. Enemy admission resolved per enemy roster at P1; unresolved admission blocks
   promotion, not this packet; no host chal0 fixture treated as Challenge mode.

## Adapter and tests (reserved files)

- `experimental/content_lanes/p2-challenge-ch_muki_enemyzero.py` ? isolated
  two-source adapter (contract load, live decode+hash, stage verify, cave
  coverage, closure verify, packet emit).
- `tests/content_lanes/test_p2_challenge_ch_muki_enemyzero.py` ? 7 focused
  tests (stage-block parse, contract match, real lanes-doc load, malformed
  block/contract/cave rejection, unreadable-source rejection). All pass on
  synthetic inputs (no disc needed).
- Delivery packet for the integrator:
  `output/deepseek-wave/inbox/content-546-p0.md` (points at this doc + packet
  JSON at `output/workflow/content-expansion/p2-challenge-ch_muki_enemyzero/packet/`).

No placements emitted, no runtime run, no ADMIT. P1/P2 acceptance stays OPEN.
