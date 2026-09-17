# Valley of Repose (p2-overworld-tutorial) P0 real-source import contract (#148)

Implementation owner: Codex through shared account `4laric`. Lane
`p2-overworld-tutorial-p0-real-source` (root-only tooling). This finishes the
synthetic-only P0 on real legal bytes.

## Source identity

- `user/Abe/stages.txt` from the verified local US GPVE01 image:
  3275 bytes, sha256
  `4de9008c99e799b99b2746c0156846eeb7ad50895ad110fc7f2070db6de1fff8`.
- Tutorial course (`name tutorial`): three cave links plus one `test` row,
  all decoded and recorded, none omitted:

| Tag | File | Table index |
|---|---|---|
| t_01 | `user/Mukki/mapunits/caveinfo/tutorial_1.txt` | 0 |
| t_02 | `user/Mukki/mapunits/caveinfo/tutorial_2.txt` | 1 |
| t_03 | `user/Mukki/mapunits/caveinfo/tutorial_3.txt` | 2 |
| test | `user/Mukki/mapunits/caveinfo/caveinfo.txt` | 3 |

Cave entries `t_01..t_03` belong to sibling shard caves-tutorial (#593);
routed here, never duplicated. The `test` row is source data, not a
playable cave.

## Deliverable

- `experimental/content_lanes/p2-overworld-tutorial.py` ? reuses the shared
  `stage_cave_links` parser; `decode_tutorial`, hashed `build_manifest`,
  `validate_manifest`, `locate_source`/`decode_source_file` helpers and a
  CLI. No placements emitted, ever.
- `tests/content_lanes/test_p2_overworld_tutorial.py` ? 11 synthetic
  boundary tests + 6 real-bytes tests pinned to the observed hash/size/tags;
  all 17 green (real-bytes class skips only if the legal ISO is absent).
- Real-source manifest: `manifest.json` beside the extracted `stages.txt`
  in the lane output directory (`playable: false`).

## Remaining P1/P2 blockers (reported, not claimed)

Surface days/saves/progression (#132), actor/asset/species closure
(#128/#130/#131/#140/#144/#145/#146); captain safety #632 must be adopted
(`scripts/p2_fixture_captain_guard.h`) before any runtime run. The 15-file
`user/Abe/map/tutorial/` generator/schedule tree is present on disc and is
P1 scope, not decoded here.

No shared edits, no runtime run, no playability claim, no ADMIT. Issue #148
stays OPEN.
