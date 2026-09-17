# Valley of Repose P0 import contract (lane p2-overworld-tutorial, #148)

Owner: Codex through shared GitHub account `4laric`. Lane
`p2-overworld-tutorial`, issue #148, phase P0 only (source audit and additive
import contract). Full content issue stays OPEN for P1/P2. No claim of
playability, terrain, placements, or runtime behavior anywhere in this file.

## Source identity and provenance

- Course `tutorial` (Valley of Repose); source `user/Abe/stages.txt` on a US
  GPVE01 revision 0 disc.
- A legal local disc is present at
  `C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso`. The source is read
  **read-only** through the shared `disc_files` reader (which enforces the
  `GPVE01` header); bytes are kept under the ignored lane output.
- Observed pin: 3275 bytes, sha256
  `4de9008c99e799b99b2746c0156846eeb7ad50895ad110fc7f2070db6de1fff8`.
  Independently corroborated by two sibling overworld lanes that extracted
  identical bytes, and the challenge-table sibling's hash matches the
  inventory-recorded `user/Matoba/challenge/stages.txt`.
- The canonical inventory records **no** hash for this path, so the observed
  hash is carried as an observed pin, not a recorded one. When the source is
  absent, manifests record `source_sha256: 'unknown'` plus the exact missing
  prerequisite and nothing is invented.
- Related map sources (referenced, not yet decoded): `user/Kando/map/tutorial`,
  `user/Abe/map/tutorial`.

## What P0 delivers

`experimental/content_lanes/p2-overworld-tutorial.py` consumes the existing
parsers (`stage_cave_links` framed by `gameStages.cpp CourseInfo::read`, and
`pikmin2_cave.tree`) and the shared disc reader, and provides:

- `decode_stages(data)` / `sha256_bytes(data)` — decode and hash raw bytes.
- `locate_source()` / `extract_source_from_iso()` — find/read the source
  from the local ISO read-only, or report the exact prerequisite.
- `tutorial_links(links)` / `classify_links(links)` — select the tutorial
  course's cave links and mark each `story` (canonical `tutorial_1/2/3`) or
  `registered_non_story` (the retail `test` placeholder).
- `tutorial_header(text)` — authored folder/abe_folder/model/collision/
  waterbox/mapcode/route/start/startangle (source coordinates preserved).
- `tutorial_generator_schedules(text)` — both authored `LimitGenInfo`
  tables (non-loop then loop); each row's filename day-range is
  cross-checked against its declared window so a misparse fails closed.
- `tutorial_surface_total(text)` — the declared surface treasure total
  (retail 7), read with the same table framing.
- `story_cave_coverage(links)` — completeness of the canonical story caves.
- `resource_closure(...)` — every needed source path with hash status.
- `build_manifest(...)` / `validate_manifest(...)` — fail-closed manifest
  (identity pins, hash-or-prerequisite coupling, coverage, no fabricated
  runtime keys, `playable: False`).
- `decode_source_file(path)` / `main()` — CLI over a staged file or the ISO.

Tests: `tests/content_lanes/test_p2_overworld_tutorial.py` (33 tests:
synthetic malformed/missing-input boundary + coverage + schedule mismatch +
real-source decode when the local ISO is present; skipped cleanly otherwise).

## Real decoded definitions (evidence)

- Header: `folder user/Kando/map/tutorial`, `abe_folder
  user/Abe/map/tutorial`, model `pra_sample.bmd`, collision `collision.bin`,
  waterbox `waterbox.txt`, mapcode `mapcode.bin`, route `route.txt`,
  start `(-357.18, 0, 2900)`, startangle `150`.
- Generator schedules: 7 non-loop (`0-1`, `1-4`, `1-2`, `2-2`, `3-9`,
  `5-29`, `10-29`) + 3 loop (`30-39`, `40-49`, `50-59`).
- Cave links (table order): `t_01`/`tutorial_1.txt`, `t_02`/`tutorial_2.txt`,
  `t_03`/`tutorial_3.txt` (all canonical story caves) + `test`/`caveinfo.txt`
  (registered non-story placeholder).
- Surface treasure total: 7 (matches the issue's source field).

## Required-inventory coverage

| Lane obligation | P0 status | Detail |
|---|---|---|
| terrain/collision/water | open | header names decoded; map decode + conversion blocked |
| generator day schedules and regrowth | metadata_decoded | both schedule tables decoded; regrowth behavior stays with runtime |
| buried/enemy-held treasure | open | declared total only; per-instance needs map + #140 ledger |
| Onions/ship/bridges/gates | open | map-table fixtures |
| all cave entrances and return anchors | metadata_decoded | all canonical story caves linked; positions/anchors need map + #132 |

## Exact blockers (no runtime work until these publish)

- Runtime dependencies, all OPEN: #128 (converter/assets), #130, #131,
  #132 (surface days/saves/progression), #140 (treasure ledger), #144,
  #145, #146.
- Map-table decoders for `user/Kando/map/tutorial` and
  `user/Abe/map/tutorial` (terrain, water, fixtures, entrances).
- Weighted generator definitions and regrowth semantics (source data, not
  expanded here).
- Species admission for any tutorial enemy remains with family owners.
- Captain safety #632: not triggered (zero runtime runs in this P0 slice).

## Evidence

- Manifest (real source): `output/workflow/content-expansion/p2-overworld-tutorial/manifest-real.json`.
- Focused tests: `output/workflow/content-expansion/p2-overworld-tutorial/tests-p0.log`.
- Staged source bytes: `output/workflow/content-expansion/p2-overworld-tutorial/stages.txt` (ignored).
- Delivery packet: `output/deepseek-wave/inbox/content-148-p0.md`.

## Limitations

Metadata only: header, generator schedules, cave links and the declared
surface total. No actor placements, terrain, water, routes, saves or
receipts are established. Weighted generator rows are definitions, never
actor counts.
