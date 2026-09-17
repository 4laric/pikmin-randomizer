# Crawler floor-1 content-wiring bridge: staged layout to boot (#706)

Lane `crawler-floor1-content-wiring`, issue #706 (OPEN). Implementation owner:
Codex through shared account 4laric. This bridge connects the staged
`ch_MAT_crawler` floor-1 run layout (the #562 consumer staging) to a booted
stage. No family/shared/native edits, no runtime, no ADMIT. All six runtime
gates UNTESTED. Modeled on the integrated #688 kusachi analog (commit
`a2bd2122`).

## Problem it closes

`p2-challenge-ch-mat-crawler-p1` (#562, blocked gen 8) consumer-verified the
stage-specific boot over staged floor-1 sidecars (SELECTED cave=ch_MAT_crawler
floor=1, SPAWN_COVERED YellowChappy x2, READY/LIVE squad=20, PASS
P2_CHALLENGE_CONTENT_RUN; consumer log sha256
`99e71a06b5af32c9d4d0d7067c31fc0543fdd3238b836af8102812ab76eb48ec`). The #701
binder is selection/coverage only, so the real decoded floor content (unit
pools, enemy rows, ItemGateMgr gate) was not placed. This bridge carries that
content into boot parameters.

## Staged inputs consumed read-only (never duplicated)

- #562 staged run layout, `challenge-0/prepared/p1-crawler-output/run-layout`:
  `stage-manifest.json`, `squad.json`, `run-config.json`, `markers.txt`.
  Pinned facts (verified this turn, staged manifest and disc agree exactly):
  2 floors; floor 1 pool `4_units_c_e_j_l_conc.txt`, 14 enemy rows, 3
  treasures, 1 ItemGateMgr gate (`gate`, life 4000); floor 2 pool
  `1_units_manh_conc.txt`, 7 enemy rows; squad 30+30 (total 60); floor seconds
  170/120; `ui_index` 29; source
  `user/Mukki/mapunits/caveinfo/ch_MAT_crawler.txt` offset 770486496, size
  2411, sha256 `ab3b2dbb238e4a0c2d1bd4c3c958fd52d25b8ee0a0245f756d6d6a138a325bbd`.
- #701 content-loading binder path and #688 kusachi bridge: documented
  read-only interfaces (never imported).
- Shared decoder reused unedited: `experimental.pikmin2_cave_catalog.parse`.

## Boot parameters produced

`boot_params()` returns per-floor arena geometry bindings (unit pool + light
from the decoded stage), actor placement ROWS as weighted definitions
(enemy/treasure/gate/cap, never placements or coordinates), starting-squad
wiring (30+30=60, floor seconds, ui_index 29), the selection contract, the
harness contract, and five observation markers (`P2_CRAWLER_BOOT`,
`P2_CRAWLER_ARENA_BOUND`, `P2_CRAWLER_SQUAD`, `P2_CRAWLER_ACTOR_ROWS`,
`P2_CRAWLER_SELECT`). `wiring_packet()` wraps these with the source pin, staged
evidence, the #688 analog commit, open semantic status, the native candidate
record, blockers and limitations.

`load_staged_layout()` reads and validates the staged layout, failing closed
(`MissingInput`/`LayoutDecodeError`/`HashMismatch`) on a missing directory,
missing file, bad JSON/schema, wrong `source_id`/`source_sha256`/`ui_index`, or
incomplete markers. `cross_check()` fails closed unless the decoded stage
agrees with the staged layout on floor count, unit pools and roster counts.

## Native fixture changes, if any (private candidate only)

None required by this bridge: every input is a root-level staged file or a
documented external interface. The packet records a `native_fixture_candidate`
with `required: false` and the process requirement: if the downstream consumer
(#562) later proves a native fixture change necessary, it must be specified as
a private scoped candidate for owner review with exact file:line anchors and
hashes - never a shared edit. Read-only anchors named: the host-mode stage table
(`pc_port/pc_p2_challenge_mode.h`) and the #701 binder.

## Verification

`tests/test_pikmin2_crawler_floor1_content_wiring.py`: 15 tests + 4 subtests
pass - staged identity pins, source hash/size gate, staged-layout load plus
missing-file/bad-schema/wrong-identity/incomplete-marker fail-closed, synthetic
decode + arena/cross-check, actor-row kinds and counts, mismatch fail-closed,
malformed/unknown-reference rejection, squad wiring, boot-param shape,
no-placement guarantee, packet shape + native candidate, and a real-disc decode
that cross-checks the pinned 14/7/3/1 roster against the disc bytes.

## Downstream consumer

`p2-challenge-ch-mat-crawler-p1` (#562, blocked): consumes this packet's boot
parameters against the challenge host-mode harness and ui_index-29 selection
wiring for its P1 runtime observation, then collision/routes and the six gates.
Enemy/treasure token resolution and unit-asset presence stay with the #562
adapter record and the shared asset readers.

## Captain safety #632

Planning/implementation turn with no runtime run: guard adoption is N/A here.
Any runtime consumer must adopt `scripts/p2_fixture_captain_guard.h`
(sha256 `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`)
with orimaDead/NaviDead/HP<=1 checks, CAPTAIN_DOWN + BLOCKED exit, a parked
captain and labelled protection.