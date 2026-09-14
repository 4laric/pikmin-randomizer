# Lane 04 — DeepSeek handoff: native placement-evidence probe (#440)

Lane 04 (placement/encounter compatibility). Implementing worker/session:
DeepSeek (deepseek-v4-pro); implementation owner: Codex through shared account
`4laric`. Executing this slice unattended.

## Concrete deliverable

One real consumer — the **Snow Bulborb / Dwarf Orange Bulborb host cohort**
(native `TEKI_Chappy` dwarf, roster `YellowKochappy` source_id 45 and
`BlueKochappy` source_id 44) — exercising the lane-04 placement interface
end-to-end, plus the missing ledger slice: **native terrain / space / water /
route evidence** that the placement schema requires before a `(slot, identity)`
pair is admitted.

A new native probe (`pc_p2_placement_probe`) samples the live map (ground
triangle exists = `xyz`, `MapCode` attribute = `ground`/`water`, nearest route
waypoint = `route`) at each spawned Teki actor's position and emits
`P2_PLACEMENT_SLOT` / `P2_PLACEMENT_PROBE` markers. A root layer
(`randomizer.p2_placement_native`) folds those markers into the slot `evidence`
record and the audit. The net effect is a deny → evidence-stamped decision
flip that is reproducibly wired, with the profile placement gates left to lane
33/QA.

## Source IDs and files owned

- Identity exercised end-to-end: `YellowKochappy` (Snow), `BlueKochappy`
  (Dwarf Orange) — both lane-13 candidates already present in
  `randomizer.p2_placement_catalog.CANDIDATE_SPECS`.
- Native (new, lane-owned): `pc_port/pc_p2_placement_probe.h`, `pc_port/pc_p2_placement_probe.cpp`.
- Native (narrow additive hook): `pc_port/pc_p2_preview.cpp` (one `#include` +
  one `pc_p2_placement_probe_run();` call after the legacy `P2_ROOM_GROUND`
  probe); `CMakeLists.txt` (one source line).
- Root: `randomizer/p2_placement_native.py` (new), `tests/test_p2_placement_native.py`
  (new), `scripts/run_p2_placement_probe.py` (new), `scripts/audit_p2_placement_evidence.py` (new).

## Ordered commits

- Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91` → head
  `3992d2c00316b7a6c72149f6cb5b0afc1c773da9` (branch `deepseek/p2-l04`), clean.
  - `3992d2c` lane04: native placement-evidence probe + root stamping/audit bridge and tests (#440)
- Native base `b805d9c626e4f4558c95aef7cac311a5d9a2068f` → head
  `cd9ee6b57f4d4c3e0ef57b62d8a9e66bc9df2e86` (branch `deepseek/p2-l04-native`), clean.
  - `cd9ee6b5` lane04: native placement/encounter evidence probe (terrain/water/route) (#440)

## Interfaces / hooks touched and why

- `void pc_p2_placement_probe_run()` (new lane-owned header). Read-only; no
  shared-semantics edit. It reuses existing P1 primitives rather than adding a
  subsystem: `MapMgr::getCurrTri`/`getMinY` (terrain existence + height),
  `MapCode::getAttribute` (`ATTR_Water` → water class), `RouteMgr::findNearestWayPoint('test', pos, false)`
  (carry-route coverage). Emits `P2_PLACEMENT_SLOT uid=.. actor=.. xyz=.. terrain=.. route=.. water_depth=..`.
- `pc_p2_preview.cpp`: additive hook only (import + one call). No change to any
  other shared file (`teki.h`, `tekiinteraction.cpp`, `tekibteki.cpp`,
  `tekimgr.cpp`, `gameCoreSection.cpp`, `navi.cpp`, `pc_randomizer.cpp`,
  `pc_p2_preview.h`) is needed.
- Root `randomizer/p2_placement_native.py`: `PROBE_SCHEMA='p2-placement-probe-v1'`,
  `normalize_probe`, `stamp_evidence` (upgrade-only merge into a validated
  document copy), `audit_native`, `slot_evidence_summary` (all imported by the
  audit script; additive to `randomizer.p2_placement`).

## Build evidence (from `output/dsw/l04-build-evidence.txt`)

```
2026-09-14T19:40:45 lane=l04 target=pikmin_pc native=cd9ee6b57f4d4c3e0ef57b62d8a9e66bc9df2e86 dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l04-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l04-build\bin\nectar.exe sha256=65b174456caf39917b20b6a945929055dbe9be8655001d22df6ef138d56e4bd4 ninja_n="ninja: no work to do." seconds=158
```

## Fixture adoption evidence

- Fresh arena staged into `output/dsw/l04-out/<uuid>/assets` with
  `scripts/preview_pikmin2_room.prepare` → `overlay()` → `ensure_pikmin_squad()`
  (20 red Pikmin starting squad added).
- Converted room inputs (room.mod / room.ini / treasure.mod) copied from
  `output/dsw/l20-out/converted`; the `output/pikmin2-room105` path named in
  `docs/PIKMIN2_NEXT_WAVE.md` is missing from this host, so the verified sibling
  conversion was reused read-only.
- Window/startup log (`native.log`): `[PC Port] SDL2 Window & OpenGL Context
  initialized successfully (960x540)` and `Experimental preview window set to
  960x540 windowed and centered`.
- Live gameplay, no extinction: `[Pikipelago] P2_ROOM_READY treasure=bolt
  carry=5 repairs=1` reached; process thereby entered active room gameplay.
- Runtime evidence dir: `output/dsw/l04-out/42f3153e010446da9983cbffe52efd75`
  (`native.log`, `probe.json`, `evidence.json`).

## Six arena gates (natural vs injected, honest)

Lane 04 owns placement evidence, not family FSM/receivers; combat/transport
gates below are reported as owned upstream where applicable.

| Gate | Result | Label |
|---|---|---|
| 1. Exact identity and spawn | PASS (native spawn of the Chappy dwarf host at probe uid `385875968`, `xyz=1`); full P2 Snow/Orange visual bank NOT staged in this probe | natural spawn; P2-identity enrollment remains family/lane-13+09 |
| 2. Autonomous movement/animation | UNTESTED (not lane-04 scope) | — |
| 3. Attacks/receivers | source-backed N/A (lane 10/13) | — |
| 4. Death/corpse | source-backed N/A (lane 06/07) | — |
| 5. Transport/reward | source-backed N/A (lane 06); only `route=1` (carry-corridor origin) proven here | — |
| 6. Cleanup/re-entry | UNTESTED (lane 07) | — |

Lane-04 placement-evidence gates (this slice's actual result, all **native**):

| Evidence | Result | Native source |
|---|---|---|
| `xyz`    | PASS   | `MapMgr::getCurrTri` returns a triangle at (185, -180) |
| `terrain`| PASS   | `MapCode::getAttribute == solid/grass` (not `ATTR_Water`) → `ground` |
| `route`  | PASS   | `RouteMgr::findNearestWayPoint` returns a waypoint |

Admission decision (native evidence folded in):

- `pre_probe`: denied — `no accepted placement evidence` + `slot lacks accepted native placement evidence`.
- `stamped`: denied **only** on `no accepted placement evidence` (the
  profile `accepted_gates`, owned by lane 33/QA); slot-evidence reason gone.
- `injected_legal` (clearly labelled INJECTED): with `accepted_gates=['arena']`
  added by hand, both Snow and Dwarf Orange are `legal` on slot 385875968 —
  proving the interface is wired, not a natural acceptance claim.

## Tests run and results

```
py -3.12 -m pytest tests/test_p2_placement_native.py tests/test_p2_placement.py -q
65 passed, 17 subtests passed in 0.26s
```

New `tests/test_p2_placement_native.py`: 16 tests (probe normalization,
upgrade-only stamping, evidence-gated deny→legal, `audit_native`). Existing
`tests/test_p2_placement.py` remains green.

## Assumptions made

- The P2-room encounter arena spawn point (generator id `385875968`) is a
  **synthetic encounter-arena slot**, not one of the 72 P1 campaign catalog
  slots, so this probe proves encounter-arena terrain/space/water/route
  evidence, not P1 campaign-stage evidence.
- `route` is the minimal honest corridor-origin check (nearest navmesh waypoint
  exists); full corpse path to the Onion/ship is lane 06 transport scope.
- Profile `accepted_gates` are lane 33/QA-owned; lane 04 only supplies slot
  evidence.
- Conventional room-preview probe timing (runs once at `pc_p2_preview_setup`,
  unbuffered stdout) is sufficient because the marker is emitted at setup.

## Remaining blockers (named provider lane)

- P1 campaign-stage XYZ/terrain/return-route evidence for **generated
  placements** still needs a reserved real-GL run that loads actual P1 stages
  (the campaign path), held by **lane 01/33**. This probe is the encounter-arena
  half; the campaign-catalog half is unchanged.
- `Jigumo` (Hermit Crawmad) nest-anchor `PanHouse` remains `unplaceable`
  (pre-existing schema gap; lane 16).
- Snow/Dwarf Orange visual bank enrollment in the room probe (lane 09/13) and
  natural combat/transport/cleanup (lanes 13/06/07) are not part of this slice.

## One exact reproduction command

```
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l04 -- py -3.12 scripts/run_p2_placement_probe.py --exe C:/Users/alari/pikmin-randomizer/output/dsw/native-l04-build/bin/nectar.exe --output "C:/Users/alari/pikmin-randomizer/output/dsw/l04-out" && py -3.12 scripts/audit_p2_placement_evidence.py --probe "C:/Users/alari/pikmin-randomizer/output/dsw/l04-out/42f3153e010446da9983cbffe52efd75/probe.json"
```
(run the second command from the root worktree `C:/Users/alari/pikmin-randomizer/output/dsw/l04-root`)

## Subagent usage

- `explore` #1 (native terrain/route/XYZ primitive source audit): used as-is.
  Supplied exact signatures for `getCurrTri`/`getMinY`/`MapCode::getAttribute`/
  `findNearestWayPoint` and the Snow/Dwarf Orange bind entry points; saved
  significant header-hunting time (no compile-time blind poking).
- `explore` #2 (lane-04 placement inventory): used as-is. Confirmed no native
  `pc_p2_placement*` existed, mapped marker naming conventions and the
  campaign/spawn catalog uid scheme; prevented reinventing the schema/markers.
- `general` #3 (root stamping layer + tests): used as-is. Produced
  `randomizer/p2_placement_native.py` + 16 passing tests with the exact
  `evaluate`/`audit` API I then consumed unchanged in the audit script. Net
  time saved is large (the read-heavy audit/inventory work was fully offloaded);
  no result was discarded.
