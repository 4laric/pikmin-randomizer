# Valley of Repose P0 import contract (lane p2-overworld-tutorial, #148)

Owner: Codex through shared GitHub account `4laric`. Lane
`p2-overworld-tutorial`, issue #148, phase P0 only (source audit and additive
import contract). Full content issue stays OPEN for P1/P2. No claim of
playability, terrain, placements, or runtime behavior anywhere in this file.

## Source identity

- Course `tutorial` (Valley of Repose); source `user/Abe/stages.txt` on a US
  GPVE01 revision 0 disc (first six header bytes `GPVE01`, byte 7 revision 0,
  enforced by `experimental.pikmin2_assets.disc_files`).
- Canonical inventory (`docs/PIKMIN2_CONTENT_INVENTORY.json`) records **no
  hash** for this path, and no legal disc source is present on this host.
  Manifests therefore carry `source_sha256: 'unknown'` plus the exact missing
  prerequisite from `source_prerequisite()`. Nothing is invented to fill it.
- Related map sources (not decoded here): `user/Kando/map/tutorial`,
  `user/Abe/map/tutorial`.

## What P0 delivers

`experimental/content_lanes/p2-overworld-tutorial.py` consumes the existing
parsers (`experimental.pikmin2_regional_audit.stage_cave_links`,
`experimental.pikmin2_cave.tree`) and provides one isolated boundary:

- `decode_stages(data)` — Shift-JIS decode of raw `stages.txt` bytes.
- `tutorial_links(links)` — select the tutorial course's cave links
  (tag/filename/source path); raises when the course is absent.
- `tutorial_surface_total(text)` — the course's trailing declared surface
  treasure total (retail value 7), read with the same `CourseInfo::read`
  framing the existing parser enforces. A declared total, not placements.
- `build_manifest(text, links, source_sha256=None)` — manifest with cave
  links, surface total, required-inventory coverage, runtime dependencies,
  missing prerequisites and limitations. Never emits
  placements/coordinates/actors/spawns.
- `validate_manifest(manifest)` — fail-closed checks: identity pins,
  hash-or-prerequisite coupling, link shape/uniqueness, no fabricated
  runtime keys, inventory/dependency sync with
  `docs/PIKMIN_CONTENT_IMPORT_LANES.json`.

Tests: `tests/content_lanes/test_p2_overworld_tutorial.py` (18 tests, all
synthetic minimal tables; malformed/missing-input coverage; plan-sync test).

## Required-inventory coverage

| Lane obligation | P0 status | Detail |
|---|---|---|
| terrain/collision/water | open | map decode + conversion; runtime deps |
| generator day schedules and regrowth | open | filename/window rows not yet extracted; bounded table decode is a P0 follow-up |
| buried/enemy-held treasure | open | declared total only; per-instance needs map + #140 ledger |
| Onions/ship/bridges/gates | open | map-table fixtures |
| all cave entrances and return anchors | metadata | cave tags/filenames linked; positions/anchors need map + #132 |

## Exact blockers (no runtime work until these publish)

- Missing local source: US GPVE01 disc image with `user/Abe/stages.txt`
  (hash unrecorded; supply locally, never redistribute).
- Runtime dependencies, all OPEN: #128 (converter/assets), #130, #131,
  #132 (surface days/saves/progression), #140 (treasure ledger), #144,
  #145, #146.
- Map-table decoders for `user/Kando/map/tutorial` and
  `user/Abe/map/tutorial` (terrain, water, fixtures, entrances).
- Generator filename/window-row extraction from the two stages.txt
  generator tables (P0 follow-up inside this lane's reserved files).
- Species admission for any tutorial enemy remains with family owners;
  unresolved admission blocks promotion, not preparatory work.

## Evidence

- Focused tests: `output/workflow/content-expansion/p2-overworld-tutorial/tests-p0.log`.
- Delivery packet: `output/deepseek-wave/inbox/content-148-p0.md`.
- Handoff: `output/workflow/content-expansion/p2-overworld-tutorial/handoff.json`
  (kind tooling; all six gates UNTESTED; fixture adoption N/A).

## Limitations

Metadata only: cave links plus the declared surface total. No generator
coordinates, actor placements, terrain, water, routes, saves or receipts are
established. Weighted generator rows are definitions, never actor counts.
