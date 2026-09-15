# Lane 11 (Species/Bulbmin) — DeepSeek handoff

Parent [#131](https://github.com/4laric/pikmin-randomizer/issues/131);
checkpoint tracking [#112](https://github.com/4laric/pikmin-randomizer/issues/112).
Implementation owner: Codex through shared `4laric`; executing session/agent:
DeepSeek (lane 11, `dsw/l11-root` / `dsw/native-l11`).

## Slice delivered

**Source IDs owned / inspected:** Bulbmin = species 5
(`include/Game/Piki.h:54`), Mother Bulbmin = LeafChappy/KumaChappy
(`include/Game/Entities/LeafChappy.h:7,12`). Related inspected species files:
Purple/White modules (unchanged).

**Concrete slice:** reconcile recruitment with checkpoint schema by closing the
one live-wiring gap in the "identity storage → capability routing → recruitment →
checkpoint schema" series. The lane already had identity (species 5), the hazard
capability matrix, the whistle→recruited recruitment path and the schema-3 wire
format, but **`pc_p2_bulbmin_transition` had no live engine caller** and the
actual cave checkpoint wrote *every* surviving Bulbmin (wild or not). The source
`PikiMgr::caveSaveAllPikmins` / `saveAllPikmins` filter
(`src/plugProjectKandoU/pikiMgr.cpp:723,762`) never saves a wild (unwhistled)
Bulbmin. This slice adds that source-faithful rule to the live checkpoint.

## Ordered commits

Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`; native base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`. Both clean at handoff.

| Branch | Commit | Subject |
|---|---|---|
| native `deepseek/p2-l11-native` | `f16fa173f75cf63c4fe6fd6f15fd2f2b1741f6be` | lane11: source-faithful Bulbmin cave save filter (wild dependents never saved) (#131) |
| root `deepseek/p2-l11` | `76aa6b345fcbbcaf4c8f3b917dc6466d9bc689fa` | lane11: cave-filter contract test (wild Bulbmin never saved) (#131) |

Dirty state: none (both clean).

## Interfaces / hooks touched and why

Native `pc_p2_*` modules plus one narrow, separately reviewable cave hook:

- `pc_port/pc_p2_bulbmin_policy.h` — new engine-free `inline bool
  p2_bulbmin_should_save(int species, int phase)`, the source predicate mirrored
  over the port's species/phase representation (wild → never save).
- `pc_port/pc_p2_bulbmin.h/.cpp` — new `pc_p2_bulbmin_phase(const Piki*)`
  (`-1`/`P2BulbminWild`/`P2BulbminRecruited`) and
  `pc_p2_bulbmin_should_save(const Piki*, bool isExitingCave)`. Reads the live
  bridge ledger; inert unless `pc_p2_bulbmin_active()` (default off).
- `pc_port/pc_p2_cave.cpp` — additive hook in `pc_p2_cave_checkpoint`: a wild
  Bulbmin dependent is excluded from the checkpoint squad and the run logs
  `P2_CAVE_BULBMIN_FILTER wild=N recruited=M dropped=D kept=K exiting=0|1`.
  No behavior change with no opt-in config.
- `CMakeLists.txt` — add `bulbmin_cave_filter` to the engine-free `-UNDEBUG`
  contract-test foreach (target `p2_bulbmin_cave_filter_test`).
- `tools/test_p2_bulbmin_cave_filter.cpp` — new standalone gate
  `PASS P2_BULBMIN_CAVE_FILTER`.

Root: `tests/test_pikmin2_bulbmin_cave_filter.py` (compile-and-run gate + source
wiring assertions + pure-Python source-rule contract).

No shared engine file (`teki.h`, `tekiinteraction.cpp`, `tekibteki.cpp`,
`tekimgr.cpp`, `gameCoreSection.cpp`, `navi.cpp`, `pc_p2_preview.cpp`) was
edited; `pc_p2_cave.cpp` (a lane-11-owned Bulbmin carrier per #131 history)
received only the additive filter hook.

## Build evidence (`output/dsw/l11-build-evidence.txt`)

- `pikmin_pc` build: `[603/603] Linking CXX executable bin\nectar.exe` (exit 0);
  `ninja -n` → `ninja: no work to do.`
- `nectar.exe` SHA-256 `e00c73c0fcd1a3c67d6d99398df921f397e25ca27f67c10b2e3c6ce7d30324c4`.
- Config: Ninja + MinGW g++ 16.2.0, Release, `PIKMIN_NATIVE_JAUDIO=ON`.
- Evidence line was captured while the tree was still dirty (the same content
  that is now commit `f16fa173`); a clean-label re-run was attempted but the
  host-wide build semaphore (LIMITS build=2) was fully occupied by concurrent
  lanes across the session. Verified in the built image regardless:
  `nm -C` shows `T pc_p2_bulbmin_phase(Piki const*)` and
  `pc_p2_bulbmin_should_save(Piki const*, bool)`, and `strings` shows the
  `P2_CAVE_BULBMIN_FILTER ...` literal.

## Fixture adoption evidence

Not exercised this slice: a live GL arena was deliberately not run because the
slice is a cave-persistence/policy slice, not a combat/actor slice, and the only
way to produce a live wild dependent is a real Mother Bulbmin (LeafChappy)
actor, which the port still lacks (see blockers). The current 960×540 centred
window and live starting-Pikmin overlay were therefore **not** re-verified in a
new run here — the prior lane-11 checkpoint-restart evidence and the other
lanes' this-wave runs cover that baseline. No extinction-screen or fabricated
run is claimed.

## Six arena gates (Bulbmin cave persistence slice)

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | source-backed N/A this slice (identity unchanged) | species 5 wired via `pc_p2_species`/`pc_p2_make_bulbmin`; no new spawn path |
| 2. Autonomous movement + animation | source-backed N/A this slice | no mother actor |
| 3. Attacks / receivers | source-backed N/A this slice | hazard immunity already runtime-proven by lane 10/14 (`interactBattle.cpp`, ElecBug Denki) |
| 4. Death + corpse | source-backed N/A this slice | Bulbmin death is ordinary Piki death; unchanged |
| 5. Transport + reward | source-backed N/A this slice | Bulbmin are not carried/rewarded |
| 6. Cleanup + re-entry | **PASS (contract/build), live-drop BLOCKED** | `PASS P2_BULBMIN_CAVE_FILTER`; `p2_bulbmin_should_save` linked into `nectar.exe`; live wild-drop needs a mother actor |

Labels: the filter predicate and the cave hook are pure source logic (no
injected health/state). The `PASS P2_BULBMIN_CAVE_FILTER` is a compile-and-run
contract gate, **not** a gameplay PASS; a live wild-dependent drop was not
observed because no Mother Bulbmin actor exists to birth a wild dependent.

## Subagent usage

- **explore #1 (source audit)** — extracted the exact `pikiMgr.cpp:722-725/762`
  save-filter predicate, `LeafChappy.cpp:131-152` birth loop, and
  `interactPiki.cpp` whistle/immunity lines. Used as-is; it pinned the filter to
  `(kind != Bulbmin || isPikmin())` and confirmed `isPikmin()` is false for wild.
- **explore #2 (candidate inventory)** — found the key gap (`pc_p2_bulbmin_transition`
  has no live caller) and the full caller map, plus the PASS banners. Used as-is;
  it directly selected this slice's target.
- **general #3 (pytest scaffolding)** — wrote `tests/test_pikmin2_bulbmin_cave_filter.py`
  with skip-if-absent semantics. Used as-is; after I landed the native code it
  ran 4/4. It also caught that `native-l11` already existed (so tests 2/3 assert
  on content, not file presence).

Net: the audits selected the slice and removed ~40 min of manual grep/read; the
scaffold removed the test-authoring pass. No result was discarded; none was used
to falsify evidence.

## Tests run

```
py -3.12 -m pytest tests/test_pikmin2_bulbmin_cave_filter.py -q        -> 4 passed
py -3.12 -m pytest tests/test_pikmin2_bulbmin_{bridge,mother,cave_filter}.py \
                    tests/test_pikmin2_cave_transfer.py \
                    tests/test_pikmin2_campaign_bulbmin.py \
                    tests/test_pikmin2_lanes_1012_policies.py \
                    tests/test_pikmin2_cave_restart_runtime.py -q
        -> 34 passed, 1 skipped, 1 failed
```

The one failure is **pre-existing and unrelated to this slice**:
`test_pikmin2_lanes_1012_policies.py::test_elemental_receivers_consult_species_capability_matrix`
asserts `p2_species_immune(pc_p2_species(piki), P2HazardElectric)` appears in
`interactBattle.cpp`, but the electric/gas receivers were already migrated to
`p2_hazard_reaction(pc_p2_species(piki), P2HazardElectric, …)` in a prior sweep
(`PIKMIN2_RECEIVER_PATHS.md` §9). This slice does not touch `interactBattle.cpp`;
the test is stale against the current base and is left for the receivers lane.

## Assumptions

- On the port, "wild" is represented only by a tracked dependent in the live
  `P2BulbminFlock`; an injected/restored Bulbmin (not in the ledger) is treated
  as already-whistled (`isPikmin()`), so it is carried. This mirrors the source
  flag semantics (`FPFLAGS_IsWildBulbmin` only set at mother birth).
- The source's exit-only drop (a Bulbmin never *leaves* the cave) is deferred:
  the preview has no surface-rebirth target to convert a carried Bulbmin into.
  `pc_p2_bulbmin_should_save` takes `isExitingCave` and logs `exiting=` so a
  future surface path can enforce it; the current filter drops wild dependents
  only. Documented deviation, not a bug.
- A standalone `g++` compile of the contract test is equivalent to the CTest
  target for establishing the predicate (the CTest registration is additive and
  will run in integration's CTest sweep).

## Remaining blockers (named provider)

- **Natural Mother Bulbmin (LeafChappy/KumaChappy actor + `piki_kochappy`
  model):** still missing; a live wild-dependent birth and therefore the live
  wild-drop observation is blocked on the Chappy-family actor lane (lane 13,
  #120) providing a real Bulbmin/mother actor. The existing Kochappy registration
  is only a labelled proxy.
- **Production cave placement / surface roundtrip:** cave lane (#112/#114).
- The stale receivers test above: receivers lane (#408) should refresh the
  `p2_hazard_reaction` assertion.

## Exact reproduction

```powershell
$env:PYTHONUTF8='1'
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
py -3.12 -m pytest tests/test_pikmin2_bulbmin_cave_filter.py -q
```

(Standalone native contract gate, without the GL slot:
`C:\msys64\mingw64\bin\g++.exe -std=c++17 -Wall -Wextra -I pc_port tools/test_p2_bulbmin_cave_filter.cpp -o cf.exe && cf.exe`
→ `PASS P2_BULBMIN_CAVE_FILTER`.)
