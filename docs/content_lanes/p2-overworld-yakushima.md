# P0 import contract — Perplexing Pool (yakushima, #150)

Lane `p2-overworld-yakushima`, P0 only. Implementation owner: Codex through
shared account `4laric`; executing contributor Muse Spark 1.3. No native
build, no runtime, no playability claim, no ADMIT.

## Source identity

- Course `yakushima` ("Perplexing Pool"), issue #150, parent #531.
- Source file `user/Abe/stages.txt` — shared by all four overworld courses
  (tutorial/forest/yakushima/last). **Bytes unavailable**: absent from the
  decomp checkout (which carries only the loader below) and no local P2 disc
  staged; lane `source_sha256` is null. Record the SHA-256 in the lane entry
  when staged; never redistribute assets.
- Loader (read-only, unmodified): `native/pikmin2-research/include/Game/gameStages.h`
  (`CourseInfo` fields, `MAX_LEVELS (4)` = overworld course count) and
  `native/pikmin2-research/src/plugProjectKandoU/gameStages.cpp`
  (`CourseInfo::read` fixed key order; `LimitGenInfo::read` rows
  name/minimum-day/maximum-day/day-limit; `CaveOtakaraInfo::read` rows
  4-char ID32/otakara-count/definition-file).

## Adapter (`experimental/content_lanes/p2-overworld-yakushima.py`)

- `decode_course_pairs(pairs)` — strict ordered validation of a decoded
  course record (scalar keys in stream order, then `limit_gens`,
  `loop_gens`, `cave_otakara`, `ground_otakara_max`). Finite numbers,
  non-negative ints, non-empty names, 4-char cave IDs, `.txt` definition
  files, no asset-tree escapes, `minimum_day <= maximum_day`. Raises
  `CourseDecodeError` naming the exact field. The JSystem-Stream byte reader
  over disc bytes is the recorded missing prerequisite; this boundary takes
  decoded values so no retail bytes are fabricated.
- `resource_closure(record, file_inventory=None)` — maps the record onto
  exactly the five required-inventory items. With no disc staged every
  record-derived item is `missing-source`; Onion/ship/bridge/gate fields and
  return anchors (no loader field exists) are `unsupported-reference` naming
  the owning system (#132/#140–146, cave lanes #158–161).
- `missing_prerequisites()` — the three exact blockers: disc bytes + hash
  recording, validated P1 publications (#128/#130/#131/#132/#140/#144/#145/#146),
  sibling cave definitions (#158–161).
- `implementation_packet()` — reviewed P0 packet incl. `floors: 0`
  (overworld course; MAX_LEVELS is the course count) and an explicit
  no-playability statement.

## Tests (`tests/content_lanes/test_p2_overworld_yakushima.py`)

12 passed, 19 subtests (`output/workflow/content-expansion/p2-overworld-yakushima/pytest.log`,
SHA-256 `ad69ed2074841d596107e33b44601c24d315098845a2418bc1f02d637cc8c3ab`):
well-formed synthetic decode, lane constants, misordered/missing keys,
non-list input, bad scalars/schedules/cave rows, full inventory coverage,
honest missing-source vs present mapping, exact prerequisites, and a
no-playability-claim assertion. All fixtures labeled synthetic; no value
claimed as retail fact.

## Native/framework blockers (exact)

1. `user/Abe/stages.txt` bytes + SHA-256 (operator disc; see above).
2. P1 runtime dependency publications #128, #130, #131, #132, #140, #144,
   #145, #146 — none validated for this course yet.
3. Sibling cave lanes #158–161 for entrance-to-cave cross-checks.
4. Shared-seam note for existing owners: none required by P0 (no shared
   file touched; no review requested).

## Delivery packet

Canonical: `output/deepseek-wave/inbox/content-150-p0.md` (expansion P0
candidate; cherry-pick reserved files only, never merge this history).
