# Awakening Wood P0 source-audit packet (p2-overworld-forest, #149)

Lane `p2-overworld-forest`, issue #149, parent #531. Implementation owner:
Codex through shared account 4laric; executing worker muse-l53 (session
`opencode:ses_f58980693ffeuOoioNcyCB1vYz`, generation 2). P0 only: source
audit and additive import contract. No native build, runtime, ADMIT, or
asset redistribution. Full content issue stays OPEN for P1/P2.

## Source

- Course `forest` (Awakening Wood), definitions in `user/Abe/stages.txt`
  (shift_jis, parsed with the existing `stage_cave_links` framing).
- Inventory baseline `docs/PIKMIN2_CONTENT_INVENTORY.json` catalogues all
  four surfaces against this same source; that catalogue is the baseline,
  not a reimplementation target.
- Actual `stages.txt` bytes were NOT available in this turn, so no hash is
  validated here and no cave roster is claimed. The adapter reports the
  exact missing prerequisite instead of inventing values:
  legal US GPVE01 rev 0 disc or an extracted `user/Abe/stages.txt`.

## Adapter (`experimental/content_lanes/p2-overworld-forest.py`)

- `decode_forest(text)` reuses `stage_cave_links` as-is, filters
  `course_id == "forest"`, preserves original tag/filename/source-path
  fields and table order. Fails closed on empty input, malformed framing,
  or a missing forest course.
- `build_manifest(text, stages_sha256=None, cave_hashes=None)` returns the
  isolated packet: course/label/issue/source, `cave_links`, `cave_count`,
  the five `required_inventory` rows marked `baseline_catalogued`,
  `resource_closure` (stages.txt + each
  `user/Mukki/mapunits/caveinfo/<file>` with hashes where supplied),
  the eight runtime `blockers` (#128/#130/#131/#132/#140/#144/#145/#146),
  and `playable: false` with an explicit no-placement policy.
- `validate_manifest()` enforces schema/course/source, non-empty forest
  links, unique tags, expected cave path prefix, count agreement,
  inventory exactness and the non-playability invariant.
- CLI: `--stages <path> [--output <path>]`; without `--stages` it prints
  the missing prerequisite and exits non-zero.

## Tests (`tests/content_lanes/test_p2_overworld_forest.py`)

10 focused tests on synthetic stages.txt text: forest filtering and order,
two-cave decode, missing-forest/missing-input/malformed/duplicate-tag
failures, manifest closure + non-playability + no-placement boundary,
bad-hash/count/playability rejection, exact prerequisite text,
sha256 helper boundary. No retail assets read.

## Verification

- `py -3.12 -m pytest tests/content_lanes/test_p2_overworld_forest.py -q`
  → 10 passed (log in lane output dir).
- `py -3.12 scripts/check_content_import_lanes.py` → PASS 53 lanes
  (plan untouched; this slice only adds reserved files).

## Blockers for P1/P2 (unchanged, reported not resolved)

#128/#130/#131/#140/#144/#145/#146 actor/asset/species closure,
#132 surface days/saves/progression. Native collision/water/routes,
generator day schedules, buried/enemy-held treasure, Onion/ship/bridge/
gate behavior and cave entrance/return anchors all require validated
dependency publications plus the actual stages.txt bytes. No runtime
gates observed; all six arena gates UNTESTED by design in the tooling
handoff.
