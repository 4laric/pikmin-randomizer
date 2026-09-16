# P2 Challenge 04 ch_NARI_01kusachi — P0 import contract (lane p2-challenge-ch_nari_01kusachi, #533)

Owner: Codex through shared account `4laric`. Parent content #137; coordination #531.
Phase: **P0 only**. No claim of playability; P1/P2 remain OPEN with runtime
dependencies #136, #137, #129, #130, #131.

## Source identity (canonical, not observed)

- Source ID `ch_NARI_01kusachi`, UI index 3 (authoritative; English title unresolved).
- Disc path `user/Mukki/mapunits/caveinfo/ch_NARI_01kusachi.txt`, pinned sha256
  `b8d232f417ce3fd4b2903571a1c53234e63dec49e127d5ef5b8ef3cc34bb8d85`
  (`docs/PIKMIN2_CONTENT_INVENTORY.json` `source_sha256`, mirrored in
  `docs/PIKMIN_CONTENT_IMPORT_LANES.json`).
- Catalogued contract: 1 floor; starting roster 50 blue leaf Pikmin (native
  color index 2, maturity index 0); floor timer 180 s within a 350 s legacy
  budget; 1 bitter + 2 spicy sprays; `treasure_count_field` 0.

## Actual-source decode (observed, this slice)

Local legal source `assets/disc/PIKMIN2 for GAMECUBE.iso` (read-only) contains
the entry: **1267 bytes, sha256 `b8d232f4…bb8d85` — matches the pinned
canonical hash.** Decoded shift_jis (1184 chars) through the shared parser
(`experimental.pikmin2_cave_catalog.parse`) with retail ID sets (100 enemy IDs
from `native/pikmin2-research/.../enemyInfo.cpp`, 201 treasure IDs from
`pelletlist_us.szs`): **1 definition, floor span 1–1 — complete floor
coverage.** Full manifest: lane output `decode.json` (sha256 `7d89054c…3285a`).

Floor 1 roster (definition weights, not placements): `Tank_key`,
2× `Jigumo_silver_medal`, `Frog_turi_uki`, 3× `Catfish_wadou_kaichin`, plants
`Clover`/`Zenmai`/`Clover` (target counts 5/5/5); treasures `kan`,
`dia_c_green`; one `gate` (life 4000.0, weight 11); cap block present with
count 0. Floor parameters: `f008` pool `1_MAT_ike_kusachi.txt`, lighting
`kusachi_light_cha.ini`, unit root `hiroba`.

Resource closure: pool file present in disc; 8 unit definitions
(`cap_kusachi`, `item_cap_kusachi`, `way3_kusachi`, `way4_kusachi`,
`wayl_kusachi`, `way2_kusachi`, `way2x2_kusachi`, `room_ike_kusachi`); all
`arc.szs`/`texts.szs` unit assets present — **zero missing unit assets.**
Unsupported-actor assessment for P1: Tank (Armored Cannon Beetle larva),
Jigumo (Beady Long Legs), Frog (Wollywog) and Catfish (Water Dumple) are
engine-owned species outside this lane; no fallback behavior fabricated here.

## Adapter (`experimental/content_lanes/p2-challenge-ch_nari_01kusachi.py`)

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

## Tests (`tests/content_lanes/test_p2_challenge_ch_nari_01kusachi.py`)

10 focused tests, all passing without disc/native/runtime: canonical-identity
parity with both JSON catalogues; missing-source prerequisite wording; staged
file location; hash-mismatch rejection; synthetic single-floor structural
decode (clearly labeled synthetic, never source evidence); 2-floor coverage
rejection; 5 malformed-input rejections; unresolved closure listing; honest
unverified packet contents; packet write round-trip with sha256.

## Blockers for P1 (exact)

1. Runtime framework #136 (Challenge timing/keys/scores/retry semantics) and
   content #137 acceptance pins.
2. Generator/actor owners #129, #130, #131 for floor construction and species
   admission; unresolved enemy admission blocks promotion, not P0.
3. Integrator cherry-picks only the three reserved files into its chosen
   integration branch; never merge this worktree's history into species wave.

## Evidence

- Focused test log: `output/workflow/content-expansion/p2-challenge-ch_nari_01kusachi/checks.log`
  (command below, exit 0).
- Real decode manifest: `output/workflow/content-expansion/p2-challenge-ch_nari_01kusachi/decode.json`
  (1267-byte hash-verified source, full roster/closure).
- Implementation packet: generated at handoff time under the lane output dir;
  delivery copy `output/deepseek-wave/inbox/content-533-p0.md`.

```powershell
py -3.12 -m pytest tests/content_lanes/test_p2_challenge_ch_nari_01kusachi.py -q
```
