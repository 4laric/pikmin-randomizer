# p2-challenge-ch_mat_route_rover import contract (P0, issue #561)

Lane `p2-challenge-ch_mat_route_rover`, phase P0 (source audit and additive
import contract). Implementation owner: Codex through shared account `4laric`;
executing contributor Muse Spark 1.3 through OpenCode. Parent content issue
#137; coordination #531; autonomous backlog parent #569; integration owner
#437. This document specifies the validated import contract; the
machine-readable packet is produced by
`experimental/content_lanes/p2-challenge-ch_mat_route_rover.py` and tested by
`tests/content_lanes/test_p2_challenge_ch_mat_route_rover.py` (15/15 pass).

## Source identity

- Source ID `ch_MAT_route_rover`, label `P2 Challenge 28: ch_MAT_route_rover`
  (English title unresolved; source ID and UI index 27 are authoritative).
- Definition: `user/Mukki/mapunits/caveinfo/ch_MAT_route_rover.txt`, recorded
  sha256
  `e03eb33a78526adb13eebd08af453555bc9cd219f6a3e624b28a0771ea12cb79`
  (inventory evidence pin, equal to the plan pin; the disc was unavailable to
  this turn, so no bytes were re-extracted).
- Stage table: `user/Matoba/challenge/stages.txt`, recorded sha256
  `59890efa80fe5a77d52b9a87301b97c91cd10c94ff9a3fb85c49b78dfae03cf1`.
- Baseline inputs: lane-plan entry (`docs/PIKMIN_CONTENT_IMPORT_LANES.json`)
  and the 30-stage inventory collection
  (`docs/PIKMIN2_CONTENT_INVENTORY.json`, table orders and UI indices each
  exactly 0-29 with no collision/gap, floor total 59). All agree; any drift
  fails the adapter closed.

## Stage contract (verbatim definitions, not gameplay)

| Field | Pinned value |
|---|---|
| Table order / UI index | 21 / 27 |
| Floors | 1, with floor_seconds [90.0] (timer total 90.0) |
| Starting Pikmin | 60 total: native color indices 0, 1 and 2, maturity index 2, count 20 each |
| Sprays | bitter 2, spicy 2 |
| Legacy time | 300.0 |
| Treasure-count field | 0 |

Native color/maturity indices are carried as indices, never guessed into
species names. The backlog label ordinal (`P2 Challenge 28`) is **not** the UI
index; across the 30-stage catalog the label ordinal equals `ui_index + 1`
(verified), and this lane's UI index is 27.

## Floor coverage

Exactly one floor (1..1) with exactly one timer entry; the adapter reports a
`floor_coverage` block (`complete: true`, `timer_total: 90.0`) and fails
closed if floors and `floor_seconds` ever disagree. Per-floor enemy/treasure
rosters are **not** decoded here: the caveinfo bytes were unavailable, so the
packet records `floor_roster_decode: OPEN` and invents no roster values.
Timers/sprays/populations are definition inputs for the P1 framework (#136),
not observed gameplay.

## Resource closure (status and owner per required resource)

| Resource | Status | Owner |
|---|---|---|
| Stage definition bytes | pinned-not-read (sha256 recorded) | content lane #561 (decode OPEN) |
| Stage table ordering | pinned-not-read | Challenge content #137 |
| Floor layout and generator seams | unsupported-reference | #129 and #137 |
| Starting roster, sprays and timers | pinned-not-read | #136 (Challenge framework) |
| Floor actors and hazards | unsupported-reference | #130/#131 and family lanes |
| TheKey/hole/geyser, scoring, retry, result semantics | unsupported-reference | #136 and #137 |

## Reserved changes

- `experimental/content_lanes/p2-challenge-ch_mat_route_rover.py` — isolated
  metadata/import adapter.
- `tests/content_lanes/test_p2_challenge_ch_mat_route_rover.py` — 15 focused
  tests (pinned-source positives plus fail-closed negatives).
- `docs/content_lanes/p2-challenge-ch_mat_route_rover.md` — this spec.

No shared parser/schema, species, native, admission or other-lane edits.

## Evidence

- Focused test log and generated packet:
  `output/workflow/autofill/p2-challenge-ch_mat_route_rover/`.
- This P0 slice ran no native build and no runtime; the host `chal0` fixture
  is not Challenge mode and proves nothing here.

## Blockers (exact)

1. Disc bytes of `user/Mukki/mapunits/caveinfo/ch_MAT_route_rover.txt` (and
   `user/Matoba/challenge/stages.txt`) are required to decode per-floor
   rosters; record their SHA-256 in the lane entry when staged. Never
   redistribute assets.
2. P1 waits on the Challenge runtime framework (#136) and the
   content/generator/actor contracts (#137, #129, #130, #131).
3. TheKey/hole/geyser, scoring, ordinary vs deathless completion and retry
   reset are unvalidated.

## Status

P0 implementation packet reviewed and tested. Full content acceptance and
dependencies stay OPEN. No claim of playability. No ADMIT.
## P1 runtime import (floor-1, issue #561)

P1 extends the P0 adapter in place (P0 sections above unchanged) with a
runtime import path for the single floor:

- Actual retail `ch_MAT_route_rover.txt` bytes re-extracted from the local
  legal ISO and hash-verified against the inventory pin
  (`e03eb33a...ea12cb79`, 1123 bytes). Decoded floor roster: KumaChappy x3
  (weight 10/type 1 each, roster minimum 1 each), KumaKochappy x2 (weight 20/
  type 0 each, minimum 2 each); treasures diamond_red, diamond_red_l,
  diamond_green_l, flask (weight 10 each); unit pool
  `1_units_bunki_2_tile.txt` (7 units, all arc/texts assets present).
- Starting squad positional from the pinned matrix: species 0/1/2
  (Blue/Red/Yellow per the framework COLORS order) x 20 flower each, 60
  total; 90 s floor timer; 2 bitter + 2 spicy sprays.
- Staged run layout: `p2-cave-entry.txt` (60 restore lines),
  `p2-cave-generate.txt` (pool + 7 units, one 7x7 room, zero doors/links,
  spawns KumaChappy 3 + KumaKochappy 4, anchor hole as a staged marker-only
  choice), markers template with `P2_ROUTE_ROVER_*` lines, run-config.json.
- Runtime evidence (hashed logs under the lane output dir): private leased
  build with provenance + Ninja no-work, fresh arena with live squad,
  observed 960x540 centred window, generate/restore/nav markers parsed with
  `p1_parse_markers` (absent markers stay absent, never defaulted).
- Captain safety #632 adopted: canonical `scripts/p2_fixture_captain_guard.h`
  recorded by hash; orimaDead/deadState/HP<=1 checks with CAPTAIN_DOWN +
  BLOCKED exit policy; captain parked (no input) during observation; no
  blanket invincibility. Protected observations cannot prove captain damage.
- Gates are PASS only where real markers prove them; everything else stays
  UNTESTED (never upgraded from P0). No playability claim beyond observed
  evidence; no ADMIT.

## P1 remaining work

Higher floors: none (single-floor stage). P2 persistence (save/reload,
death/extinction, reentry, receipts, deterministic replay, no leakage),
spray/receipt semantics, TheKey/hole/geyser completion, scoring and retry
stay OPEN with owners #136/#137/#132/#140 and family lanes.

## P1 runtime evidence and corrected staging (gen 7, issue #561)

Verified consumer chain on the integrated pins (native cherry-picks #679
`960cd5ef`/`11665704` + #695 `8c7b97fd`; exe sha256 `6412e008`):

- The engine resolves assets as `assets/dataDir/...` from the run cwd, so the
  arena override MUST be applied to the run`s `assets` tree
  (`overlay(ASSETS, run/"assets", {...})`), not to `run/dataDir`. #699
  (`rover-spawn-count-reconciliation`) named this staging-path fault; the
  entry checkpoint itself was correct.
- Corrected run (`run-rover-12`): 60 `P2_CAVE_RESTORE species=0/1/2
  maturity=2`, `P2_CAVE_READY floor=1 survivors=60 health=1`,
  `P2_CAVE_GENERATE_SPAWN id=KumaChappy count=3` +
  `id=KumaKochappy count=4`, `P2_CAVE_GENERATE_ANCHOR kind=hole x=0 y=0 z=0
  radius=20`, `P2_CAVE_GENERATE_PASS rooms=1 spawns=2 links=0 anchor=hole`,
  `P2_ROOM_READY treasure=bolt carry=5 repairs=1`; 960x540 centred window,
  alive, no abort, no captain-down, no extinction. Log sha256
  `238996404789a80260c7012bb2267acd076959b5609c0b0bfa1655f73ccc8416`.
- Captain safety #632 adopted (`d2f678c9...`); captain parked, no input.
- All six arena gates remain UNTESTED except the observed boot facts above;
  no playability claim; no ADMIT.
