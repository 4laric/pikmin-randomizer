# P0 import contract — tutorial_1 (lane cave-tutorial1-p0-source-decode, #114)

Lane: cave-tutorial1-p0-source-decode, issue #114 (OPEN), phase P0 only.
Source entry: tutorial_1 (Emergence Cave), definition file
user/Mukki/mapunits/caveinfo/tutorial_1.txt (1779 bytes on the local
GPVE01 rev 0 disc, sha256
5dae39d831ec5b68f16176cc4a54bb828aaed4a4bda10d05aef409c54987a84d).
No native worktree, build, or runtime belongs to this slice.

## Catalogued contract (2 floors)

| Floor | Unit pool | Enemies | Treasures |
|---|---|---|---|
| 1 | 1_units_north_tutorial_snow.txt | YellowKochappy | tape_yellow, dia_a_red |
| 2 | 1_units_purple_snow.txt | BlackPom, YellowKochappy, KareOoinu_s, KareOoinu_l, Clover | map01 |

Neither floor carries cargo-suffixed tokens; the contract check verifies
empty cargo on both floors. No gates and no caps on either floor.

## Adapter (experimental/content_lanes/p2-cave-tutorial_1.py)

Isolated per-source layer over the EXISTING shared parsers
(experimental.pikmin2_cave_catalog.parse,
experimental.pikmin2_cave.unit_definition,
experimental.pikmin2_pod.pellet_catalog,
experimental.pikmin2_assets.disc_files) - reused, never forked. Fails
closed on malformed definitions (ValueError) and absent inputs
(FileNotFoundError); contract drift returns mismatch strings.

## Verified P0 result (live decode, this host)

- 2 of 2 floors decoded; contract mismatches: none.
- Both unit pools decoded (7 + 1 units); unit arc and texts closure:
  complete, 0 missing.
- Tests: tests/content_lanes/test_p2_cave_tutorial_1.py - 12 passed
  (synthetic plus the live-decode test, which skips cleanly without a
  local disc image).

## Exact blockers (framework, not decode failures)

- P1 and P2 runtime import needs existing owners: caves #129, assets
  #128, species #131, saves #132, #140/#144/#145/#146.
- Promotion needs species admission per the roster ledger; unadmitted
  floor roster members block promotion, not this preparatory packet.
- No playability is claimed; the full content issue stays OPEN.

## Boundaries

Owns only the three reserved files. No shared parser or schema edits,
no native hooks, no asset redistribution. Evidence and runtime state
live under output/workflow/autofill/planning-shards/caves-tutorial/
prepared/tutorial1-p0-output. Captain safety #632 is N/A for this
tooling slice (no runtime observation); any later runtime phase must
adopt the guard before observed ticks.