# Kusachi content-wiring bridge: staged layout to boot parameters (#688)

Lane `kusachi-content-wiring`, issue #688 (OPEN). Implementation owner: Codex
through shared account 4laric. This bridge connects the staged kusachi run
layout (commit `380610a3`, issue #533) to a booted stage. No shared/native/
family edits, no runtime, no ADMIT. All six runtime gates UNTESTED.

## Staged inputs consumed read-only (never duplicated)

- #533 staging adapter + manifest/markers/spec at commit `380610a3`:
  `experimental/content_lanes/p2-challenge-ch_nari_01kusachi.py` - source
  identity (`ch_NARI_01kusachi.txt`, sha256 `b8d232f4...`), 1 floor, 50 blue
  leaf roster, 180 s timer within 350 s legacy, sprays 1/2, ui_index 3.
- Shared decoders reused unedited: `experimental.pikmin2_cave_catalog.parse`,
  `experimental.pikmin2_assets.disc_files`.
- #656 build/run harness interface (documented, not imported): consumes a
  staged run layout plus the #632 guard header and emits boot/run evidence.
- #675 native stage-boot hook (documented): native entry mechanism.
- #651 host-mode fixture stage table (documented): `selectByUiIndex`
  keyed by ui_index; kusachi resolves at ui_index 3. The P1
  `--experimental-challenge-level` namespace is for P1 layouts and is NOT the
  kusachi boot path.

## Boot parameters produced

`boot_params()` returns arena geometry binding (unit pool + light from the
decoded stage), actor placement ROWS as weighted definitions (enemy/treasure/
gate/cap, never placements or coordinates), starting-squad wiring (50 blue
leaf, timers, sprays), the selection contract, the harness contract, and five
observation markers (`P2_KUSACHI_BOOT`, `P2_KUSACHI_ARENA_BOUND`,
`P2_KUSACHI_SQUAD`, `P2_KUSACHI_PLACEMENT_ROWS`, `P2_KUSACHI_SELECT`).
`wiring_packet()` wraps these with the source pin, staged commit, open
semantic status, blockers and limitations.

## Native fixture changes, if any (private candidate only)

None required by this bridge: every input above is root-level metadata or a
documented external interface. If the consumer (#533 P1) later proves a
native fixture change necessary, it must be specified as a private scoped
candidate for owner review with exact file:line anchors and hashes - never a
shared edit. This packet records that requirement explicitly.

## Verification

`tests/test_pikmin2_kusachi_content_wiring.py`: 9 tests + 4 subtests pass -
staged identity pins, source hash gate, synthetic decode + coverage, arena/
light binding, roster kinds, malformed/missing fail-closed (synthetic and
mutations), unknown-reference rejection, squad wiring, boot-param shape,
no-placement guarantee, packet shape.

## Downstream consumer

#533 (`p2-challenge-ch_nari_01kusachi-p1`, blocked): consumes this packet's
boot parameters against the #656 harness and #675/#651 selection wiring for
its P1 runtime observation. Enemy/treasure token resolution and unit-asset
presence stay with #137 and the #533 adapter record.

## Captain safety #632

Planning/implementation turn with no runtime run: guard adoption is N/A here.
Any runtime consumer must adopt `scripts/p2_fixture_captain_guard.h`
(sha256 `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`)
with orimaDead/NaviDead/HP<=1 checks, CAPTAIN_DOWN + BLOCKED exit, parked
captain and labelled protection.
