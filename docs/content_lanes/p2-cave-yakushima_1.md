# yakushima_1 P0 import packet (issue #158, lane p2-cave-yakushima_1)

Implementation owner: Codex through shared account `4laric`; executing worker
muse-l62 (same session). Phase P0 only: source audit and additive import
contract. No claim of imported or playable content; full issue #158 stays open
for P1/P2.

## Source identity

- Source entry: `yakushima_1` (p2-cave), `user/Mukki/mapunits/caveinfo/yakushima_1.txt`.
- Live-decoded SHA-256: `3732d4a2d5ae8a06e7457f709b498407b5c21b6f5b50fa43c6d8e9158f06034d`
  (read from local GPVE01 disc image at audit time; matches the recorded
  `source_sha256` in the existing catalog baseline byte-for-byte).
- Decoder: shared retail parser `experimental.pikmin2_cave_catalog.parse`
  (enemy IDs from research `src/plugProjectYamashitaU/enemyInfo.cpp`, treasure
  IDs from disc `user/Abe/Pellet/us/pelletlist_us.szs`). No parser fork.
- Lane contract: `docs/PIKMIN_CONTENT_IMPORT_LANES.json`, lane
  `p2-cave-yakushima_1` (single source of truth; adapter reads it by name).

## Floor coverage (decoded vs contract — all match)

| Floor | Unit pool | Enemies | Treasures | Gates | Caps |
|---|---|---|---|---|---|
| 1 | 1_NARI_4x4c_conc.txt | Tobi x2, Sokkuri x2, Wakame_s, Clover | leaf_normal | 0 | 2 |
| 2 | 1_NARI_4x4b_conc.txt | Frog_g_futa_titiyas, Frog, FireOtakara x2, Hiba x2, Wakame_s, Zenmai | ahiru_head, kan_b_gold | 1 | 2 |
| 3 | 1_units_a_conc.txt | Sarai, ElecBug x3, Zenmai | sinjyu, kan_nichiro | 1 | 3 |
| 4 | 3_ABE_d_pypen_dani_conc.txt | Jigumo_chocolate, Jigumo, Catfish, Hiba x2, Zenmai | locket, tape_blue | 1 | 2 |
| 5 | 1_units_DKumo_conc.txt | Damagumo_key, Kogane, Clover, KareOoinu_s, HikariKinoko | diamond_blue | 0 | 0 |

Raw source tokens verified token-for-token against the contract, including the
cargo-suffixed `Frog_g_futa_titiyas` (Frog carrying `g_futa_titiyas`),
`Jigumo_chocolate` (Jigumo carrying `chocolate`) and `Damagumo_key`
(Damagumo carrying `key`). Weights are definition inputs, not placements.

## Resource closure

All five unit pools resolve in the existing catalog baseline with decoded unit
definitions: `1_NARI_4x4c_conc.txt` (7 units), `1_NARI_4x4b_conc.txt` (7),
`1_units_a_conc.txt` (7), `3_ABE_d_pypen_dani_conc.txt` (9),
`1_units_DKumo_conc.txt` (1). Full unit lists are in the packet JSON
(`output/workflow/content-expansion/p2-cave-yakushima_1/packet/content-yakushima-1-p0.json`).
No missing pool, no unsupported reference.

## Native/framework blockers for P1 (exact)

1. Native cave/generator import hook for caveinfo definitions (integration
   owner); this packet decodes definitions only and wires no native path.
2. Unit-pool asset staging for the five pools above via the existing unit
   pipeline; the packet records pool sources, not staged assets.
3. Seeded topology/hole selection and per-floor generator pins are unproven for
   these 5 floors; weights are definition inputs, not placements.
4. Enemy admission resolved per enemy roster at P1; unresolved admission blocks
   promotion, not this preparatory packet.

## Adapter and tests (reserved files)

- `experimental/content_lanes/p2-cave-yakushima_1.py` — isolated adapter
  (contract load, live decode+hash, contract verify, closure verify, packet emit).
- `tests/content_lanes/test_p2_cave_yakushima_1.py` — 6 focused tests
  (contract match, real lanes-doc load, malformed contract/token/floor/pool
  rejection, unreadable-source rejection). All pass; synthetic inputs only.
- Delivery packet for the integrator:
  `output/deepseek-wave/inbox/content-158-p0.md` (points at this doc + packet JSON).

No placements emitted, no runtime run, no ADMIT. P1/P2 acceptance stays OPEN.
