# P2 Challenge 23 ch_MUKI_bombing — P0 import contract (lane p2-challenge-ch_muki_bombing, #556)

Owner: Codex through shared account `4laric`. Parent content #137; coordination #531.
Phase: **P0 only**. No claim of playability; P1/P2 remain OPEN with runtime
dependencies #136, #137, #129, #130, #131.

## Source identity (canonical, then observed)

- Source ID `ch_MUKI_bombing`, UI index 22 (authoritative; English title unresolved).
- Disc path `user/Mukki/mapunits/caveinfo/ch_MUKI_bombing.txt`, pinned sha256
  `558fa438ba56377f5242020e3389354d9be4db01243cc6423fd299d66a3442b0`
  (`docs/PIKMIN2_CONTENT_INVENTORY.json` `source_sha256`, mirrored in
  `docs/PIKMIN_CONTENT_IMPORT_LANES.json`).
- Catalogued contract: 1 floor; starting roster 30 + 20 leaf Pikmin at native
  roster rows 2 and 3; floor timer 255 s; 1 bitter + 1 spicy sprays;
  `treasure_count_field` 0.

## Actual-source decode (observed, this slice)

Local legal source `assets/disc/PIKMIN2 for GAMECUBE.iso` (read-only) contains
the entry: **1852 bytes, sha256 `558fa438…3442b0` — matches the pinned
canonical hash.** Decoded shift_jis through the shared parser
(`experimental.pikmin2_cave_catalog.parse`) with retail ID sets (100 enemy IDs
from `native/pikmin2-research/.../enemyInfo.cpp`, 201 treasure IDs from
`pelletlist_us.szs`): **1 definition, floor span 1–1 — complete floor
coverage.** Full manifest: lane output `decode.json` (sha256 `8582e3eb…6fbb14`).

Floor 1 roster (definition weights, not placements): `FminiHoudai_be_dama_red_l`,
`Fkabuto_diamond_blue_l`, `Rkabuto_diamond_red`, `$1BombSarai_be_dama_blue_l`
(drop mode 1, pikmin_or_leader), `BlueChappy_be_dama_yellow_l`,
3× `BlueKochappy` (be_dama yellow/red/blue, 2 each), 2× `YellowKochappy`
(gold/silver medal), 5× `KareOoinu_s`/`KareOoinu_l`, plants `Nekojarashi` (6),
`KareOoinu_l` (8), `Watage` (4), plus a second `Fkabuto` placement type 8.
Treasures `key`, `diamond_red_l`, `diamond_green_l`, `haniwa`, `saru_head`.
No gates; one cap record (`Egg`, weight 11, non-empty).

Resource closure: pool file present in disc; 8 unit definitions
(`item_cap_kusachi`, `way3_kusachi`, `way4_kusachi`, `wayl_kusachi`,
`way2_kusachi`, `way2x2_kusachi`, `room_5x5a_2_tekiF_kusachi`,
`room_big_tekiF_kusachi`); all `arc.szs`/`texts.szs` unit assets present —
**zero missing unit assets.** Unsupported-actor assessment for P1:
FminiHoudai, Fkabuto/Rkabuto, BombSarai, BlueChappy/BlueKochappy,
YellowKochappy, KareOoinu_s/_l, Nekojarashi, Watage and Egg are engine-owned
species/plants outside this lane; no fallback behavior fabricated here.

## Adapter (`experimental/content_lanes/p2-challenge-ch_muki_bombing.py`)

Isolated per-lane boundary reusing the existing shared parser
(`experimental.pikmin2_cave_catalog.parse` — not forked, not edited):

- `source_identity()` — pinned identity + catalogued metadata.
- `locate_source(roots)` / `read_disc_source(iso_path)` — find the
  disc-relative path or read the pinned bytes via the existing disc reader;
  absent image/entry raises the exact missing-disc prerequisite.
- `verify_source_bytes(data)` — fail-closed sha256 check vs the pinned hash.
- `decode_stage(text, enemy_ids, treasure_ids)` — shared parse plus the
  1-floor coverage check; malformed input raises `StageDecodeError`.
- `resource_closure(cave)` — lists `f008` unit-pool references as unresolved
  without source bytes.
- `build_import_packet` / `write_packet` — JSON implementation packet under
  ignored output with verification status, floor coverage, blockers and the
  definition-not-placement limitations.

## Tests (`tests/content_lanes/test_p2_challenge_ch_muki_bombing.py`)

10 focused tests, all passing without disc/native/runtime: canonical-identity
parity with both JSON catalogues; missing-source prerequisite wording; staged
file location; hash-mismatch rejection; synthetic single-floor structural
decode (clearly labeled synthetic); 2-floor coverage rejection; 5 malformed
input rejections; unresolved closure listing; honest unverified packet
contents; packet write round-trip with sha256.

## Blockers for P1 (exact)

1. Runtime framework #136 (Challenge timing/keys/scores/retry semantics) and
   content #137 acceptance pins.
2. Generator/actor owners #129, #130, #131 for floor construction and species
   admission; unresolved enemy admission blocks promotion, not P0.
3. Integrator cherry-picks only the three reserved files into its chosen
   integration branch; never merge this worktree's history into species wave.

## Evidence

- Focused test log: `output/workflow/autofill/p2-challenge-ch_muki_bombing/checks.log`
  (command below, exit 0).
- Real decode manifest: `output/workflow/autofill/p2-challenge-ch_muki_bombing/decode.json`
  (1852-byte hash-verified source, full roster/closure).

```powershell
py -3.12 -m pytest tests/content_lanes/test_p2_challenge_ch_muki_bombing.py -q
```