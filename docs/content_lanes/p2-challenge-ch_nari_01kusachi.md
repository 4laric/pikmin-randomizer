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

## Actual-source status

Actual source bytes were **unavailable** in this slice: no local US GPVE01 rev 0
disc image exists in the environment (searched `output/`, home top level; the
room-preview workflow expects a user-supplied `PATH/PIKMIN2.iso`). The adapter
therefore reports `MissingSourcePrerequisite` naming that exact prerequisite
and never synthesizes values. Hash validation and resource closure against real
bytes are P1-unblocking work, not claimed here.

## Adapter (`experimental/content_lanes/p2-challenge-ch_nari_01kusachi.py`)

Isolated per-lane boundary reusing the existing shared parser
(`experimental.pikmin2_cave_catalog.parse` — not forked, not edited):

- `source_identity()` — pinned identity + catalogued metadata.
- `locate_source(roots)` — finds the disc-relative path or raises the exact
  missing-disc prerequisite.
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

1. Local legal source: owned US Pikmin 2 GPVE01 rev 0 disc image exposing the
   pinned path/hash (see prerequisite string in adapter).
2. Runtime framework #136 (Challenge timing/keys/scores/retry semantics) and
   content #137 acceptance pins.
3. Generator/actor owners #129, #130, #131 for floor construction and species
   admission; unresolved enemy admission blocks promotion, not P0.
4. Integrator cherry-picks only the three reserved files into its chosen
   integration branch; never merge this worktree's history into species wave.

## Evidence

- Focused test log: `output/workflow/content-expansion/p2-challenge-ch_nari_01kusachi/checks.log`
  (command below, exit 0).
- Implementation packet: generated at handoff time under the lane output dir;
  delivery copy `output/deepseek-wave/inbox/content-533-p0.md`.

```powershell
py -3.12 -m pytest tests/content_lanes/test_p2_challenge_ch_nari_01kusachi.py -q
```
