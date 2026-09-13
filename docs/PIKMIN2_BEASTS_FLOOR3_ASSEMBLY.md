# Beasts floor 3 engineering assembly (#306)

Owner: Codex using shared 4laric account. Base: frozen #303,
`6e325b21331fa3a46cf8b67d595cbd91a054444c`.

This source-only package joins both floor-three room candidates with a straight
corridor and seals the other two block-room doors with source cap units. It is an
authored engineering arrangement, not retail map generation. Every selected unit
belongs to the floor-three source pool. The placement is derived from matching
opposite source door directions and coincident waypoint positions.

| Instance | Quarter turns | Center X/Y/Z |
|---|---:|---|
| room_block1_3_hiba_tsuchi | 0 | 0 / 0 / 0 |
| way2_tsuchi | 0 | -85 / 0 / -425 |
| room_north_1_hiba_tsuchi | 0 | -85 / 0 / -935 |
| cap_tsuchi | 2 | 85 / 0 / 425 |
| cap_tsuchi | 3 | -425 / 0 / 85 |

All unit grid footprints are nonoverlapping. Each of four seams joins coincident,
opposite-facing doors. Each seam has 39 offline floor samples across a 50-unit
width and 60-unit length: **156 samples passed**, including both sides and the
seam center. These tests cover the seam strips, not all scenery or carry footprints.

The assembly applies the opt-in [source waypoint grounding](PIKMIN2_BEASTS_NAVIGATION.md)
before transforms. It preserves source directed edges and merges only matched
seam nodes. All **12 merged waypoints** reach the block north-door waypoint at
`[-85,0,-340]`, chosen as an engineering return target. All-pairs connectivity
remains false because source one-way leaves remain intact. This target does not
spawn a Pod/captain, expose a cave exit or define a campaign destination.

Rendered geometry has 1,098 vertices, 1,946 triangles, 24 shapes and 13 textures.
Actual source models are read from the hash-verified GPVE01 revision 0 archives;
catalog sources and converted collision inputs are checked before assembly.
Material conversion retains the existing approximation policy. No actor or
treasure has been instantiated, and no native gameplay test was performed.

## Reproduction and evidence

Run from the private `output/p2-beasts-floor3-track` root worktree:

```powershell
python -m experimental.pikmin2_beasts_floor3_assembly `
  --iso 'C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso' `
  --catalog ../../output/p2-cave-catalog-batch/audit-final/catalog.json `
  --imported ../../output/p2-mapcode0-batch/import `
  --output output/floor3-306/new-package
python -m pytest -q tests/test_pikmin2_beasts_floor3_assembly.py tests/test_pikmin2_beasts_assembly.py tests/test_pikmin2_beasts_navigation.py tests/test_pikmin2_beasts_floor3.py
```

**14 tests and 26 subtests passed.** Coverage includes source-door placement,
coincident/opposite seam endpoints, complete door pairing, overlap rejection,
missing seam ground, directed return paths, cut return paths and ambiguous targets.

Actual-disc builds `output/floor3-306/final-a` and `final-b` produced six
byte-identical files. Earlier probes revealed path-dependent render sidecars;
the final implementation normalizes them. Final hashes:

| File | SHA256 |
|---|---|
| assembly.json | `8132868948332b6e0bfb5cdfc9e09de55e4835ab67af3345ef4c2c312009c2d8` |
| room.mod | `d4e269abb937fad64b682754cfa855d2928ea66fd63f32e06c5b1e3518e2f4a1` |
| collision.json | `93118a7aeb8578357475904ed876aa74bedb195e5735917124b82f1e6ea23146` |
| room.ini | `04f6d8364e8f36c964b611f3c5236ee84f3e249a2723a315d4e233aabad5f261` |

All six hashes are local in `output/floor3-306/verification.json`. Output is fresh,
private and source assets remain read-only. No native/build/save files changed.

Remaining work: select and ground actual engineering gameplay anchors, install
both source treasures and Hiba/plant content, validate native navigation and
carrying through the corridor, then join the separate handoff track. Offline
geometry and graph evidence do not establish native-ready or playable floor 3.
