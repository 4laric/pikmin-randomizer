# Lane 04 — DeepSeek handoff (review fix round 1): native placement-evidence probe (#440)

Lane 04 (placement/encounter compatibility). Implementing worker/session:
DeepSeek (deepseek-v4-pro); implementation owner: Codex through shared account
`4laric`. Executing this slice unattended. This revision incorporates the
review feedback on the first handoff.

## Concrete deliverable

One real consumer — the **Snow Bulborb / Dwarf Orange Bulborb host cohort**
(the native `TEKI_Chappy` dwarf; roster `YellowKochappy` source_id 45 and
`BlueKochappy` source_id 44) — exercising the lane-04 placement interface
end-to-end, plus the missing ledger slice: **native terrain / space / water /
route evidence** that the placement schema requires before a `(slot, identity)`
pair is admitted.

A native probe (`pc_p2_placement_probe`) samples the live map at each spawned
Teki actor's position and emits `P2_PLACEMENT_SLOT` / `P2_PLACEMENT_PROBE`
markers. It reports `xyz` (ground triangle exists), `terrain` (`ground` /
`water` / `none` — `none` when no triangle, so a destination-denied spawn cannot
be misread as ground), and `route` (nearest OPEN waypoint within a 2D `200.0`
coverage cap, with the measured `route_distance` printed). A root layer
(`randomizer.p2_placement_native` + `randomizer.p2_placement_probe`) folds the
markers into slot `evidence` and the audit.

## Source IDs and files owned

- Identity exercised end-to-end: `YellowKochappy` (Snow), `BlueKochappy`
  (Dwarf Orange) — lane-13 candidates already in
  `randomizer.p2_placement_catalog.CANDIDATE_SPECS`. The runtime probe
  consumes the native `TEKI_Chappy` dwarf host; the P2 Snow/Orange visual bank
  is not staged in this probe run (see Gate 1).
- Native (new, lane-owned): `pc_port/pc_p2_placement_probe.h`, `pc_port/pc_p2_placement_probe.cpp`.
- Native (narrow additive hook, split into its own commit): `pc_port/pc_p2_preview.cpp`
  (one `#include` + one `pc_p2_placement_probe_run();` call); `CMakeLists.txt` (one source line).
- Root: `randomizer/p2_placement_probe.py` (marker parser), `randomizer/p2_placement_native.py`
  (stamping/audit), `tests/test_p2_placement_probe.py`, `tests/test_p2_placement_native.py`,
  `scripts/run_p2_placement_probe.py`, `scripts/audit_p2_placement_evidence.py`.

## Ordered commits

- Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91` → head
  `1ddc04f4b45ab7efeafd72336fd4bcc15cf85115` (branch `deepseek/p2-l04`), clean.
  - `3992d2c00316b7a6c72149f6cb5b0afc1c773da9` lane04: native placement-evidence probe + root stamping/audit bridge and tests (#440)
  - `07a846278abd3be3e09119a54d9e790550f9d949` lane04: handoff doc (#440)
  - `1ddc04f4b45ab7efeafd72336fd4bcc15cf85115` lane04: review fixes — native marker parser, runner MinGW/converted correction, arena-only audit label (#440)
- Native base `b805d9c626e4f4558c95aef7cac311a5d9a2068f` → head
  `b68c2ddca670d899382a1e9875c622b79dbcbc53` (branch `deepseek/p2-l04-native`), clean.
  - `68dbf4a0235a6af08e218230ce43e0c51f03f4a8` lane04: placement/encounter evidence probe module (terrain/water/distance-capped route) (#440)
  - `b68c2ddca670d899382a1e9875c622b79dbcbc53` lane04: hook pc_p2_preview.cpp/CMake for placement probe (#440)

The earlier native commit `cd9ee6b5` (which bundled the hook with the module)
was rewritten (local-only, no upstream) so the shared `pc_p2_preview.cpp`/CMake
hook is a separate, labelled commit outside lane 04's module ownership.

## Interfaces / hooks touched and why

- `void pc_p2_placement_probe_run()` (lane-owned header). Read-only; no
  shared-semantics edit. Reuses P1 primitives: `MapMgr::getCurrTri`/`getMinY`
  (terrain existence + height), `MapCode::getAttribute` (`ATTR_Water`),
  `RouteMgr::findNearestWayPoint('test', pos, false)` + a `200.0f` XZ radius
  cap. Emits `P2_PLACEMENT_SLOT generator=.. actor=.. xyz=.. terrain=ground|water|none route=.. route_distance=.. water_depth=..`.
- `pc_p2_preview.cpp`: additive import + one call (separate commit). No change
  to `teki.h`, `tekiinteraction.cpp`, `tekibteki.cpp`, `tekimgr.cpp`,
  `gameCoreSection.cpp`, `navi.cpp`, `pc_randomizer.cpp`, `pc_p2_preview.h`.
- Root `randomizer/p2_placement_native.py`: `PROBE_SCHEMA`, `normalize_probe`,
  `stamp_evidence` (upgrade-only merge), `audit_native`, `slot_evidence_summary`.
- Root `randomizer/p2_placement_probe.py`: `capture_markers`, `build_probe`
  (the native-marker parser; `terrain` is True only when `xyz` is True AND the
  native class is `ground`/`water`; `generator`/`uid` both accepted).

## Build evidence (from `output/dsw/l04-build-evidence.txt`)

```
2026-09-14T19:40:45 lane=l04 target=pikmin_pc native=cd9ee6b57f4d4c3e0ef57b62d8a9e66bc9df2e86 dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l04-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l04-build\bin\nectar.exe sha256=65b174456caf39917b20b6a945929055dbe9be8655001d22df6ef138d56e4bd4 ninja_n="ninja: no work to do." seconds=158
2026-09-14T20:10:15 lane=l04 target=pikmin_pc native=b68c2ddca670d899382a1e9875c622b79dbcbc53 dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l04-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l04-build\bin\nectar.exe sha256=5fd00043009560f2b2639a1b29553fcdc5c1d4226b468e1e1083fdc39432be08 ninja_n="ninja: no work to do." seconds=91
```

(The `cd9ee6b5` line is the superseded pre-split build; the review-fix
executable is `b68c2ddc`, SHA-256 `5fd00043…be08`.)

## Fixture adoption evidence

- Fresh arena staged into `output/dsw/l04-out/<uuid>/assets` with
  `scripts/preview_pikmin2_room.prepare` → `overlay()` → `ensure_pikmin_squad()`
  (20 red Pikmin starting squad added).
- Converted room inputs passed via `--converted` (a `room.mod`/`room.ini`/
  `treasure.mod` directory). The script no longer hardcodes another lane's
  `l20-out/converted` path; it defaults to the documented
  `output/pikmin2-room105` and fails with a clear error if that is absent. For
  this host the converted room was provided explicitly from
  `output/dsw/l04-out/converted` (copied once, read-only).
- Window/startup log: `[PC Port] SDL2 Window & OpenGL Context initialized
  successfully (960x540)` and `Experimental preview window set to 960x540
  windowed and centered`.
- Live gameplay, no extinction: `[Pikipelago] P2_ROOM_READY treasure=bolt
  carry=5 repairs=1` reached.
- Runtime evidence dir (post-fix): `output/dsw/l04-out/4442ce0f4d5e4d8b87132f1b189bfdda`
  (`native.log`, `probe.json`, `evidence.json`). Probe marker:

```
P2_PLACEMENT_SLOT generator=385875968 actor=3 xyz=1 terrain=ground route=1 route_distance=71.7 water_depth=0.00
P2_PLACEMENT_PROBE actors=1 evidence_slots=1
```

## Six arena gates (natural vs injected, honest)

Lane 04 owns placement evidence, not family FSM/receivers; combat/transport
gates below are reported as owned upstream where applicable.

| Gate | Result | Label |
|---|---|---|
| 1. Exact identity and spawn | **NOT a P2-identity PASS**: only the native P1 `TEKI_Chappy` dwarf (`species=0`, no P2 bank) is spawned by the room overlay; the Snow/Orange (Yellow/BlueKochappy) visual bank was NOT staged in this probe. The native spawn + `xyz=1` IS observed | natural native P1 host spawn; P2 identity enrollment remains family/lane-13+09 |
| 2. Autonomous movement/animation | UNTESTED (not lane-04 scope) | — |
| 3. Attacks/receivers | source-backed N/A (lane 10/13) | — |
| 4. Death/corpse | source-backed N/A (lane 06/07) | — |
| 5. Transport/reward | source-backed N/A (lane 06); only `route=1` (carry-corridor origin) proven here | — |
| 6. Cleanup/re-entry | UNTESTED (lane 07) | — |

Lane-04 placement-evidence gates (this slice's actual result, all **native**):

| Evidence | Result | Native source |
|---|---|---|
| `xyz`    | PASS   | `MapMgr::getCurrTri` returns a triangle under the spawn |
| `terrain`| PASS   | `MapCode::getAttribute != ATTR_Water` → `ground` (no-triangle reads `none`, not `ground`) |
| `route`  | PASS   | nearest OPEN waypoint at XZ distance `71.7` ≤ `200.0` cap |

Admission decision (native evidence folded in):

- `pre_probe`: denied — `no accepted placement evidence` + `slot lacks accepted native placement evidence`.
- `stamped`: denied **only** on `no accepted placement evidence` (the profile
  `accepted_gates`, owned by lane 33/QA); slot-evidence reason gone.
- `injected_legal` (clearly labelled INJECTED): with `accepted_gates=['arena']`
  added by hand, both Snow and Dwarf Orange are `legal` on generator id
  385875968 — proving the interface is wired, not a natural acceptance claim.

## Fixed review items

1. `terrain` now prints `none` when there is no ground triangle (no longer
   `ground` on a null triangle).
2. Parser `terrain` gated on `xyz=='1'` (a `xyz=0` marker never yields
   `terrain=True`); a no-terrain test was added.
3. The audit report is **arena-only, no catalog join** (not a hard failure).
   Chosen because the probe ids are `Generator::_70` 4-byte file ids, a
   different id space from `p2_placement_catalog.all_slots()` crc32 uids; a
   join would be meaningless and a synthetic match would be misleading.
4. Runner takes the MinGW path from `MINGW_BIN`/`PATH` (no hardcoded
   `C:/msys64/mingw64/bin` except as a fallback); `--converted` defaults to the
   documented `output/pikmin2-room105` and is otherwise required.
5. Native history split into a module commit + a labelled
   `pc_p2_preview.cpp`/CMake hook commit.
6. `route` is distance-capped (2D `200.0f`) with `route_distance` printed; the
   header comment was softened to match.
7. Generator `_70` value `385875968` is described as a **4-byte generator file
   id**, not a "slot uid"; root commit `07a8462` is now in the commit list.
8. Gate 1 is reposted honestly as a native P1 `TEKI_Chappy` spawn, not a
   P2-identity PASS.

## Tests run and results

```
py -3.12 -m pytest tests/test_p2_placement_probe.py tests/test_p2_placement_native.py tests/test_p2_placement.py -q
72 passed, 17 subtests passed in 0.88s
```

New `tests/test_p2_placement_probe.py` (7 tests) covers the native marker
parser, including the no-terrain / legacy-`xyz=0` cases that must yield
`terrain=False`. `tests/test_p2_placement_native.py` (16) and
`tests/test_p2_placement.py` remain green.

## Assumptions made

- The room encounter spawn point (generator id `385875968`) is a **synthetic
  encounter-arena key**; it is the generator 4-byte file id, not a P1 campaign
  catalog slot, so this probe proves encounter-arena terrain/space/water/route
  evidence, not P1 campaign-stage evidence.
- `route` is a distance-capped nearest-waypoint coverage check (2D `200.0f`),
  not a full corpse path-to-Onion find (lane 06 transport scope).
- Profile `accepted_gates` are lane 33/QA-owned; lane 04 only supplies slot
  evidence.
- Unbuffered stdout + once-at-setup timing is sufficient (marker emitted at setup).

## Remaining blockers (named provider lane)

- P1 campaign-stage XYZ/terrain/return-route evidence for **generated
  placements** still needs a reserved real-GL run that loads actual P1 stages,
  held by **lane 01/33**. This probe is the encounter-arena half; the
  campaign-catalog half is unchanged.
- `Jigumo` (Hermit Crawmad) nest-anchor `PanHouse` remains `unplaceable`
  (pre-existing schema gap; lane 16).
- Snow/Dwarf Orange visual bank enrollment (lane 09/13) and natural
  combat/transport/cleanup (lanes 13/06/07) are not part of this slice.

## One exact reproduction command

```
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l04 -- py -3.12 scripts/run_p2_placement_probe.py --exe C:/Users/alari/pikmin-randomizer/output/dsw/native-l04-build/bin/nectar.exe --converted "C:/Users/alari/pikmin-randomizer/output/dsw/l04-out/converted" --output "C:/Users/alari/pikmin-randomizer/output/dsw/l04-out" && py -3.12 scripts/audit_p2_placement_evidence.py --probe "<latest-run>/probe.json"
```
(run from the root worktree `C:/Users/alari/pikmin-randomizer/output/dsw/l04-root`;
substitute the fresh run dir printed by the first command.)

## Subagent usage

- `explore` #1 (route distance-cap research): used as-is. Established a
  defensible `200.0f` XZ cap from engine reach priors (aiRescue `mRadius`,
  navi.cpp `200.0f`, P2-room waypoint spacing) and the `WayPoint::mPosition`
  accessor; the cap and printed distance follow it directly.
- `explore` #2 (locate every review-fix reference): used as-is. Confirmed the
  native branch was local-only (safe to rewrite), the exact uid/id schemes
  (`_70` 4-byte id vs crc32 catalog uids), the hardcoded paths, and
  `scripts/` being a namespace package (hence the parser moved to `randomizer/`).
- `general` #3 (marker-parser test scaffolding): used as-is. Wrote
  `tests/test_p2_placement_probe.py` (7 tests) against the agreed
  `randomizer.p2_placement_probe` contract; it fell back to a stub only before
  the real module existed and now passes against the real module. Net time
  saved was large; no result was discarded.
