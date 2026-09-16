# p2-cave-yakushima_4 P1 floor-1 runtime import (#161)

Lane `shard-caves-yakushima-yakushima4-p1`, generation 2, issue #161 (parent
#531; existing content owner #137). Pins: root `36b86839`, native `a95040b6`.
Outcome: **P1 floor-1 staging/observation contract delivered; runtime boot
BLOCKED on a concrete pin-prerequisite gap**. No ADMIT, no false PASS, issue
#161 stays OPEN.

## What is delivered (reserved files only)

- `experimental/content_lanes/p2-cave-yakushima_4_p1.py` ? floor-1 staging and
  observation contract. Consumes the pinned P0 audit packet read-only, selects
  the real floor-1 rows (`2_units_gw_l_conc.txt`, 8 enemy / 2 treasure
  definitions, 0 gates, 2 caps, treasures `baum_kuchen_s` + `chocoichigo`),
  emits the bounds-validated native entry line, probes the required provider
  files, and parses/validates the real `P2_CAVE_READY` / `P2_CAVE_NAV` boot
  markers. Unit staging is never inferred from nav lines.
- `tests/content_lanes/test_p2_cave_yakushima_4_p1.py` ? 14 focused synthetic
  tests (floor selection, pool drift, entry bounds, provider probe, blockers,
  observation positive/negative).
- `docs/content_lanes/p2-cave-yakushima_4-p1.md` ? this contract.
- `native/tools/p2_yakushima4_p1_fixture.cpp` ? engine-independent stdlib-only
  staging writer + boot checker (`-Wall -Wextra -Werror`), never linked into a
  game target.

## Blocking prerequisite (verified, not assumed)

The lane brief states the P0 packet and the #129/#132 provider contracts are
done+integrated at these pins. They are not present in the pinned worktrees:

| Required at pin | State |
|---|---|
| `pc_port/pc_p2_cave_generate.h` / `.cpp` (#129 native provider) | **absent** from native `a95040b6` |
| `experimental/content_lanes/p2-cave-yakushima_4.py` (P0 adapter) | **absent** from root `36b86839` (committed only on `codex/shard-caves-yakushima-y4p0`) |
| native per-floor unit-staging consumer | **absent**: `pc_p2_cave.cpp` consumes a floor entry and emits `P2_CAVE_NAV`, but does not stage cave-decode units |

The #129 provider module exists on the divergent `output/dsw/native-wave` line
(`pc_p2_cave_generate.h`), which is not an ancestor of this lane's native pin.
Consequently no real floor-1 **unit staging** boot can be produced on the
assigned pins without a cross-line integration that is outside the four
reserved files. This is recorded as the exact blocker instead of simulating it.

## Honest status

- Floor selection, entry-manifest emission, provider probe and boot-observation
  validation are implemented and tested (14/14).
- `collision_routes` are only claimed once a real `P2_CAVE_READY floor=1` plus
  a `P2_CAVE_NAV` walk-inside sample exist; none was produced this turn
  (BLOCKED at staging), so the acceptance runtime items are UNTESTED.
- Higher floors, persistence and full-campaign resume remain out of scope;
  #128/#131/#140 and unadmitted encounter species remain OPEN.
- Captain-safety (#632) adoption is recorded for the future run: the fixture
  guard must be present before any observation tick; no protected-invincibility
  claim is made here.

## Exact next dependency

Re-provision this lane on an integrated pin that contains both the #129
`pc_p2_cave_generate` module and the #161 P0 adapter (the P0 adapter commit is
`ad4a34e5` on `codex/shard-caves-yakushima-y4p0`), or authorize a scoped
cross-line integration. Then a leased private engine build with the captain
guard can observe the floor-1 boot and complete the runtime acceptance items.
