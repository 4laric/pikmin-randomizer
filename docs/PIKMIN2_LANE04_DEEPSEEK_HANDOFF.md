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

## Slice 2

Bounded slice: **catalog join and a P2-identity placement.** Supersedes the
lane-04 "arena-only, no catalog join" state from the fix round.

### (a) Catalog join — mechanism

- Native (`pc_port/pc_p2_placement_probe.cpp`): the probe now reads a staged
  sidecar `p2-placement-slots.txt` (header `P2_PLACEMENT_SLOTS_1`, then one
  `<generator_id> <catalog_slot_uid>` pair per line) and emits BOTH ids in the
  marker: `P2_PLACEMENT_SLOT generator=<_70> slot=<catalog_uid|0> actor=...
  xyz=... terrain=... route=... route_distance=... water_depth=...`.
- Root parser (`randomizer/p2_placement_probe.py`): `capture_markers` returns
  per-slot `generator` + `slot` (None when `slot=0`); `build_probe` returns
  `{schema, catalog_join, mapping, slots}`. `terrain` stays gated on
  `xyz==True` + class in ground/water.
- Audit (`scripts/audit_p2_placement_evidence.py::run_audit`): when
  `catalog_join` is true, every mapped `slot` is looked up in
  `p2_placement_catalog.all_slots()`; an **unmatched uid is a hard failure**
  (`SystemExit`). Matched slots are stamped onto the real catalog document and
  audited. The old synthetic `arena_document` path is now only the
  `catalog_join=false` fallback (no sidecar).

### (b) P2-identity placement

> **CORRECTED BY fix2** — the slot below (`648204418`, Stage 3 / Distant Spring)
> was a stage-mismatch bug: Impact Site arena evidence was stamped onto a
> Distant Spring catalog slot. See the fix2 section; the accepted slot is now
> the stage-0 `impact_7_1764` (`513430982`).

Staged a Dwarf Orange (BlueKochappy source 44) two-actor original Impact Site
arena via lane-13's stager (`experimental.pikmin2_dwarf_orange_runtime.prepare`,
bank `output/p2-dwarf-orange-bank`, profile `output/p2-dwarf-orange-ref`,
generators `211001` source + `211002` control) and wrote a sidecar mapping. The
original choice (first `dwarf`-cohort campaign slot) was WRONG — it selected a
Stage 3 slot while the arena is on the Stage 0 practice/Impact Site map. Running
the private build under the GL slot produced a genuine P2-identity spawn **with**
native terrain/route evidence; the evidence join was then corrected to a
stage-matching slot (see fix2).

### Gate 1 (updated)

Now a **P2-identity spawn**: native `P2_ENEMY_READY species=BlueKochappy
source_id=44` with health 250 and the converted dwarf-orange bank, on the
original Impact Site map, with native `xyz/terrain/route` evidence at
`route_distance 61.2` (within the 200u cap). This replaces the slice-1 P1
`TEKI_Chappy` proxy. Identity is still `behavior=P1` (host AI), matching lane
13's documented candidate scope.

### Commits (this slice)

- Native `b805d9c6` ... `4601bdd84b5b039d88145b8f2a8f391a42295f10`:
  - `4601bdd8` lane04: sidecar slot-id join in placement probe (#440)
- Root `d6987073eaa3d7c39cb3bebf3f0d35296f6b9192`:
  - `d698707` lane04: catalog join (sidecar slot uid) + P2-identity arena probe (#440)

### Build evidence (from `output/dsw/l04-build-evidence.txt`)

```
2026-09-14T20:40:38 lane=l04 target=pikmin_pc native=4601bdd84b5b039d88145b8f2a8f391a42295f10 dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l04-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l04-build\bin\nectar.exe sha256=ce78e953f24d09d9a6303a609a5d45d266801bbcb2786e651c69ed6344e5c046 ninja_n="ninja: no work to do." seconds=0
```

### Runtime evidence

Run dir `output/dsw/l04-out/8a02d908ee644fa8b13ba53b95e60f9b` (native.log,
probe.json, evidence.json, report.json).

### Tests

- `tests/test_p2_placement_probe.py` rewritten: the in-test `sys.modules` stub
  fallback (previously lines 8-101) is removed and the production marker
  (`generator=` + `slot=`) is covered. 8 test functions pass.
- Full placement suite: `py -3.12 -m pytest tests/test_p2_placement_probe.py
  tests/test_p2_placement_native.py tests/test_p2_placement.py -q` → `73 passed,
  17 subtests passed`.
- Manual audit checks: unmatched mapped uid `999999999` hard-fails; no-sidecar
  probe reports `catalog_join=false`.

## One exact reproduction command (slice 2)

```
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l04 -- py -3.12 scripts/run_p2_catalog_placement.py --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" --bank "C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-bank" --profile "C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-ref" --exe "C:/Users/alari/pikmin-randomizer/output/dsw/native-l04-build/bin/nectar.exe" --output "C:/Users/alari/pikmin-randomizer/output/dsw/l04-out"
```
(run from the root worktree `C:/Users/alari/pikmin-randomizer/output/dsw/l04-root`.)

## Subagent usage (slice 2)

- `explore` #1 (catalog uid scheme + slot selection): used as-is. Traced the
  crc32 uid derivation, confirmed BlueKochappy/YellowKochappy are
  `cohort=None`/`terrains=['ground']`, and recommended the `dwarf`-cohort slot
  uid `648204418` plus the deterministic selection rule; the sidecar uses it.
- `explore` #2 (sidecar/arena run inventory): used as-is. Confirmed no
  `p2-placement-slots` name collision, located the bank/profile dirs
  (`output/p2-dwarf-orange-bank`, `output/p2-dwarf-orange-ref`), confirmed the
  native `pc_p2_dwarf_orange` emits `source_id=44`, and that `arena-private.txt`
  is an inert label.
- `general` #3 (rewrite the parser test file): used as-is. Removed the stub
  fallback and produced the 8 production-marker tests (which temporarily
  reported 7 failures against the old module contract before I rewrote
  `p2_placement_probe.py` to match; they now pass). Honest negative mid-state,
  final result retained unchanged.

## Slice 2 review fixes (fix2)

Fixes the six review items on the slice-2 join. All blocking.

1. **Stage-matched slot / stage guard.** `choose_slot` (renamed from
   `choose_slot_uid`) now selects a campaign slot whose `stage` matches the
   staged map (`practice` = Impact Site = stage 0) and is constrained to the
   `ground` cohort (BlueKochappy's host cohort). Deterministic pick by
   `(first_day, uid)` → **`impact_7_1764` uid `513430982`** (stage 0). The
   prior `648204418` (stage 3, Distant Spring) is corrected. `run_audit` now
   hard-fails when a mapped slot's catalog `stage` differs from `arena_stage`,
   and the sampled actor `position` is recorded beside each mapping entry.
2. **`run_audit` tests.** New `tests/test_p2_placement_audit.py` (5 tests)
   covers unmatched-uid `SystemExit`, matched stamping, stage-mismatch refusal,
   arena-only fallback, and the unmapped guard.
3. **Unmapped-generator guard.** `build_probe` reports `unmapped_generators`
   explicitly; `run_audit` fails unless `--allow-unmapped`/`allow_unmapped`.
   The arena runner passes `allow_unmapped=True` (the `211002` P1 Chappy
   control is intentionally unmapped) and reports it.
4. **Runner CLI.** `--assets/--bank/--profile` are now required (no user-
   absolute module constants); the docstring no longer embeds lane/build paths.
5. **Parser tolerance.** `capture_markers` is token-based: `slot`,
   `route_distance`, and `x/y/z` are optional; `generator`/`uid` both accepted;
   required keys are `generator|uid`, `xyz`, `terrain`, `route`, `water_depth`.
   Slice-1 logs (no `slot`) now parse instead of silently yielding zero slots.
6. **No uid overload.** `build_probe` emits `mapping` (`{generator, slot,
   xyz, terrain, route, position}`) and a stamp-only `slots` keyed by the
   catalog `slot` uid; unmasked generators are NOT overloaded onto `uid`.
7. **Positional marker + rerun.** The native probe now emits
   `x=.. y=.. z=..`; the run was redone on committed native head.

Fresh corrected run (committed head `b446f0b1`, exe sha256
`8b6d9967…73f4`), run dir `output/dsw/l04-out/a1c71372ec9f4b6bacee4725b46dee0b`:

```
P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001 x=-150.0000000 y=30.0000000 z=1850.0000000 health=250.0 max_health=250.0 behavior=P1 purple_stun=bluekochappy_5s
P2_PLACEMENT_SLOT generator=211001 slot=513430982 actor=3 xyz=1 terrain=ground route=1 route_distance=61.2 x=-150.000 y=30.000 z=1850.000 water_depth=0.00
P2_PLACEMENT_SLOT generator=211002 slot=0 actor=3 xyz=1 terrain=ground route=1 route_distance=129.3 x=150.000 y=30.000 z=1550.000 water_depth=0.00
P2_PLACEMENT_PROBE actors=2 evidence_slots=2
[PC Port] Experimental preview window set to 960x540 windowed and centered
```

report.json: `catalog_join=true`, `arena_stage=0`, `matched_slot_uids=[513430982]`,
`unmapped_generators=[211002]`, `mapping` records `position [-150.0,30.0,1850.0]`
beside the slot, and `injected_legal_admitted = {BlueKochappy:[513430982],
YellowKochappy:[513430982]}`.

Build evidence (clean):

```
2026-09-14T21:09:27 lane=l04 target=pikmin_pc native=b446f0b1147a5052c67d6aff4df83965c96ff405 dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l04-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l04-build\bin\nectar.exe sha256=8b6d9967c95d5b7af98e43d0f8a5e00fb3959bdaf273e2162022f36c01a373f4 ninja_n="ninja: no work to do." seconds=0
```

Tests: `py -3.12 -m pytest tests/test_p2_placement_probe.py
tests/test_p2_placement_audit.py tests/test_p2_placement_native.py
tests/test_p2_placement.py -q` → `79 passed, 17 subtests passed`.

Commits (this fix round):

- Native: `b446f0b1147a5052c67d6aff4df83965c96ff405`
  `lane04: review fixes 2 - emit sampled position in placement probe marker (#440)`
- Root: `4b9a4c5` `lane04: review fixes 2 - stage-matched join, unmapped guard, positional marker, audit tests (#440)`

Subagent-usage note: slice-2 explore #1's "min-uid dwarf slot" rule was the
cause of the stage bug (a delegated selection rule adopted without cross-checking
the slot's stage against the arena). fix2 re-derived the rule from
`campaign_data`/`levels.py` (practice==stage 0) and guards it in `run_audit`, so
a delegated choice can no longer pass through a stage mismatch unnoticed.

## Slice 3

Bounded slice: **the placement catalog driving a real generated seed.** Slice 2
hand-built the `p2-placement-slots.txt` sidecar from a lane-04 `choose_slot`; this
slice flips that dependency so the catalog slot uid comes from the seed's
`p2_layout` (lane 03's `resolve_placement_layout` over lane 02's admitted cohort
+ lane 04's catalog), and the native probe's `P2_PLACEMENT_SLOT slot=...` marker
joins to the slot the *seed actually chose*. Also folds in the three non-blocking
review items from slice-2 fix2.

### Proofs (all three met, native evidence)

| # | Claim | Result |
|---|---|---|
| 1 | slot in log == slot in seed's placement document | PASS — `seed_slot_uid` for `seed-slice3-a` is `5465461`, `seed-slice3-b` is `1866045954`; the native log's `P2_PLACEMENT_SLOT generator=211001 slot=<uid>` equals exactly those values. |
| 2 | stage guard passes without manual `--stage` | PASS — `run_audit` reads `arena_stage` from the probe document (runner embeds `probe['arena_stage'] = 0`); `stage_guard_passed` true for both seeds, and a wrong recorded stage still hard-fails (guarded, not skipped). |
| 3 | two consecutive seeds give different markers | PASS — `seed-slice3-a`→`5465461` vs `seed-slice3-b`→`1866045954` (2 distinct slots). |

### Fold-ins (slice-2 fix2 non-blocking items)

1. **`audit_p2_placement_evidence.py` stage guard** — `run_audit` falls back to
   `probe['arena_stage']` when `arena_stage` is not passed; the standalone CLI
   reads the stage from the probe (or `--stage`), and a catalog-join probe with
   no stage anywhere is now rejected instead of silently skipping the guard.
   `run_p2_catalog_placement.py` embeds `probe['arena_stage']`.
2. **`choose_slot` unit test** — `tests/test_p2_seed_placement.py` now covers
   `choose_slot` picking a stage-0 ground-cohort ground slot, and failing on an
   empty catalog.
3. **Malformed-marker count** — `build_probe` now emits `malformed_markers`
   (count of `P2_PLACEMENT_SLOT`-prefixed lines that failed to parse) instead of
   dropping them silently. `capture_markers`' 3-tuple is unchanged.

### Files owned (root; no native change this slice)

- New: `experimental/pikmin2_seed_placement.py` (real-catalog placement document
  with the cohort acceptance labelled injected; admitted-seed `generate` via the
  same `bridge.admitted_ids` patch lane 03's own seed-generation test uses;
  `seed_slot_uid`; `write_sidecar`).
- New: `scripts/run_p2_seed_placement.py` (stage the Dwarf Orange arena, write the
  seed-derived sidecar, run the native probe, audit, report the three proofs).
- New: `tests/test_p2_seed_placement.py` (7 pure-Python tests, no native root).
- Modified: `randomizer/p2_placement_probe.py`, `scripts/audit_p2_placement_evidence.py`,
  `scripts/run_p2_catalog_placement.py` (the three fold-ins above).
- Native: **unchanged** (the probe-sidecar mechanism landed in slice 2 commit
  `4601bdd8`; no C++ work was needed for a seed-derived slot uid).

### Runtime evidence

Run dir `output/dsw/l04-out/1016e64403ce47e58bf7ae3f7d5c90a5` (plus
`seed-seed-slice3-a.log` / `seed-seed-slice3-b.log` beside it). Native markers:

```
[PC Port] Experimental preview window set to 960x540 windowed and centered (override with PIKMIN_P2_ROOM_WINDOW=WxH or =off).
P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001 x=-150.0000000 y=30.0000000 z=1850.0000000 health=250.0 max_health=250.0 behavior=P1 purple_stun=bluekochappy_5s
P2_PLACEMENT_SLOT generator=211001 slot=5465461   actor=3 xyz=1 terrain=ground route=1 route_distance=61.2 x=-150.000 y=30.000 z=1850.000 water_depth=0.00   # seed-slice3-a
P2_PLACEMENT_SLOT generator=211001 slot=1866045954 actor=3 xyz=1 terrain=ground route=1 route_distance=61.2 x=-150.000 y=30.000 z=1850.000 water_depth=0.00   # seed-slice3-b
P2_PLACEMENT_SLOT generator=211002 slot=0         actor=3 xyz=1 terrain=ground route=1 route_distance=129.3 x=150.000 y=30.000 z=1550.000 water_depth=0.00   # P1 Chappy control, intentionally unmapped
P2_PLACEMENT_PROBE actors=2 evidence_slots=2
```

`seed-placement-report.json` reports `distinct_slots=2`,
`all_markers_match_seed=true`, `all_stage_guards_passed=true`,
`unmapped_generators=[211002]` (the control) with `allow_unmapped` handling.

### Six arena gates (natural vs injected, unchanged from slice 1/2 framing)

Lane 04 owns placement evidence; the P2 identity spawn is now a natural PASS on
the pinned pair.

| Gate | Result | Label |
|---|---|---|
| 1. Exact identity and spawn | **PASS** | natural `P2_ENEMY_READY species=BlueKochappy source_id=44` + `xyz=1 terrain=ground route=1` on the original Impact Site map |
| 2. Autonomous movement/animation | UNTESTED (lane 13) | — |
| 3. Attacks/receivers | source-backed N/A (lane 10/13) | — |
| 4. Death/corpse | source-backed N/A (lane 06/07) | — |
| 5. Transport/reward | source-backed N/A (lane 06); only `route=1` proven | — |
| 6. Cleanup/re-entry | UNTESTED (lane 07) | — |

Placement evidence: `xyz`/`terrain`/`route` all PASS natively (sourced as in
slice 1); admission is still INJECTED at the profile/ledger boundary (below).

### Assumptions made

- The Snow/Dwarf Orange cohort's acceptance and the admitted ledger are injected
  (the catalog and committed lane-02 ledger are deny-by-default). The placement
  document is the real `build_document()` filtered to stage-0 ground slots with
  `evidence` stamped and `accepted_gates=['arena']`, and the admitted cohort is
  injected by patching `bridge.admitted_ids` exactly as
  `tests/test_pikmin2_seed_generation.py` does. This is labelled, not a natural
  acceptance claim.
- The arena generator id `211001` remains lane-13's synthetic two-actor arena key
  (not a campaign generator `_70`), so the sidecar still supplies the
  generator→slot map for the probe. The full native `ENEMY_P2`/`P2_SEED_RESOLVE`
  bind (lane 03 slice 2) is out of lane-04 scope and not exercised by this probe.
- `exit=timeout` is the normal capture path (markers flush at setup; the runner
  retires the window).

### Remaining blockers (named provider lane)

- **lane 03**: `randomizer.seed.generate` has no roster-injection parameter, so a
  "seed on a synthetic ledger" can only be produced by patching
  `bridge.admitted_ids` (as lane 03's own test does). A first-class
  `roster=`/`admitted=` parameter on `generate` would remove the patch.
- **lane 03/05**: the seed's actual generator id (`Generator::_70`) for a bound
  catalog slot is not surfaced at the root level; the sidecar still maps the
  synthetic arena generator to the slot uid. Surfacing `uid`→`_70` from the
  native seed bridge would let the sidecar be derived end-to-end with no synthetic
  arena key.

### Tests

```
py -3.12 -m pytest tests/test_p2_placement_probe.py tests/test_p2_placement_audit.py tests/test_p2_placement_native.py tests/test_p2_placement.py tests/test_p2_seed_placement.py tests/test_pikmin2_seed_generation.py tests/test_pikmin2_seed_bridge.py -q
116 passed, 17 subtests passed in 0.69s
```

No native root is required for the new tests (pure Python).

### Commits (this slice)

- Native: **none** (no C++ change; branch `deepseek/p2-l04-native` stays at
  `b446f0b1`, clean).
- Root: `deepseek/p2-l04` — `lane04: slice 3 handoff — placement catalog drives a generated seed (#440)`
  (see `git log` for the exact sha; the work + tests + runtime runner are in one
  root commit plus the handoff).

### One exact reproduction command

```
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l04 -- \
  py -3.12 scripts/run_p2_seed_placement.py \
    --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" \
    --bank "C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-bank" \
    --profile "C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-ref" \
    --exe "C:/Users/alari/pikmin-randomizer/output/dsw/native-l04-build/bin/nectar.exe" \
    --output "C:/Users/alari/pikmin-randomizer/output/dsw/l04-out" \
    --seed seed-slice3-a --seed seed-slice3-b
```
(run from `C:/Users/alari/pikmin-randomizer/output/dsw/l04-root`.)

### Subagent usage (slice 3)

No `task` tool was available in this session, so I could not spawn the three
`explore`/`explore`/`general` subagents the brief asked for and did the read-heavy
and test work inline. Net result: negative — no time saved, but the source audit,
existing-candidate inventory and test scaffolding are all captured directly in
this handoff and the three proof/test files above rather than in a delegated
report.

### Integrator note (review of slice 3)

- resolve_placement_layout binds every stage-0 ground target to source 44/45 (seed-a: 6 of 11 to 44); `seed_slot_uid` takes the first binding in (len, str) order, so the sidecar value is a lane-04 pick and the marker equals it by construction. "The slot the seed actually chose" is overstated: the seed chose a set, the sidecar took one of them. `seed_slot_uids` returns the last binding per source and is unused.
- `run_audit` still skips the stage guard when neither argument nor probe arena_stage is present; only the CLI rejects. The claim "a catalog-join probe with no stage anywhere is rejected" holds for the CLI only.

## Slice 4

Bounded slice: **every binding, not one.** The seed bridge binds a *set* of
stage-0 ground slots to each admitted source (44/45), so the sidecar and the
probe report must carry the whole set and the audit must validate set equality,
not membership of a single sidecar-inserted pick. This closes the reviewer's
three slice-3 findings and adds the native co-occurrence contract.

### (1) Every binding, not one — DONE (root)

- `seed_slot_uid` is removed; `seed_slots(manifest, source_id)` returns the full
  sorted binding set, and `seed_slot_uids(manifest)` returns
  `{source_id: sorted [uids]}` (the old dict-comprehension kept only the last
  binding per source and was unused).
- `write_sidecar(directory, generator_slots)` now records every
  `(generator_id, slot_uid)` pair (one line per generator), matching the probe's
  one-marker-per-resolved-generator behaviour.
- `tests/test_p2_seed_placement.py::test_marker_slot_set_equals_binding_set`
  proves the parse-back marker-slot set equals the seed's binding set (not
  membership of one); `test_seed_slot_uids_returns_full_set_per_source` proves the
  two sources jointly cover the whole stage-0 ground set.

### (2) Catalog-join stage rejection lives in `run_audit` — DONE

- `run_audit` now hard-fails (`SystemExit`) when a catalog-join probe has no
  stage anywhere (neither argument nor `arena_stage` field), after the
  unmatched-uid check so a missing uid still reports its own error first. the
  standalone CLI no longer needs its own rejection. Two tests:
  `test_run_audit_rejects_catalog_join_without_any_stage` and
  `test_run_audit_rejects_wrong_recorded_stage` (plus the passing
  `test_run_audit_stage_guard_from_probe_passes`).
- `scripts/run_p2_seed_placement.py` docstring lane references were removed.

### (3) Native co-occurrence contract — validator + flip tests DONE; live run blocked

New `experimental/pikmin2_seed_placement_native.py::validate_cooccurrence` and
`tests/test_p2_seed_placement_native.py` close the three-marker loop a room run
should emit once the native bridge + spawn catalog + family adapter keying agree:

- `P2_PLACEMENT_SLOT generator=<g> slot=<u>` (lane 04) ↔
- `P2_SEED_RESOLVE source_id=<s> target=<u>` (seed bridge) ↔
- `P2_ENEMY_READY source_id=<s> generator=<g>` (identity birth)

The validator requires a closed `generator -> slot -> source` and
`generator -> birth source` triple for a cohort source (44/45); six flip tests
prove each marker (and a non-cohort source) flips the result. Two
`PIKMIN_NATIVE_ROOT`-guarded source-pin tests confirm the emission sites
(`P2_PLACEMENT_SLOT` in `pc_p2_placement_probe.cpp`, `P2_SEED_RESOLVE` in
`genteki.cpp`). Against the wave native the whole file is green (9 passed);
against the lane-04 native worktree only the `genteki.cpp` pin fails, confirming
the seed-bridge hook is present on the wave but not yet in the lane-04 native
base.

The **live room run** of the three markers together is **NOT achieved** this
slice: it needs the seed bridge (lane 03) merged into the lane-04 native build,
the room generator to resolve a spawn-catalogue uid, and the family adapter
(lane 13/05) to key the live birth on the spawn-slot uid instead of `_70` — the
same blockers the lane 03 slice-2 handoff names. See "Remaining blockers".

### Files owned (root only; no native change this slice)

- New: `experimental/pikmin2_seed_placement_native.py`, `tests/test_p2_seed_placement_native.py`.
- Modified: `experimental/pikmin2_seed_placement.py`, `scripts/audit_p2_placement_evidence.py`,
  `scripts/run_p2_seed_placement.py`, `tests/test_p2_seed_placement.py`,
  `tests/test_p2_placement_audit.py` (adds `arena_stage=0` to the `allow_unmapped`
  call).
- Native: **unchanged** (the probe + sidecar mechanism already landed; nothing was
  needed for the root-side full-set/stage-guard/validator work).

### Assumptions

- The full-set equality is proven at the root boundary (sidecar + parser) with
  synthetic generator ids; the two-generator Dwarf Orange arena can only observe
  a subset of a seed's binding set, so the runtime runner asserts membership-in-set
  and reports the full set rather than claiming an N-generator set equality.
- The Snow/Dwarf Orange acceptance and the admitted cohort remain injected
  (deny-by-default ledger/catalog), labelled as such.

### Remaining blockers (provider lane)

- **Live part-(3) room run**: needs the seed-bridge spawn resolution to reach a
  real bound actor in the room. That is lane 13/05 work (switch the family
  adapter's actor selection from `mGenerator->_70` to the spawn-slot uid the seed
  bridge keys on) plus the room-course generator entry in the native spawn
  catalogue (lane 03 named this the lane-04 ask in their slice-2 handoff). The
  co-occurrence validator, flip tests and wave source-pins are committed and
  green so the run can be claimed immediately once the native side lines up.

### Tests

```
py -3.12 -m pytest tests/test_p2_seed_placement.py tests/test_p2_seed_placement_native.py tests/test_p2_placement_probe.py tests/test_p2_placement_audit.py tests/test_p2_placement_native.py tests/test_p2_placement.py tests/test_pikmin2_seed_generation.py tests/test_pikmin2_seed_bridge.py -q
128 passed, 2 skipped, 17 subtests passed
```

`2 skipped` are the `PIKMIN_NATIVE_ROOT`-guarded native source-pins; with
`PIKMIN_NATIVE_ROOT=<native-wave>` the whole `test_p2_seed_placement_native.py`
file is `9 passed`.

### Commits (this slice)

- Native: **none** (no C++ change; branch `deepseek/p2-l04-native` stays at `b446f0b1`).
- Root: `55ea972` `lane04: slice 4 - full binding set, audit stage guard, co-occurrence validator (#440)`
  (+ this handoff commit).

### One exact reproduction command

```
py -3.12 -m pytest tests/test_p2_seed_placement.py tests/test_p2_seed_placement_native.py -q
PIKMIN_NATIVE_ROOT=C:/Users/alari/pikmin-randomizer/output/dsw/native-wave py -3.12 -m pytest tests/test_p2_seed_placement_native.py -q
```
(run from `C:/Users/alari/pikmin-randomizer/output/dsw/l04-root`.)

## Subagent usage (slice 4)

No `task` tool is present, so this slice was done solo, as the slice-3 handoff
already noted.

## Slice 5

Bounded slice: **the live three-marker run.** Slice 4 committed the
co-occurrence validator but the live room run was blocked; this slice lands it on
the merged wave native (lane 03's `p2-placement-slots.txt` join under
`pc_randomizer_p2_bridge`, native `0f8decd4`).

### What changed

- **Native**: `deepseek/p2-l04-native` was fast-forwarded onto
  `claude/p2-deepseek-wave-native` (now at `b948ce002267…`), bringing lane 03's
  `pc_randomizer_bind_generator` ← `p2-placement-slots.txt` join and
  `P2_SEED_RESOLVE` at `GenObjectTeki::birth`. No new native commit (FF-merge);
  the lane-04 probe/sidecar commits were already ancestors of the wave.
- **Root** (`experimental/pikmin2_seed_placement.py`): added
  `ARENA_GENERATORS = (211001, 211002)`; docstring lane references removed.
- **Root** (`scripts/run_p2_seed_placement.py`): rewritten — marks BOTH arena
  generators in `p2-dwarf-orange-actors.txt`, writes `zip(ARENA_GENERATORS,
  seed_slots)` sidecar pairs, writes the `ENEMY_P2` bootstrap and runs with
  `--randomizer-seed`, then runs `validate_cooccurrence` on the real log and
  records it. Docstring has no lane names.
- **Root** (`experimental/pikmin2_seed_placement_native.py` +
  `tests/test_p2_seed_placement_native.py`): docstring lane references removed;
  added `test_validator_passes_on_two_generator_chain` (both generators close).

### Live run (one log, both generators, all three markers)

Run dir `output/dsw/l04-out/f25dc172c63e4a22bc4c507dd277ac81`:

```
P2_PLACEMENT_SLOT generator=211001 slot=1911597745 actor=3 xyz=1 terrain=ground route=1 route_distance=61.2 x=-150.000 y=30.000 z=1850.000 water_depth=0.00
P2_PLACEMENT_SLOT generator=211002 slot=4063112254 actor=3 xyz=1 terrain=ground route=1 route_distance=129.3 x=150.000 y=30.000 z=1550.000 water_depth=0.00
P2_SEED_RESOLVE source_id=44 target=1911597745 original_type=3 x=-150.0 z=1850.0
P2_SEED_RESOLVE source_id=44 target=4063112254 original_type=3 x=150.0 z=1550.0
P2_ENEMY_READY species=BlueKochappy source_id=44 ... generator=211001 x=-150.0000000 ...
P2_ENEMY_READY species=BlueKochappy source_id=44 ... generator=211002 x=150.0000000 ...
```

`validate_cooccurrence` on that log → `ok=true`, `generator=211001`,
`slot=1911597745`, `source=44` (closed `generator → slot → source` + birth chain).
`markers_are_binding_members=true` (marker slots `{1911597745, 4063112254}` ⊆
the seed's binding set `{1911597745, 4063112254, 4224027716}`).

### Build evidence (clean)

```
2026-09-14T22:29:12 lane=l04 target=pikmin_pc native=b948ce002267b850157afb8d20feebfa74d1a3e0 dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l04-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l04-build\bin\nectar.exe sha256=e5ca8189c85004ff3e91d480b46e67a550c8a760435bc47b29d9e99b4a388f13 ninja_n="ninja: no work to do." seconds=95
```

### Tests (PIKMIN_NATIVE_ROOT only)

```
PIKMIN_NATIVE_ROOT=C:/Users/alari/pikmin-randomizer/output/dsw/native-l04 py -3.12 -m pytest tests/test_p2_seed_placement_native.py -q
10 passed
```

Full placement suite (no native root): `87 passed, 2 skipped, 17 subtests`
(the 2 skips are the `PIKMIN_NATIVE_ROOT`-guarded source pins).

### Assumptions

- Both arena generators resolve and birth as source 44 (BlueKochappy) — the
  second generator is marked in the dwarf-orange actor list so the full binding
  set (not a single picked slot) closes the three-marker chain in one run. Source
  45 (Snow) is not staged because the Snow bank/install path is separate and out
  of scope for this bound slice.
- The Snow/Dwarf Orange acceptance and the admitted cohort remain injected
  (deny-by-default ledger/catalog), labelled as such.

### Commits (this slice)

- Native: **FF-merge only** — `deepseek/p2-l04-native` now at
  `b948ce002267b850157afb8d20feebfa74d1a3e0` (== `claude/p2-deepseek-wave-native`
  tip); no new lane-04 native commit.
- Root: `b57286061c82e19729a19052e3b990df0e25e2cd`
  `lane04: slice 5 - both arena generators resolve and birth in one three-marker run (#440)`.

### One exact reproduction command

```
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l04 -- \
  py -3.12 scripts/run_p2_seed_placement.py \
    --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" \
    --bank "C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-bank" \
    --profile "C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-ref" \
    --exe "C:/Users/alari/pikmin-randomizer/output/dsw/native-l04-build/bin/nectar.exe" \
    --output "C:/Users/alari/pikmin-randomizer/output/dsw/l04-out" \
    --seed p2-seed-placement-live
```
(run from `C:/Users/alari/pikmin-randomizer/output/dsw/l04-root`.)

## Subagent usage (slice 5)

The slice-5 brief did not mandate subagents ("work solo if the task tool is
absent"). I did this slice solo: the one bounded task was the two-generator
sidecar write, the bootstrap run, and recording `validate_cooccurrence` on the
real log, which I completed directly.

## Slice 6

Bounded slice: **source 45 and the report row lane 02 can ingest.**

### (1) Source 45 (Snow) births and the chain closes for both sources

- Native: the Snow bind now emits the source id
  (`pc_p2_enemy.cpp`: `P2_ENEMY_READY species=YellowKochappy source_id=45
  native_family=Chappy generator=%u ...`).
- Root: new `scripts/run_p2_cohort_seed_placement.py` stages the three-actor
  mixed arena via `experimental.pikmin2_mixed_bulborb_runtime.prepare` (Dwarf
  Orange 211001 = source 44, Snow 5001 = source 45, plus the P1 Chappy control
  211002), writes the sidecar mapping `211001 -> slot(44)` and
  `5001 -> slot(45)`, writes the `ENEMY_P2` bootstrap, runs with
  `--randomizer-seed`, and runs `validate_cooccurrence` on the real log.

Live run `output/dsw/l04-out/d144931bf1194474ac204fcdd0e75cdd` (one log, both
sources close; the run ends by timeout as expected):

```
P2_SEED_RESOLVE source_id=44 target=513430982 original_type=3 x=-150.0 z=1850.0
P2_SEED_RESOLVE source_id=45 target=5465461 original_type=3 x=-150.0 z=1700.0
P2_ENEMY_READY species=YellowKochappy source_id=45 native_family=Chappy generator=5001 behavior=P1
P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001 ...
P2_PLACEMENT_SLOT generator=211001 slot=513430982 actor=3 xyz=1 terrain=ground route=1 route_distance=61.2 x=-150.000 y=30.000 z=1850.000 water_depth=0.00
P2_PLACEMENT_SLOT generator=5001 slot=5465461 actor=3 xyz=1 terrain=ground route=1 route_distance=80.9 x=-150.000 y=30.000 z=1700.000 water_depth=0.00
```

`validate_cooccurrence` → `ok=true`, `closed generator->slot->source and birth
chain for 2 generator(s): [(5001, 5465461, 45), (211001, 513430982, 44)]`.

### (2) Gate tables (lane 02 ingest format)

### 44 BlueKochappy

| Gate | Result | Evidence |
|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/dsw/l04-out/d144931bf1194474ac204fcdd0e75cdd/native.log:975 |
| 2. Autonomous movement and animation | UNTESTED | lane 13 family render/FSM |
| 3. Attacks and receivers | UNTESTED | receiver lanes |
| 4. Death and corpse | UNTESTED | lifecycle lane |
| 5. Actual transport and reward | UNTESTED | reward lane |
| 6. Cleanup and re-entry | UNTESTED | lifecycle lane |

### 45 YellowKochappy

| Gate | Result | Evidence |
|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/dsw/l04-out/d144931bf1194474ac204fcdd0e75cdd/native.log:846 |
| 2. Autonomous movement and animation | UNTESTED | lane 13 family render/FSM |
| 3. Attacks and receivers | UNTESTED | receiver lanes |
| 4. Death and corpse | UNTESTED | lifecycle lane |
| 5. Actual transport and reward | UNTESTED | reward lane |
| 6. Cleanup and re-entry | UNTESTED | lifecycle lane |

### (2b) Ingest checker output

`py -3.12 scripts/ingest_p2_handoff_gates.py docs/PIKMIN2_LANE04_DEEPSEEK_HANDOFF.md`
(ran on the wave, which has lane 02's `ingest_p2_handoff_gates.py`):

```
# PIKMIN2_LANE04_DEEPSEEK_HANDOFF.md
44 BlueKochappy (role=source):
  advances: identity_spawn
  blocking (admission_requirements): identity_spawn:injected, movement_animation, attacks_receivers, death_corpse, cleanup_reentry, transport_reward
45 YellowKochappy (role=source):
  advances: identity_spawn
  blocking (admission_requirements): movement_animation, attacks_receivers, death_corpse, cleanup_reentry, transport_reward
```

Both identities advance `identity_spawn` from this handoff. The `identity_spawn:injected`
on 44 is the roster's own lane-13 annotation (44's `eligibility_reason` carries
"P1-host AI"), not a refusal of this handoff's cited natural spawn — 45 has a
clean reason so its `identity_spawn` is fully un-flagged.

### (3) Carry-forward fixes

- Added `test_validator_flips_when_second_generator_ready_stripped` (strip
  211002's READY from the two-generator log → False), matching the integrator's
  "every resolving generator must close" change.
- Removed the unused `import re` in `scripts/run_p2_seed_placement.py`.
- Removed the unused `ARENA_SOURCE_GENERATOR` in
  `experimental/pikmin2_seed_placement.py`.
- The run ends by timeout as expected (`exit=timeout`); slice 5 showed only
  source 44, this slice shows both 44 and 45.

### Build evidence (clean)

```
2026-09-14T23:22:04 lane=l04 target=pikmin_pc native=1dd030a7cefd9b60ad0d190aa50b03a7ed25f879 dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l04-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l04-build\bin\nectar.exe sha256=c690981f3db4fcf5fecbee7b0e7c7cfd6ed4878954d6fc68539e68aec8d62086 ninja_n="ninja: no work to do." seconds=0
```

### Tests (PIKMIN_NATIVE_ROOT only)

```
PIKMIN_NATIVE_ROOT=C:/Users/alari/pikmin-randomizer/output/dsw/native-l04 py -3.12 -m pytest tests/test_p2_seed_placement_native.py -q
11 passed
```

### Commits (this slice)

- Native: `1dd030a7cefd9b60ad0d190aa50b03a7ed25f879`
  `lane04: Snow P2_ENEMY_READY carries source_id=45 (#440)`
- Root: (this slice's code + handoff, one commit plus the handoff follow-up).

### One exact reproduction command

```
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l04 -- \
  py -3.12 scripts/run_p2_cohort_seed_placement.py \
    --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" \
    --bank "C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-bank" \
    --profile "C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-ref" \
    --snow "C:/Users/alari/pikmin-randomizer/output/p2-cohort-mixed-arena/4a4626c5a6844c4884e4a40224c6caa4" \
    --exe "C:/Users/alari/pikmin-randomizer/output/dsw/native-l04-build/bin/nectar.exe" \
    --output "C:/Users/alari/pikmin-randomizer/output/dsw/l04-out" \
    --seed p2-cohort-seed-placement-live
```
(run from `C:/Users/alari/pikmin-randomizer/output/dsw/l04-root`.)

## Subagent usage (slice 6)

Slice 6 was done solo (the brief did not mandate subagents): the work was one
native one-line source-id fix, one new runner reusing the existing mixed-bulborb
stager, the carry-forward test/import cleanups, and the gate-table formatting.

## Slice 7

Bounded slice: **ordinary generated-spawn placement evidence at native birth.**

Real consumer: Snow/Dwarf Orange cohort, source IDs `45 YellowKochappy` and
`44 BlueKochappy`, exercised end-to-end through an injected generated-seed
cohort, the ENEMY_P2/bootstrap binding, and ordinary `GenObjectTeki::birth`
placement. Missing slice from the ledger: **ordinary spawn binding** backed by
accepted native XYZ/terrain and carry-return-route evidence.

### Native implementation

- Factored one shared read-only placement sampler into
  `pc_port/pc_p2_placement_probe.{h,cpp}` and added
  `pc_p2_placement_probe_birth(...)`.
- Added a six-line, separately committed additive hook in
  `src/plugPikiNakata/genteki.cpp`. It calls the probe only after lane 03's
  resolved `uid` is known, only when that uid is nonzero, and mutates no
  gameplay state.
- When the P2 seed bridge is active, the room-preview scan no longer re-emits
  one marker per actor; the log explicitly records
  `P2_PLACEMENT_PROBE actors=0 evidence_slots=0 source=birth_hook`. This
  preserves ordinary birth reporting while avoiding duplicate evidence for the
  same generated spawn.

### Root implementation

- `scripts/run_p2_cohort_seed_placement.py` now preserves and reports the real
  `placement_probe_summary` line as well as individual placement, resolve, and
  ready lines.
- `tests/test_p2_placement_probe.py` has a focused regression proving that a
  `source=birth_hook` summary does not create an unmapped generator entry and
  does not disturb the existing generator→catalog-slot join.

The unused parallel validator and tests created by this slice's test-scaffolding
subagent were **not** merged: that draft used a different record grammar and
unsupported Snow home-anchor/helper assumptions. The implementation instead
reuses `randomizer/p2_placement_probe.py`.

### Runtime evidence

Fresh generated mixed-arena run:

`output/dsw/l04-out/f3cf40cd8df943c6ac14d705267442a9/native.log`

The real log contains exactly one mapped placement marker per generated
Snow/Dwarf Orange actor:

```text
P2_SEED_RESOLVE source_id=44 target=513430982 original_type=3 x=-150.0 z=1850.0
P2_PLACEMENT_SLOT generator=211001 slot=513430982 actor=3 xyz=1 terrain=ground route=1 route_distance=61.2 x=-150.000 y=30.000 z=1850.000 water_depth=0.00
P2_SEED_RESOLVE source_id=45 target=5465461 original_type=3 x=-150.0 z=1700.0
P2_PLACEMENT_SLOT generator=5001 slot=5465461 actor=3 xyz=1 terrain=ground route=1 route_distance=80.9 x=-150.000 y=30.000 z=1700.000 water_depth=0.00
P2_ENEMY_READY species=YellowKochappy source_id=45 native_family=Chappy generator=5001 behavior=P1
P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001 x=-150.0000000 y=30.0000000 z=1850.0000000 health=250.0 max_health=250.0 behavior=P1 purple_stun=bluekochappy_5s
P2_PLACEMENT_PROBE actors=0 evidence_slots=0 source=birth_hook
```

The runtime report says `validate_cooccurrence.ok=true` for both mapped
Snow/Dwarf Orange triples.

Fixture adoption: mixed-arena manifest stages Orange `211001`, Snow `5001`, P1
control `211002`, and 20 reds; the log records a 960×540 initialized and
centered window. It also records both live Snow/Orange banks and `corpse=0`
draws. No extinction-screen marker is reported. The generated cohort/admission
setup is injected and is not a production admission claim. The process was
retired by the fixture timeout after markers were collected.

### Six arena gates

| Gate | Result | Label |
|---|---|---|
| 1. Exact identity and spawn | PASS | Natural ordinary generated births for sources 45 and 44; P2 banks staged and bind markers observed |
| 2. Autonomous movement/animation | UNTESTED | Family/lane-13 scope |
| 3. Attacks/receivers | Source-backed N/A | Lanes 10/13 |
| 4. Death/corpse | Source-backed N/A | Lanes 06/07 |
| 5. Actual transport/reward | Source-backed N/A | Lane 06; only a natural carry-corridor origin is shown |
| 6. Cleanup/re-entry | UNTESTED | Lane 07 |

### Branches, interfaces, and commits

- Root branch: `deepseek/p2-l04`; root base:
  `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`.
- Native branch: `deepseek/p2-l04-native`; native base:
  `b805d9c626e4f4558c95aef7cac311a5d9a2068f`.
- Both branches are clean after the commits below.
- Root implementation commit:
  `efd1875b758b72315c0edc79c9ba75ed775da617`
  `lane04: record birth-hook placement evidence and add bridge-source regression test (#440)`.
- Native lane-owned module commit:
  `fe5088d6289c99ac245f69e1bca1c9033f727241`
  `lane04: factor shared placement sampler and add campaign birth entry (#440)`.
- Native shared-hook commit:
  `5178f598d9cb92943d622fa525c541b5ffe3a0d7`
  `lane04: hook generated Teki births into placement evidence (#440)`.
- Root-side code changes only add the runner report field and a focused parser
  regression. This handoff document is the follow-up root commit.
- Consumer/interface agreements: lane-03 supplied the resolved slot uid and
  source at birth; lane-13 supplied the configured Snow/Dwarf Orange generators
  and banks; lane-04 only reads those contracts. No seed-serialization,
  family-AI, reward, save, receiver, or shared-semantics edits were made.
- No GitHub issue write was made: tracking is #440, and integration posts
  updates after review, as this brief requires.

### Build

`output/dsw/l04-build-evidence.txt`:

```text
2026-09-15T16:47:23 lane=l04 target=pikmin_pc native=5178f598d9cb92943d622fa525c541b5ffe3a0d7 dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l04-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l04-build\bin\nectar.exe sha256=513990ffe61514a14045d6861a350807f3a9c37744686511b5a5c8aa34fe44ef ninja_n="ninja: no work to do." seconds=102
```

### Tests

```text
py -3.12 -m pytest tests/test_p2_placement_probe.py tests/test_p2_seed_placement_native.py tests/test_p2_placement_audit.py tests/test_p2_seed_placement.py tests/test_p2_placement_native.py tests/test_p2_placement.py -q
101 passed, 2 skipped, 17 subtests passed in 0.64s
```

The two skips are the existing `PIKMIN_NATIVE_ROOT`-guarded native source-pin
tests:

```text
PIKMIN_NATIVE_ROOT=C:/Users/alari/pikmin-randomizer/output/dsw/native-l04 py -3.12 -m pytest tests/test_p2_seed_placement_native.py -q
11 passed in 0.08s
```

### Assumptions

- The generated arena remains engineered: coordinate/scatter, overlay,
  sidecar pairs, and bootstrap are fixture staging, so this is ordinary-spawn
  placement evidence rather than untouched-campaign traversal.
- The public admitted roster remains deny-by-default; the generated seed cohort
  is injected/test-only and not an admission claim.
- `route=1` means a sampled carry-corridor origin within 200 units, not proof of
  a completed corpse path or reward.
- P1-derived AI/animation remains as already owned by lane 13; only placement
  sampling and readiness evidence are in lane-04 scope.

### Remaining blockers

- Full untouched production campaign traversal and placement collection remain
  with lane 01 integration and family/QA acceptance.
- Natural combat, damage/receivers, death/corpse, actual transport/reward,
  cleanup/re-entry, persistence, and whole-cohort completion belong to lanes
  13, 06/07, 10/11/12, 33, and lane 02 admission.

### One exact reproduction command

```text
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l04 -- py -3.12 scripts/run_p2_cohort_seed_placement.py --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" --bank "C:/Users/alari/pikmin-randomizer/output/dsw/l05-out/slice5/cohort44/content/BlueKochappy/bank" --profile "C:/Users/alari/pikmin-randomizer/output/dsw/l05-out/slice5/cohort44/content/BlueKochappy/profile" --snow "C:/Users/alari/pikmin-randomizer/output/dsw/l05-out/slice4-snow/session/runs/0af4813f692d8dd009931be69b6e5339fe3781e2e96d449af4fe426506aec812" --exe "C:/Users/alari/pikmin-randomizer/output/dsw/native-l04-build/bin/nectar.exe" --output "C:/Users/alari/pikmin-randomizer/output/dsw/l04-out" --seed p2-cohort-seed-placement-live
```

Run from `C:/Users/alari/pikmin-randomizer/output/dsw/l04-root`.

### Subagent usage

- Source audit (`explore`): used as-is for exact identities, numeric
  Snow/Dwarf parameters, water/home/helper bounds, and source-backed placement
  limits. It also guided the consumer-local scope and avoided new family FSM
  work.
- Existing-candidate inventory (`explore`): used as-is to identify the
  integrated probe/parser/runner contracts and the correct additive insertion
  points, avoiding reimplementation.
- Test/harness scaffolding (`general`): corrected/discarded. It produced two
  untracked helper files and reported seven passes, but its marker grammar and
  assumptions conflicted with the integrated placement-evidence contract, so
  those files were removed before commit. That delegation cost a small amount of
  reconciliation time while helping confirm the integrated parser was the right
  place to extend.

